# CLAUDE.md — mealprepping

Browser-based weekly meal planner for a Norwegian family doing batch-cook meal prep. Single self-contained `index.html` — React 18 + Babel via CDN, no build step, served with `python3 -m http.server 8080`.

**Meal prep philosophy:** everything is cooked on one batch day, frozen in portions, and dinner is reheating and eating only — no per-dinner prep whatsoever. All AI prompts (suggestions, recipes, shopping list) enforce this strictly.

**Localisation:** the UI and all AI-generated content (suggestions, recipes, shopping lists) are in Norwegian bokmål. All three AI prompts begin with `Svar alltid på norsk bokmål.` to enforce this. The codebase itself is in English. There is no i18n layer — Norwegian is hardcoded throughout. Prompts also explicitly require common supermarket ingredient names (e.g. "løk" not "kepaløk", "kokosmelk" not "kokosmilk") to avoid confusion when the same ingredient appears under different names in the same recipe or shopping list.

---

## Key files

| File | Purpose |
|------|---------|
| `index.html` | Entire application — React components, CSS, all logic |

---

## Architecture

- **No build step** — React 18 and Babel Standalone loaded from `unpkg.com` CDN. JSX transpiled in-browser via `<script type="text/babel">`. Pinned to exact versions (react / react-dom 18.3.1, @babel/standalone 7.29.8) with sha384 `integrity` hashes, and a `Content-Security-Policy` meta tag allows scripts only from unpkg (plus the inline Babel block) and network calls only to Anthropic, Kassal and Google. Upgrading a CDN file means changing its URL and hash together; a new external service needs its origin added to `connect-src`.
- **All state in localStorage** — prefixed `mp_`. Initialized via lazy `useState(() => lsGet(...))`, persisted with individual `useEffect` hooks per state slice.
- **Anthropic API** — called directly from the browser using `fetch`. Requires `anthropic-dangerous-direct-browser-access: true` header to bypass CORS. Model: `claude-sonnet-5`, with `thinking: {type: "disabled"}` on every call (Sonnet 5 thinks by default; disabled keeps latency and the tuned `max_tokens` budgets unchanged). Always read the response via `content.find(b => b.type === "text")`, never `content[0]`.
- **Kassalapp API** — `kassal.app/api/v1/products` for real Norwegian grocery prices. Optional — falls back to AI price estimates if key is absent.
- **No backend** — everything runs client-side.

---

## localStorage keys

All keys use the `mp_` prefix.

| Key | Type | Description |
|-----|------|-------------|
| `mp_anthropicKey` | string | Anthropic API key — required for all AI features |
| `mp_kassalKey` | string | Kassalapp API key — optional, enables real grocery prices |
| `mp_plan` | array[4][7] | Weekly grid — 4 weeks × 7 days, each cell is a meal object or null |
| `mp_suggestions` | array | Current AI-generated meal suggestions |
| `mp_favourites` | array | Starred meals, persists across sessions |
| `mp_mealHistory` | array | Names of all meals ever assigned to the plan (max 100), sent to AI to avoid repetition |
| `mp_mealNotes` | object | Free-text notes per meal, keyed by meal name |
| `mp_recipeCache` | object | Full recipe + nutrition data per meal, keyed by meal name |
| `mp_shoppingLists` | object | Shopping lists keyed by week index — each value is `{categories, totalPrice}` |
| `mp_lastShoppingKeys` | object | planKey snapshots keyed by week index — used to detect when a week's list needs regeneration |
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
| `mp_driveSyncedHash` | string | Hash of the last payload this device and Drive agreed on — the base for three-way sync decisions |
| `mp_preImportBackup` | object | Data replaced by the last import (without recipe cache) — powers "Angre siste import" |

---

## Views

Four top-level views switched by `setView(...)`:

| View | Description |
|------|-------------|
| `plan` | Main view — weekly grid, suggestions, favourites, nutrition summary |
| `shopping` | Generated shopping list by category with total price estimate |
| `fryser` | Freezer tracker — logged batch-cook weeks, portion countdown, age warnings |
| `settings` | API keys, defaults, meal history, data import/export |

Navigation is hash-only (`#plan`, `#shopping`, `#fryser`, `#settings`): `setView` updates `location.hash`, and a `hashchange` listener updates the view, so deep links, bookmarks and Back/Forward all work. **Do not add a `pushState`/`popstate` layer next to it** — one existed until the September 2026 audit and fought the hash: a hash change fires `popstate` with a null state, whose handler reset the view to `plan`. Clicking a nav button then bounced back to the plan at random (about 4 times in 5 in a browser test), and Back skipped views.

---

## Plan view

- **Weekly grid** — table of weeks × days. Cells show meal emoji, name, and a `ProteinBadge` pill. Click empty cell to enter "select mode" (amber highlight); click meal card to assign. Drag meal cards directly onto cells. All cells in a row share equal height regardless of content.
- **Drag and drop** — `draggable` on suggestion/favourite cards and on meals already in the grid. `onDragOver`/`onDrop` on grid cells. A `dragSource` state (`{week,day}` or `null`) distinguishes the two cases: dragging from the grid to another grid cell **swaps** the two meals; dragging from suggestions/favourites onto an occupied cell displaces the existing meal back to suggestions — also when the incoming item is a leftover day. Removing a leftover day from the plan never adds it to suggestions.
- **Plan modal** — clicking an assigned meal opens a detail modal with recipe, nutrition, price, and a notes textarea. Header includes a ★ favourite button (amber when active) to star/unstar the meal without leaving the modal. Separate 🗑 Fjern fra plan button prevents accidental deletion. Notes are saved to `mp_mealNotes` 500 ms after typing stops and again on close (all close paths call `saveNote`); an empty note removes the key instead of storing `''`. ESC closes the modal (saves notes first).
- **Suggestion modal** — clicking an expanded suggestion card opens a detail overlay. ESC closes it (priority over plan modal in the shared ESC handler).
- **Protein stats column** — rightmost grid column shows actual vs. target counts per protein type for each week.
- **Weekly batch time estimate** — shown below the grid for each week with at least one non-leftover meal. When recipes are cached, uses `activeMins` + `passiveMins` fields returned by `fetchRecipe`: active prep is serial (`sum(activeMins)`); passive cooking assumes 4 concurrent slots (1 oven + 3 burner simmers) — passive times sorted descending, grouped into fours, sum the max of each group. Only shown when every non-leftover meal in the week has a cached recipe with `activeMins` — hidden until all recipes are loaded to avoid showing a misleading prepTime-based overestimate. Shows single `≈ Xt Ymin` estimate. Card uses `width: fit-content` so it doesn't span the full container. Border and value shift amber with a `⚠` prefix when estimate exceeds 480 min (8 hours).
- **Weekly nutrition summary** — shown below the grid for weeks where at least one meal has recipe data loaded. Summed from `mp_recipeCache` as 1 portion of each planned meal; updates automatically as recipes load. Label format: `NÆRING UKE N — 1 porsjon × M middager (ukestotal per person)`.
- **Load all recipes button** — "Last alle oppskrifter" appears above the nutrition summary when uncached planned meals exist. Calls `fetchAllRecipes()` which iterates unique planned meals and fetches each sequentially.
- **Progress bar** — filled days vs. total slots for active weeks.
- **Favourites panel** — toggled via ★ button. Shows starred meals as draggable chips; clicking one adds it back to the suggestion list.
- **Suggestion cards** — grid of AI-generated meals. Clicking a card opens the suggestion modal (full detail overlay) showing name, badges, description, and a "Last inn oppskrift" button. Recipe is **not** fetched on card click — only fetched when a meal is already in the plan. Drag to grid or click in select mode to assign. Manually added cards additionally show a ✏ pencil icon in the top-right (beside the prep time badge) and a snowflake batch score (`❄❄···`) on their own row below the protein/category badges.
- **Filters** — filter suggestions by protein type. Applied client-side, no re-fetch.
- **Manual meal entry** — text input below the generate/clear buttons. Typing a meal name and pressing Enter or "Legg til" calls `addManualMeal()` (max_tokens: 1200), which always returns 3 variants of the dish. The variants appear in a centered modal ("Velg en rett") — the user picks one, which is then prepended to `suggestions`. Duplicate guard prevents adding a meal already in the list. Loading state ("Legger til…") and error feedback shown inline. Exclusions/allergens are applied to this prompt (same wording as `generateSuggestions`). Store-bought components (pizzabunn, tortillas, etc.) are explicitly allowed. Manually added cards show a ✏ pencil icon in the top-right and a ✕ remove button (gated by `meal.batchScore`). `batchScore` is 1–5: how well the dish suits batch cooking and freezing (1 = poor, e.g. sushi; 5 = ideal, e.g. stews). AI-generated suggestions intentionally omit `batchScore` — they are already enforced batch-friendly by the prompt, so a score would always be high and uninformative. The suggestion modal shows a scored block with a spelled-out label ("Ikke egnet for batch", "Perfekt for batch", etc.) and a tinted border when `batchScore` is present.
- **"→ Fryser" button** — appears in the week label cell when the week has at least one non-leftover meal. Calls `addWeekToFreezer(week)`, which logs all non-leftover meals for that week to `mp_freezerItems` with `remaining = total = portions` and `cookedAt = today`, then navigates to the Fryser view.
- **"✕ Tøm" button** — clears the plan. Located beside the generate button in the suggestions panel (not in the nav bar).
- **Maks tid slider** — inline in the suggestions action row (beside "Tøm"), not in the header. Controls max prep time for generation and filters the visible suggestion cards client-side.

---

## Fryser view

Freezer inventory for tracking batch-cooked portions.

**Data model** — each entry in `mp_freezerItems`:
```js
{ id, name, emoji, protein, remaining, total, cookedAt, freezerLifeDays }
// id: `${Date.now()}-${name}` — unique key
// cookedAt: "YYYY-MM-DD" local calendar date (localDateString(), not toISOString(), which is UTC)
// freezerLifeDays: nullable integer — max recommended days in freezer, copied from recipeCache at log time; null if recipe not yet fetched
```

**`FREEZER_LIFE_DEFAULTS`** — protein-type fallback shelf lives used when `freezerLifeDays` is null: `{ fisk: 60, kylling: 90, kjott: 90, vegeta: 90 }`. Fish dishes default to 60 days; all others to 90.

**Layout:**
- Header: "🧊 Fryser" + green badge showing total active portions remaining. Tab label also shows active count.
- Items grouped by `cookedAt` date, most recent first. Date heading in Norwegian locale: `LAGET DD. MMMM YYYY`.
- Each item row: emoji + name + `ProteinBadge` + `remaining/total` counter with **−** / **+** buttons + **✕** remove.
- Depleted items (`remaining === 0`): 40% opacity, "Tomt" label replaces the −/+ controls.
- **Age warnings** — computed per date-group (all items cooked on the same day). Age is `daysSince(cookedAt)`: whole local calendar days, so it ticks over at midnight. `batchShelfLife` = `Math.min` of each item's `freezerLifeDays || FREEZER_LIFE_DEFAULTS[protein] || 90`. Two states: `isOld` (age ≥ shelfLife) shows amber `⚠ Nd gammel` badge + amber border tint (`#4a3a1a`); `isAgeing` (within 14 days of limit) shows `⏰ N dager igjen`. The batch warns based on its most perishable item — health/safety motivation (e.g. a fish gratin at 55 days should warn even if other items in the batch are fine).
- "Fjern tomme" button (top-right) — removes all depleted items. Only shown when at least one item is depleted.
- "Fjern batch" (per date group) — removes every item cooked that day, after a "Fjerne hele batchen?" confirmation.
- Empty state message with instructions to use "→ Fryser" in the plan view.

**`addWeekToFreezer(week)`** — collects all non-null, non-leftover meals for the week, maps each to a freezer entry (`remaining = total = portions`), reads `freezerLifeDays` from `recipeCache[meal.name]` if available (null otherwise), appends to `freezerItems`, then navigates to `"fryser"` view.

**Ratings** — 👍 / 👎 buttons appear on a Fryser item row once `remaining < total` (at least one portion eaten). 👍 adds the meal to `mp_favourites` (same object shape as suggestion cards) and removes it from `dislikedMeals`. 👎 adds the meal name to `mp_dislikedMeals` and removes it from favourites. The buttons toggle their border/background to show the active state. A "👎 Likt ikke" badge appears in the item's subtitle row when it's in the disliked list. `mp_dislikedMeals` is viewable and clearable per-item (or all at once) in Innstillinger → Liker ikke.

---

## AI calls

### Generate suggestions — `generateSuggestions()`
`POST /v1/messages` — returns `{ meals: [...] }`. Prompt includes:
- Protein targets per week (soft guidance)
- Cuisine targets per week (soft guidance)
- Max prep time (hard constraint)
- Exclusions / allergens — enforced on ingredient names, dish names, and inspiration sources (prevents "fårikål-inspirert" style workarounds)
- Already-planned meals (avoid repeats within current plan)
- Meal history (`mp_mealHistory`, last 30 entries) — avoids long-term repetition

### Fetch recipe — `fetchRecipe(meal)`
`POST /v1/messages` — returns `{ components: [{name, ingredients[]}], steps, nutrition, pricePerPortion?, tips?, activeMins, passiveMins, freezerLifeDays }`. Called when a plan modal is opened or via the "Last alle oppskrifter" button. **Not called on suggestion card click** — recipe is only fetched when a meal is already in the plan. Result cached in `mp_recipeCache` after passing through `normalizeRecipe()`. `max_tokens` is 4000. Failures (non-OK status, `stop_reason: "max_tokens"`, unparseable JSON, network) set `recipeError` and the modal shows the message with a "Prøv igjen" button; "Last alle oppskrifter" lists failed dishes. A result is discarded if portions or units changed while it was loading (`scaleRef`), so the cache never holds amounts for the wrong scale. Prompt scales ingredients to the configured `portions` count; nutrition is always requested per 1 portion. AI always estimates `pricePerPortion`; Kassal overrides it if it finds at least 1 price match. Prompt includes the active unit system (metric: g/kg/dl/ml; imperial: oz/lbs/cups/fl oz). In metric mode the prompt additionally instructs the AI to use dl (not grams) for dry goods (ris, pasta, linser, gryn, mel) so cached recipes stay unit-consistent with the shopping list. Prompt explicitly requests 1–3 batch/freeze tips (`tips` array) — how to pack and freeze the dish, and the best reheating method (oven, microwave, pan). Tips must not suggest any per-dinner prep or fresh components. Tips are displayed in the plan modal when cached. `freezerLifeDays` is an integer representing the recommended maximum days in the freezer for this specific dish (e.g. 60 for fish, 90 for meat stews, 120 for some chicken dishes) — stored in the cache and copied to freezer entries when the week is logged. Old cached recipes with flat `ingredients[]` still render correctly via a backward-compatible fallback in the modal.

### Generate shopping list — `generateShoppingList(force?)`
`POST /v1/messages` — returns `{ categories: [{name, emoji, items: [{name, amount, items?: [{name, amount}]}], price: {low, high}}], totalPrice: {low, high} }`. Each category includes a `price` range estimate shown in the UI. Only regenerates when `planKey` changes or `force=true`. `max_tokens` is 12000; a truncated reply shows an error instead of a partial list. The reply passes through `normalizeShoppingList()`. `planKey` is a hash of planned meal names + portions. Prompt includes the active unit system. Regenerating also clears `checkedItems` for that week.

**Recipe-aware ingredient input:** Before calling the API, each planned meal is checked against `mp_recipeCache`. If a cached recipe exists with ingredients, those ingredient strings (already scaled to `portions`) are passed directly into the prompt so the AI aggregates known data rather than estimating. Falls back to meal name only for uncached meals. This makes ingredient names and amounts consistent between regenerations for cached meals.

**Dish context sub-items:** Each ingredient in the response includes an `items` array listing which dishes use it and how much. The prompt requires sub-items for all ingredients without exception — no hardcoded exemption list. Category-level collapse in the UI handles the length concern instead.

**Ingredient consolidation:** The prompt instructs the AI to merge varieties of the same base ingredient into one line with a summed amount (e.g. jasminris + langkornet ris → "Ris"), unless the specific variety is dish-essential (e.g. spaghetti for bolognese, basmatiris for Indian dishes). The sub-item rows still show which dish uses what. This is a soft guideline — the AI may keep genuinely distinct varieties separate (jasminris vs. basmatiris are both considered dish-essential). Also applies to `generateShoppingList` for uncached meals.

**Freezer-aware:** `freezerCoverage(plan, freezerItems, week, portions)` sums `remaining` per dish name (case-insensitive) across all freezer entries and hands stock to earlier weeks first; each planned cell needs `portions` portions. Covered dishes inject one note line each: fully covered → skip ingredients; partly covered → scale to the missing portions. The same result drives `allFrozen` in the shopping view.

**Store-bought components:** The prompt instructs the AI to list commonly pre-made components (pizzabunn, tortillas, butterdeig, etc.) as a single finished item rather than expanding into individual dough ingredients.

---

## Shopping view

- **Week tabs** — one tab per active week. Shows a `checkedCount/totalCount` amber fraction badge when any items are checked for that week.
- **Check-off** — each item `<li>` is clickable (`cursor: pointer`). Clicking toggles `checkedItems[week][catName|itemName]`. Checked items show name with `line-through`, dimmed color, and 55% opacity. Sub-items are hidden while the parent is checked.
- **"✕ Nullstill" button** — appears in the shopping header only when ≥1 item is checked for the current week. Clears all checked items for that week. Styled as a ghost/outline button matching the other header buttons.
- **Persistence** — `mp_checkedItems` persists in localStorage so check-off state survives page refresh. Cleared automatically when the list is regenerated for that week.
- **Freezer notice** — shown above the list when any planned meals are already in the freezer with `remaining > 0`. Single-sentence summary (e.g. "Kyllinggryte ligger allerede i fryseren og er ikke inkludert i listen."). When `allFrozen` (all planned meals covered by freezer), the "Har du dette hjemme?" pantry category and the total price estimate are hidden — the list is effectively empty and showing them would be misleading.
- **Uncached meals notice** — amber banner shown when any planned meals lack cached recipe data, indicating that ingredient amounts are AI-estimated rather than derived from actual recipes. Banner disappears once all recipes are loaded and the list is regenerated.
- **Dish context sub-items** — each ingredient row has indented sub-rows showing which dish uses it and how much. Sub-items are hidden when the parent item is checked off.
- **Collapsible categories** — each category header is clickable to collapse/expand the item list. Collapsed headers show a `▸` chevron and a `checked/total` count badge so progress is visible without expanding. State is in `collapsedCategories` (`useState({})`) — keyed by week index (`{ [weekIndex]: Set<categoryName> }`) so collapsed state is independent per week. Not persisted, resets on page refresh.

---

## Kassal price fetch — `fetchKassalPrice(ingredients)`

`kassalSkip()` drops pantry staples (salt, water, oil, etc.) matched as whole words or compound endings ("olivenolje", "hvetemel" — but not "melk"). `kassalSearchWord()` strips leading amounts and units as whole words only ("3 gulrøtter" → "gulrøtter", not "ulrøtter") and skips adjectives ("1 stor løk" → "løk"). Up to 4 distinct words are searched in parallel at `kassal.app/api/v1/products?search={word}&size=5`. Takes the minimum price found per word, sums them, divides by `portions`. Returns `{low, high, source:"kassal"}` only if at least 2 words matched (or all of them, when fewer than 2 were searched); otherwise `null`, and the AI estimate is kept.

**Hobby plan limits** — the free Kassalapp API tier allows 60 req/min, no commercial use, no support. Each recipe fetch makes up to 4 Kassal requests (one per meaningful ingredient). In normal use this is not a concern — a user would need to expand ~15 recipe cards within a single minute to approach the limit, which is unlikely. No rate-limit handling is implemented; if the limit is hit, `fetchKassalPrice` will return `null` and the app falls back to the AI price estimate silently. If usage grows, the only mitigation needed would be reducing the ingredient cap below 4 or adding a short delay between searches.

---

## Data validation

Imported files, Drive backups, stored localStorage data and AI replies are treated as untrusted. Top-level helpers normalise them before they reach state:

- `normalizeData(d)` — returns only recognised, well-formed slices: `plan` padded to 4×7, `weeks` 1–4, `portions` 1–20, meals need a string `name`, `batchScore` clamped to 1–5, freezer items get a valid `cookedAt`; shopping lists and recipes go through their own normalisers. Used by import, undo import, Drive pull, and `lsGetNorm()` for the risky slices at startup.
- `normalizeMeal`, `normalizeShoppingList` (every category gets an `items` array, amounts become strings) and `normalizeRecipe` (numeric nutrition and minutes, array `tips`/`steps`) are also applied to AI replies.
- `ErrorBoundary` wraps `<App />`: a render crash shows "Noe gikk galt" with "Gå til planen", "Last ned data (.json)" (all `mp_` data except keys and tokens) and "Prøv igjen", instead of a blank page.

These helpers, plus `esc()`, `hashString`, `decideSync`, `freezerCoverage`, `kassalSkip`, `kassalSearchWord`, `localDateString` and `daysSince`, are top-level so Playwright tests can call them through `page.evaluate`.

---

## Export / import

| Action | Implementation |
|--------|---------------|
| Export plan | Blob URL → `middagsplan-{date}.json`. Includes: `plan`, `weeks`, `portions`, `suggestions`, `proteinTargets`, `cuisineTargets`, `enabledCuisines`, `suggestionCount`, `maxTime`, `exclusions`, `units`, `shoppingLists`, `lastShoppingKeys`, `favourites`, `mealNotes`, `mealHistory`, `freezerItems`, `dislikedMeals`. Excludes: API keys and recipe cache (`mp_recipeCache` — recipes are re-fetched on demand). |
| Import plan | `FileReader` → JSON parse → `normalizeData()` → preview dialog with counts ("Importere middagsplan?"). Nothing changes until "Importer" is clicked; the current data (minus recipe cache) is first saved to `mp_preImportBackup`, and "↶ Angre siste import" appears in Settings → Data. If portions or units differ, the recipe cache and shopping lists are cleared (amounts are baked in). Files with no recognised data are rejected. API keys never imported. Works on mobile (the hidden file input sits at the app root). |
| Export shopping list | Blob URL → `handleliste.txt`. Plain text with category sections and price estimate. |
| Print / share | `window.open('','_blank')` → `document.write(html)`. Dark-theme page (matches app slate palette) with weekly grid + shopping list. `@media print` overrides to white-on-light for physical printing. Includes a Print button and a Lukk button; ESC also closes the popup window. **Note:** `<\/script>` must be escaped inside the JS template literal used to build the popup HTML — raw `</script>` terminates the outer Babel script block early and breaks the app. All data inserted into the popup HTML must go through `esc()` — the popup shares the app's origin, so unescaped meal or ingredient names could run script with access to the stored API keys. |

---

## Google Drive sync

Auto-saves to a single JSON file (`reheat-and-eat-backup.json`) in the user's Drive using OAuth PKCE flow with `drive.file` scope.

**Payload** — includes everything except API keys and OAuth tokens: `plan`, `weeks`, `portions`, `suggestions`, `proteinTargets`, `cuisineTargets`, `enabledCuisines`, `suggestionCount`, `maxTime`, `exclusions`, `units`, `shoppingLists`, `lastShoppingKeys`, `recipeCache`, `favourites`, `mealNotes`, `mealHistory`, `freezerItems`, `dislikedMeals`. Recipe cache is included so other devices don't need to re-fetch recipes.

**Sync model** — one routine, `doSync`, runs through `syncDrive()` (a promise chain, so Drive requests never overlap). It compares three hashes: this device's payload, the Drive file, and the last version both agreed on (`mp_driveSyncedHash`, the base). `decideSync()` returns `in-sync`, `push` (only local changed), `pull` (only Drive changed) or `conflict` (both changed, or no base while local has content). A conflict opens "Endringer både her og i Google Drive" with "Behold denne enheten" / "Bruk Drive-versjonen". A fresh device with no content pulls without asking.

- The Drive file's `modifiedTime` is compared with `remoteModifiedRef` (per tab) before every upload and check; the full file is only downloaded when it changed, so another device's newer save is reconciled instead of overwritten.
- **Triggers:** startup and post-OAuth reconcile (`checkRemote`); auto-save 2 s after any payload slice changes, but only once `driveReadyRef` is true (this tab has reconciled — nothing is uploaded before the startup download is compared); `online` and `visibilitychange → visible` (at most every 30 s); `visibilitychange → hidden` flushes a pending save; "Synkroniser nå" in settings.
- **Payload:** `buildDrivePayload()` picks `DRIVE_KEYS` in a fixed order so local state and a downloaded backup hash identically; uploads add `savedAt`. A new synced slice must be added to `DRIVE_KEYS`, `payloadRef.current` and the auto-save dep array. Local edits made offline or in a closed tab are detected on the next start because the base hash is persisted.
- **Errors:** 401 forces a token refresh and retries once; 404 or a trashed file clears `driveFileId` and retries (a new file is created only if the search, `trashed=false`, newest first, finds none). Errors and conflicts show the amber Drive badge on the settings tab even while connected. Remote data passes through `normalizeData()` before it is applied; decisions use the raw download's hash so normalisation can't cause false conflicts.
- **Other tabs:** a `storage` event on any `mp_` data key (Drive bookkeeping keys excluded) blocks the stale tab with "Appen er endret i en annen fane" and a reload button, so it can't overwrite the other tab's changes.

**Token lifecycle:**
- PKCE verifier stored in `localStorage` (not `sessionStorage`) to survive cross-origin redirects on mobile.
- `getValidAccessToken` refreshes the access token automatically using the stored refresh token.
- If the refresh returns `invalid_grant` (e.g. user revoked access externally), the token is cleared and `driveStatus` is set to `'expired'`. Callers detect the `'TOKEN_EXPIRED'` sentinel and show an amber reconnect prompt in settings. Any other refresh failure (offline, 5xx, non-JSON) returns `'NETWORK'` and keeps the token; the status becomes `'error'` and the next trigger retries.
- Disconnecting calls `https://oauth2.googleapis.com/revoke` to invalidate the token server-side before clearing localStorage. Manual disconnect also clears `mp_driveFileId`.
- `connectGoogleDrive` uses `useCallback` with `[googleClientId, googleClientSecret]` as deps — both must be in the array or the callback captures stale empty strings and silently does nothing.
- **Disconnection badge** — `hadDriveConnection` state (`useState(() => !!lsGet('driveFileId', null))`) detects prior connections on startup. When `!driveConnected && googleClientId && (driveStatus==='expired' || hadDriveConnection)`, an amber **Drive** pill appears on the desktop ⚙ Innstillinger button and an amber dot on the mobile nav settings tab. Manual disconnect clears `driveFileId`, so the badge disappears after refresh (intentional — user chose to disconnect). External revocation leaves `driveFileId` intact, so the badge persists across refreshes until reconnected.

---

## Cuisines

`CUISINE_LIBRARY` contains 19 predefined cuisines (Nordisk, Italiensk, Asiatisk, Meksikansk, Indisk, Japansk, Kinesisk, Thai, Gresk, Midtøsten, Latinamerikansk, Spansk, Fransk, Amerikansk, Vietnamesisk, Koreansk, Tyrkisk, Nordafrikansk, Filippinsk). No free-text entry — all cuisines come from the library.

`enabledCuisines` (localStorage array of keys, default: the first 5) controls which appear in the Kjøkken panel. Active cuisines show their CuisineCounter + ✕ to disable. Inactive cuisines appear as dashed + chips below the active list. Disabling a cuisine also removes its target from `cuisineTargets`. `allCuisines` is derived via `useMemo` filtering `CUISINE_LIBRARY` by `enabledCuisines`.

---

## Meal history

Every meal assigned to the plan (via click, select mode, or drag) is added to `mp_mealHistory` (max 100 unique names, oldest dropped first). The last 30 entries are included in the suggestion prompt. Viewable and clearable in Innstillinger.

---

## Settings page

Sections (in display order):

1. **API-nøkler** — Anthropic (required) and Kassal (optional). Password inputs with "Fjern" clear buttons, stored immediately in localStorage on change. Never included in plan exports.
2. **Google Drive Sync** — Client ID + Client Secret inputs (disabled when connected). "Koble til Google Drive" button; when connected shows sync status (syncing / synced / error / idle), "Synkroniser nå" button, and "Koble fra" disconnect button. Amber warning when token has expired (`driveStatus === 'expired'`), prompting reconnection. An amber badge also appears on the settings nav entry point (desktop pill, mobile dot) when Drive is disconnected — visible from any view so the user notices before going to the store with a stale list.
3. **Standardverdier** — weeks (1–4), portions (1–20 via Stepper), suggestion count (5–30 step 5), max prep time slider (15–120 min step 15), and measurement units (Metrisk / Imperialt toggle). Switching units clears `mp_recipeCache` and `mp_shoppingLists` immediately. Changing portions calls `changePortions(n)` which also clears those caches.
4. **Allergener og ekskluderinger** — free-text input for ingredients/allergens the AI should always avoid. "× Fjern alle" clear button shown when non-empty. Value is `mp_exclusions`, injected into all three AI prompts.
5. **Favoritter** — all starred meals shown as chips with per-item ✕ removal and a "Tøm alle" button. Empty state prompts to use ★ on a suggestion or in the plan.
6. **Liker ikke** — list of disliked meal names with per-item ✕ removal and a "Tøm liste" button. Empty state explains how to add entries (via 👎 in Fryser view).
7. **Mathistorikk** — scrollable wrapped list of recent meals as chips, with count and "Tøm historikk" button. Empty state explains meals are added automatically when assigned to the plan.
8. **Data** — export plan (.json), import plan (.json), export shopping list (.txt). Sub-section **Resett**: "Tøm oppskriftsbuffer" (clears `mp_recipeCache`) and "Tøm ukeplan" (clears plan + shopping lists; suggestions and favourites are kept, matching the confirmation text) — both use a custom confirmation modal.

---

## Units

`mp_units` — `"metric"` (default) or `"imperial"`. Toggled in Innstillinger → Standardverdier.

- **Metric**: g, kg, dl, ml, liter — dry goods (ris, pasta, linser, gryn, mel) use dl by convention
- **Imperial**: oz, lbs, cups, fl oz, tbsp, tsp

The active unit is injected as a sentence into the `fetchRecipe` and `generateShoppingList` prompts. Because amounts are stored as free text in `mp_recipeCache` (e.g. `"500g kylling"`), switching units calls `changeUnits()` which resets `recipeCache`, `shoppingLists`, and `lastShoppingKeys` — forcing fresh AI calls in the new system. `changePortions(n)` does the same: ingredient amounts are scaled and baked into the cached text, so any portions change also clears those caches.

---

## Mobile layout

Breakpoint: `window.innerWidth < 640` — tracked in `isMobile` state with a `resize` listener.

**On mobile (< 640px):**
- Header controls row hidden entirely (UKE, PORSJONER, Proteinmål, Kjøkken, Skriv ut)
- Compact header padding (`12px 16px 10px`)
- Week selector shown in header when `weeks > 1` — buttons 1…N set `mobileWeek` (plan view) and `shoppingWeek` (shopping view) together
- Plan grid renders only the `mobileWeek` row instead of all weeks
- Bottom nav bar (`height: 56px`) with four tabs: Plan / Handleliste / Fryser / Innstillinger. Switching tabs closes any open plan or suggestion modal.
- Root div is `position: fixed; inset: 0; display: flex; flex-direction: column` — content scrolls inside a `flex: 1; overflow-y: auto` inner div; nav bar sits in normal flow at the bottom. This avoids iOS Safari's `position: fixed` scroll drift bug.
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
Plan grid uses `tableLayout: "fixed"` so all day columns stay equal width regardless of meal name length. `maxWidth` on the main container and header is 1400px to better utilise wide screens.
Grid rows use equal-height cells: `<td>` has `height: "1px"` (table layout trick meaning "fill the row") and the inner div uses `height: "100%"` so all cells in a row stretch to match the tallest.
Plan grid table has `minWidth: 560px` so it scrolls horizontally on narrow screens rather than squashing columns.

---

## Running locally

```
python3 -m http.server 8080
```

Open `http://localhost:8080`. Add Anthropic API key in ⚙ Innstillinger before generating suggestions.
