# TESTING.md — Testing

## Current State

There are zero passing tests in this codebase.

`test_scraper.py` exists at the project root but is broken:
```python
from scraper import scrape_tm_season, scrape_fbref_stat, run_tm_scrapers, run_fbref_scrapers
```
It imports `scrape_fbref_stat` and `run_fbref_scrapers`, which do not exist in the current `scraper.py`. FBref was the original data source; the scraper was rewritten to use Understat and API-Football. `test_scraper.py` was never updated and will throw an `ImportError` on import. It has no test framework (no pytest, no unittest); it just calls functions and prints results.

There is no pytest configuration, no `conftest.py`, no `tests/` directory, and no CI/CD pipeline.

---

## What Would Need to Be Tested

### 1. config.py — Pillar weight validation
- Each position's pillar weights sum to 100
- Each pillar's internal stat weights sum to 1.0
- `UNDERSTAT_SUM` + `API_FOOTBALL_SUM` = `SUM_STATS`
- All stats referenced in pillar configs appear in `PER90_STATS` or `MEAN_STATS` or are derived metrics (`SavePct`, `DuelsWon%`)
- These are pure arithmetic checks with no I/O, making them trivial to test

### 2. scraper.py — Position mapping functions
- `_map_understat_pos`: `"F M"` → `"FW"`, `"D M"` → `"DF"`, `"GK"` → `"GK"`, `"M"` → `"MF"`, `""` → `"MF"`, `"G"` → `"GK"`, `"S"` → `"MF"`
- `_map_api_football_pos`: `"Goalkeeper"` → `"GK"`, `"Attacker"` → `"FW"`, unknown → `"MF"`
- `_parse_tm_value`: `"€45.00m"` → `45_000_000.0`, `"€500Th."` → `500_000.0`, `"-"` → `nan`, `""` → `nan`, `"€1.5m"` → `1_500_000.0`
- `_is_fresh`: mock `os.path.getmtime` and `os.path.exists` to test age boundary (6.9 days = fresh, 7.1 days = stale)

### 3. merger.py — Core pipeline logic

**`normalize_name`:**
- `"Raphaël Varane"` → `"raphael varane"`
- `"Bruno Fernandes"` → `"bruno fernandes"`
- Leading/trailing/double spaces collapsed
- Non-string input returns `""`

**`_aggregate_seasons`:**
- Two seasons of the same player are summed for sum_cols and averaged for mean_cols
- `Squad` and `Pos` take the last season's values
- Player appearing in only one season still appears in output

**`aggregate_understat` with min_minutes filter:**
- Player with 800 total minutes (< 900 × 1 season threshold) is excluded
- Player with 950 minutes is included
- Threshold scales correctly with season count

**`compute_per90s`:**
- Player with 90 minutes and 1 goal → `Gls_p90 = 1.0`
- Player with 180 minutes and 1 goal → `Gls_p90 = 0.5`
- Player with 0 minutes → all `_p90` columns are `NaN` (not infinity)
- `DuelsWon%`: player with 0 total duels → `NaN` (not ZeroDivisionError)
- `SavePct`: GK with 10 saves, 5 goals conceded → `SavePct = 66.67`

**`merge_stat_sources`:**
- Exact name match attaches correct stats
- Fuzzy match below threshold (< 80) results in NaN row
- Fuzzy match above threshold attaches stats
- Player in Understat with no API-Football entry → all API-Football cols are NaN

**`match_market_values`:**
- Exact match on normalized name attaches correct `market_value_eur`
- Fuzzy match on `"Salah"` / `"Mohamed Salah"` attaches value if score ≥ 80
- Player with no match gets `NaN`

### 4. scorer.py

**`_score_group`:**
- With empty DataFrame returns early without error
- All output `scout_score` values are in range [0, 100]
- A player with all-max stats scores higher than a player with all-min stats
- Missing stat columns are reported via print and scored as 0
- `score_attacking + score_progression + score_creation + score_defense + score_retention ≈ scout_score` (floating point equality within tolerance)

**`compute_scout_scores`:**
- GK players use GK_PILLARS (e.g., `score_attacking` represents Shot Stopping)
- FW players use PILLARS_FW
- All rows are present after position-split and recombination
- No position group is dropped silently

**`compute_efficiency`:**
- Players with `market_value_eur = 0` or `NaN` are excluded from output
- `uv_score` range is (0, 100] for all returned rows (percentile rank)
- Top-ranked player has highest `uv_score`
- `value_gap_eur` is positive for undervalued players (predicted > actual)
- Output is sorted descending by `uv_score`

### 5. Integration test: build_dataset → compute_scout_scores → compute_efficiency
- Feed known fixture DataFrames through the full pipeline
- Assert output has expected columns
- Assert no unexpected NaN in `scout_score` for any player with full data
- Assert `uv_score` exists for all players who had a market value

---

## Recommended Test Approach

### Framework
**pytest** — standard for Python data projects. No configuration currently exists; add a `pyproject.toml` or `pytest.ini` at the project root.

### Directory structure
```
tests/
├── conftest.py            # shared fixtures (sample DataFrames)
├── test_config.py         # weight validation
├── test_scraper.py        # position mappers, value parser, cache freshness
├── test_merger.py         # normalize_name, aggregation, per-90, merge, market value
└── test_scorer.py         # _score_group, compute_scout_scores, compute_efficiency
```

### Fixture strategy
Build minimal DataFrames in `conftest.py` that represent the output of each pipeline stage. This avoids network calls entirely:

```python
# conftest.py
import pytest
import pandas as pd

@pytest.fixture
def sample_understat_df():
    return pd.DataFrame([
        {"Player": "Alice Smith", "Squad": "Arsenal", "Pos": "FW",
         "Min": 2700, "Gls": 18, "Ast": 5, "xG": 16.2, "xA": 4.1,
         "npxG": 15.1, "xGChain": 20.0, "xGBuildup": 3.0, "Sh": 70, "KP": 30,
         "season": "2024-25"},
    ])

@pytest.fixture
def sample_api_df():
    return pd.DataFrame([
        {"Player": "Alice Smith", "Squad": "Arsenal", "Pos": "FW",
         "Saves": 0, "GoalsConceded": 0, "SoT": 40, "Cmp%": 82.0,
         "Tkl": 15, "Blocks": 8, "Int": 10, "DuelsTotal": 100,
         "DuelsWon": 55, "DrbAttempts": 60, "DrbSucc": 35, "Fld": 20,
         "season": "2024-25"},
    ])
```

### What NOT to test (network-dependent)
- Live scraper network calls (mock these or skip with `pytest.mark.skip`)
- Transfermarkt HTML parsing against live pages (HTML structure changes)
- API-Football pagination logic against live API (costs requests)

Use `unittest.mock.patch` or `pytest-mock` to mock `requests.get`, `aiohttp.ClientSession`, and `curl_cffi.requests.Session` when testing the scraper routing logic without hitting the network.

### Continuous integration note
There is no CI configuration (no `.github/workflows/`, no `Makefile`). If tests are added, a minimal GitHub Actions workflow running `pytest tests/` on push would be the natural addition.
