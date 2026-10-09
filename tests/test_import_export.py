"""Export and import: what the file holds, the round trip, the preview, undo, and hostile files.

Run:   python tests/test_import_export.py          (BROWSERS=firefox to run one engine)
"""
import tempfile
from harness import *

PREVIEW = "Importere middagsplan?"
FREEZER = [{"id": "f1", "name": "Eksport-rett", "emoji": "🍲", "protein": "kylling", "remaining": 3, "total": 4,
            "cookedAt": "2026-10-01", "freezerLifeDays": None}]


def first_plan_name(page):
    plan = ls(page, "plan") or []
    return (plan[0][0] or {}).get("name") if plan and plan[0] and plan[0][0] else None


def write_temp(content, suffix=".json"):
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(content if isinstance(content, str) else json.dumps(content))
    f.close()
    return f.name


def import_file(page, path):
    go(page, "settings")
    page.set_input_files("input[type=file]", path)
    page.wait_for_timeout(500)


def core(browser, tag):
    # ── Export: the user's data, never their credentials ─────────────────
    seed = {**CREDS, "googleClientSecret": "topp-hemmelig", "anthropicKey": "sk-ant-hemmelig",
            "kassalKey": "kassal-hemmelig", "driveToken": VALID,
            "weeks": 1, "portions": 4, "plan": plan_with("Eksport-rett"),
            "freezerItems": FREEZER, "mealNotes": {"Eksport-rett": "husk lime"}}
    ctx, page, errors = open_app(browser, seed, path="#settings")
    with page.expect_download() as dl:
        click(page, "⬇ Eksporter plan (.json)")
    text = Path(dl.value.path()).read_text(encoding="utf-8")
    data = json.loads(text)
    check(f"[{tag}] export holds the plan", (data.get("plan") or [[{}]])[0][0].get("name") == "Eksport-rett")
    check(f"[{tag}] export holds freezer and notes",
          len(data.get("freezerItems") or []) == 1 and (data.get("mealNotes") or {}).get("Eksport-rett") == "husk lime")
    check(f"[{tag}] export is dated", bool(data.get("exportedAt")))
    leaks = [s for s in ("sk-ant-hemmelig", "topp-hemmelig", "kassal-hemmelig", "access_token", "refresh_token") if s in text]
    check(f"[{tag}] export contains no keys or tokens", not leaks, str(leaks))
    check(f"[{tag}] export leaves the recipe cache out", "recipeCache" not in data)
    export_path = write_temp(text)
    ctx.close()

    # ── Round trip into a fresh browser ──────────────────────────────────
    ctx, page, errors = open_app(browser, {"anthropicKey": "sk-ant-mine"})
    import_file(page, export_path)
    check(f"[{tag}] import shows a preview first", shown(page, PREVIEW))
    check(f"[{tag}] nothing changes before 'Importer'", first_plan_name(page) is None)
    click(page, "Importer", exact=True)
    wait_until(page, lambda: first_plan_name(page) == "Eksport-rett")
    check(f"[{tag}] round trip restores the plan", first_plan_name(page) == "Eksport-rett")
    check(f"[{tag}] round trip restores freezer and notes",
          len(ls(page, "freezerItems") or []) == 1 and (ls(page, "mealNotes") or {}).get("Eksport-rett") == "husk lime")
    check(f"[{tag}] import keeps this browser's own API key", ls(page, "anthropicKey") == "sk-ant-mine")
    check(f"[{tag}] round trip: no page errors", not errors, "; ".join(errors))
    ctx.close()

    # ── Cancel changes nothing; undo restores what was replaced ──────────
    mine = {"anthropicKey": "sk-ant-mine", "weeks": 1, "plan": plan_with("Min plan")}
    ctx, page, errors = open_app(browser, mine)
    import_file(page, export_path)
    click(page, "Avbryt", exact=True)
    page.wait_for_timeout(300)
    check(f"[{tag}] Avbryt leaves the plan alone", first_plan_name(page) == "Min plan" and not shown(page, PREVIEW))
    import_file(page, export_path)
    click(page, "Importer", exact=True)
    wait_until(page, lambda: first_plan_name(page) == "Eksport-rett")
    check(f"[{tag}] 'Angre siste import' is offered", page.get_by_role("button", name="↶ Angre siste import").count() == 1)
    click(page, "↶ Angre siste import")
    restored = wait_until(page, lambda: first_plan_name(page) == "Min plan")
    check(f"[{tag}] undo brings the replaced plan back", restored, str(first_plan_name(page)))
    ctx.close()

    # ── A file carrying credentials can't plant them ─────────────────────
    hostile = write_temp({"weeks": 1, "plan": plan_with("Fra fil"), "anthropicKey": "sk-ant-evil",
                          "googleClientSecret": "evil", "googleClientId": "evil-id", "driveToken": VALID})
    ctx, page, errors = open_app(browser, {"anthropicKey": "sk-ant-mine"})
    import_file(page, hostile)
    click(page, "Importer", exact=True)
    wait_until(page, lambda: first_plan_name(page) == "Fra fil")
    check(f"[{tag}] imported data applied", first_plan_name(page) == "Fra fil")
    check(f"[{tag}] imported API key is ignored", ls(page, "anthropicKey") == "sk-ant-mine")
    check(f"[{tag}] imported Google credentials and token are ignored",
          ls(page, "googleClientSecret") in (None, "") and ls(page, "googleClientId") in (None, "") and ls(page, "driveToken") is None)
    ctx.close()

    # ── Broken and malformed files ───────────────────────────────────────
    ctx, page, errors = open_app(browser, {"weeks": 1, "plan": plan_with("Min plan")})
    import_file(page, write_temp("dette er ikke json {"))
    check(f"[{tag}] a non-JSON file is refused with a message", shown(page, "Kunne ikke lese filen"))
    import_file(page, write_temp({"foo": 1}))
    check(f"[{tag}] a file with no plan data is refused", shown(page, "Filen inneholder ingen middagsplan-data."))
    import_file(page, write_temp({"weeks": 5, "plan": "x", "portions": -3}))
    if shown(page, PREVIEW):
        click(page, "Importer", exact=True)
        page.wait_for_timeout(500)
    check(f"[{tag}] a malformed file can't crash the app", not shown(page, "Noe gikk galt") and not errors, "; ".join(errors))
    check(f"[{tag}] malformed values are clamped", 1 <= (ls(page, "weeks") or 0) <= 4 and 1 <= (ls(page, "portions") or 0) <= 20,
          f"weeks={ls(page, 'weeks')} portions={ls(page, 'portions')}")
    ctx.close()

    # ── Different portions in the file: cached recipes stay labelled with their own scale ──
    recipe = {"components": [{"name": "Gryte", "ingredients": ["500 g kylling"]}], "steps": ["Kok"],
              "nutrition": {"calories": 400}, "activeMins": 20, "passiveMins": 30}
    ctx, page, errors = open_app(browser, {"weeks": 1, "portions": 4, "units": "metric",
                                           "plan": plan_with("Kyllinggryte"), "recipeCache": {"Kyllinggryte": recipe}})
    import_file(page, write_temp({"weeks": 1, "portions": 6, "plan": plan_with("Kyllinggryte")}))
    click(page, "Importer", exact=True)
    wait_until(page, lambda: ls(page, "portions") == 6)
    entry = (ls(page, "recipeCache") or {}).get("Kyllinggryte") or {}
    check(f"[{tag}] 4-portion recipe keeps its 4|metric label after a 6-portion import",
          entry.get("scale") == "4|metric", f"scale={entry.get('scale')}")
    go(page, "plan")
    check(f"[{tag}] … and is not used at 6 portions", shown(page, "Last alle oppskrifter"))
    ctx.close()


# Render crash on demand: once window.__crash is set, any date formatting throws. The freezer view formats
# its batch dates, so opening it after setting the flag drops the app into the ErrorBoundary.
CRASH_INIT = """(() => { const orig = Date.prototype.toLocaleDateString;
  Date.prototype.toLocaleDateString = function (...a) {
    if (window.__crash) throw new Error('test crash'); return orig.apply(this, a); }; })();"""


def rescue_download(browser, tag):
    """The crash screen's download must be an importable backup without credentials (template gap e)."""
    seed = {**CREDS, "googleClientSecret": "topp-hemmelig", "anthropicKey": "sk-ant-hemmelig",
            "driveFileId": "file9", "driveSyncedHash": "abc", "weeks": 1,
            "plan": plan_with("Redning"), "freezerItems": FREEZER}
    raw = {"mp_mealNotes": "{ødelagte notater",          # user data: lsGet keeps it as mp_mealNotes_corrupt
           "mp_preImportBackup": "{ødelagt backup"}     # not rewritten by the app, so it stays unreadable
    ctx, page, errors = open_app(browser, seed, raw=raw, init=CRASH_INIT)
    page.evaluate("window.__crash = true")
    go(page, "fryser")
    crashed = wait_until(page, lambda: shown(page, "Noe gikk galt"))
    check(f"[{tag}] rescue: the crash screen appears", crashed)
    with page.expect_download() as dl:
        click(page, "Last ned data (.json)")
    text = Path(dl.value.path()).read_text(encoding="utf-8")
    data = json.loads(text)
    check(f"[{tag}] rescue: holds the plan and freezer",
          (data.get("plan") or [[{}]])[0][0].get("name") == "Redning" and len(data.get("freezerItems") or []) == 1)
    check(f"[{tag}] rescue: is dated", bool(data.get("exportedAt")))
    leaks = [s for s in ("sk-ant-hemmelig", "topp-hemmelig", '"googleClientId"', '"anthropicKey"') if s in text]
    check(f"[{tag}] rescue: no keys or credentials", not leaks, str(leaks))
    check(f"[{tag}] rescue: no Drive bookkeeping", not any(k in data for k in ("driveFileId", "driveSyncedHash")),
          str([k for k in data if k.startswith("drive")]))
    unreadable = data.get("unreadable") or {}
    check(f"[{tag}] rescue: an unreadable value is kept as text, not dropped",
          unreadable.get("preImportBackup") == "{ødelagt backup", str(unreadable)[:100])
    check(f"[{tag}] rescue: a kept rescue copy is included", unreadable.get("mealNotes") == "{ødelagte notater")
    path = write_temp(text)
    ctx.close()

    ctx, page, errors = open_app(browser, {"anthropicKey": "sk-ant-mine"})
    import_file(page, path)
    check(f"[{tag}] rescue file: Import accepts it", shown(page, PREVIEW))
    click(page, "Importer", exact=True)
    restored = wait_until(page, lambda: first_plan_name(page) == "Redning")
    check(f"[{tag}] rescue file: the plan and freezer come back",
          restored and len(ls(page, "freezerItems") or []) == 1)
    check(f"[{tag}] rescue file: no page errors", not errors, "; ".join(errors))
    ctx.close()


def envelope_import(browser, tag):
    """A backup in the template's {version, data} envelope imports too."""
    ctx, page, errors = open_app(browser, {"weeks": 1, "plan": plan_with("Min plan")})
    import_file(page, write_temp({"version": 1, "exportedAt": "2026-10-01T10:00:00.000Z",
                                  "data": {"weeks": 1, "plan": plan_with("Fra konvolutt")}}))
    check(f"[{tag}] envelope: Import shows the preview", shown(page, PREVIEW))
    click(page, "Importer", exact=True)
    check(f"[{tag}] envelope: the wrapped plan is imported", wait_until(page, lambda: first_plan_name(page) == "Fra konvolutt"),
          str(first_plan_name(page)))
    ctx.close()


def run(browser, tag):
    scenario(tag, "export and import", lambda: core(browser, tag))
    scenario(tag, "rescue download", lambda: rescue_download(browser, tag))
    scenario(tag, "envelope import", lambda: envelope_import(browser, tag))


if __name__ == "__main__":
    main(run)
