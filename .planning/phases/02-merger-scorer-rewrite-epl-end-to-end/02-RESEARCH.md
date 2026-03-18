## RESEARCH COMPLETE

**Gathered:** 2026-03-16
**Method:** Simulated `pd.read_html(header=1)` on FBref HTML structures; cross-checked against community scraping resources; static analysis of existing codebase.

---

### 1. FBref Column Names Per Table

All column names below are as they appear after `pd.read_html(header=1)` on the actual FBref table HTML (group-label row skipped; stat-name row is header). Verified by simulating the exact FBref thead structure in Python.

#### stats_standard (table_id: `stats_standard_9`)
```
Rk, Player, Nation, Pos, Squad, Comp, Age, Born, MP, Starts, Min, 90s,
Gls, Ast, G+A, G-PK, PK, PKatt, CrdY,
xG, npxG, xAG, npxG+xAG,
PrgC, PrgP, PrgR,
Gls.1, Ast.1, G+A.1, G-PK.1, G+A-PK, xG.1
```
- `xAG` is renamed to `xA` at scrape time (already done in Phase 1 `scrape_fbref_stat`).
- `PrgC` and `PrgP` are in the raw-count section — NOT suffixed.
- `Gls.1`, `Ast.1`, `xG.1` etc. are FBref's pre-computed per-90 values — the `.1` suffix comes from pandas deduplication of the second occurrence of those column names.

#### stats_shooting (table_id: `stats_shooting_9`)
```
Rk, Player, Nation, Pos, Squad, Age,
Gls, Sh, SoT, SoT%, Sh/90, SoT/90, G/Sh, G/SoT, Dist, FK,
xG, npxG, npxG/Sh, G-xG, np:G-xG, Matches
```
- `SoT` is confirmed as the exact column name (shots on target, raw count).

#### stats_passing (table_id: `stats_passing_9`)
```
Rk, Player, Nation, Pos, Squad, Age,
Cmp, Att, Cmp%, TotDist, PrgDist,
Cmp.1, Att.1, Cmp%.1, 1/3s,
Cmp.2, Att.2, Cmp%.2, 1/3m,
Cmp.3, Att.3, Cmp%.3, 1/3l,
Ast, xAG, xA, A-xAG, KP, 1/3, PPA, CrsPA, PrgP
```
- `Cmp%` (first, unsuffixed) = **total pass completion percentage** — this is the correct column for the Retention pillar.
- `KP` = key passes (raw count).
- `PrgP` = progressive passes (raw count).
- `xAG` in stats_passing is the same stat as `xA` in stats_standard. It is NOT renamed at scrape time for stats_passing. The merger must use `xA` from `stats_standard` only and ignore `xAG` from `stats_passing` to avoid double-counting.

#### stats_defense (table_id: `stats_defense_9`)
```
Rk, Player, Nation, Pos, Squad, Age,
Tkl, TklW, Def 3rd, Mid 3rd, Att 3rd,
Tkl.1, Att, Tkl%, Lost,
Blocks, Sh, Pass,
Int, Tkl+Int, Clr
```
- **`Tkl` (first, unsuffixed)** = total tackles from the **Tackles** group — this is the authoritative total tackle count. Use this for the Defense pillar.
- **`Tkl.1`** = tackles won from the **Challenges** group (tackles against dribblers) — a different stat. Do NOT use `Tkl.1` as the total tackles.
- `Blocks` (unsuffixed) = total blocks — correct for the Defense pillar.
- `Int` = interceptions — no duplicate, unsuffixed.
- `Att` in this table = dribble attempts faced (from Challenges group) — **not** the same as `Att` in stats_possession (dribble attempts made). Name collision across tables; the merger must select columns by table source.

#### stats_possession (table_id: `stats_possession_9`)
```
Rk, Player, Nation, Pos, Squad, Age,
Touches, Def Pen, Def 3rd, Mid 3rd, Att 3rd,
Att, Succ, Succ%,
Carries, TotDist, PrgDist, PrgC, 1/3, Rec, PrgR
```
- `Att` = dribble attempts made by the player (Take-Ons group). This is `DrbAttempts` in the old API-Football scheme.
- `Succ` = successful dribbles. `DrbSucc%` = `Succ / Att * 100` (computed in merger).
- `PrgC` = progressive carries. This is the same stat as `PrgC` in stats_standard.

#### stats_misc (table_id: `stats_misc_9`)
```
Rk, Player, Nation, Pos, Squad, Age,
CrdY, CrdR, 2CrdY, Fls, Fld, Off,
Won, Lost, Won%
```
- Aerial duel columns: **`Won`** (aerial duels won) and **`Lost`** (aerial duels lost). NOT `AerWon`/`AerLost` — the exact names are `Won` and `Lost`.
- `Won%` = pre-computed aerial win percentage (available but we re-derive as `Won / (Won + Lost) * 100` post-aggregation to handle cross-season sums correctly).
- `DuelsWon%` derivation: `Won / (Won + Lost) * 100`.
- `DuelsWon_p90` derivation: `Won / Min * 90`.

#### stats_keeper (table_id: `stats_keeper_9`)
```
Rk, Player, Nation, Pos, Squad, Age,
MP, Starts, Min, 90s,
GA, GA90, SoTA, Saves, Save%, W, D, L,
CS, CS%,
PKatt, PKA, PKsv, PKm,
Matches
```
- `Save%` = save percentage — exact column name, confirmed.
- `GA` = goals against — exact column name.
- GK `Min` is available here; use `stats_standard` Min as the authoritative minutes for all players.

#### stats_keeper_adv (table_id: `stats_keeper_adv_9`)
```
Rk, Player, Nation, Pos, Squad, Age,
GA, PKA, FK,
PSxG, PSxG/SoT, PSxG+/-, /90, Att (GK), Thr,
Cmp, Att, Cmp%, Att (GK).1, Launch%, AvgLen,
Opp, Stp, Stp%, Att.1, Launch%.1, AvgLen.1,
Opp.1, Stp.1, Stp%.1,
#OPA, #OPA/90, AvgDist,
Att.2, Mid%
```
- **`PSxG/SoT`** = post-shot expected goals per shot on target — exact column name confirmed (slash included).
- `Cmp%` in this table = completion% for **launched (long) passes only** — do NOT use this for the Distribution pillar. Use `Cmp%` from `stats_passing` for overall pass completion.
- `GA` appears here too (goals against) — same stat as in `stats_keeper`. Use `stats_keeper` `GA` to avoid ambiguity.

#### stats_gca (table_id: `stats_gca_9`)
```
Rk, Player, Nation, Pos, Squad, Age,
SCA, SCA90,
PassLive, PassDead, TO, Sh, Fld, Def,
GCA, GCA90,
PassLive.1, PassDead.1, TO.1, Sh.1, Fld.1, Def.1
```
- **`SCA`** = shot-creating actions (raw count) — exact column name confirmed.
- `SCA90` = pre-computed per-90 rate. Do NOT use — always derive from `SCA / Min * 90` after cross-season aggregation.

---

### 2. Multi-Club Row Identification

FBref labels the season-total row for a transferred player in the **`Squad`** column as **`"2 Clubs"`** (two words, capital C). This applies in all 9 stat tables.

**The edge case that requires explicit deduplication in the merger:**

When a player plays ≥900 min at their first club before transferring (e.g. 950 min at Club A, 400 min at Club B), the Phase 1 scraper keeps both rows:
- Club A row (950 min) — passes the ≥900 min filter
- `"2 Clubs"` row (1350 min) — also passes the ≥900 min filter
- Club B row (400 min) — dropped

Both rows for that player are in the cached CSV. The merger must deduplicate **before** the 9-table join:

```python
# Deduplication rule: per-player, per-table, within a season
# If any row has Squad == "2 Clubs", keep ONLY that row and drop all others.
# Otherwise, keep the single row (no duplication).
def _deduplicate_multiclub(df):
    # For players with a "2 Clubs" row, drop their per-club rows
    has_summary = df.groupby("Player")["Squad"].transform(lambda x: (x == "2 Clubs").any())
    return df[~(has_summary & (df["Squad"] != "2 Clubs"))].reset_index(drop=True)
```

**Note:** The string may also appear as `"2 teams"` in older seasons or edge cases. The implementation should handle both: `Squad.str.contains(r"^\d+ [Cc]lub", regex=True)` as the detection pattern is more robust than exact string match.

---

### 3. Standings Table

**URL pattern:**
```
https://fbref.com/en/comps/9/2024-2025/2024-2025-Premier-League-Stats
```
(Follows `build_fbref_url` pattern with `url_seg = ""` and trailing stats path.)

**Table ID:** `results2024-252091_home` per CONTEXT.md. This is season-specific and fragile. The correct implementation strategy (per CONTEXT.md) is:

1. Try exact `_extract_fbref_table(html, "results2024-252091_home")` first.
2. Fallback: scan all comment nodes for a table that has both `Rk` and `Squad` columns after `pd.read_html(header=0)[0]`.

**Columns in standings table (standard FBref league table):**
```
Rk, Squad, MP, W, D, L, GF, GA, GD, Pts, Pts/G, xG, xGA, xGD, xGD/90, Attendance
```
Only `Rk` and `Squad` are needed. `Rk` becomes `league_position` on the merged player DataFrame.

**Squad name format:** FBref standings uses the same full club names as the player stat tables (e.g. `"Manchester City"`, `"Arsenal"`, `"Nottingham Forest"`). No normalization required for the `Squad → Rk` join.

**Multi-club player caveat:** Players with `Squad == "2 Clubs"` cannot be joined to standings by Squad. These players should receive `league_position = NaN` (Phase 4 will handle the adjustment when it's needed).

**Cache path for standings:**
```
cache/fbref_EPL_standings_2024-25.csv
```
Reuses `_fbref_cache_path` with `table = "standings"`.

---

### 4. Duplicate Column Handling

**pandas `read_html(header=1)` deduplication behavior (confirmed by simulation):**

When two columns in the stat-name row share the same name (from different group sections), pandas auto-appends `.1`, `.2`, `.3` suffixes in left-to-right order. The **first occurrence is always unsuffixed** (authoritative), and subsequent occurrences get `.1`, `.2`, etc.

**Affected tables and their duplicates:**

| Table | First (unsuffixed) | Second (.1) | Third (.2) | Notes |
|---|---|---|---|---|
| stats_defense | `Tkl` = total tackles (Tackles group) | `Tkl.1` = tackles vs dribblers (Challenges group) | — | Use `Tkl`, not `Tkl.1` |
| stats_defense | — | `Att` = dribble attempts faced | — | Different stat from possession `Att` |
| stats_passing | `Cmp` = total attempts | `Cmp.1` = short | `Cmp.2` = medium, `Cmp.3` = long | Use `Cmp%` (first) |
| stats_passing | `Cmp%` = total completion% | `Cmp%.1` = short, `Cmp%.2` = medium | `Cmp%.3` = long | Use `Cmp%` only |
| stats_keeper_adv | `Att` = pass attempts (Expected section) | `Att.1` = pass attempts (Passes section) | `Att.2` = cross attempts | `PSxG/SoT` has no duplicate |
| stats_gca | `PassLive` through `Def` (SCA types) | `PassLive.1` through `Def.1` (GCA types) | — | Use first set for SCA types |
| stats_standard | `Gls` = raw count | `Gls.1` = per-90 (pre-computed) | — | Use `Gls` (raw), never `Gls.1` |

**Critical rule:** Always use the **first (unsuffixed)** occurrence of any column name. The suffixed versions are either from sub-groups or FBref's own pre-computed rates — both are irrelevant for the merger's raw-count aggregation approach.

---

### 5. Per-90 Columns Strategy

**Do NOT use FBref's pre-computed per-90 columns.** Always derive per-90s from raw counts + total `Min`.

**Reasons:**
1. FBref's pre-computed per-90s (the `.1`-suffixed columns in stats_standard: `Gls.1`, `Ast.1`, `xG.1`) are season-specific. After summing raw counts across 2023-24 and 2024-25, you must re-derive all `_p90` values as `stat_sum / total_Min * 90`.
2. Averaging per-90 rates across seasons (e.g. `(3.2 + 2.8) / 2 = 3.0`) is mathematically inferior to deriving from summed totals. A player with 3200 total touches over 3200 minutes should score 1.0 per-90, not whatever average of two rates gives.
3. Some tables (stats_possession, stats_gca, stats_misc) don't have pre-computed per-90 columns at all — raw counts are the only option.

**Implementation:** The new `compute_per90s` in `merger.py` must use the `Min` column from the **aggregated** (post-season-sum) DataFrame, not per-season data.

**Rate stats (not re-derived from counts):**
- `Cmp%` (pass completion): minutes-weighted average across seasons: `sum(Cmp) / sum(Att) * 100`
- `DrbSucc%`: re-derived from summed `Succ` and `Att`: `sum(Succ) / sum(Att) * 100`
- `Won%` (aerial): re-derived: `sum(Won) / (sum(Won) + sum(Lost)) * 100`
- `Save%`: re-derived from `Saves / (Saves + GA) * 100` using summed keeper counts
- `PSxG/SoT`: special — this is a per-shot quality metric, not per-minute. Sum `PSxG` and `SoTA` separately, then `PSxG/SoT = sum(PSxG) / sum(SoTA)`.

---

### 6. app.py Dead Code Map

**Lines requiring change:**

| Line | Current | Action |
|---|---|---|
| 189 | `from scraper import run_understat_scrapers, run_api_football_scrapers, run_tm_scrapers` | Remove `run_understat_scrapers, run_api_football_scrapers`; add `run_fbref_scrapers` |
| 191 | `understat_data = run_understat_scrapers()` | Remove entire line |
| 192 | `api_data = run_api_football_scrapers()` | Remove entire line |
| 193 | `tm_data = run_tm_scrapers()` | Keep; add `fbref_data = run_fbref_scrapers()` before it |
| 194-200 | Season filter + 3-arg `run_scoring_pipeline(understat_data, api_data, tm_data)` | Replace with `return run_scoring_pipeline(fbref_data, tm_data)` |
| 409 | `"SOURCES &nbsp;&nbsp; Understat · API-Football · TM<br>"` | Update to `"SOURCES &nbsp;&nbsp; FBref · TM<br>"` |
| 411 | `"MIN MIN &nbsp;&nbsp;&nbsp; 3,000<br>"` | Update to `"MIN MIN &nbsp;&nbsp;&nbsp; 1,800<br>"` |
| 489 | `row.get('Saves_p90', 0):.2f` for GK display | Update to use `Save%` or derived stat that exists post-rewrite |

**Tab 3 display (line 530):** `display_cols` does not include `uv_score_age_weighted`. Add it to the column list and rename header accordingly.

**No other Understat/API-Football column names appear in app.py** (confirmed by grep). The chart rendering, color logic, and filter code are all column-name-agnostic (they use `market_value_eur`, `scout_score`, `uv_score`, `value_gap_eur`, `Pos`, `Squad`, `Player` — none of which change).

**scraper.py stubs to remove:** `run_understat_scrapers()` and `run_api_football_scrapers()` stubs (lines 407-418, 555-566) can be deleted in Phase 2 since their last caller (`app.py:189`) will be updated. The underlying Understat/API-Football scraper functions (`scrape_understat_season`, `scrape_api_football_season`, etc.) can also be removed but are not dead-code urgent — delete at discretion.

---

### 7. Planner Risks & Gotchas

**G1 — `Tkl` vs `Tkl.1` naming trap (HIGH RISK)**
The most dangerous column name trap in the codebase. `Tkl` (unsuffixed) = total tackles from the Tackles group = what the Defense pillar needs. `Tkl.1` = tackles won against dribblers (Challenges group) = a different, narrower stat. Any config referencing `Tkl` will correctly get the total. But if a future refactor or manual inspection sees `Tkl.1` and assumes it's "more accurate" or "total won", it will introduce a scoring bug.

**G2 — PrgC appears in both stats_standard AND stats_possession (MEDIUM RISK)**
Both tables have a `PrgC` column representing the same stat (progressive carries). When joining tables, the merged DataFrame will have duplicate column names if both are included. The merger must select `PrgC` from only one source (prefer stats_possession, which is the dedicated possession table, and use it as the canonical source). Drop `PrgC` from stats_standard before joining, or rename one.

**G3 — PrgP appears in both stats_standard AND stats_passing (MEDIUM RISK)**
Same issue as G2. `PrgP` (progressive passes) exists in both tables. Use stats_passing as canonical source. The CONTEXT's pillar definition for SCORE-02 (`PrgP_p90`) should draw from stats_passing.

**G4 — stats_passing has `xAG` that is NOT renamed (MEDIUM RISK)**
stats_standard's `xAG` is renamed to `xA` at scrape time (Phase 1). stats_passing also has an `xAG` column (same stat — expected assisted goals). This column is NOT renamed by the scraper. If the merger joins both tables without handling this, you'll end up with two columns representing the same stat: `xA` (from standard) and `xAG` (from passing). The merger should drop `xAG` from the passing table before merging.

**G5 — Age column is "NN-NNN" format (MEDIUM RISK)**
FBref's `Age` column stores values as `"25-201"` (years-days since birthday at season start). The age-weight formula requires an integer age. The merger must parse `int(str(age).split("-")[0])` before applying `log(29 - age)`. If this parsing is skipped, `29 - "25-201"` will raise a TypeError.

**G6 — Multi-club player deduplication edge case (MEDIUM RISK)**
A player who played ≥900 min at one club and then transferred will have TWO rows in the cached CSV: the per-club row AND the `"2 Clubs"` summary row. The merger must explicitly deduplicate using the `"2 Clubs"` pattern (not just `drop_duplicates("Player")`), otherwise the per-club row gets used instead of the season total.

**G7 — PSxG/SoT cross-season re-derivation (MEDIUM RISK)**
`PSxG/SoT` is a rate stat (post-shot xG per shot on target). It cannot be averaged across seasons. Instead: sum `PSxG` (raw, from keeper_adv) and `SoTA` (shots on target against, from stats_keeper) separately across seasons, then re-derive `PSxG/SoT = sum_PSxG / sum_SoTA`. The `PSxG/SoT` column from the scraped data should NOT be used in the aggregation — it's a derived value.

**G8 — Standings table ID is season-specific (LOW RISK with fallback)**
The stated table ID `results2024-252091_home` encodes the season. For 2023-24 the ID is different. Since Phase 2 only needs 2024-25 standings, this is manageable. But the fallback scan (search for table with `Rk` and `Squad`) should be implemented as primary strategy to future-proof Phase 3.

**G9 — GK Cmp% source confusion (LOW RISK)**
`stats_keeper_adv` has a `Cmp%` column, but it measures pass completion for **launched (long) passes only**, not overall distribution. The GK Distribution pillar should use `Cmp%` from `stats_passing` (same as outfield players). If the merger naively takes `Cmp%` from the first available table for GKs, it may pick the wrong one.

**G10 — `Won` and `Lost` column names in stats_misc are generic (LOW RISK)**
The aerial duel columns are simply named `Won` and `Lost` — not `AerWon`/`AerLost`. These column names could collide with any future table that also has `Won`/`Lost` columns. Rename them immediately post-join to `AerWon` and `AerLost` to avoid ambiguity in the scorer.

---

### 8. Validation Architecture

All tests should run **without network access** (same pattern as `test_scraper.py`). Tests use synthetic DataFrames as fixtures.

| Test ID | What it verifies | Network? |
|---|---|---|
| `test_multiclub_deduplication` | Given a player with both a `"2 Clubs"` row and a per-club row in the same table, `_deduplicate_multiclub()` returns only the `"2 Clubs"` row | No |
| `test_nine_table_join_full` | `merge_fbref_tables(fbref_season_data)` returns one row per player with all expected columns present; no duplicate column names in output | No |
| `test_nine_table_join_missing_table` | When one of the 9 tables is empty (e.g. stats_keeper for an outfield player), the join fills missing columns with NaN without error | No |
| `test_cross_season_aggregation` | Given 2 seasons of data, aggregated DataFrame has summed `Min`, summed `Gls`, summed `SoT`; rate stats (`Cmp%`) are minutes-weighted | No |
| `test_per90_derivation` | `compute_per90s` correctly computes `Gls_p90 = Gls / Min * 90`; handles `Min = 0` (no division error) | No |
| `test_drbsucc_rate_derivation` | `DrbSucc% = Succ / Att * 100`; handles `Att = 0` with NaN | No |
| `test_duels_won_pct_derivation` | `DuelsWon% = Won / (Won + Lost) * 100`; handles `Won + Lost = 0` with NaN | No |
| `test_age_weight_formula` | Age-weight calculation: age 17 → multiplier ~1.30, age 25 → ~1.09, age 29 → 1.00, age 35 → 1.00 (clamps at 0); `uv_score_age_weighted = uv_score * min(1.5, 1 + 0.30 * age_weight)` | No |
| `test_age_column_parsing` | FBref `"25-201"` format parsed to integer `25`; plain `"25"` also works | No |
| `test_uv_score_age_weighted_column_exists` | `run_scoring_pipeline` output contains both `uv_score` and `uv_score_age_weighted` columns | No |
| `test_min_minutes_threshold_1800` | Players with `total_Min < 1800` are excluded from scorer output; players with exactly 1800 are included | No |
| `test_current_season_filter` | Players not in 2024-25 season data are excluded even if they have sufficient total minutes | No |
| `test_primary_position_extraction` | `"DF,MF"` → `"DF"` primary position; `"GK"` unchanged; `"FW,MF"` → `"FW"` | No |
| `test_prgc_source_is_possession` | Merged DataFrame contains exactly one `PrgC` column sourced from `stats_possession` (no duplicate) | No |
| `test_scorer_new_pillar_columns` | `PILLARS_FW.progression.stats` contains `PrgC_p90` and `DrbSucc%` (not `xGBuildup_p90`); `PILLARS_MF.progression.stats` contains `PrgP_p90` and `SCA_p90` | No |
| `test_gk_shot_stopping_pillar` | `GK_PILLARS.attacking.stats` contains `Save%` (weight 0.60) and `PSxG/SoT` (weight 0.40); does NOT contain `SavePct` | No |
| `test_standings_scraper_caches` | `scrape_fbref_standings()` writes a CSV to `cache/fbref_EPL_standings_2024-25.csv` with columns `Squad` and `Rk` | No (mock HTTP) |
| `test_league_position_attached` | After `build_dataset()`, merged DataFrame contains `league_position` column; multi-club players (`Squad == "2 Clubs"`) have `NaN` for `league_position` | No |
| `test_run_scoring_pipeline_signature` | `run_scoring_pipeline(fbref_data, tm_data)` accepts the new 2-arg signature and raises `TypeError` if called with 3 args | No |
| `test_load_data_no_legacy_imports` | `app.py` does not import `run_understat_scrapers` or `run_api_football_scrapers` (static AST check) | No |

---

*Phase: 02-merger-scorer-rewrite-epl-end-to-end*
*Research gathered: 2026-03-16*
