"""Shared test harness: static server, seeded app contexts, fake Google and Anthropic, PASS/FAIL reporting.

Modelled on the template's tests/harness.py (C:\\temp\\GitHub\\template). Python + Playwright, no Node:
the app itself stays npm-free.

Env:   BROWSERS=firefox,webkit,chromium   PORT=8766
       Firefox is the main desktop browser; WebKit is the engine behind every iOS browser.

Two traps this file exists to avoid (both found 2026-10-09):
- Seed storage with an init script, never "load, seed from outside, reload": on WebKit the app mounted
  mid-seed and its persistence effects wrote the defaults back over the seed in 5 of 6 runs.
- Read text from #root, never document.body: the body's text includes the inline Babel <script>, whose
  source contains every UI string. And on WebKit get_by_text() missed a dialog that was on screen.
"""
import json, os, re, socket, subprocess, sys, time
from email import message_from_bytes
from email.policy import default as email_policy
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("PORT", "8766"))
URL = f"http://127.0.0.1:{PORT}/"
PFX = "mp_"
FILENAME = "reheat-and-eat-backup.json"
BROWSERS = [b.strip() for b in os.environ.get("BROWSERS", "firefox,webkit,chromium").split(",") if b.strip()]

VALID = {"access_token": "at", "refresh_token": "rt", "expires_at": 9999999999999}
EXPIRED = {"access_token": "at", "refresh_token": "rt", "expires_at": 0}
CREDS = {"googleClientId": "cid", "googleClientSecret": "secret"}

results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


# ── Seed data ────────────────────────────────────────────────────────────────
def MEAL(name, **kw):
    return dict({"name": name, "emoji": "🍲", "protein": "kylling", "category": "gryte",
                 "prepTime": "30 min", "description": "Test"}, **kw)

def plan_with(*names):
    """4×7 plan with `names` on the first days of week 1."""
    plan = [[None] * 7 for _ in range(4)]
    for i, n in enumerate(names):
        plan[0][i] = MEAL(n)
    return plan

def drive_backup(**slices):
    """A Drive file body as this app writes it: flat payload slices plus savedAt."""
    return {"weeks": 1, "plan": plan_with(), **slices, "savedAt": "2026-10-01T10:00:00.000Z"}


# ── Fake Google ──────────────────────────────────────────────────────────────
class FakeGoogle:
    """In-memory stand-in for the OAuth token endpoint and the Drive v3 API."""

    def __init__(self):
        self.files = {}
        self.seq = 0
        self.log = []
        self.token_mode = "ok"  # refresh: ok | offline | 503 | invalid_grant
        self.code_mode = "ok"   # code exchange: ok | invalid_client (Google replies with an error body)
        self.delay = {}         # request kind -> seconds; blocks the handler, so later requests queue behind it
        self.fail = {}          # request kind -> HTTP status to return instead of succeeding

    def _tick(self):
        self.seq += 1
        return self.seq

    def add_file(self, content, name=FILENAME, trashed=False):
        fid = f"file{self._tick()}"
        self.files[fid] = {"name": name, "content": json.dumps(content),
                           "modifiedTime": f"2026-10-01T10:00:{self._tick():02d}.000Z", "trashed": trashed}
        return fid

    def replace(self, fid, content):
        """Another device saved: new content and a newer modifiedTime."""
        self.files[fid]["content"] = json.dumps(content)
        self.files[fid]["modifiedTime"] = f"2026-10-01T13:00:{self._tick():02d}.000Z"

    def live_files(self):
        return {i: f for i, f in self.files.items() if f["name"] == FILENAME and not f["trashed"]}

    def content(self, fid):
        return json.loads(self.files[fid]["content"])

    def writes(self):
        return [body for kind, body in self.log if kind in ("patch", "create")]

    def kinds(self):
        return [kind for kind, _ in self.log]

    def attach(self, ctx):
        ctx.route("https://oauth2.googleapis.com/**", self._oauth)
        ctx.route("https://www.googleapis.com/**", self._drive)
        ctx.route("https://accounts.google.com/**", self._consent)

    def _consent(self, route):
        self.log.append(("consent", route.request.url))
        route.fulfill(status=200, content_type="text/html", body="<p>fake consent screen</p>")

    def _wait(self, kind):
        if self.delay.get(kind):
            time.sleep(self.delay[kind])

    def _json(self, route, obj, status=200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(obj))

    def _oauth(self, route):
        req = route.request
        if "/revoke" in req.url:
            self.log.append(("revoke", req.post_data))
            return route.fulfill(status=200, body="")
        grant = parse_qs(req.post_data or "").get("grant_type", [""])[0]
        self.log.append(("token", grant))
        if grant == "refresh_token":
            if self.token_mode == "offline":
                return route.abort("internetdisconnected")
            if self.token_mode == "503":
                return self._json(route, {"error": "backend_error"}, 503)
            if self.token_mode == "invalid_grant":
                return self._json(route, {"error": "invalid_grant"}, 400)
        if grant == "authorization_code" and self.code_mode == "invalid_client":
            return self._json(route, {"error": "invalid_client", "error_description": "Unauthorized client secret"})
        self._json(route, {"access_token": "at-new", "refresh_token": "rt", "expires_in": 3600})

    def _drive(self, route):
        req = route.request
        u = urlparse(req.url)
        qs = parse_qs(u.query)
        m = re.match(r"^/(upload/)?drive/v3/files(?:/([^/]+))?$", u.path)
        if not m:
            return route.fulfill(status=404, body="")
        fid = m.group(2)

        if req.method == "GET" and not fid:
            self._wait("list")
            q = qs.get("q", [""])[0]
            nm = re.search(r"name\s*=\s*'((?:\\'|[^'])*)'", q)
            name = nm.group(1).replace("\\'", "'") if nm else None
            skip_trashed = "trashed=false" in q.replace(" ", "")
            hits = [(i, f) for i, f in self.files.items()
                    if (name is None or f["name"] == name) and not (skip_trashed and f["trashed"])]
            hits.sort(key=lambda x: x[1]["modifiedTime"], reverse=True)
            self.log.append(("list", name))
            return self._json(route, {"files": [{"id": i} for i, _ in hits]})

        f = self.files.get(fid) if fid else None
        if req.method == "GET":
            if not f:
                return self._json(route, {"error": {"code": 404}}, 404)
            if qs.get("alt") == ["media"]:
                self._wait("media")
                self.log.append(("media", fid))
                return route.fulfill(status=200, content_type="application/json", body=f["content"])
            self._wait("meta")
            self.log.append(("meta", fid))
            return self._json(route, {"id": fid, "modifiedTime": f["modifiedTime"], "trashed": f["trashed"]})

        if req.method == "PATCH":
            if not f:
                return self._json(route, {"error": {"code": 404}}, 404)
            self._wait("patch")
            if self.fail.get("patch"):
                self.log.append(("patch-failed", None))
                return self._json(route, {"error": {"code": self.fail["patch"]}}, self.fail["patch"])
            f["content"] = req.post_data
            f["modifiedTime"] = f"2026-10-01T11:00:{self._tick():02d}.000Z"
            self.log.append(("patch", json.loads(req.post_data)))
            return self._json(route, {"id": fid, "modifiedTime": f["modifiedTime"]})

        if req.method == "POST" and not fid:
            self._wait("create")
            # Playwright's WebKit doesn't expose multipart bodies that contain Blobs, so the
            # upload can arrive empty here; record the create with unknown content instead of crashing
            meta, content = {"name": FILENAME}, None
            try:
                head = f"Content-Type: {req.headers.get('content-type', '')}\r\n\r\n".encode()
                msg = message_from_bytes(head + (req.post_data_buffer or b""), policy=email_policy)
                parts = []
                for p in msg.iter_parts():
                    c = p.get_content()
                    parts.append(json.loads(c if isinstance(c, str) else c.decode()))
                meta, content = parts[0], parts[1]
            except (ValueError, IndexError):
                pass
            new_id = f"file{self._tick()}"
            self.files[new_id] = {"name": meta["name"], "content": json.dumps(content),
                                  "modifiedTime": f"2026-10-01T12:00:{self._tick():02d}.000Z", "trashed": False}
            self.log.append(("create", content))
            return self._json(route, {"id": new_id, "modifiedTime": self.files[new_id]["modifiedTime"]})

        route.fulfill(status=400, body="")


# ── Fake Anthropic ───────────────────────────────────────────────────────────
class FakeAnthropic:
    """Records request bodies and answers with `reply` (a dict sent as the text block's JSON),
    or with an error status when `status` is set. Unrouted, the harness refuses every real API call."""

    def __init__(self, reply=None, status=200):
        self.reply, self.status, self.bodies = reply, status, []

    def attach(self, ctx):
        ctx.route("https://api.anthropic.com/**", self._handle)

    def _handle(self, route):
        self.bodies.append(json.loads(route.request.post_data or "{}"))
        if self.status != 200:
            return route.fulfill(status=self.status, content_type="application/json",
                                 body=json.dumps({"type": "error", "error": {"type": "api_error", "message": "fake"}}))
        route.fulfill(status=200, content_type="application/json", body=json.dumps(
            {"content": [{"type": "text", "text": json.dumps(self.reply or {})}], "stop_reason": "end_turn"}))


# ── CDN cache ────────────────────────────────────────────────────────────────
CDN_CACHE = ROOT / "tests" / ".cdn-cache"  # gitignored; delete to refetch


def cache_cdn(ctx, tamper=None):
    """Serve the CDN scripts from a disk cache filled on first use, so a slow unpkg can't time a run out
    (template 3f4e218, QRbox 56bd832). The bytes are unchanged, so the browser still checks them against
    the SRI hashes. `tamper(url, body)` alters the served bytes — the control that proves SRI still applies."""
    import hashlib

    def handle(route):
        url = route.request.url
        f = CDN_CACHE / hashlib.sha256(url.encode()).hexdigest()
        if not f.exists():
            resp = route.fetch()
            if resp.status != 200:
                return route.fulfill(response=resp)
            CDN_CACHE.mkdir(exist_ok=True)
            # Write-then-rename, so a run that stops mid-write never leaves a truncated script behind
            tmp = f.with_suffix(f".{os.getpid()}.tmp")
            tmp.write_bytes(resp.body())
            tmp.replace(f)
        body = f.read_bytes()
        if tamper:
            body = tamper(url, body)
        route.fulfill(status=200, body=body, content_type="application/javascript",
                      headers={"Access-Control-Allow-Origin": "*"})
    ctx.route("https://unpkg.com/**", handle)


# ── App contexts ─────────────────────────────────────────────────────────────
def open_app(browser, seed=None, raw=None, path="#plan", google=None, anthropic=None, init=""):
    """Seed localStorage before any app script runs, then load the app once.
    `seed` values are JSON-encoded under the mp_ prefix; `raw` is written verbatim (full key names) — for
    unreadable values and the unprefixed OAuth keys. `init` is extra JS that runs before the app on every load."""
    # Pinned locale and zone: the app formats dates in nb-NO and counts calendar days in local time
    ctx = browser.new_context(viewport={"width": 1400, "height": 900}, locale="nb-NO", timezone_id="Europe/Oslo")
    cache_cdn(ctx)
    (google or FakeGoogle()).attach(ctx)
    (anthropic or FakeAnthropic(status=529)).attach(ctx)          # never reach the real API
    ctx.route("https://kassal.app/**", lambda r: r.fulfill(status=404, body=""))
    if init:
        ctx.add_init_script(init)
    # Report CSP violations as page errors, so every "no page errors" check also guards the CSP
    ctx.add_init_script("""document.addEventListener('securitypolicyviolation', e =>
        console.error(`CSP violation: ${e.violatedDirective} blocked ${e.blockedURI || 'inline code'}`));""")
    items = {PFX + k: json.dumps(v) for k, v in (seed or {}).items()}
    items.update(raw or {})
    # Seed once per context, so reloads and second tabs keep what the app wrote
    ctx.add_init_script(f"""(items => {{ try {{
        if (localStorage.getItem('__seeded')) return;
        localStorage.clear();
        for (const [k, v] of Object.entries(items)) localStorage.setItem(k, v);
        localStorage.setItem('__seeded', '1');
    }} catch {{}} }})({json.dumps(items)})""")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and m.text.startswith("CSP violation") else None)
    # The app asks through its own dialogs; a native confirm/alert is a regression
    page.on("dialog", lambda d: (errors.append(f"native dialog: {d.message}"), d.dismiss()))
    page.goto(URL + path)
    page.wait_for_selector("text=Innstillinger", timeout=30000)
    return ctx, page, errors


def ls(page, key):
    return page.evaluate(f"JSON.parse(localStorage.getItem('{PFX}{key}'))")


def root_text(page):
    return page.evaluate("document.getElementById('root').innerText")


def shown(page, text):
    return text in root_text(page)


def click(page, name, exact=False):
    """Click a button if it exists; a missing button fails the checks that follow, not the whole run."""
    btn = page.get_by_role("button", name=name, exact=exact)
    if not btn.count():
        return False
    btn.first.click()
    return True


def wait_until(page, fn, timeout=8.0, step=0.1):
    """Poll `fn()` from Python (page.wait_for_function needs eval, which the app's CSP refuses).
    page.wait_for_timeout between polls keeps Playwright serving the fake routes."""
    end = time.time() + timeout
    while time.time() < end:
        if fn():
            return True
        page.wait_for_timeout(int(step * 1000))
    return fn()


def go(page, view):
    page.evaluate(f"location.hash = '{view}'")
    page.wait_for_timeout(200)


def scenario(tag, name, fn):
    """Run one scenario; an exception is recorded as a FAIL instead of ending the whole suite (a missing
    function or a timeout in one scenario must not hide the results of the others). Contexts are closed
    by closing the browser's remaining contexts."""
    try:
        fn()
    except Exception as e:
        check(f"[{tag}] {name}: ran to completion", False, repr(e)[:160])


def start_server():
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.2).close()
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    sys.exit(f"http.server did not start on port {PORT}")


def main(run):
    """Serve the repo, run `run(browser, tag)` on every configured engine, exit non-zero on any FAIL."""
    server = start_server()
    try:
        with sync_playwright() as p:
            for name in BROWSERS:
                browser = getattr(p, name).launch()
                try:
                    run(browser, name)
                finally:
                    browser.close()
    finally:
        server.kill()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    for name, _, detail in failed:
        print(f"  FAILED: {name}  {detail}")
    sys.exit(1 if failed else 0)
