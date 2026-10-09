"""Local storage: an unreadable stored value is kept and offered back, never silently overwritten
(template gap c; the D16 leftover from the September audit).

Run:   python tests/test_storage.py          (BROWSERS=firefox to run one engine)
"""
from harness import *

BROKEN = {"mp_plan": "{ødelagt", "mp_freezerItems": "[1, 2"}
BANNER = "kunne ikke leses"


def raw(page, key):
    return page.evaluate(f"localStorage.getItem('{key}')")


def kept_and_offered(browser, tag):
    ctx, page, errors = open_app(browser, {"weeks": 1}, raw=BROKEN)
    page.wait_for_timeout(500)
    check(f"[{tag}] unreadable data: the app still starts", not shown(page, "Noe gikk galt") and not errors, "; ".join(errors))
    check(f"[{tag}] unreadable plan is kept verbatim", raw(page, "mp_plan_corrupt") == "{ødelagt", str(raw(page, "mp_plan_corrupt")))
    check(f"[{tag}] unreadable freezer is kept verbatim", raw(page, "mp_freezerItems_corrupt") == "[1, 2")
    check(f"[{tag}] the live key holds a readable default again", isinstance(ls(page, "plan"), list))
    check(f"[{tag}] a banner says what couldn't be read",
          shown(page, BANNER) and shown(page, "ukeplanen") and shown(page, "fryseren"))

    page.reload()
    page.wait_for_selector("text=Innstillinger", timeout=30000)
    check(f"[{tag}] after a reload the copy is still there", raw(page, "mp_plan_corrupt") == "{ødelagt")
    check(f"[{tag}] … and so is the banner", shown(page, BANNER))

    with page.expect_download() as dl:
        click(page, "Last ned kopien")
    saved = json.loads(Path(dl.value.path()).read_text(encoding="utf-8"))
    check(f"[{tag}] the download holds the raw text", (saved.get("unreadable") or {}).get("plan") == "{ødelagt",
          str(saved)[:120])

    click(page, "Slett kopien")
    page.wait_for_timeout(300)
    check(f"[{tag}] 'Slett kopien' removes the copies and the banner",
          raw(page, "mp_plan_corrupt") is None and raw(page, "mp_freezerItems_corrupt") is None and not shown(page, BANNER))
    click(page, "Angre", exact=True)
    page.wait_for_timeout(300)
    check(f"[{tag}] … and Angre brings them back", raw(page, "mp_plan_corrupt") == "{ødelagt" and shown(page, BANNER))
    check(f"[{tag}] unreadable data: no page errors", not errors, "; ".join(errors))
    ctx.close()


def only_user_data(browser, tag):
    # An unreadable setting (here the API key) just falls back; there is no user data to rescue
    ctx, page, errors = open_app(browser, {"weeks": 1}, raw={"mp_anthropicKey": "ikke json"})
    page.wait_for_timeout(500)
    check(f"[{tag}] an unreadable setting gets no copy", raw(page, "mp_anthropicKey_corrupt") is None)
    check(f"[{tag}] … and no banner", not shown(page, BANNER))
    ctx.close()


def copies_dont_block_tabs(browser, tag):
    ctx, page, errors = open_app(browser, {"weeks": 1})
    page.evaluate("window.dispatchEvent(new StorageEvent('storage', { key: 'mp_plan_corrupt', newValue: 'x' }))")
    page.wait_for_timeout(300)
    check(f"[{tag}] another tab saving a rescue copy doesn't block this one", not shown(page, "Appen er endret i en annen fane"))
    # Control: a real data key from another tab still blocks
    page.evaluate("window.dispatchEvent(new StorageEvent('storage', { key: 'mp_plan', newValue: '[]' }))")
    page.wait_for_timeout(300)
    check(f"[{tag}] (control) another tab saving the plan still blocks this one", shown(page, "Appen er endret i en annen fane"))
    ctx.close()


def run(browser, tag):
    scenario(tag, "kept and offered", lambda: kept_and_offered(browser, tag))
    scenario(tag, "only user data", lambda: only_user_data(browser, tag))
    scenario(tag, "tabs", lambda: copies_dont_block_tabs(browser, tag))


if __name__ == "__main__":
    main(run)
