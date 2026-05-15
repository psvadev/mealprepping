# Roadmap

Loose collection of ideas and features discussed for future development. Not a commitment — just a living reference so nothing gets lost.

The app's core constraint: **single `index.html`, no build step, no backend**. Ideas that fit this constraint are cheap to ship. Ideas that break it are architectural decisions, not features.

---

## Long-term / architectural changes

### SaaS / multi-user
Would require: backend (auth, user data storage), billing, API key management on the server side (to hide Anthropic/Kassalapp keys), and a proper build pipeline. Essentially a complete rewrite. Not planned — the personal single-file approach works well and the biggest friction for non-technical users (managing API keys and topping up credits) would need to be fully abstracted away.

---

## Deferred / SaaS-tier

Features that don't make sense in a personal single-file app but would be natural in a multi-user product.

### Structured allergen management
The current exclusions field is free text, which works fine for a personal family app where the AI understands context. A proper allergen system — predefined chips for the 14 EU allergens (gluten, laktose, nøtter, egg, skalldyr, etc.) plus a free-text overflow field, and per-person profiles — would be the right approach if the app ever becomes multi-user. For a single family, the free-text field is sufficient; the main risk is typos or ambiguous entries.

**If added:** exclusions are already injected into all "selection" AI prompts (`generateSuggestions`, `addManualMeal`) with strong wording that also covers dish names and inspiration sources. The structured allergen list would just replace the string input that feeds those same variables — no prompt architecture change needed.

### Nutritional targets
Highly individual (age, sex, weight, activity level, goals) — no natural owner in a shared family tool. The weekly nutrition summary already shows totals per person; setting targets and tracking against them requires per-user profiles and ideally a TDEE calculator. Natural fit for a SaaS with accounts.

### Spend tracking / price history
Logging grocery spend over time pulls the app towards budgeting territory. The app's identity is batch-cook inspiration and workflow (plan → shop → freeze → reheat); price estimates are a convenience, not a core feature. Meaningful spend tracking needs persistent per-user history — a database concern.

### Multi-provider AI (OpenAI, Gemini, etc.)
Would require abstracting all three prompts behind a provider layer and testing structured JSON output across providers. No user benefit in a personal tool where the API key is yours. In a SaaS the provider choice and key management are hidden from the user, making this a backend infrastructure decision rather than a feature.

### Recipe import from URLs
Useful but requires a server-side proxy to work around CORS — not viable in a pure client-side app. Straightforward to add once there's a backend.

---

## Not planned

Features that conflict with the core philosophy regardless of architecture.

- **Per-day prep tracking** — conflicts with the batch-cook philosophy. Everything is cooked on one day; tracking per-day prep adds complexity for no gain.
- **Barcode scanning** — pantry management via camera. Interesting but a different product category entirely.
- **Weekly dessert slot** — technically straightforward, but batch-cook day is already heavy. Adding a mandatory dessert batch increases effort rather than reducing it. Dessert is better handled ad hoc.
- **Pantry staples / carry-over ingredients** — shopping list awareness of recently purchased non-perishables. No reliable way to track consumption rate without a manual pantry inventory — overhead exceeds the benefit. The existing check-off on the shopping list already handles this in practice.
