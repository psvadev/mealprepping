"""Dialogs and Escape.

Run:   python tests/test_ui.py          (BROWSERS=firefox to run one engine)
"""
import tempfile
from harness import *

VARIANTS = {"meals": [MEAL(f"Lasagne {i}", batchScore=4) for i in range(3)]}


def picker_open(page):
    return shown(page, "Velg en rett")


def request_variants(page):
    page.get_by_placeholder("Legg til en rett manuelt…").fill("Lasagne")
    page.wait_for_timeout(200)   # let React commit the typed value before the click reads it
    page.get_by_role("button", name="Legg til", exact=True).click()


def escape_at_appearance(browser, tag):
    # The variant picker opens after a fetch, i.e. from an async (non-discrete) update, so React runs a
    # useEffect only in a later task. A MutationObserver fires in the microtask right after React commits
    # the dialog's DOM — the window in which a useEffect-registered handler is still the old one.
    # Moved from docs/audit-tests/test_template_gaps.py (template gap b, commit 2845517).
    ctx, page, errors = open_app(browser, {"weeks": 1, "anthropicKey": "sk-ant-test"},
                                 anthropic=FakeAnthropic(reply=VARIANTS))
    page.evaluate("""() => {
      const root = document.getElementById('root');
      const mo = new MutationObserver(() => {
        if (!root.textContent.includes('Velg en rett')) return;
        mo.disconnect();
        window.__escSent = true;
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      });
      mo.observe(root, { childList: true, subtree: true, characterData: true });
    }""")
    request_variants(page)
    page.wait_for_timeout(1200)
    sent = page.evaluate("!!window.__escSent")
    check(f"[{tag}] Escape pressed as a dialog appears closes it", sent and not picker_open(page),
          f"escape sent={sent}, still open={picker_open(page)}")
    ctx.close()
    # Control: an ordinary, later Escape — passes before and after the fix, so the check above isolates timing
    ctx, page, errors = open_app(browser, {"weeks": 1, "anthropicKey": "sk-ant-test"},
                                 anthropic=FakeAnthropic(reply=VARIANTS))
    request_variants(page)
    appeared = wait_until(page, lambda: picker_open(page))
    page.wait_for_timeout(300)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    check(f"[{tag}] (control) a later Escape closes it", appeared and not picker_open(page), f"appeared={appeared}")
    check(f"[{tag}] picker: no page errors", not errors, "; ".join(errors))
    ctx.close()


def escape_import_preview(browser, tag):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    f.write(json.dumps({"weeks": 1, "plan": plan_with("Fra fil")}))
    f.close()
    ctx, page, errors = open_app(browser, {"weeks": 1, "plan": plan_with("Min plan")}, path="#settings")
    page.set_input_files("input[type=file]", f.name)
    opened = wait_until(page, lambda: shown(page, "Importere middagsplan?"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    check(f"[{tag}] Escape cancels the import preview", opened and not shown(page, "Importere middagsplan?"),
          f"opened={opened}")
    check(f"[{tag}] … and imports nothing", (ls(page, "plan") or [[{}]])[0][0].get("name") == "Min plan")
    ctx.close()


def escape_batch_confirm(browser, tag):
    fz = [{"id": i, "name": f"Rett {i}", "emoji": "🍲", "protein": "kylling", "remaining": 2, "total": 4,
           "cookedAt": "2026-10-01", "freezerLifeDays": None} for i in ("a", "b")]
    ctx, page, errors = open_app(browser, {"weeks": 1, "freezerItems": fz}, path="#fryser")
    click(page, "Fjern batch")
    opened = wait_until(page, lambda: shown(page, "Fjerne hele batchen?"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    check(f"[{tag}] Escape cancels 'Fjerne hele batchen?'", opened and not shown(page, "Fjerne hele batchen?"),
          f"opened={opened}")
    check(f"[{tag}] … and removes nothing", len(ls(page, "freezerItems") or []) == 2)
    ctx.close()


def run(browser, tag):
    scenario(tag, "Escape race", lambda: escape_at_appearance(browser, tag))
    scenario(tag, "Escape import preview", lambda: escape_import_preview(browser, tag))
    scenario(tag, "Escape batch confirm", lambda: escape_batch_confirm(browser, tag))


if __name__ == "__main__":
    main(run)
