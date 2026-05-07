# Roadmap

Loose collection of ideas and features discussed for future development. Not a commitment — just a living reference so nothing gets lost.

The app's core constraint: **single `index.html`, no build step, no backend**. Ideas that fit this constraint are cheap to ship. Ideas that break it are architectural decisions, not features.

---

## Near-term (fits current architecture)

### Google Drive sync
**Goal:** share plan state between desktop planning and phone (in-store shopping, freezer checks).  
**Approach:** OAuth2 PKCE flow in the browser → Google Drive API v3. Save/load a single `mealprepping-backup.json` file in the user's Drive. No backend needed — the OAuth redirect can target `localhost:8080` (local) or the GitHub Pages URL.  
**Scope:** Export and import are already built. Drive sync is essentially "auto-export on change, auto-import on load" with a Google identity layer on top.  
**Setup:** one-time per device — enter Google OAuth client ID in Innstillinger, click "Koble til Google Drive", log in via Google popup. After that sync is silent and automatic.  
**OAuth scope:** `https://www.googleapis.com/auth/drive.file` — grants access only to files the app itself created, nothing else in the user's Drive.  
**Complexity:** ~200–300 lines. Needs a Google Cloud project with the Drive API enabled and an OAuth client ID (free, does not expire, no per-use cost).

### Skriv ut button — style as action, not nav tab
The print button sits in the nav row but looks identical to view tabs (Plan, Handleliste, Fryser, Innstillinger). It should be visually distinct — ghost/outline style — to signal it's an action, not a destination.

### Shopping list — mobile week auto-scroll
On mobile, tapping "Handleliste" in the bottom nav jumps to the shopping view for `shoppingWeek`. If the shopping list hasn't been generated yet, the view is empty. A small "Generer handleliste" CTA when the list is missing would smooth this flow.

### Freezer — edit item name / emoji
Currently, freezer items inherit the meal name and emoji from the plan and can't be edited. A tap-to-edit would let users correct AI-generated names before they become permanent in the log.

---

## Medium-term (moderate complexity, still single-file)

### Nutritional targets
Weekly nutrition summary already shows calories/protein/fat/carbs/fibre. A next step would be letting users set per-week targets (e.g. 2000 kcal/day) and showing progress bars or colour indicators against them.

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
