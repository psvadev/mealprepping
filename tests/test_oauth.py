"""Google sign-in: Connect, and the redirect back with ?code= / ?error= (template gap f, audit S5).

Every exit of the callback must leave a clean URL and no single-use value behind, reject a response
that doesn't answer this app's own request, and say what went wrong in Settings.

Run:   python tests/test_oauth.py          (BROWSERS=firefox to run one engine)
"""
from urllib.parse import urlparse, parse_qs
from harness import *

OURS = {"drive_pkce_verifier": "verifier-1", "drive_oauth_state": "state-1"}


def stored(page, key):
    return page.evaluate(f"localStorage.getItem('{key}')")


def code_exchanges(g):
    return [1 for kind, grant in g.log if kind == "token" and grant == "authorization_code"]


def clean(page, tag, label):
    q = urlparse(page.url).query
    check(f"[{tag}] {label}: URL cleaned", not any(k in q for k in ("code=", "state=", "error=")), page.url)
    check(f"[{tag}] {label}: single-use values removed",
          stored(page, "drive_pkce_verifier") is None and stored(page, "drive_oauth_state") is None)


def told_in_settings(page, tag, label, text):
    page.wait_for_timeout(300)
    check(f"[{tag}] {label}: Settings explains it", page.evaluate("location.hash") == "#settings" and shown(page, text),
          f"hash={page.evaluate('location.hash')}")


def redirect(browser, query, raw=OURS, google=None):
    g = google or FakeGoogle()
    ctx, page, errors = open_app(browser, CREDS, raw=raw, path=query, google=g)
    page.wait_for_timeout(1500)
    return g, ctx, page, errors


def connect(browser, tag):
    g = FakeGoogle()
    ctx, page, errors = open_app(browser, CREDS, path="#settings", google=g)
    click(page, "Koble til Google Drive")
    wait_until(page, lambda: "consent" in g.kinds(), timeout=10)
    consent = next((u for k, u in g.log if k == "consent"), "")
    sent = parse_qs(urlparse(consent).query)
    other = ctx.new_page()                         # back on the app's origin, to read what Connect stored
    other.goto(URL + "#settings")
    other.wait_for_selector("text=Innstillinger", timeout=30000)
    state = (sent.get("state") or [""])[0]
    check(f"[{tag}] Connect sends a state", len(state) >= 16, f"state={state!r}")
    check(f"[{tag}] … and keeps the same state for the callback", state and stored(other, "drive_oauth_state") == state)
    check(f"[{tag}] … alongside the PKCE challenge", (sent.get("code_challenge_method") or [""])[0] == "S256")
    ctx.close()


def happy(browser, tag):
    g, ctx, page, errors = redirect(browser, "?code=abc&state=state-1")
    connected = wait_until(page, lambda: (ls(page, "driveToken") or {}).get("access_token") == "at-new")
    check(f"[{tag}] matching state: tokens are stored", connected)
    clean(page, tag, "matching state")
    check(f"[{tag}] matching state: no page errors", not errors, "; ".join(errors))
    ctx.close()


def rejected(browser, tag, label, query, raw=OURS):
    g, ctx, page, errors = redirect(browser, query, raw=raw)
    check(f"[{tag}] {label}: the code is not exchanged", not code_exchanges(g), str(g.kinds()))
    check(f"[{tag}] {label}: not connected", ls(page, "driveToken") is None)
    clean(page, tag, label)
    told_in_settings(page, tag, label, "passet ikke")
    ctx.close()


def cancelled(browser, tag):
    g, ctx, page, errors = redirect(browser, "?error=access_denied&state=state-1")
    clean(page, tag, "cancelled sign-in")
    told_in_settings(page, tag, "cancelled sign-in", "avbrutt")
    ctx.close()


def foreign_error(browser, tag):
    # An ?error= this app didn't start (no verifier): not ours to report
    g, ctx, page, errors = redirect(browser, "?error=something", raw={})
    check(f"[{tag}] foreign ?error=: no sign-in message", not shown(page, "Google-innloggingen") and not shown(page, "avbrutt"))
    check(f"[{tag}] foreign ?error=: app unaffected", not errors, "; ".join(errors))
    ctx.close()


def google_says_no(browser, tag):
    g = FakeGoogle()
    g.code_mode = "invalid_client"
    g, ctx, page, errors = redirect(browser, "?code=abc&state=state-1", google=g)
    check(f"[{tag}] rejected client: not connected", ls(page, "driveToken") is None)
    clean(page, tag, "rejected client")
    told_in_settings(page, tag, "rejected client", "Unauthorized client secret")
    ctx.close()


def offline(browser, tag):
    g = FakeGoogle()
    g.code_mode = "offline"
    g, ctx, page, errors = redirect(browser, "?code=abc&state=state-1", google=g)
    clean(page, tag, "network error")
    told_in_settings(page, tag, "network error", "Nettverksfeil mot Google")
    ctx.close()


def run(browser, tag):
    scenario(tag, "connect", lambda: connect(browser, tag))
    scenario(tag, "happy path", lambda: happy(browser, tag))
    scenario(tag, "wrong state", lambda: rejected(browser, tag, "wrong state", "?code=abc&state=forged"))
    scenario(tag, "missing state", lambda: rejected(browser, tag, "missing state", "?code=abc"))
    scenario(tag, "no verifier", lambda: rejected(browser, tag, "code without a sign-in", "?code=abc&state=x", raw={}))
    scenario(tag, "cancelled", lambda: cancelled(browser, tag))
    scenario(tag, "foreign error", lambda: foreign_error(browser, tag))
    scenario(tag, "invalid_client", lambda: google_says_no(browser, tag))
    scenario(tag, "offline", lambda: offline(browser, tag))


if __name__ == "__main__":
    main(run)
