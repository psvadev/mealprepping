# Roadmap

Loose collection of ideas and features discussed for future development. Not a commitment — just a living reference so nothing gets lost.

The app's core constraint: **single `index.html`, no build step, no backend**. Ideas that fit this constraint are cheap to ship. Ideas that require a backend are a different category entirely — see `SAAS_NOTES.md` for those.

---

## Deferred

Features that could fit the single-file constraint but haven't been prioritised.

### FreezerBox integration
A local companion app for tracking physical freezer containers with QR labels. Potential to integrate container availability into the freezer logging flow. No priority set.

### Automated browser tests before pushing
The repo has no tests or CI; every change is checked by hand in the browser before pushing. The September 2026 audit fixes were verified with Python Playwright scripts that serve the app with `python -m http.server`, mock `api.anthropic.com`, `oauth2.googleapis.com` and `www.googleapis.com` (including an in-memory Drive file), and drive the real UI in Chromium. Checked in as a `tests/` folder, they would give a one-command pre-push check (`python tests/run.py`), and could later run in a GitHub Actions workflow on push.

**Fits the constraint:** tests are dev-only tooling. The app itself stays a single `index.html` with no build step. Needs only Python 3 and `pip install playwright` plus `python -m playwright install chromium`; no Node.

### Structured allergen management
The current exclusions field is free text, which works fine for a personal family app where the AI understands context. A proper allergen system — predefined chips for the 14 EU allergens (gluten, laktose, nøtter, egg, skalldyr, etc.) plus a free-text overflow field — would reduce typo risk. For a single family the free-text field is sufficient.

**If added:** exclusions are already injected into all "selection" AI prompts (`generateSuggestions`, `addManualMeal`) with strong wording that also covers dish names and inspiration sources. The structured allergen list would just replace the string input that feeds those same variables — no prompt architecture change needed.

---

## Audit backlog (September 2026)

Remaining findings from the September 2026 audit. The P1 and P2 findings and nine P3s were fixed in the first pass; a second pass cleared ten more — D10 (quota banner + recipe-cache eviction), D14 (stale shopping list no longer auto-regenerates over your check-offs), L11/L12 (rounded totals), PF1/PF2 (hash-skipped uploads, three concurrent recipe loads), D15 (`navigator.storage.persist()` + "last export" line), L10 (drag highlight in state), L15/L17/L18 (manual-dish filtering, the mobile breakpoint, kr/porsjon/dag) and S3 (revoke the refresh token in a POST body). All are covered by `test_phase5.py`.

These are what's left, roughly in the order they're worth doing.

- **D8 portions stepper** — one misclick still clears cached recipes and shopping lists. Fix: tag each cached recipe with its portions/units and select by scale, instead of clearing the cache. This is the only remaining item with real data cost, and the largest of the four: every `recipeCache[name]` read has to go through the scale-aware view.
- **S5–S8, D11, D16, L19, PF3** — low-severity items: no OAuth `state` parameter (PKCE covers the real risk), client secret in localStorage (an accepted trade-off), no client-side check that AI output respects the allergen exclusions, personal email in early public commits, various missing undo toasts, and one large component re-rendering on every keystroke.

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
