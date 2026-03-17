# Phase 3: Multi-League Expansion — Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend `scraper.py` and `merger.py` to cover all five leagues: EPL (already working), LaLiga, Bundesliga, SerieA, Ligue1. Add a `League` column throughout the pipeline. Loop the full pipeline over all five leagues so the master scoring output contains players from all five. The `build_dataset` and `run_scoring_pipeline` functions stay 2-arg — no signature changes. Team-strength adjustment and league quality multiplier are Phase 4. Dashboard changes are Phase 5.

</domain>

<decisions>
## Implementation Decisions

### League Keys & Naming

- **Five league keys (canonical):** `EPL`, `LaLiga`, `Bundesliga`, `SerieA`, `Ligue1`
- **EPL unchanged** — existing cache files, URL patterns, and column logic are preserved exactly.
- **Cache naming:** `cache/fbref_{LEAGUE}_{table}_{season}.csv` — e.g. `cache/fbref_LaLiga_stats_standard_2024-25.csv`
- **TM cache naming:** `cache/tm_values_{LEAGUE}_{season}.csv` — already used for EPL; extend same pattern.
- **`League` column value** in the scored DataFrame uses the same key strings (`"EPL"`, `"LaLiga"`, etc.).

### FBref URL Patterns for New Leagues

Each FBref league has a numeric competition ID. These are the canonical IDs needed to build table URLs:

| League | FBref comp ID |
|--------|--------------|
| EPL | 9 |
| LaLiga | 12 |
| Bundesliga | 20 |
| Serie A | 11 |
| Ligue 1 | 13 |

URL pattern: `https://fbref.com/en/comps/{id}/{season_long}/stats/{season_long}-{LeagueName}-Stats`
Season long form: `"2024-25"` → `"2024-2025"` (existing `build_fbref_url` handles this).
The researcher must confirm exact URL slugs for each league during Phase 3 research.

### Season Coverage

- **Both seasons scraped for all 5 leagues:** `["2023-24", "2024-25"]` — same as EPL.
- **No differential treatment** between EPL and new leagues.
- **Min-minutes threshold:** 900 per season (1800 total) — uniform across all leagues.
- **Single-season flag:** Players who qualify on minutes but only appear in one of the two seasons receive a boolean `single_season = True` column. This surfaces in the dashboard as a data caveat (Phase 5 renders it). The column is derived in `_aggregate_fbref_seasons` by checking whether both seasons contributed rows.
- **Current-season filter (2024-25 presence):** Unchanged — players must appear in 2024-25 to be included in scoring output.

### Transfermarkt Integration — 3-Pass Matching

Current matching uses exact → fuzzy WRatio ≥ 80. Phase 3 upgrades to 3-pass to reduce missing values:

1. **Pass 1 — Exact name match** (unchanged)
2. **Pass 2 — Fuzzy WRatio ≥ 80** (unchanged)
3. **Pass 3 — Fuzzy WRatio 70–79, club name also matches** — candidate must share the same club name (after normalization) to accept the lower-confidence name match

Goal: reduce `market_value_eur = NaN` rows, especially for players with hyphenated or accented names common in La Liga and Ligue 1.

TM URLs for new leagues must be researched — existing EPL URL pattern won't apply directly. The researcher must confirm Transfermarkt league listing URLs for each of the 4 new leagues.

### Scraper Entry Point

- **`python scraper.py`** — always scrapes all 5 leagues, no flag or selection prompt.
- **`run_fbref_scrapers(leagues=None)`** — accepts optional `leagues` list; `None` means all 5. `app.py` calls it without arguments (returns all 5).
- **`run_tm_scrapers(leagues=None)`** — same pattern; `None` = all 5.
- **Cache logic unchanged** — 7-day TTL respected; re-running within 7 days serves from cache for all leagues.

### MinMaxScaler Normalization Scope

- **Per league+position group** (ROADMAP SUCCESS CRITERION 4, locked).
- `_score_group` in `scorer.py` currently fits per position group within a single league. Phase 3 must ensure the loop calls `compute_scout_scores` per-league, not on the pooled 5-league DataFrame.
- UV regression (`compute_efficiency`) continues to fit on the **full unfiltered pool** across all leagues (SCORE-06 unchanged).

### `League` Column Propagation

- `build_dataset` adds `League` column to the merged DataFrame for each league before concatenating all five into the master DataFrame.
- `attach_league_position` already takes `league` as a parameter — no change needed there.
- The `League` column must be present on every row before `compute_scout_scores` is called so the per-league normalization loop can group correctly.

### Claude's Discretion

- Exact FBref URL slugs for each league (researcher must confirm)
- TM league listing URLs for La Liga, Bundesliga, Serie A, Ligue 1
- Whether `run_fbref_scrapers` loops leagues sequentially (preferred for rate-limit compliance) or restructures the existing scraping logic
- Error handling when a specific league's FBref tables are temporarily unavailable (log warning, skip league, continue)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project requirements
- `.planning/REQUIREMENTS.md` — DATA-01 (all leagues), DATA-04, DATA-05 (league-keyed cache)
- `.planning/ROADMAP.md` — Phase 3 Success Criteria (4 acceptance conditions)

### Existing code to read before modifying
- `scraper.py` — `run_fbref_scrapers`, `build_fbref_url`, `scrape_fbref_stat`, `run_tm_scrapers`, `_fbref_cache_path`, `_is_fresh`, `_fetch_with_backoff` — all need league-aware extensions
- `merger.py` — `build_dataset(fbref_data, tm_data)` — needs outer league loop + `League` column attachment + 3-pass TM matching
- `scorer.py` — `compute_scout_scores` — normalization loop must group per league+position
- `config.py` — `FBREF_LEAGUES` dict (if it exists) or equivalent league→comp-ID mapping to add
- `test_scraper.py`, `test_merger.py`, `test_scorer.py` — existing test suite; new tests extend these files

### Prior phase context
- `.planning/phases/02-merger-scorer-rewrite-epl-end-to-end/02-CONTEXT.md` — all pillar column decisions, join logic, per-90 derivation, age-weight formula — all carry forward unchanged

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scraper.build_fbref_url(league, table_type, season)` — already parametric on league; just needs the new comp IDs added to its lookup table
- `scraper.scrape_fbref_stat(league, table_type, season)` — already league-keyed; no structural changes needed
- `scraper._fbref_cache_path(league, table_type, season)` — naming convention already correct for new leagues
- `scraper.run_fbref_scrapers()` — currently loops EPL only; extend inner loop to iterate `FBREF_LEAGUES.keys()`
- `merger.build_dataset(fbref_data, tm_data)` — `fbref_data` is already `{league: {season: {table: df}}}`; the league-first nesting was chosen in Phase 1 specifically to support this expansion
- `merger.match_market_values(df, tm_df)` — extend with Pass 3 logic (club cross-check at WRatio 70–79)
- `scorer.compute_scout_scores(df)` — add outer `for league in df['League'].unique()` grouping before inner position loop

### Established Patterns
- `run_fbref_scrapers` returns `{league: {season: {table_type: df}}}` — league-first nesting (Phase 1 decision, forward-compatible)
- Serial scraping with `_fetch_with_backoff` + randomized delay — no changes, applies to all leagues
- `_is_fresh` + `_fbref_cache_path` cache check pattern — apply unchanged for new league cache files
- `_deduplicate_multiclub` regex `r"^\d+\s+[Cc]lub|^\d+\s+[Tt]eam"` — FBref uses same pattern across leagues

### Integration Points
- `config.py` — add `FBREF_LEAGUES = {"EPL": 9, "LaLiga": 12, "Bundesliga": 20, "SerieA": 11, "Ligue1": 13}` (comp IDs)
- `scraper.run_fbref_scrapers` — iterate `FBREF_LEAGUES.keys()` instead of hardcoded `["EPL"]`
- `scraper.run_tm_scrapers` — same league-loop extension
- `merger.build_dataset` — add `df["League"] = league` before appending each league's DataFrame to master
- `scorer.compute_scout_scores` — per-league normalization: fit MinMaxScaler on each league's position group separately

</code_context>

<specifics>
## Specific Ideas

- **3-pass TM matching club cross-check:** Normalize club names (lowercase, strip accents, drop "FC"/"CF"/"AFC") before comparing — same normalization applied to both FBref Squad and TM club columns.
- **`single_season` flag derivation:** In `_aggregate_fbref_seasons`, count distinct seasons per player. If count == 1 (only one season met the 900-min threshold), set `single_season = True`; otherwise `False`.
- **Per-league normalization isolation:** Running MinMaxScaler per league prevents a mediocre La Liga forward from scoring near zero just because EPL forwards happen to be stronger in that season.

</specifics>

<deferred>
## Deferred Ideas

- League quality multiplier (UEFA coefficient weighting) — Phase 4 (SCORE-05)
- Cross-league player comparison / cosine similarity — Phase 4 (SCORE-08)
- League filter in dashboard — Phase 5 (FILTER-01)
- Rendering `single_season` asterisk in the UI — Phase 5

</deferred>

---

*Phase: 03-multi-league-expansion*
*Context gathered: 2026-03-17*
