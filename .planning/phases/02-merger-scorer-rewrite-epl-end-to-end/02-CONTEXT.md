# Phase 2: Merger & Scorer Rewrite (EPL End-to-End) - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Rebuild `merger.py` and `scorer.py` to consume FBref data instead of Understat + API-Football. Join 9 FBref tables into one player DataFrame, remap all pillar column references to FBref equivalents, add age-weighted UV score, scrape EPL league standings (attach `league_position` column for Phase 4 use), and rewire `app.py` so the dashboard shows real EPL players again. Multi-league work and team-strength multipliers are Phase 3/4.

</domain>

<decisions>
## Implementation Decisions

### Table Join & Season Aggregation

- **Join order:** Join all 9 FBref tables into one wide row per player **per season first**, then aggregate across seasons. (More accurate per-90s — based on total minutes across all seasons, not averaged averages.)
- **Multi-club players:** Keep only the season-total row. FBref provides a summary row for players who moved clubs mid-season (Squad shows "2 Clubs" or similar). Drop the per-club split rows.
- **Cross-season aggregation:** Sum raw counts (Min, Gls, Ast, xG, Tkl, etc.) across both seasons, then re-derive all `_p90` columns as `(stat / total_Min × 90)`. Rate stats (Cmp%, DrbSucc%) use minutes-weighted average.
- **Season weighting:** Equal weight — both 2023-24 and 2024-25 contribute equally. No recency multiplier.
- **Cross-season min-minutes threshold:** 1800 total minutes (900 × 2 seasons). Players must have ≥1800 total minutes across both seasons to qualify.
- **Current-season filter:** Retain only players who appeared in 2024-25 (the most recent cached season). Players not active in the EPL in 2024-25 are excluded from scoring output.

### Pillar Column Remapping

All FBref column names are from the relevant table (see Canonical References for table→column mapping).

**Columns that change from Understat/API-Football → FBref:**

| Old column | New FBref column | Source table | Notes |
|---|---|---|---|
| `xGChain_p90` (MF Progression) | `PrgP_p90` (0.6) + `SCA_p90` (0.4) | stats_passing + stats_gca | SCORE-02 locked |
| `xGBuildup_p90` (FW/DF Progression) | `PrgC_p90` | stats_possession | SCORE-03 locked |
| `DrbAttempts_p90` | `Att_p90` (dribble attempts) | stats_possession | |
| `DrbSucc_p90` | Replaced by `DrbSucc%` (rate) | stats_possession | Rate = Succ / Att × 100 |
| `SavePct` (derived) | `Save%` + `PSxG/SoT` (keeper_adv) | stats_keeper + stats_keeper_adv | See GK pillars below |
| `GoalsConceded` | `GA` | stats_keeper | |
| `KP_p90` | `KP_p90` | stats_passing | Column name unchanged |
| `xA_p90` | `xA_p90` | stats_standard | Renamed from xAG at scrape time (Phase 1) |

**Columns that stay the same name in FBref:**
`Gls`, `Ast`, `xG`, `xA`, `SoT`, `Tkl`, `Int`, `Blocks`, `Cmp%`, `Min`, `Age` — all exist in FBref with same names.

### GK Pillar Updates

Shot Stopping pillar: **two stats instead of one derived SavePct:**
- `Save%` (0.60 weight) — from `stats_keeper` — volume-adjusted save rate
- `PSxG/SoT` (0.40 weight) — from `stats_keeper_adv` — post-shot quality per shot on target

Distribution pillar: `Cmp%` (0.65) + `DuelsWon%` (0.35) — unchanged, both in FBref.
Aerial Command: `DuelsWon_p90` (0.65) + `DuelsWon%` (0.35) — unchanged.
Sweeping: `Blocks_p90` (0.55) + `Int_p90` (0.45) — unchanged.
Composure: `Cmp%` (1.0) — unchanged.

### FW Progression Pillar (updated)

Replace raw dribble counts with success rate:
- `PrgC_p90` (0.55) — SCORE-03 locked
- `DrbSucc%` (0.45) — new: `Succ / Att × 100` from stats_possession (rewards quality, not volume)

### Creation Pillar (unchanged)

- `xA_p90` (0.55) + `KP_p90` (0.45) — both map cleanly to FBref columns; no reason to change.

### Defense & Retention Pillars (unchanged structure)

- Defense: `Tkl_p90` + `Int_p90` + `Blocks_p90` + `DuelsWon_p90` — all in stats_defense / stats_misc
- Retention: `Cmp%` + `DuelsWon%` — stats_passing / stats_misc

### Dual-Position Handling

FBref encodes dual-position players as e.g. `"DF,MF"`. Take the **first token only** as the primary position: `"DF,MF"` → `"DF"`. Applied before scorer position-group splitting.

### Age-Weighted UV Score Formula (SCORE-07)

```python
age_weight = max(0.0, log(29 - age) / log(12))  # natural or log base 12; 0 at age 29+
uv_score_age_weighted = uv_score * min(1.5, 1 + 0.30 * age_weight)
```

Shape: log decay — fast drop after ~23, flattens near 29. Values:
- age 17 → weight 1.00 → multiplier 1.30
- age 21 → weight 0.69 → multiplier 1.21
- age 25 → weight 0.30 → multiplier 1.09
- age 29+ → weight 0.00 → multiplier 1.00 (no change)

Cap at 1.5× per REQUIREMENTS (in practice never reached with these parameters, but enforced regardless).
`Age` column comes from `stats_standard`.

### League Standings Scraper (DATA-03)

- Add `scrape_fbref_standings(league, season)` to `scraper.py`, reusing `_extract_fbref_table` and `_fetch_with_backoff`.
- Cache as `cache/fbref_{league}_standings_{season}.csv` (e.g. `cache/fbref_EPL_standings_2024-25.csv`).
- Output columns needed: `Squad`, `Rk` (league position 1–20).
- Attach `league_position` to the merged player DataFrame by matching `Squad` → `Rk`.
- The column sits unused until Phase 4 applies the SCORE-04 ±20% defensive multiplier.
- FBref standings URL pattern: `https://fbref.com/en/comps/9/2024-2025/2024-2025-Premier-League-Stats`; table ID `results2024-252091_home` (may vary by season — fall back to scanning for a table with `Rk` and `Squad` columns if exact ID fails).

### app.py Rewire

- Rewire `load_data` to call `run_fbref_scrapers()` + `run_tm_scrapers()` and pass result to `run_scoring_pipeline(fbref_data, tm_data)`.
- Remove dead Understat/API-Football import lines and legacy `run_understat_scrapers` / `run_api_football_scrapers` calls from `app.py`.
- **New `run_scoring_pipeline` signature:** `run_scoring_pipeline(fbref_data: dict, tm_data: pd.DataFrame) -> pd.DataFrame`
- The season filter UI (`seasons` param in `load_data`) will be rebuilt in Phase 5; for Phase 2, `load_data` can ignore or simplify the seasons argument.
- No visual changes to the dashboard in Phase 2 — goal is functional EPL data, not UI redesign.

### Claude's Discretion

- Exact join key for merging 9 FBref tables (Player + Season + Squad recommended, but Claude can use Player + Season if Squad disambiguation is handled)
- Implementation detail of the DuelsWon% derivation (likely aerial duels from stats_misc: Won / (Won + Lost) × 100)
- Error handling for tables where a player is missing (fill with NaN, propagate to scorer as 0 via existing fillna behaviour)
- Test structure and which assertions cover the new merger path

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external spec documents — requirements are fully captured in decisions above and REQUIREMENTS.md.

### Project requirements
- `.planning/REQUIREMENTS.md` — Full requirement list; SCORE-01 through SCORE-07 all apply to Phase 2. Read the Scoring Model section carefully.
- `.planning/ROADMAP.md` — Phase 2 Success Criteria (5 acceptance conditions that define done)

### Existing code to read before modifying
- `config.py` — Current pillar configs (`PILLARS_FW`, `PILLARS_MF`, `PILLARS_DF`, `GK_PILLARS`); needs update per decisions above
- `merger.py` — Full rewrite; read before touching — understand existing `_aggregate_seasons`, `merge_stat_sources`, `compute_per90s`, `match_market_values`, `build_dataset` signatures
- `scorer.py` — `run_scoring_pipeline` signature changes; `compute_scout_scores` and `compute_efficiency` may need updates for `uv_score_age_weighted`
- `app.py` lines 188–196 — The `load_data` function to rewire; read before editing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scraper._extract_fbref_table` + `_fetch_with_backoff` — Reuse directly for standings scraper (same Comment-node HTML pattern)
- `scraper._fbref_cache_path` — Use for standings cache path (extend naming to `standings` table type)
- `scraper._is_fresh` — Use for standings 7-day cache check
- `merger.normalize_name` + `match_market_values` — Unchanged; Transfermarkt matching logic stays
- `scorer._score_group` + `compute_efficiency` — Keep structure; update column refs and add age-weight step
- `scorer.compute_scout_scores` — Keep position-group splitting; add primary-position extraction (`Pos.str.split(",").str[0]`)

### Established Patterns
- `_aggregate_seasons(data, sum_cols, mean_cols)` — Existing season aggregation pattern; adapt for FBref multi-table structure
- `build_dataset(understat_data, api_data, tm_data)` → becomes `build_dataset(fbref_data, tm_data)` — same overall pipeline shape, different inputs
- MinMaxScaler fitted per position group (within `_score_group`) — unchanged
- UV regression on full unfiltered pool (SCORE-06) — `compute_efficiency` already does this; preserve

### Integration Points
- `app.py:189` — `from scraper import run_understat_scrapers, run_api_football_scrapers, run_tm_scrapers` → update import
- `app.py:196` — `run_scoring_pipeline(understat_data, api_data, tm_data)` → `run_scoring_pipeline(fbref_data, tm_data)`
- `scorer.py:117` — `run_scoring_pipeline` signature change cascades to `app.py` call site
- `config.py` — `PILLARS_FW`, `PILLARS_MF`, `PILLARS_DF`, `GK_PILLARS`, `PER90_STATS`, `SUM_STATS` all need updating to reflect FBref column names

</code_context>

<specifics>
## Specific Ideas

- GK Shot Stopping quality signal: `PSxG/SoT` (post-shot xG per shot on target) — rewards stopping harder shots, not just volume. This directly addresses the Phase 1 motivation of fixing GK scoring at weak teams.
- DrbSucc% over raw DrbSucc counts — "a player completing 6/8 dribbles is better than 8/15" — rate metric preferred for all dribble stats.
- Log-decay age weighting: drops fast after ~23, matches how the transfer market prices prospect potential in practice.

</specifics>

<deferred>
## Deferred Ideas

- None raised — discussion stayed within Phase 2 scope.

</deferred>

---

*Phase: 02-merger-scorer-rewrite-epl-end-to-end*
*Context gathered: 2026-03-16*
