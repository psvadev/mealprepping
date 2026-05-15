# Roadmap

Loose collection of ideas and features discussed for future development. Not a commitment — just a living reference so nothing gets lost.

The app's core constraint: **single `index.html`, no build step, no backend**. Ideas that fit this constraint are cheap to ship. Ideas that break it are architectural decisions, not features.

---

## Long-term / architectural changes

### SaaS / multi-user
Would require: backend (auth, user data storage), billing, API key management on the server side (to hide Anthropic/Kassal keys), and a proper build pipeline. Essentially a complete rewrite. Not planned — the personal single-file approach works well and the biggest friction for non-technical users (managing API keys and topping up credits) would need to be fully abstracted away.

---

## Deferred / SaaS-tier

### Structured allergen management
The current exclusions field is free text, which works fine for a personal family app where the AI understands context. A proper allergen system — predefined chips for the 14 EU allergens (gluten, laktose, nøtter, egg, skalldyr, etc.) plus a free-text overflow field, and per-person profiles — would be the right approach if the app ever becomes multi-user. For a single family, the free-text field is sufficient; the main risk is typos or ambiguous entries.

**If added:** exclusions are already injected into all "selection" AI prompts (`generateSuggestions`, `addManualMeal`) with strong wording that also covers dish names and inspiration sources. The structured allergen list would just replace the string input that feeds those same variables — no prompt architecture change needed.

---

## Deferred / not planned

- **Per-day prep tracking** — conflicts with the batch-cook philosophy. Everything is cooked on one day; tracking per-day prep adds complexity for no gain.
- **Barcode scanning** — pantry management via camera. Interesting but well outside scope.
- **Recipe import from URLs** — useful but requires CORS workarounds or a proxy.
- **Multi-provider AI (OpenAI, Gemini, etc.)** — would require abstracting all three prompts behind a provider layer and testing structured JSON output across providers. No user benefit in a personal tool where the API key is yours. More relevant if this ever becomes a SaaS product where the provider choice is hidden from the user.
- **Nutritional targets** — highly individual (age, sex, weight, goals); no natural owner in a shared family tool. Better suited to a SaaS context with per-user profiles and a TDEE calculator.
- **Weekly dessert slot** — one batch-made dessert per week alongside the dinners. Technically straightforward (section below the plan grid, same AI enrichment pattern as manual meal entry, hooks into shopping list). Deferred because it conflicts with the core philosophy: batch-cook day is already heavy; adding a mandatory dessert batch increases effort rather than reducing it. Dessert is better handled ad hoc or from a bakery.
- **Pantry staples / carry-over ingredients** — shopping list awareness of recently purchased non-perishables (e.g. skip pepper if bought last week). No reliable way to track consumption rate or when a staple runs out without maintaining a manual pantry inventory — the overhead exceeds the benefit. The existing check-off on the shopping list already handles this in practice.
- **Spend tracking / price history** — logging grocery spend over time would pull the app towards budgeting territory. The app's identity is batch-cook inspiration and workflow (plan → shop → freeze → reheat); price estimates are a convenience, not a core feature.
