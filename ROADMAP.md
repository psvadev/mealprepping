# Roadmap

Loose collection of ideas and features discussed for future development. Not a commitment — just a living reference so nothing gets lost.

The app's core constraint: **single `index.html`, no build step, no backend**. Ideas that fit this constraint are cheap to ship. Ideas that require a backend are a different category entirely — see `SAAS_NOTES.md` for those.

---

## Deferred

Features that could fit the single-file constraint but haven't been prioritised.

### FreezerBox integration
A local companion app for tracking physical freezer containers with QR labels. Potential to integrate container availability into the freezer logging flow. No priority set.

### Automated browser tests before pushing
**Started October 2026:** `tests/` now exists (see CLAUDE.md → Tests) with a shared harness and suites for Drive sync and import/export, run on Firefox, WebKit and Chromium with `python tests/run_all.py`. Still to do: move the remaining useful checks from the local `docs/audit-tests/` phases (shopping list, freezer, allergen check, undo toast, Escape) into `tests/` by area, and later run `run_all.py` in a GitHub Actions workflow on push.

**Fits the constraint:** tests are dev-only tooling. The app itself stays a single `index.html` with no build step. Needs only Python 3 and Playwright; no Node.

### Structured allergen management
The current exclusions field is free text, which works fine for a personal family app where the AI understands context. A proper allergen system — predefined chips for the 14 EU allergens (gluten, laktose, nøtter, egg, skalldyr, etc.) plus a free-text overflow field — would reduce typo risk. For a single family the free-text field is sufficient.

**If added:** exclusions are already injected into all "selection" AI prompts (`generateSuggestions`, `addManualMeal`) with strong wording that also covers dish names and inspiration sources. The structured allergen list would just replace the string input that feeds those same variables — no prompt architecture change needed.

---

## Audit backlog (September 2026)

Remaining findings from the September 2026 audit. The P1 and P2 findings and nine P3s were fixed in the first pass; a second pass cleared ten more — D10 (quota banner + recipe-cache eviction), D14 (stale shopping list no longer auto-regenerates over your check-offs), L11/L12 (rounded totals), PF1/PF2 (hash-skipped uploads, three concurrent recipe loads), D15 (`navigator.storage.persist()` + "last export" line), L10 (drag highlight in state), L15/L17/L18 (manual-dish filtering, the mobile breakpoint, kr/porsjon/dag) and S3 (revoke the refresh token in a POST body). All are covered by `test_phase5.py`.

D8 followed in October: recipes are now scale-tagged, so a portions or units misclick no longer throws away the recipe cache or the shopping lists (`test_phase6.py`). S7 too: the AI's output is checked against the exclusions in the browser, with Norwegian allergen synonyms (`test_phase7.py`). Then most of D16 and L19: a shared undo toast for one-click deletes, an explicit warning when a week is logged to the freezer twice in a day, modals closing on Back, hidden weeks kept out of prompts, and smaller fixes (`test_phase8.py`).

What's left is deliberately parked:

- ~~**S5 OAuth `state` parameter**~~ — done in October with template gap f below. It changes the Drive connect flow, so the next real-Drive test must include connecting.
- **S6 client secret in localStorage** — accepted trade-off for a personal app; revisit only if the audience grows.
- **S8 personal email in early public commits** — informational; rewriting public history would be more disruptive than the exposure.
- **PF3 one large component re-renders per keystroke** — profile before acting; nobody has reported lag.
- ~~**D16 leftovers**~~ — done in October with template gap c below: an unreadable value is kept as `mp_<key>_corrupt` and offered back.
- **L19 leftover** — in select mode, clicking an occupied grid cell copies that dish into the selected cell. Possibly intended (it's a quick way to plan the same dish twice), so ask before changing it.

## Template gaps (October 2026)

Patterns from the template app (`C:\temp\GitHub\template`, its AUDIT.md and PATTERNS.md), checked against this app on 2026-10-09. One commit per item.

- **b. Escape handler before paint** — done: `useLayoutEffect` (`test_template_gaps.py`, all three engines).
- **Test harness** — done: `tests/` with `harness.py`, Drive sync and import/export suites. Against the live `main` code (22ff4b3) they fail 16 of 32 Drive checks and 9 of 23 import checks — the documented September bugs, now reproduced by test.
- **a. Babel pin** — done: 7.29.8 → 7.29.10 with `pin_cdn.py` (newer than the 7.29.9 the template pins; chosen by the user). `tests/test_environment.py` checks the pins and that a tampered script is refused.
- **c. Corrupt stored data** — done: an unreadable user-data value is kept as `mp_<key>_corrupt` with a recovery banner (download, delete with undo); closes the D16 leftover above (`tests/test_storage.py`).
- **d. Drive conflict** — done: "Bestem senere" and Escape pick neither side; sync pauses with a "Velg nå" banner, auto-save stays blocked, and automatic triggers don't reopen the question. Escape also cancels the import preview and "Fjerne hele batchen?" now (`test_drive_sync.py`, `test_ui.py`).
- **e. Rescue download** — the ErrorBoundary file already imports and excludes credentials, but silently drops any value it can't parse — the very values a crash is likely about.
- **f. OAuth callback** — done: `state` sent and checked (closes S5), URL and single-use values cleaned before any exit, `?error=` handled, every failure explained in Settings, and a return from Google starts in Settings (`tests/test_oauth.py`). Before the fix the same 20 checks failed on every engine — a callback with a forged `state` was exchanged and connected.
- **g. Dates** — the two `+'T12:00:00'` display parses are correct for every time zone a Norwegian household is in; changing them is optional.

**Two account chores, no code:** clear leftover `mp_*` keys from the old `psvadev.github.io` origin on every browser that used the app before the custom domain (May 2026), and add `reheatandeat.app` under GitHub → Settings → Pages → Verified domains to prevent takeover.

---

## Not planned

Features that conflict with the core philosophy or are out of scope regardless of architecture. Documented here so the reasoning isn't lost.

- **Per-day prep tracking** — conflicts with the batch-cook philosophy. Everything is cooked on one day; tracking per-day prep adds complexity for no gain.
- **Barcode scanning** — pantry management via camera. Interesting but a different product category entirely.
- **Weekly dessert slot** — technically straightforward, but batch-cook day is already heavy. Adding a mandatory dessert batch increases effort rather than reducing it. Dessert is better handled ad hoc.
- **Pantry staples / carry-over ingredients** — shopping list awareness of recently purchased non-perishables. No reliable way to track consumption rate without a manual pantry inventory — overhead exceeds the benefit. The existing check-off on the shopping list already handles this in practice.
- **Nutritional targets** — highly individual (age, sex, weight, activity level, goals) with no natural owner in a shared family tool. The weekly nutrition summary already shows totals; targets require per-user profiles. Makes sense in a multi-user product but not here.
- **Spend tracking / price history** — pulls the app towards budgeting territory. Price estimates are a convenience; meaningful history needs a database. Out of scope for a single-file app.
- **Multi-provider AI (OpenAI, Gemini, etc.)** — no user benefit when the API key is yours and all prompts are tuned for Claude's structured JSON output. A backend infrastructure decision, not a feature.
- **Recipe import from URLs** — requires a server-side proxy to work around CORS. Not viable client-side.
