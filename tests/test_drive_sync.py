"""Google Drive sync: the three-way decision and every path through doSync.

Google is replaced by FakeGoogle, so each test controls latency and failures and can assert exactly
what Drive ended up holding.

Run:   python tests/test_drive_sync.py          (BROWSERS=firefox to run one engine)
"""
from harness import *

CONFLICT = "Endringer både her og i Google Drive"


def first_plan_name(page):
    plan = ls(page, "plan") or []
    return (plan[0][0] or {}).get("name") if plan and plan[0] and plan[0][0] else None


def decide_sync_table(browser, tag):
    ctx, page, errors = open_app(browser)
    got = page.evaluate("""() => [
        decideSync('a', 'a', 'x', false),   // same on both sides
        decideSync('a', 'b', '',  true),    // no base, empty device: take Drive
        decideSync('a', 'b', '',  false),   // no base, device has content: ask
        decideSync('a', 'b', 'b', false),   // only this device changed
        decideSync('a', 'b', 'a', false),   // only Drive changed
        decideSync('a', 'b', 'c', false),   // both changed
    ]""")
    want = ["in-sync", "pull", "conflict", "push", "pull", "conflict"]
    check(f"[{tag}] decideSync covers every branch", got == want, f"got {got}")
    ctx.close()


def setup_conflict(browser, delay_media=0):
    """This device and Drive both changed since they last agreed (the base hash is stale)."""
    g = FakeGoogle()
    fid = g.add_file(drive_backup(plan=plan_with("Drive-rett")))
    g.delay["media"] = delay_media
    ctx, page, errors = open_app(browser, {**CREDS, "driveToken": VALID, "driveFileId": fid,
                                           "driveSyncedHash": "stale", "weeks": 1,
                                           "plan": plan_with("Lokal-rett")}, google=g)
    asked = wait_until(page, lambda: shown(page, CONFLICT), timeout=12)
    return g, fid, ctx, page, errors, asked


def defer_conflict(browser, tag, how):
    """Closing the conflict question without choosing must pick neither side (template gap d)."""
    g, fid, ctx, page, errors, asked = setup_conflict(browser)
    check(f"[{tag}] defer ({how}): the question was asked", asked)
    if how == "button":
        click(page, "Bestem senere")
    else:
        page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    check(f"[{tag}] defer ({how}): the question closes", not shown(page, CONFLICT))
    check(f"[{tag}] defer ({how}): a pause banner says sync is waiting", shown(page, "satt på pause"))
    page.get_by_role("button", name="2", exact=True).first.click()      # an edit while paused
    page.wait_for_timeout(3500)                                          # past the 2 s auto-save
    check(f"[{tag}] defer ({how}): nothing is uploaded while paused", not g.writes(), str(g.kinds()))
    check(f"[{tag}] defer ({how}): Drive keeps its own data", "Drive-rett" in json.dumps(g.content(fid).get("plan")))
    check(f"[{tag}] defer ({how}): this device keeps its own data", first_plan_name(page) == "Lokal-rett")
    page.evaluate("window.dispatchEvent(new Event('online'))")          # an automatic trigger
    page.wait_for_timeout(1500)
    check(f"[{tag}] defer ({how}): automatic checks don't reopen the question", not shown(page, CONFLICT))
    if how == "button":
        click(page, "Velg nå")
        reasked = wait_until(page, lambda: shown(page, CONFLICT))
        check(f"[{tag}] defer: 'Velg nå' asks again", reasked)
        click(page, "Behold denne enheten")
        wait_until(page, lambda: "patch" in g.kinds())
        saved = g.content(fid)
        check(f"[{tag}] defer: keeping this device uploads it, edits made while paused included",
              "Lokal-rett" in json.dumps(saved.get("plan")) and saved.get("weeks") == 2,
              f"weeks={saved.get('weeks')}")
        check(f"[{tag}] defer: the banner goes once it's resolved", not shown(page, "satt på pause"))
    check(f"[{tag}] defer ({how}): no page errors", not errors, "; ".join(errors))
    ctx.close()


def run(browser, tag):
    scenario(tag, "decideSync", lambda: decide_sync_table(browser, tag))
    scenario(tag, "sync paths", lambda: sync_paths(browser, tag))
    scenario(tag, "defer by button", lambda: defer_conflict(browser, tag, "button"))
    scenario(tag, "defer by Escape", lambda: defer_conflict(browser, tag, "Escape"))


def sync_paths(browser, tag):
    # ── First device: creates the one backup, then later edits PATCH it ───
    g = FakeGoogle()
    ctx, page, errors = open_app(browser, {**CREDS, "driveToken": VALID, "weeks": 1, "plan": plan_with("Lokal A")}, google=g)
    wait_until(page, lambda: "create" in g.kinds())
    check(f"[{tag}] first sync creates exactly one backup", g.kinds().count("create") == 1 and len(g.live_files()) == 1,
          str(g.kinds()))
    check(f"[{tag}] first sync records the file and the agreed hash",
          bool(ls(page, "driveFileId")) and bool(ls(page, "driveSyncedHash")))
    page.get_by_role("button", name="2", exact=True).first.click()      # UKE 1 → 2
    wait_until(page, lambda: "patch" in g.kinds())
    patches = [b for k, b in g.log if k == "patch"]
    check(f"[{tag}] a later edit is uploaded to the same file", bool(patches) and patches[-1].get("weeks") == 2,
          f"patches={len(patches)}")
    check(f"[{tag}] still one backup file", len(g.live_files()) == 1)
    check(f"[{tag}] first device: no page errors", not errors, "; ".join(errors))
    ctx.close()

    # ── Fresh device: takes Drive's data without asking ──────────────────
    g = FakeGoogle()
    g.add_file(drive_backup(plan=plan_with("Fra Drive")))
    ctx, page, errors = open_app(browser, {**CREDS, "driveToken": VALID}, google=g)
    pulled = wait_until(page, lambda: first_plan_name(page) == "Fra Drive")
    check(f"[{tag}] fresh device pulls Drive's plan", pulled, str(first_plan_name(page)))
    check(f"[{tag}] fresh device is not asked to choose", not shown(page, CONFLICT))
    check(f"[{tag}] fresh device creates no second file", len(g.live_files()) == 1)
    ctx.close()

    # ── Only Drive changed: pulled, no question ──────────────────────────
    g = FakeGoogle()
    ctx, page, errors = open_app(browser, {**CREDS, "driveToken": VALID, "weeks": 1, "plan": plan_with("Lokal A")}, google=g)
    wait_until(page, lambda: "create" in g.kinds())
    fid = next(iter(g.live_files()))
    g.replace(fid, drive_backup(plan=plan_with("Endret på mobilen")))
    go(page, "settings")
    click(page, "Synkroniser nå")
    pulled = wait_until(page, lambda: first_plan_name(page) == "Endret på mobilen")
    check(f"[{tag}] a change made on another device is pulled", pulled, str(first_plan_name(page)))
    check(f"[{tag}] pulling a remote-only change asks nothing", not shown(page, CONFLICT))
    ctx.close()

    # ── Both changed: ask, write nothing until answered, honour the answer ──
    conflict_setup = lambda delay_media=0: setup_conflict(browser, delay_media)
    g, fid, ctx, page, errors, asked = conflict_setup()
    check(f"[{tag}] both changed: the conflict dialog appears", asked)
    page.wait_for_timeout(3000)                                          # past the 2 s auto-save
    check(f"[{tag}] nothing is uploaded while the question is open", not g.writes(), str(g.kinds()))
    click(page, "Bruk Drive-versjonen")
    wait_until(page, lambda: first_plan_name(page) == "Drive-rett")
    check(f"[{tag}] 'Bruk Drive-versjonen' takes Drive's plan", first_plan_name(page) == "Drive-rett")
    check(f"[{tag}] … and never writes the local plan to Drive",
          not any("Lokal-rett" in json.dumps(w) for w in g.writes()))
    check(f"[{tag}] conflict (Drive): no page errors", not errors, "; ".join(errors))
    ctx.close()

    g, fid, ctx, page, errors, asked = conflict_setup()
    click(page, "Behold denne enheten")
    wait_until(page, lambda: "patch" in g.kinds())
    check(f"[{tag}] 'Behold denne enheten' uploads this device's plan",
          "Lokal-rett" in json.dumps(g.content(fid).get("plan")), str(g.kinds()))
    check(f"[{tag}] … and keeps it locally", first_plan_name(page) == "Lokal-rett")
    ctx.close()

    # Slow download: the auto-save timer fires before Drive's copy arrives, and must not upload
    g, fid, ctx, page, errors, asked = conflict_setup(delay_media=4)
    kinds = g.kinds()
    before = kinds[:kinds.index("media")] if "media" in kinds else kinds
    check(f"[{tag}] slow download: no upload before Drive's copy is compared",
          not any(k in ("patch", "create") for k in before), str(kinds))
    check(f"[{tag}] slow download: still asks", asked)
    ctx.close()

    # ── Token refresh fails transiently: keep the token, show the error, recover ──
    for mode in ("offline", "503"):
        g = FakeGoogle()
        g.token_mode = mode
        ctx, page, errors = open_app(browser, {**CREDS, "driveToken": EXPIRED, "weeks": 1, "plan": plan_with("Lokal A")},
                                     path="#settings", google=g)
        wait_until(page, lambda: shown(page, "Synkroniseringsfeil"))
        tok = ls(page, "driveToken")
        check(f"[{tag}] refresh {mode}: the refresh token is kept", bool(tok) and tok.get("refresh_token") == "rt", str(tok))
        check(f"[{tag}] refresh {mode}: the error is shown", shown(page, "Synkroniseringsfeil"))
        g.token_mode = "ok"
        click(page, "Synkroniser nå")
        check(f"[{tag}] refresh {mode}: recovers when Google answers again",
              wait_until(page, lambda: shown(page, "Synkronisert")), root_text(page)[-120:].replace("\n", " | "))
        ctx.close()

    # ── invalid_grant: access was revoked, so the token goes and the user is told ──
    g = FakeGoogle()
    g.token_mode = "invalid_grant"
    ctx, page, errors = open_app(browser, {**CREDS, "driveToken": EXPIRED}, path="#settings", google=g)
    expired = wait_until(page, lambda: shown(page, "Google-tilkoblingen er utløpt"))
    check(f"[{tag}] invalid_grant: 'utløpt' is shown", expired)
    check(f"[{tag}] invalid_grant: the token is cleared", ls(page, "driveToken") is None)
    ctx.close()

    # ── A trashed backup is never written to again ───────────────────────
    g = FakeGoogle()
    old = g.add_file(drive_backup(plan=plan_with("Gammel")), trashed=True)
    ctx, page, errors = open_app(browser, {**CREDS, "driveToken": VALID, "driveFileId": old, "weeks": 1,
                                           "plan": plan_with("Lokal A")}, google=g)
    wait_until(page, lambda: "create" in g.kinds())
    check(f"[{tag}] trashed backup: a new file is created", len(g.live_files()) == 1 and ls(page, "driveFileId") != old,
          str(g.kinds()))
    check(f"[{tag}] trashed backup: the trashed file is left alone", "Gammel" in json.dumps(g.content(old)))
    ctx.close()

    # ── A second tab that changes data blocks the stale one ──────────────
    ctx, page, errors = open_app(browser, {"weeks": 1, "plan": plan_with("Lokal A")})
    other = ctx.new_page()
    other.goto(URL + "#plan")
    other.wait_for_selector("text=Innstillinger", timeout=30000)
    page.get_by_role("button", name="2", exact=True).first.click()
    blocked = wait_until(other, lambda: shown(other, "Appen er endret i en annen fane"))
    check(f"[{tag}] the stale tab is blocked after another tab saves", blocked)
    check(f"[{tag}] the editing tab is not blocked", not shown(page, "Appen er endret i en annen fane"))
    ctx.close()


if __name__ == "__main__":
    main(run)
