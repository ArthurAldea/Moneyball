# CONVENTIONS.md — Code Conventions and Patterns

## Module-Level Docstrings

Every source file opens with a triple-quoted module docstring that explains what the file does and lists its key responsibilities. Examples:

```python
# scraper.py
"""
scraper.py — Fetches EPL player data from two sources:
  1. Understat (async Python library) — xG, xA, npxG, xGChain, goals, assists, shots, key passes
  2. API-Football (api-sports.io REST) — tackles, blocks, interceptions, dribbles, pass accuracy, duels
  3. Transfermarkt (curl_cffi Chrome impersonation with persistent session) — market values
Caches all results to cache/ for 7 days.
"""
```

```python
# scorer.py
"""
scorer.py — Position-specific scout scoring and undervaluation formula.

Each position group uses a tailored pillar model:
  FW  — Attacking 45 / Progression 20 / Creation 20 / Defense 5  / Retention 10
  ...
"""
```

## Function Docstrings

Public functions have single-line or short paragraph docstrings. Private helper functions (`_` prefix) sometimes have inline comments instead of full docstrings.

```python
def aggregate_understat(data: dict, min_minutes: int = MIN_MINUTES) -> pd.DataFrame:
    """Aggregate Understat seasons into a single per-player DataFrame."""
```

```python
def build_dataset(understat_data: dict, api_data: dict, tm_data: pd.DataFrame) -> pd.DataFrame:
    """Full merge pipeline: aggregate → merge sources → per-90s → market values."""
```

Longer docstrings explain algorithm choices:
```python
def compute_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """
    UV Score via position-aware regression residuals.

    Fits: log10(market_value) ~ scout_score + position_dummies
    Residual = actual_log_mv − predicted_log_mv
    Negative residual → player is cheaper than expected for their output → undervalued.
    UV Score = percentile rank of (−residual); 100 = most undervalued.
    Value Gap = predicted_mv − actual_mv (€).
    """
```

## Type Hints

Function signatures use type hints consistently on all public functions:
- `-> pd.DataFrame` for DataFrame returns
- `-> dict` for dictionary returns
- `-> str`, `-> float`, `-> bool`, `-> list` for primitive returns
- Parameters typed: `df: pd.DataFrame`, `data: dict`, `name: str`, `max_age_days: int = 7`

Private helpers follow the same convention. No use of `Optional`, `Union`, or `typing` module imports — Python 3.10+ union syntax is not used either; hints are kept simple.

## Naming Conventions

**Functions:** `snake_case`. Private helpers prefixed with `_`:
- `_cache_path()`, `_is_fresh()`, `_map_understat_pos()`, `_fetch_understat_season()`
- `_score_group()`, `_aggregate_seasons()`

**Variables:** `snake_case`. DataFrame variables follow a short-form convention:
- `df` — working DataFrame (current pipeline stage)
- `us_df` — Understat aggregated DataFrame
- `af_df` — API-Football aggregated DataFrame
- `tm_df` — Transfermarkt DataFrame
- `base`, `af` — local copies in merge functions
- `sub` — filtered subset in scatter chart

**Constants in config.py:** `UPPER_SNAKE_CASE` for all module-level constants.

**Pillar dicts:** lowercase keys (`"attacking"`, `"progression"`, etc.) matching both config.py and the `score_*` column naming pattern in scorer.py.

**Column names:** PascalCase for raw stats matching their source convention (`Player`, `Squad`, `Pos`, `Min`, `Gls`, `Ast`, `xG`, `Cmp%`). Lowercase with underscores for derived columns (`market_value_eur`, `scout_score`, `uv_score`, `value_gap_eur`, `predicted_log_mv`). Per-90 columns append `_p90` suffix (`xG_p90`, `Tkl_p90`). Rate columns append `%` or `%` suffix (`Cmp%`, `DuelsWon%`).

## Section Comments

Code within files is divided into clearly labelled sections using banner-style comments:

```python
# ── Cache helpers ─────────────────────────────────────────────────────────────
# ── Position mappers ──────────────────────────────────────────────────────────
# ── Understat ─────────────────────────────────────────────────────────────────
# ── API-Football ──────────────────────────────────────────────────────────────
# ── Transfermarkt via curl_cffi — club squad pages ────────────────────────────
# ── Entry point ───────────────────────────────────────────────────────────────
```

Inline comments explain non-obvious choices:
```python
# Understat uses space-separated tokens: 'F', 'M', 'D', 'G', 'S', or 'GK'
# e.g. 'F M' = winger, 'D M' = defensive mid, 'GK' = goalkeeper
```
```python
# SavePct = saves / (saves + goals_conceded) — rewards quality, not volume.
# Higher saves/90 at a weak team is penalised; good GKs at strong teams rewarded.
```

## Print-Based Logging

There is no logging module, no log levels, no structured logging. All progress output uses `print()` with a consistent bracketed-prefix convention:

| Prefix | Meaning |
|---|---|
| `[cache]` | Returning data from cache file |
| `[fetch]` | Fetching live data from source |
| `[warn]` | Non-fatal error (scrape failed, key missing, no data) |
| `[merger]` | Step in merger.build_dataset() |
| `[scorer]` | Step in scorer pipeline |
| `→` | Counts/results after a fetch |

Examples:
```python
print(f"  [cache] {cache_key}")
print(f"  [fetch] Understat {season_label}")
print(f"    → {len(df)} players")
print(f"  [warn] Understat failed {season_label}: {e}")
print(f"  [scorer] Missing columns (scored 0): {missing}")
```

Two-space indent on sub-steps, four-space on counts. Top-level phase headers use `===` wrapping in the `__main__` block.

## DataFrame Mutation Patterns

### Explicit `.copy()` to avoid SettingWithCopyWarning

Every function that modifies a DataFrame starts with `df = df.copy()`:
```python
def compute_per90s(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ...

def match_market_values(df: pd.DataFrame, tm_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    tm = tm_df.copy()
    ...

def compute_scout_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ...
```

The only exception is within `_score_group`, which receives a `.copy()` from the caller:
```python
frames.append(_score_group(df[mask].copy(), pillars))
```

### In-place operations (intentional)
`inplace=True` is used in a few places where the variable is a local copy:
```python
df.drop(columns=["market_value_raw"], inplace=True)
df.drop(columns=["_norm"], inplace=True)
```

### fillna(0) for scoring
Missing stat values are filled with 0 before MinMaxScaler normalization, treating absent data as the minimum possible performance:
```python
df[available] = scaler.fit_transform(df[available].fillna(0))
```

### pd.to_numeric with errors="coerce"
Used defensively throughout to handle mixed-type columns from CSV round-trips:
```python
df[col] = pd.to_numeric(combined[col], errors="coerce")
df["market_value_eur"] = pd.to_numeric(df["market_value_eur"], errors="coerce")
```

### .replace(0, np.nan) for division
Prevents division-by-zero in per-90 calculations and rate derivations:
```python
min_col = pd.to_numeric(df["Min"], errors="coerce").replace(0, np.nan)
total = pd.to_numeric(df["DuelsTotal"], errors="coerce").replace(0, np.nan)
shots_faced = (saves + conceded).replace(0, np.nan)
```

## Error Handling Patterns

### try/except with [warn] print and empty DataFrame return
All external requests are wrapped in try/except. On failure, a warning is printed and an empty DataFrame returned. Callers check `df.empty` before proceeding:

```python
try:
    df = asyncio.run(_fetch_understat_season(season_year, season_label))
    df.to_csv(path, index=False)
    return df
except Exception as e:
    print(f"  [warn] Understat failed {season_label}: {e}")
    return pd.DataFrame()
```

```python
try:
    resp = requests.get(...)
except Exception as e:
    print(f"  [warn] team {team_id} p{page}: {e}")
    break
```

### HTTP status code checks
Non-200 status codes are checked explicitly and cause a `return []` or `break`:
```python
if resp.status_code != 200:
    return []
```

### Graceful degradation (not full error recovery)
If Understat returns empty, `merge_stat_sources` returns the empty DataFrame immediately. If API-Football returns empty, merger returns Understat-only data (Defense/Retention pillars score 0). If Transfermarkt returns empty, `market_value_eur` is set to NaN for all players — they are then excluded from `compute_efficiency()` and thus absent from UV scoring entirely.

### app.py top-level catch
The pipeline call in app.py is wrapped in a broad `except`:
```python
try:
    full_df = load_data(tuple(sorted(season_filter)))
except Exception as e:
    st.error(f"// PIPELINE ERROR: {e}")
    st.stop()
```
This surfaces errors to the dashboard user but stops all rendering.

## Async Conventions

Only Understat uses async. It is executed synchronously at the call site via `asyncio.run()`, keeping the rest of the codebase synchronous:
```python
def scrape_understat_season(...) -> pd.DataFrame:
    ...
    df = asyncio.run(_fetch_understat_season(season_year, season_label))
```

The async function `_fetch_understat_season` is private and never called directly.

## Import Style

Standard library imports first, then third-party, then local config imports:
```python
import os
import re
import time
import asyncio
import requests
import pandas as pd
from curl_cffi import requests as cf_requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from config import (SEASONS, API_FOOTBALL_BASE, ...)
```

Local imports that would cause circular imports are deferred inside function bodies:
```python
def run_scoring_pipeline(...):
    from merger import build_dataset  # deferred to avoid circular import
```
```python
def aggregate_understat(...):
    from config import UNDERSTAT_SUM  # deferred (avoids re-importing at module level)
```
