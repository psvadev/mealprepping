# Roadmap

Loose collection of ideas and features discussed for future development. Not a commitment — just a living reference so nothing gets lost.

The app's core constraint: **single `index.html`, no build step, no backend**. Ideas that fit this constraint are cheap to ship. Ideas that require a backend are a different category entirely — see `SAAS_NOTES.md` for those.

---

## Deferred

Features that could fit the single-file constraint but haven't been prioritised.

### Structured allergen management
The current exclusions field is free text, which works fine for a personal family app where the AI understands context. A proper allergen system — predefined chips for the 14 EU allergens (gluten, laktose, nøtter, egg, skalldyr, etc.) plus a free-text overflow field — would reduce typo risk. For a single family the free-text field is sufficient.

**If added:** exclusions are already injected into all "selection" AI prompts (`generateSuggestions`, `addManualMeal`) with strong wording that also covers dish names and inspiration sources. The structured allergen list would just replace the string input that feeds those same variables — no prompt architecture change needed.

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
