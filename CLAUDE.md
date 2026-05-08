# CLAUDE.md — mealprepping

Browser-based weekly meal planner for a Norwegian family doing batch-cook meal prep. Single self-contained `index.html` — React 18 + Babel via CDN, no build step, served with `python3 -m http.server 8080`.

**Meal prep philosophy:** everything is cooked on one batch day, frozen in portions, and dinner is reheating and eating only — no per-dinner prep whatsoever. All AI prompts (suggestions, recipes, shopping list) enforce this strictly.

**Localisation:** the UI and all AI-generated content (suggestions, recipes, shopping lists) are in Norwegian bokmål. All three AI prompts begin with `Svar alltid på norsk bokmål.` to enforce this. The codebase itself is in English. There is no i18n layer — Norwegian is hardcoded throughout.

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
| `mp_freezerItems` | array | Freezer inventory — meals logged from the plan with portion tracking |
| `mp_checkedItems` | object | Shopping list check-off state — `{ [weekIndex]: { [catName|itemName]: true } }` |
| `mp_dislikedMeals` | array | Meal names the family didn't enjoy — fed into suggestion prompts as hard exclusions |
| `mp_googleClientId` | string | Google OAuth client ID — required for Drive sync |
| `mp_googleClientSecret` | string | Google OAuth client secret — required for Drive sync (stored client-side; acceptable for personal use with `drive.file` scope) |
| `mp_driveToken` | object | OAuth token — `{ access_token, refresh_token, expires_at }`. Managed automatically, never exported. |
| `mp_driveFileId` | string | Google Drive file ID of the backup JSON — set on first save, reused on subsequent syncs |
| `mp_driveSyncedAt` | string | ISO timestamp of last successful sync |

---

## Views

Four top-level views switched by `setView(...)`:

| View | Description |
|------|-------------|
| `plan` | Main view — weekly grid, suggestions, favourites, nutrition summary |
| `shopping` | Generated shopping list by category with total price estimate |
| `fryser` | Freezer tracker — logged batch-cook weeks, portion countdown, age warnings |
| `settings` | API keys, defaults, meal history, data import/export |

---

## Plan view

- **Weekly grid** — table of weeks × days. Cells show meal emoji, name, and a `ProteinBadge` pill. Click empty cell to enter "select mode" (amber highlight); click meal card to assign. Drag meal cards directly onto cells. All cells in a row share equal height regardless of content.
- **Drag and drop** — `draggable` on suggestion/favourite cards and on meals already in the grid. `onDragOver`/`onDrop` on grid cells. A `dragSource` state (`{week,day}` or `null`) distinguishes the two cases: dragging from the grid to another grid cell **swaps** the two meals; dragging from suggestions/favourites onto an occupied cell displaces the existing meal back to suggestions.
- **Plan modal** — clicking an assigned meal opens a detail modal with recipe, nutrition, price, and a notes textarea. Header includes a ★ favourite button (amber when active) to star/unstar the meal without leaving the modal. Separate 🗑 Fjern fra plan button prevents accidental deletion. Notes saved to `mp_mealNotes` on modal close. ESC closes the modal (saves notes first).
- **Suggestion modal** — clicking an expanded suggestion card opens a detail overlay. ESC closes it (priority over plan modal in the shared ESC handler).
- **Protein stats column** — rightmost grid column shows actual vs. target counts per protein type for each week.
- **Weekly nutrition summary** — shown below the grid for weeks where at least one meal has recipe data loaded. Summed from `mp_recipeCache` as 1 portion of each planned meal; updates automatically as recipes load. Label format: `NÆRING UKE N — 1 porsjon × M middager (ukestotal per person)`.
- **Load all recipes button** — "Last alle oppskrifter" appears above the nutrition summary when uncached planned meals exist. Calls `fetchAllRecipes()` which iterates unique planned meals and fetches each sequentially.
- **Progress bar** — filled days vs. total slots for active weeks.
- **Favourites panel** — toggled via ★ button. Shows starred meals as draggable chips; clicking one adds it back to the suggestion list.
- **Suggestion cards** — grid of AI-generated meals. Click to expand inline (full-width) showing name, cuisine, protein type, and prep time. Recipe is **not** fetched on expand — only fetched when opened via plan modal. Drag to grid or click in select mode to assign.
- **Filters** — filter suggestions by protein type. Applied client-side, no re-fetch.
- **"→ Fryser" button** — appears in the week label cell when the week has at least one non-leftover meal. Calls `addWeekToFreezer(week)`, which logs all non-leftover meals for that week to `mp_freezerItems` with `remaining = total = portions` and `cookedAt = today`, then navigates to the Fryser view.
- **"✕ Tøm" button** — clears the plan. Located beside the generate button in the suggestions panel (not in the nav bar).

---

## Fryser view

Freezer inventory for tracking batch-cooked portions.

**Data model** — each entry in `mp_freezerItems`:
```js
{ id, name, emoji, protein, remaining, total, cookedAt }
// id: `${Date.now()}-${name}` — unique key
// cookedAt: "YYYY-MM-DD" ISO string
```

**Layout:**
- Header: "🧊 Fryser" + green badge showing total active portions remaining. Tab label also shows active count.
- Items grouped by `cookedAt` date, most recent first. Date heading in Norwegian locale: `LAGET DD. MMMM YYYY`.
- Each item row: emoji + name + `ProteinBadge` + `remaining/total` counter with **−** / **+** buttons + **✕** remove.
- Depleted items (`remaining === 0`): 40% opacity, "Tomt" label replaces the −/+ controls.
- Items ≥ 90 days old: amber `⚠ Nd gammel` badge shown next to the protein pill; card border shifts to amber tint (`#4a3a1a`).
- "Tøm tomme" button (top-right) — removes all depleted items. Only shown when at least one item is depleted.
- Empty state message with instructions to use "→ Fryser" in the plan view.

**`addWeekToFreezer(week)`** — collects all non-null, non-leftover meals for the week, maps each to a freezer entry (`remaining = total = portions`), appends to `freezerItems`, then navigates to `"fryser"` view.

**Ratings** — 👍 / 👎 buttons appear on a Fryser item row once `remaining < total` (at least one portion eaten). 👍 adds the meal to `mp_favourites` (same object shape as suggestion cards) and removes it from `dislikedMeals`. 👎 adds the meal name to `mp_dislikedMeals` and removes it from favourites. The buttons toggle their border/background to show the active state. A "👎 Likt ikke" badge appears in the item's subtitle row when it's in the disliked list. `mp_dislikedMeals` is viewable and clearable per-item (or all at once) in Innstillinger → Liker ikke.

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
`POST /v1/messages` — returns `{ components: [{name, ingredients[]}], steps, nutrition, pricePerPortion?, tips? }`. Called when a plan modal is opened or via the "Last alle oppskrifter" button. **Not called on suggestion card expand** — recipe is only fetched when a meal is already in the plan. Result cached in `mp_recipeCache`. Prompt scales ingredients to the configured `portions` count; nutrition is always requested per 1 portion. AI always estimates `pricePerPortion`; Kassal overrides it if it finds at least 1 price match. Prompt includes the active unit system (metric: g/kg/dl/ml; imperial: oz/lbs/cups/fl oz). Prompt explicitly requests 1–3 batch/freeze tips (`tips` array) — how to pack and freeze the dish, and the best reheating method (oven, microwave, pan). Tips must not suggest any per-dinner prep or fresh components. Tips are displayed in the plan modal and in suggestion card expanded view when cached. Old cached recipes with flat `ingredients[]` still render correctly via a backward-compatible fallback in the modal.

### Generate shopping list — `generateShoppingList(force?)`
`POST /v1/messages` — returns `{ categories: [{name, emoji, items: [{name, amount}], price: {low, high}}], totalPrice: {low, high} }`. Each category includes a `price` range estimate shown in the UI. Only regenerates when `planKey` changes or `force=true`. `planKey` is a hash of planned meal names + portions. Prompt includes the active unit system. Regenerating also clears `checkedItems` for that week.

---

## Shopping view

- **Week tabs** — one tab per active week. Shows a `checkedCount/totalCount` amber fraction badge when any items are checked for that week.
- **Check-off** — each item `<li>` is clickable (`cursor: pointer`). Clicking toggles `checkedItems[week][catName|itemName]`. Checked items show name with `line-through`, dimmed color, and 55% opacity. Sub-items are hidden while the parent is checked.
- **"✕ Nullstill" button** — appears in the shopping header only when ≥1 item is checked for the current week. Clears all checked items for that week. Styled as a ghost/outline button matching the other header buttons.
- **Persistence** — `mp_checkedItems` persists in localStorage so check-off state survives page refresh. Cleared automatically when the list is regenerated for that week.

---

## Kassal price fetch — `fetchKassalPrice(ingredients)`

Picks up to 4 meaningful ingredients (skips salt, water, oil, etc.), strips amounts and adjectives, extracts the main noun word, searches `kassal.app/api/v1/products?search={word}&size=5`. Takes the minimum price found per ingredient, sums them, divides by `portions`. Returns `{low, high, source:"kassal"}` if ≥1 ingredient matched, otherwise `null`. Attached to `recipe.pricePerPortion` after recipe fetch, overriding the AI estimate.

**Hobby plan limits** — the free Kassal API tier allows 60 req/min, no commercial use, no support. Each recipe fetch makes up to 4 Kassal requests (one per meaningful ingredient). In normal use this is not a concern — a user would need to expand ~15 recipe cards within a single minute to approach the limit, which is unlikely. No rate-limit handling is implemented; if the limit is hit, `fetchKassalPrice` will return `null` and the app falls back to the AI price estimate silently. If usage grows, the only mitigation needed would be reducing the ingredient cap below 4 or adding a short delay between searches.

---

## Export / import

| Action | Implementation |
|--------|---------------|
| Export plan | Blob URL → `middagsplan-{date}.json`. Includes: `plan`, `weeks`, `portions`, `suggestions`, `proteinTargets`, `cuisineTargets`, `enabledCuisines`, `suggestionCount`, `maxTime`, `exclusions`, `units`, `shoppingLists`, `favourites`, `mealNotes`, `mealHistory`, `freezerItems`. Excludes: API keys (`mp_anthropicKey`, `mp_kassalKey`) and recipe cache (`mp_recipeCache` — recipes are re-fetched on demand). |
| Import plan | `FileReader` → JSON parse → restore state slices individually. API keys never imported. Recipe cache is not included so recipes will be re-fetched when meals are opened. `freezerItems` restored if present in the file. |
| Export shopping list | Blob URL → `handleliste.txt`. Plain text with category sections and price estimate. |
| Print / share | `window.open('','_blank')` → `document.write(html)`. Dark-theme page (matches app slate palette) with weekly grid + shopping list. `@media print` overrides to white-on-light for physical printing. Includes a Print button and a Lukk button; ESC also closes the popup window. **Note:** `<\/script>` must be escaped inside the JS template literal used to build the popup HTML — raw `</script>` terminates the outer Babel script block early and breaks the app. |

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
2. **Standardverdier** — weeks, portions, suggestion count, max time, and measurement units (Metrisk / Imperialt toggle). Switching units clears `mp_recipeCache` and `mp_shoppingList` immediately, since AI-generated amounts are baked into the cached text. Changing portions calls `changePortions(n)` which also clears `recipeCache`, `shoppingLists`, and `lastShoppingKeys` — so re-fetched recipes reflect the new count.
3. **Mathistorikk** — scrollable list of recent meals, clear button.
4. **Liker ikke** — list of disliked meal names with per-item ✕ removal and a "Tøm liste" button. Empty state explains how to add entries (via 👎 in Fryser view).
5. **Data** — export plan, import plan, export shopping list, clear recipe cache, clear plan.

---

## Units

`mp_units` — `"metric"` (default) or `"imperial"`. Toggled in Innstillinger → Standardverdier.

- **Metric**: g, kg, dl, ml, liter
- **Imperial**: oz, lbs, cups, fl oz, tbsp, tsp

The active unit is injected as a sentence into the `fetchRecipe` and `generateShoppingList` prompts. Because amounts are stored as free text in `mp_recipeCache` (e.g. `"500g kylling"`), switching units calls `changeUnits()` which resets `recipeCache`, `shoppingLists`, and `lastShoppingKeys` — forcing fresh AI calls in the new system. `changePortions(n)` does the same: ingredient amounts are scaled and baked into the cached text, so any portions change also clears those caches.

---

## Mobile layout

Breakpoint: `window.innerWidth < 640` — tracked in `isMobile` state with a `resize` listener.

**On mobile (< 640px):**
- Header controls row hidden entirely (UKE, PORSJONER, Proteinmål, Kjøkken, Maks tid, Skriv ut)
- Compact header padding (`12px 16px 10px`)
- Week selector shown in header when `weeks > 1` — buttons 1…N set `mobileWeek` (plan view) and `shoppingWeek` (shopping view) together
- Plan grid renders only the `mobileWeek` row instead of all weeks
- Fixed bottom nav bar (`height: 56px`, `zIndex: 200`) with four tabs: Plan / Handleliste / Fryser / Innstillinger
- Main content has `paddingBottom: 72px` to clear the bottom nav bar
- No `zoom: 1.1`

**On desktop (≥ 640px):**
- Full header with all controls and top nav tabs
- All weeks rendered in the plan grid
- `zoom: 1.1` applied via `@media (min-width: 640px)`
- Bottom nav bar not rendered

---

## Styling

Dark neutral slate: `#0e0f11` background, `#18191c` cards, `#141517` inset areas, `#22232a`/`#2a2b30` borders.
Warm amber accent: `#e8a838` for active states, buttons, highlights.
Text: primary `#e4ddd0`, secondary `#b4b2c2`, muted `#747280`.
Font: `'Georgia', 'Times New Roman', serif` for headings/body; `sans-serif` for UI labels and data.
All layout via inline styles — no CSS classes except global resets and scrollbar styling.
Mobile friendly via `flexWrap`, `auto-fill` grid columns, and a dedicated mobile layout at `< 640px`.
`zoom: 1.1` is restricted to `@media (min-width: 640px)` — not applied on phones.
Plan grid uses `tableLayout: "fixed"` so all day columns stay equal width regardless of meal name length. `maxWidth` on the main container and header is 1400px (up from 1000px) to better utilise wide screens.
Grid rows use equal-height cells: `<td>` has `height: "1px"` (table layout trick meaning "fill the row") and the inner div uses `height: "100%"` so all cells in a row stretch to match the tallest.
Plan grid table has `minWidth: 560px` so it scrolls horizontally on narrow screens rather than squashing columns.

---

## Running locally

```
python3 -m http.server 8080
```

Open `http://localhost:8080`. Add Anthropic API key in ⚙ Innstillinger before generating suggestions.
