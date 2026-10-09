"""The CDN scripts: pinned to exact versions, with integrity hashes the browser actually enforces.

Upgrade with the template's tool, then update PINNED below and run this suite:
    python C:\\temp\\GitHub\\template\\tools\\pin_cdn.py index.html            (dry run)
    python C:\\temp\\GitHub\\template\\tools\\pin_cdn.py --write index.html

Run:   python tests/test_environment.py
"""
from harness import *

# Majors are deliberate: React 18 (UMD builds), Babel 7 (Babel 8 breaks type="text/babel")
PINNED = {"react": "18.3.1", "react-dom": "18.3.1", "@babel/standalone": "7.29.10"}
SCRIPT_RE = re.compile(r'<script src="https://unpkg\.com/((?:@[^/@"]+/)?[^/@"]+)@([^/"]+)/[^"]+"([^>]*)></script>')


def pins(tag):
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    found = {pkg: (ver, attrs) for pkg, ver, attrs in SCRIPT_RE.findall(html)}
    for pkg, want in PINNED.items():
        ver, attrs = found.get(pkg, (None, ""))
        check(f"[{tag}] {pkg} pinned to {want}", ver == want, f"found {ver}")
        check(f"[{tag}] {pkg} has an sha384 integrity hash and crossorigin",
              'integrity="sha384-' in attrs and 'crossorigin="anonymous"' in attrs)
    check(f"[{tag}] no unpinned unpkg script", not re.search(r'src="https://unpkg\.com/[^@"]+/', html.replace("@babel/", "")))


def load(browser, tamper=None):
    ctx = browser.new_context(viewport={"width": 1400, "height": 900}, locale="nb-NO")
    cache_cdn(ctx, tamper=tamper)
    FakeGoogle().attach(ctx)
    FakeAnthropic(status=529).attach(ctx)
    page = ctx.new_page()
    page.goto(URL + "#plan")
    rendered = wait_until(page, lambda: "Innstillinger" in root_text(page), timeout=20)
    return ctx, rendered


def sri(browser, tag):
    ctx, rendered = load(browser)
    check(f"[{tag}] the app starts with the cached, unmodified scripts", rendered)
    ctx.close()
    # Control: one changed byte in Babel must stop the app — proves the hash is enforced, not just present
    ctx, rendered = load(browser, tamper=lambda url, body: body + b"\n/* tampered */" if "babel" in url else body)
    check(f"[{tag}] a tampered Babel is refused (SRI enforced)", not rendered)
    ctx.close()


def run(browser, tag):
    scenario(tag, "pins", lambda: pins(tag))
    scenario(tag, "sri", lambda: sri(browser, tag))


if __name__ == "__main__":
    main(run)
