# Roadmap

Loose collection of ideas and features discussed for future development. Not a commitment — just a living reference so nothing gets lost.

The app's core constraint: **single `index.html`, no build step, no backend**. Ideas that fit this constraint are cheap to ship. Ideas that break it are architectural decisions, not features.

---

## Medium-term (moderate complexity, still single-file)

### Leftover handling improvements
Currently "leftover" is a freeform concept. A structured leftovers system could let users mark a freezer meal as "also provides lunch" and track that separately, reducing manual portion math.

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
