# CLAUDE.md — mealprepping

Browser-based meal planning tool for a Norwegian family doing weekly meal prep. Single self-contained `index.html` — React 18 + Babel via CDN, no build step, served with `python3 -m http.server 8080`.

---

## Key files

| File | Purpose |
|------|---------|
| `index.html` | Entire application — React components, CSS, all logic |
| `middag-planner.jsx` | Original Claude.ai artifact (reference only, not used) |

---

## Architecture

- **No build step** — React 18 and Babel Standalone loaded from `unpkg.com` CDN. JSX transpiled in-browser via `<script type="text/babel">`.
- **All state in localStorage** — prefixed `mp_`. Initialized via lazy `useState(() => lsGet(...))`, persisted with individual `useEffect` hooks per state slice.
- **Anthropic API** — called directly from the browser using `fetch`. Requires `anthropic-dangerous-direct-browser-access: true` header to bypass CORS. Model: `claude-sonnet-4-6`.
- **Kassal API** — `kassal.app/api/v1/products` for real Norwegian grocery prices. Optional — falls back to AI price estimates if key is absent.
- **No backend** — everything runs client-side.

---

## localStorage keys

All keys use the `mp_` prefix.

| Key | Type | Description |
|-----|------|-------------|
| `mp_anthropicKey` | string | Anthropic API key — required for all AI features |
| `mp_kassalKey` | string | Kassal API key — optional, enables real grocery prices |
| `mp_plan` | array[4][7] | Weekly grid — 4 weeks × 7 days, each cell is a meal object or null |
| `mp_suggestions` | array | Current AI-generated meal suggestions |
| `mp_favourites` | array | Starred meals, persists across sessions |
| `mp_mealHistory` | array | Names of all meals ever assigned to the plan (max 100), sent to AI to avoid repetition |
| `mp_mealNotes` | object | Free-text notes per meal, keyed by meal name |
| `mp_recipeCache` | object | Full recipe + nutrition data per meal, keyed by meal name |
| `mp_shoppingList` | object | Last generated shopping list (categories + totalPrice) |
| `mp_lastShoppingKey` | string | planKey snapshot — used to detect when shopping list needs regeneration |
| `mp_proteinTargets` | object | Per-protein weekly targets: `{fisk, kylling, kjott, vegeta}` |
| `mp_cuisineTargets` | object | Per-cuisine weekly targets, keyed by cuisine key |
| `mp_enabledCuisines` | array | Keys of cuisines active in the Kjøkken panel (subset of `CUISINE_LIBRARY`) |
| `mp_weeks` | number | Active number of weeks (1–4) |
| `mp_portions` | number | Portions per meal (1–20) |
| `mp_maxTime` | number | Max prep time in minutes (15–120, step 15) |
| `mp_exclusions` | string | Free-text ingredient/allergen exclusions |
| `mp_suggestionCount` | number | Number of suggestions to generate (5–30, step 5) |
| `mp_units` | string | Measurement system: `"metric"` (default) or `"imperial"` |

---

## Views

Three top-level views switched by `setView(...)`:

| View | Description |
|------|-------------|
| `plan` | Main view — weekly grid, suggestions, favourites, nutrition summary |
| `shopping` | Generated shopping list by category with total price estimate |
| `settings` | API keys, defaults, meal history, data import/export |

---

## Plan view

- **Weekly grid** — table of weeks × days. Cells show meal emoji + name + protein colour bar. Click empty cell to enter "select mode" (amber highlight); click meal card to assign. Drag meal cards directly onto cells.
- **Drag and drop** — `draggable` on suggestion/favourite cards, `onDragOver`/`onDrop` on grid cells. When a meal is dropped on an occupied cell, the displaced meal returns to suggestions.
- **Plan modal** — clicking an assigned meal opens a detail modal with recipe, nutrition, price, and a notes textarea. Separate 🗑 Fjern fra plan button prevents accidental deletion. Notes saved to `mp_mealNotes` on modal close.
- **Protein stats column** — rightmost grid column shows actual vs. target counts per protein type for each week.
- **Weekly nutrition summary** — shown below the grid for weeks where at least one meal has recipe data loaded. Summed from `mp_recipeCache`; updates automatically as recipes load.
- **Progress bar** — filled days vs. total slots for active weeks.
- **Favourites panel** — toggled via ★ button. Shows starred meals as draggable chips; clicking one adds it back to the suggestion list.
- **Suggestion cards** — grid of AI-generated meals. Click to expand inline (full-width) showing ingredients, steps, nutrition. Collapse by clicking again. Drag to grid or click in select mode to assign.
- **Filters** — filter suggestions by protein type. Applied client-side, no re-fetch.

---

## AI calls

### Generate suggestions — `generateSuggestions()`
`POST /v1/messages` — returns `{ meals: [...] }`. Prompt includes:
- Protein targets per week (soft guidance)
- Cuisine targets per week (soft guidance)
- Max prep time (hard constraint)
- Exclusions / allergens
- Already-planned meals (avoid repeats within current plan)
- Meal history (`mp_mealHistory`, last 30 entries) — avoids long-term repetition

### Fetch recipe — `fetchRecipe(meal)`
`POST /v1/messages` — returns `{ ingredients, steps, nutrition, pricePerPortion? }`. Called on card expand or plan modal open. Result cached in `mp_recipeCache`. Prompt includes the active unit system (metric: g/kg/dl/ml; imperial: oz/lbs/cups/fl oz). If Kassal key is present, price is fetched from Kassal instead and the AI is told not to estimate.

### Generate shopping list — `generateShoppingList(force?)`
`POST /v1/messages` — returns `{ categories: [{name, emoji, items: [{name, amount}]}], totalPrice: {low, high} }`. Only regenerates when `planKey` changes or `force=true`. `planKey` is a hash of planned meal names + portions. Prompt includes the active unit system.

---

## Kassal price fetch — `fetchKassalPrice(ingredients)`

Picks up to 4 meaningful ingredients (skips salt, water, oil, etc.), strips amounts, searches `kassal.app/api/v1/products?search=...&unique=true&size=3`. Averages lowest prices found. Returns `{low, high, source:"kassal"}` if ≥2 ingredients matched, otherwise `null`. Attached to `recipe.pricePerPortion` after recipe fetch.

**Hobby plan limits** — the free Kassal API tier allows 60 req/min, no commercial use, no support. Each recipe fetch makes up to 4 Kassal requests (one per meaningful ingredient). In normal use this is not a concern — a user would need to expand ~15 recipe cards within a single minute to approach the limit, which is unlikely. No rate-limit handling is implemented; if the limit is hit, `fetchKassalPrice` will return `null` and the app falls back to the AI price estimate silently. If usage grows, the only mitigation needed would be reducing the ingredient cap below 4 or adding a short delay between searches.

---

## Export / import

| Action | Implementation |
|--------|---------------|
| Export plan | Blob URL → `middagsplan-{date}.json`. Includes all plan state except API keys. |
| Import plan | `FileReader` → JSON parse → restore state slices individually. API keys never imported. |
| Export shopping list | Blob URL → `handleliste.txt`. Plain text with category sections and price estimate. |
| Print / share | `window.open('','_blank')` → `document.write(html)`. Dark-theme page (matches app slate palette) with weekly grid + shopping list. `@media print` overrides to white-on-light for physical printing. Includes a Print button for in-page printing. |

---

## Cuisines

`CUISINE_LIBRARY` contains 19 predefined cuisines (norsk, italiensk, asiatisk, meksikansk, indisk, japansk, kinesisk, thai, gresk, midtøsten, middelhavet, spansk, fransk, amerikansk, vietnamesisk, koreansk, tyrkisk, afrikansk/marokkansk, filippinsk). No free-text entry — all cuisines come from the library.

`enabledCuisines` (localStorage array of keys, default: the first 5) controls which appear in the Kjøkken panel. Active cuisines show their CuisineCounter + ✕ to disable. Inactive cuisines appear as dashed + chips below the active list. Disabling a cuisine also removes its target from `cuisineTargets`. `allCuisines` is derived via `useMemo` filtering `CUISINE_LIBRARY` by `enabledCuisines`.

---

## Meal history

Every meal assigned to the plan (via click, select mode, or drag) is added to `mp_mealHistory` (max 100 unique names, oldest dropped first). The last 30 entries are included in the suggestion prompt. Viewable and clearable in Innstillinger.

---

## Settings page

Sections:

1. **API-nøkler** — Anthropic (required) and Kassal (optional). Password inputs, stored immediately in localStorage on change. Never included in plan exports.
2. **Standardverdier** — weeks, portions, suggestion count, max time, and measurement units (Metrisk / Imperialt toggle). Switching units clears `mp_recipeCache` and `mp_shoppingList` immediately, since AI-generated amounts are baked into the cached text.
3. **Mathistorikk** — scrollable list of recent meals, clear button.
4. **Data** — export plan, import plan, export shopping list, clear recipe cache, clear plan.

---

## Units

`mp_units` — `"metric"` (default) or `"imperial"`. Toggled in Innstillinger → Standardverdier.

- **Metric**: g, kg, dl, ml, liter
- **Imperial**: oz, lbs, cups, fl oz, tbsp, tsp

The active unit is injected as a sentence into the `fetchRecipe` and `generateShoppingList` prompts. Because amounts are stored as free text in `mp_recipeCache` (e.g. `"500g kylling"`), switching units calls `changeUnits()` which resets `recipeCache`, `shoppingList`, and `lastShoppingKey` — forcing fresh AI calls in the new system.

---

## Styling

Dark neutral slate: `#0e0f11` background, `#18191c` cards, `#141517` inset areas, `#22232a`/`#2a2b30` borders.
Warm amber accent: `#e8a838` for active states, buttons, highlights.
Text: primary `#e4ddd0`, secondary `#b4b2c2`, muted `#747280`.
Font: `'Georgia', 'Times New Roman', serif` for headings/body; `sans-serif` for UI labels and data.
All layout via inline styles — no CSS classes except global resets and scrollbar styling.
Mobile friendly via `flexWrap` and `auto-fill` grid columns.

---

## Running locally

```
python3 -m http.server 8080
```

Open `http://localhost:8080`. Add Anthropic API key in ⚙ Innstillinger before generating suggestions.
