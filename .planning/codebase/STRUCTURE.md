# STRUCTURE.md — Directory Layout and Key Data Structures

## Directory Layout

```
/Users/ArthurAldea/ClaudeProjects/Moneyball/
│
├── app.py               # Streamlit dashboard (entry point for UI)
├── config.py            # All constants: seasons, API URLs, pillar weights
├── scraper.py           # Data acquisition: Understat, API-Football, Transfermarkt
├── merger.py            # Aggregation, stat merging, per-90 derivation, market value matching
├── scorer.py            # Scout score (pillar model) and UV score (regression residuals)
├── requirements.txt     # Unpinned pip dependencies
├── CLAUDE.md            # Outdated project notes (references FBref, old formula — do not trust)
│
├── test_scraper.py      # Informal smoke test (references scrape_fbref_stat which no longer
│                        #   exists — broken, never run as part of a test suite)
│
├── .env                 # Not committed — must contain API_FOOTBALL_KEY=<key>
│
├── cache/               # CSV cache files (7-day TTL, auto-created)
│   ├── understat_202324.csv
│   ├── understat_202425.csv
│   ├── understat_202526.csv
│   ├── apifootball_202324.csv
│   ├── apifootball_202425.csv     # (may be absent if not yet fetched)
│   ├── apifootball_202526.csv     # (may be absent if not yet fetched)
│   ├── tm_values_202324.csv
│   ├── tm_values_202425.csv
│   └── tm_values_202526.csv
│
├── venv/                # Python 3.11 virtual environment (not committed)
│   └── lib/python3.11/site-packages/  # all pip-installed packages
│
└── __pycache__/         # Python bytecode cache (not committed)
```

---

## File Descriptions

### config.py
Pure constants file. No imports from the project. Defines:
- `SEASONS` dict mapping season labels to year integers
- Minute thresholds (`MIN_MINUTES`, `MIN_MINUTES_PER_SEASON`)
- API URLs and rate limit constants
- All four pillar configurations (`PILLARS_FW`, `PILLARS_MF`, `PILLARS_DF`, `GK_PILLARS`)
- `PILLARS` legacy alias (points to `PILLARS_MF`)
- Aggregation column lists (`UNDERSTAT_SUM`, `API_FOOTBALL_SUM`, `SUM_STATS`, `MEAN_STATS`, `PER90_STATS`)

### scraper.py
Provides three public functions:
- `run_understat_scrapers() → dict[str, DataFrame]` — all seasons
- `run_api_football_scrapers() → dict[str, DataFrame]` — all seasons
- `run_tm_scrapers() → DataFrame` — latest market values across all seasons

Also has a `__main__` block for standalone execution (`python scraper.py`).

### merger.py
Provides one public entry point used by scorer.py:
- `build_dataset(understat_data, api_data, tm_data) → DataFrame`

Internal functions:
- `normalize_name(name)` — accent stripping, lowercase, whitespace collapsing
- `_aggregate_seasons(data, sum_cols, mean_cols)` — concat + groupby aggregation
- `aggregate_understat(data, min_minutes)` — Understat aggregation with minutes filter
- `aggregate_api_football(data)` — API-Football aggregation
- `merge_stat_sources(understat_df, api_df)` — two-pass name matching merge
- `compute_per90s(df)` — derives `*_p90` columns, `DuelsWon%`, `SavePct`
- `match_market_values(df, tm_df)` — attaches `market_value_eur`

### scorer.py
Provides:
- `run_scoring_pipeline(understat_data, api_data, tm_data) → DataFrame` — full pipeline
- `compute_scout_scores(df) → DataFrame` — position-split MinMax + pillar scoring
- `compute_efficiency(df) → DataFrame` — OLS regression UV score
- `get_top_undervalued(df, n=5) → DataFrame` — convenience head() wrapper

### app.py
Streamlit single-file dashboard. Not importable as a module (uses `st.*` calls at module level). Defines:
- `load_data(seasons: tuple) → DataFrame` — `@st.cache_data(ttl=86400)` wrapper around the full pipeline
- `get_pillar_labels(pos: str) → list` — returns display labels for a position's pillars
- `radar_chart(players_df)`, `scatter_chart(df)`, `pillar_bar_chart(df, top_n)` — Plotly figure builders
- `fmt_value(v)`, `fmt_gap(v)` — formatting helpers for currency display

### test_scraper.py
Broken smoke test. Imports `scrape_fbref_stat` which does not exist in the current `scraper.py`. References FBref, which was the data source before the rewrite. Should be treated as dead code.

---

## Key Data Structures

### Raw scraper output (per season)

**Understat DataFrame** — one row per player per season:
```
Player, Squad, Pos, Min, Gls, Ast, xG, xA, npxG, xGChain, xGBuildup, Sh, KP, season
```

**API-Football DataFrame** — one row per player per season:
```
Player, Squad, Pos, Saves, GoalsConceded, SoT, Cmp%, Tkl, Blocks, Int,
DuelsTotal, DuelsWon, DrbAttempts, DrbSucc, Fld, season
```

**Transfermarkt DataFrame** (after `run_tm_scrapers()` deduplication):
```
player_name_tm, club_tm, market_value_eur
```

### After merger.build_dataset()

All raw stats aggregated across seasons + per-90 derivations + market value:
```
Player, Squad, Pos, Min,
Gls, Ast, xG, xA, npxG, xGChain, xGBuildup, Sh, KP,          ← Understat sums
Saves, GoalsConceded, SoT, Tkl, Blocks, Int,                   ← API-Football sums
DuelsTotal, DuelsWon, DrbAttempts, DrbSucc, Fld,              ← API-Football sums
Cmp%,                                                           ← API-Football mean
Gls_p90, Ast_p90, xG_p90, xA_p90, npxG_p90, xGChain_p90,    ← derived per-90
xGBuildup_p90, Sh_p90, KP_p90, Saves_p90, SoT_p90,           ← derived per-90
Tkl_p90, Blocks_p90, Int_p90, DuelsWon_p90,                   ← derived per-90
DrbAttempts_p90, DrbSucc_p90, Fld_p90,                        ← derived per-90
DuelsWon%, SavePct,                                             ← derived rates
market_value_eur                                                ← from Transfermarkt
```

### After scorer.compute_scout_scores()

Adds pillar score columns (stats are overwritten in-place with MinMax-normalized values within the position group):
```
... all merger columns (with normalized stat values for used columns) ...,
score_attacking, score_progression, score_creation, score_defense, score_retention,
scout_score
```

### After scorer.compute_efficiency()

Adds UV score columns (rows with no market value are dropped):
```
... all scorer columns ...,
predicted_log_mv, predicted_mv_eur,
residual, uv_score, value_gap_eur
```
Sorted descending by `uv_score`.

### Display columns in Tab 3 (Full Scan Results)
```
Player → PLAYER
Squad  → CLUB
Pos    → POS
scout_score      → EXPLOIT INDEX
market_value_eur → ASSET VALUE (formatted as €Xm or €Xk)
uv_score         → VULN SCORE
value_gap_eur    → VECTOR DIFF (formatted with UNDERVALUED/OVERVALUED label)
```

### Pillar color constants (app.py)
```python
PILLAR_COLS   = ["score_attacking","score_progression","score_creation","score_defense","score_retention"]
PILLAR_COLORS = ["#ff3131","#00ff41","#00cfff","#f5a623","#c084fc"]
```
Position scatter colors: `FW="#ff3131"`, `MF="#00ff41"`, `DF="#f5a623"`, `GK="#00cfff"`.
