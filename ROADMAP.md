# Roadmap

Loose collection of ideas and features discussed for future development. Not a commitment — just a living reference so nothing gets lost.

The app's core constraint: **single `index.html`, no build step, no backend**. Ideas that fit this constraint are cheap to ship. Ideas that break it are architectural decisions, not features.

---

## Long-term / architectural changes

### SaaS / multi-user
Would require: backend (auth, user data storage), billing, API key management on the server side (to hide Anthropic/Kassal keys), and a proper build pipeline. Essentially a complete rewrite. Not planned — the personal single-file approach works well and the biggest friction for non-technical users (managing API keys and topping up credits) would need to be fully abstracted away.

---

## Deferred / not planned

- **Per-day prep tracking** — conflicts with the batch-cook philosophy. Everything is cooked on one day; tracking per-day prep adds complexity for no gain.
- **Barcode scanning** — pantry management via camera. Interesting but well outside scope.
- **Recipe import from URLs** — useful but requires CORS workarounds or a proxy.
- **Multi-provider AI (OpenAI, Gemini, etc.)** — would require abstracting all three prompts behind a provider layer and testing structured JSON output across providers. No user benefit in a personal tool where the API key is yours. More relevant if this ever becomes a SaaS product where the provider choice is hidden from the user.
- **Nutritional targets** — highly individual (age, sex, weight, goals); no natural owner in a shared family tool. Better suited to a SaaS context with per-user profiles and a TDEE calculator.
- **Weekly dessert slot** — one batch-made dessert per week alongside the dinners. Technically straightforward (section below the plan grid, same AI enrichment pattern as manual meal entry, hooks into shopping list). Deferred because it conflicts with the core philosophy: batch-cook day is already heavy; adding a mandatory dessert batch increases effort rather than reducing it. Dessert is better handled ad hoc or from a bakery.
- **Pantry staples / carry-over ingredients** — shopping list awareness of recently purchased non-perishables (e.g. skip pepper if bought last week). No reliable way to track consumption rate or when a staple runs out without maintaining a manual pantry inventory — the overhead exceeds the benefit. The existing check-off on the shopping list already handles this in practice.
