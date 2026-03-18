# ARCHITECTURE.md — System Architecture

## Overview

Moneyball is a linear data pipeline ending in a Streamlit dashboard. There is no database, no background job scheduler, and no service separation. All computation runs in-process inside the Streamlit server on demand.

```
scraper.py  →  merger.py  →  scorer.py  →  app.py (Streamlit)
```

Each stage produces a pandas DataFrame that is passed directly to the next stage.

---

## Stage 1: scraper.py — Data Acquisition

Three independent scrapers run in sequence. Each writes its result to a CSV cache. On subsequent runs, fresh cache files are returned immediately without hitting the network.

```
run_understat_scrapers()    → {season_label: DataFrame}
run_api_football_scrapers() → {season_label: DataFrame}
run_tm_scrapers()           → DataFrame (latest market values per player)
```

The three outputs are passed together into `run_scoring_pipeline()` (scorer.py), which calls `merger.build_dataset()` first.

### Understat flow
```
asyncio.run(_fetch_understat_season(year, label))
  → aiohttp session → understat.get_league_players("EPL", year)
  → list of player dicts → pd.DataFrame
  → write to cache/understat_<label>.csv
```

### API-Football flow
```
_get_epl_team_ids(year, headers)     # 1 API call → list of team IDs
for team_id in team_ids:
    for page in pages:
        GET /players?league=39&season=year&team=team_id&page=page
        → extract rows via _extract_player_row()
→ deduplicate by player name → pd.DataFrame
→ write to cache/apifootball_<label>.csv
```

### Transfermarkt flow
```
_get_tm_club_list(year, session)     # scrape league page → [{slug, id, name}]
for club in clubs:
    _scrape_tm_squad(club, year, label, session)  # scrape /kader/ page
→ deduplicate by player_name_tm
→ _parse_tm_value() on market_value_raw → market_value_eur
→ write to cache/tm_values_<label>.csv

# run_tm_scrapers() then deduplicates across seasons:
→ group by player_name_tm, take last (most recent) market value
→ return DataFrame with columns: player_name_tm, club_tm, market_value_eur
```

---

## Stage 2: merger.py — Data Integration

Entry point: `build_dataset(understat_data, api_data, tm_data) → DataFrame`

### Step 1: Aggregate Understat seasons
```python
aggregate_understat(understat_data, min_minutes)
```
- Concatenates all season DataFrames
- Groups by `Player`, sums `UNDERSTAT_SUM` columns, takes `last` for `Squad` and `Pos`
- Applies minutes filter: `MIN_MINUTES_PER_SEASON * n_seasons` (e.g. 900 × 3 = 2,700 min)
- Additionally filters to only players who appeared in the `2025-26` season (current EPL filter)

### Step 2: Aggregate API-Football seasons
```python
aggregate_api_football(api_data)
```
- Same concatenation + groupby pattern
- Sums `API_FOOTBALL_SUM` columns, takes `mean` for `Cmp%`

### Step 3: Merge stat sources
```python
merge_stat_sources(understat_df, api_df)
```
Understat is the authoritative base (left join). API-Football stats are attached via two-pass name matching:
- **Pass 1:** Exact match on normalized name (strip accents, lowercase, collapse whitespace via `normalize_name()`)
- **Pass 2:** `rapidfuzz.process.extractOne` with `fuzz.WRatio`, threshold `FUZZY_THRESHOLD = 80`

Unmatched players get `NaN` for all API-Football columns — their Defense and Retention pillars score 0.

### Step 4: Compute per-90 statistics
```python
compute_per90s(df)
```
For each stat in `PER90_STATS`, computes `stat_p90 = stat / Min * 90`. Also derives:
- `DuelsWon% = DuelsWon / DuelsTotal * 100`
- `SavePct = Saves / (Saves + GoalsConceded) * 100` (GK-specific quality metric)

### Step 5: Match market values
```python
match_market_values(df, tm_df)
```
Same two-pass name matching (exact then fuzzy) to attach `market_value_eur` from Transfermarkt data to each player row. Players without a match get `NaN`.

---

## Stage 3: scorer.py — Scoring

Entry point: `run_scoring_pipeline(understat_data, api_data, tm_data) → DataFrame`

Calls `merger.build_dataset()` then runs two scoring passes.

### 3a. Scout Score — Position-specific pillar model

```python
compute_scout_scores(df)
```

Players are split into four position groups (GK, FW, MF, DF). Each group is scored independently with its own pillar configuration. This means MinMaxScaler normalization is fitted separately per group.

#### Pillar model design

Each position has 5 named pillars. Each pillar has a `weight` (integer, pillar weights sum to 100) and a dict of `stats` with internal weights (float, sum to 1.0 within each pillar).

**FW pillars (Attacking 45 / Progression 20 / Creation 20 / Defense 5 / Retention 10)**

| Pillar | Weight | Stats (internal weights) |
|---|---|---|
| Attacking | 45 | xG_p90 0.40, Gls_p90 0.35, Ast_p90 0.15, SoT_p90 0.10 |
| Progression | 20 | xGBuildup_p90 0.45, DrbAttempts_p90 0.30, DrbSucc_p90 0.25 |
| Creation | 20 | xA_p90 0.55, KP_p90 0.45 |
| Defense | 5 | Tkl_p90 0.35, Int_p90 0.30, Blocks_p90 0.20, DuelsWon_p90 0.15 |
| Retention | 10 | Cmp% 0.60, DuelsWon% 0.40 |

**MF pillars (Attacking 20 / Progression 30 / Creation 25 / Defense 15 / Retention 10)**

| Pillar | Weight | Stats (internal weights) |
|---|---|---|
| Attacking | 20 | xG_p90 0.40, Gls_p90 0.30, Ast_p90 0.20, SoT_p90 0.10 |
| Progression | 30 | xGChain_p90 0.40, DrbAttempts_p90 0.35, DrbSucc_p90 0.25 |
| Creation | 25 | xA_p90 0.55, KP_p90 0.45 |
| Defense | 15 | Tkl_p90 0.35, Int_p90 0.30, Blocks_p90 0.20, DuelsWon_p90 0.15 |
| Retention | 10 | Cmp% 0.60, DuelsWon% 0.40 |

Note: MF Progression uses `xGChain_p90`; FW and DF Progression use `xGBuildup_p90` to avoid double-counting forward output.

**DF pillars (Attacking 10 / Progression 15 / Creation 10 / Defense 45 / Retention 20)**

| Pillar | Weight | Stats (internal weights) |
|---|---|---|
| Attacking | 10 | xG_p90 0.40, Gls_p90 0.30, Ast_p90 0.20, SoT_p90 0.10 |
| Progression | 15 | xGBuildup_p90 0.50, DrbAttempts_p90 0.30, DrbSucc_p90 0.20 |
| Creation | 10 | xA_p90 0.55, KP_p90 0.45 |
| Defense | 45 | Tkl_p90 0.35, Int_p90 0.30, Blocks_p90 0.20, DuelsWon_p90 0.15 |
| Retention | 20 | Cmp% 0.60, DuelsWon% 0.40 |

**GK pillars (Shot Stopping 50 / Distribution 20 / Aerial Command 15 / Sweeping 10 / Composure 5)**

The GK model reuses the same 5 pillar slot names (`attacking`, `progression`, `creation`, `defense`, `retention`) for UI compatibility, but assigns GK-specific labels and stats:

| Slot name | Display label | Weight | Stats (internal weights) |
|---|---|---|---|
| attacking | Shot Stopping | 50 | SavePct 1.0 |
| progression | Distribution | 20 | Cmp% 0.65, DuelsWon% 0.35 |
| creation | Aerial Command | 15 | DuelsWon_p90 0.65, DuelsWon% 0.35 |
| defense | Sweeping | 10 | Blocks_p90 0.55, Int_p90 0.45 |
| retention | Composure | 5 | Cmp% 1.0 |

#### Scoring formula per group
```python
scaler = MinMaxScaler()
df[available_stat_cols] = scaler.fit_transform(df[available_stat_cols].fillna(0))

for pillar_name, pillar_data in pillars.items():
    pillar_score = sum(df[stat] * stat_weight for stat, stat_weight in pillar_data["stats"].items())
    df[f"score_{pillar_name}"] = pillar_score * pillar_data["weight"]
    df["scout_score"] += df[f"score_{pillar_name}"]
```

Result: `scout_score` in range 0–100 (bounded because all inputs are MinMax-normalized to [0,1] and weights sum to 100). Five per-pillar columns `score_attacking`, `score_progression`, `score_creation`, `score_defense`, `score_retention` are preserved for visualization.

### 3b. UV Score — Undervaluation metric

```python
compute_efficiency(df)
```

Filters to players with `market_value_eur > 0`, then:

1. **Log-transform market value:** `log_mv = log10(market_value_eur)`
2. **One-hot encode positions:** `pd.get_dummies(df["Pos"], prefix="pos")`
3. **Fit OLS regression:** `log10(market_value) ~ scout_score + pos_GK + pos_FW + pos_MF + pos_DF`
4. **Compute residual:** `residual = actual_log_mv - predicted_log_mv`
   - Negative residual = player is cheaper than the model expects for their output level = undervalued
5. **UV Score:** `(-residual).rank(pct=True) * 100`
   - Percentile rank: 100 = most undervalued, 0 = most overvalued
6. **Value Gap:** `predicted_mv_eur - market_value_eur` (in euros)
   - Positive = undervalued by this amount; negative = overvalued

Output is sorted descending by `uv_score`. Top 5 are highlighted as "High-Value Targets".

---

## Stage 4: app.py — Dashboard

Streamlit single-page app with 4 tabs:

| Tab | Content |
|---|---|
| High-Value Targets | Top 5 player cards (HTML) + radar chart |
| Threat Matrix | Scatter plot (market value vs scout score, bubble size = UV score) |
| Full Scan Results | Paginated leaderboard table (top 100) |
| Capability Analysis | Stacked bar chart of pillar scores |

### Sidebar controls
- **Season filter:** multiselect from `("2023-24", "2024-25", "2025-26")`. Changes which seasons are passed to `load_data()`, causing a new pipeline run (new Streamlit cache key).
- **Position filter:** multiselect `["GK", "DF", "MF", "FW"]`. Applied as a DataFrame filter after loading.
- **Max asset value slider:** 1–200 €m. Applied as `df[df["market_value_eur"] <= max_mv * 1_000_000]`.
- **Rescan Data button:** clears `st.cache_data` and reruns.

### Data flow in app.py
```
sidebar inputs → load_data(tuple(sorted(season_filter)))  # cached 24h
  → full_df (complete scored pipeline output)
  → apply position filter → apply max_mv filter → df
  → top5 = df.head(5)
  → render 4 tabs
```

---

## Module Dependency Graph

```
app.py
  imports: config (PILLARS_*)
  calls:   scraper.run_understat_scrapers()
           scraper.run_api_football_scrapers()
           scraper.run_tm_scrapers()
           scorer.run_scoring_pipeline()

scorer.py
  imports: config (PILLARS_FW, PILLARS_MF, PILLARS_DF, GK_PILLARS)
  calls:   merger.build_dataset()

merger.py
  imports: config (SUM_STATS, MEAN_STATS, PER90_STATS, MIN_MINUTES, MIN_MINUTES_PER_SEASON, FUZZY_THRESHOLD)

scraper.py
  imports: config (SEASONS, API_FOOTBALL_BASE, API_FOOTBALL_LEAGUE, API_FOOTBALL_RATE_S,
                   TM_BASE, TM_HEADERS, TM_RATE_LIMIT_S)
  reads:   os.environ["API_FOOTBALL_KEY"]

config.py
  no imports from project
```
