# Phase 1 Research: FBref Scraper (EPL)

*Compiled: 2026-03-16. Sources: existing .planning/research/ files, soccerdata library source, FBref URL pattern analysis.*

---

## FBref URL Structure

### EPL Comp ID

FBref identifies the Premier League as **comp_id = 9**. This appears in every EPL stats URL.

### URL Pattern

```
https://fbref.com/en/comps/{comp_id}/{season}/{stat_page}/{season}-{league-slug}-Stats
```

**EPL Examples:**

| Stat table | URL |
|------------|-----|
| Standard | `https://fbref.com/en/comps/9/2024-2025/stats/2024-2025-Premier-League-Stats` |
| Shooting | `https://fbref.com/en/comps/9/2024-2025/shooting/2024-2025-Premier-League-Stats` |
| Passing | `https://fbref.com/en/comps/9/2024-2025/passing/2024-2025-Premier-League-Stats` |
| Defense | `https://fbref.com/en/comps/9/2024-2025/defense/2024-2025-Premier-League-Stats` |
| Possession | `https://fbref.com/en/comps/9/2024-2025/possession/2024-2025-Premier-League-Stats` |
| Misc | `https://fbref.com/en/comps/9/2024-2025/misc/2024-2025-Premier-League-Stats` |
| Keepers | `https://fbref.com/en/comps/9/2024-2025/keepers/2024-2025-Premier-League-Stats` |
| Keepers Adv | `https://fbref.com/en/comps/9/2024-2025/keepersadv/2024-2025-Premier-League-Stats` |

### Season Format in URL

FBref uses **four-digit years separated by a hyphen** in URLs: `2024-2025`, not `2024-25`.

The two target seasons map as:
- Season label `"2023-24"` → URL segment `2023-2024`
- Season label `"2024-25"` → URL segment `2024-2025`

**Current season shortcut:** `https://fbref.com/en/comps/9/stats/Premier-League-Stats` redirects to the current season. Use explicit year URLs once confirmed to avoid redirect instability mid-season.

### Stat Page URL Segments (stat_type → URL path segment)

| Stat type key | URL path segment |
|--------------|-----------------|
| `standard` | `stats` |
| `shooting` | `shooting` |
| `passing` | `passing` |
| `defense` | `defense` |
| `possession` | `possession` |
| `misc` | `misc` |
| `keeper` | `keepers` |
| `keeper_adv` | `keepersadv` |

---

## Table IDs and HTML Comment Wrapping

### The Core Gotcha: Tables Are in HTML Comments

FBref embeds most stat tables inside HTML comments. A direct `soup.find("table", id="stats_standard_9")` returns `None`. This is the most common cause of FBref scraper failures.

### Table ID Pattern

```
stats_{stat_type}_{comp_id}
```

For EPL (comp_id = 9):

| Stat type | HTML table ID |
|-----------|--------------|
| Standard | `stats_standard_9` |
| Shooting | `stats_shooting_9` |
| Passing | `stats_passing_9` |
| Defense | `stats_defense_9` |
| Possession | `stats_possession_9` |
| Misc | `stats_misc_9` |
| Keepers | `stats_keeper_9` |
| Keepers Advanced | `stats_keeper_adv_9` |

For future multi-league expansion (comp_ids: La Liga=12, Bundesliga=20, Serie A=11, Ligue 1=13), the same pattern applies.

### Correct Extraction Pattern (BeautifulSoup)

```python
from bs4 import BeautifulSoup, Comment
import pandas as pd

def get_fbref_table(url: str, table_id: str) -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # First try direct (some tables are not commented)
    table = soup.find("table", {"id": table_id})
    if table is None:
        # Search HTML comments — this is where most FBref tables live
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            if table_id in comment:
                comment_soup = BeautifulSoup(str(comment), "lxml")
                table = comment_soup.find("table", {"id": table_id})
                if table is not None:
                    break
    if table is None:
        raise ValueError(f"Table '{table_id}' not found on {url}")
    return pd.read_html(str(table), header=1)[0]
```

**Alternative using lxml/etree (soccerdata approach):**

```python
from lxml import etree

(el,) = tree.xpath(f"//comment()[contains(.,'div_stats_{stat_type}')]")
parser = etree.HTMLParser(recover=True)
(html_table,) = etree.fromstring(el.text, parser).xpath(
    f"//table[contains(@id, 'stats_{stat_type}')]"
)
```

The BeautifulSoup Comment approach is simpler and consistent with the existing codebase style.

### Multi-Level Column Headers

FBref tables use a **two-row header structure** (group row + stat name row). After `pd.read_html()`:

- Columns arrive as a `MultiIndex`: `("Performance", "Gls")`, `("Expected", "xG")`, etc.
- Identity columns (Player, Squad, Age, etc.) have `("Unnamed: N_level_0", "Player")` format
- Accessing `df["xG"]` raises `KeyError`

**Required flattening immediately after `pd.read_html()`:**

```python
# Use header=1 to skip the group row and use the stat name row directly
df = pd.read_html(str(table), header=1)[0]
# If header=1 still produces tuples, flatten manually:
if isinstance(df.columns[0], tuple):
    df.columns = [col[1] if (col[1] and not col[1].startswith("Unnamed")) else col[0]
                  for col in df.columns]
```

**Note:** `header=1` (0-indexed second row) typically gives the correct leaf names. Test both `header=0` and `header=1` — FBref has varied this structure between stat types.

### Duplicate Header Rows

FBref repeats column header rows every ~20 data rows. These appear as rows where `Rk == "Rk"`. Filter them before any processing:

```python
df = df[df["Rk"] != "Rk"].reset_index(drop=True)
```

---

## Column Name Mapping

### Source Column Names (FBref Raw)

After `pd.read_html(str(table), header=1)` and header deduplication, these are the FBref column names per table. Note that column names may vary slightly between `header=0` and `header=1` — always verify against actual output.

#### `stats_standard` — Standard Stats

| FBref column | Description | Pillar relevance |
|-------------|-------------|-----------------|
| `Player` | Player name | Identity |
| `Nation` | Nationality | Identity |
| `Pos` | Position(s) | Position assignment |
| `Squad` | Club name | Identity |
| `Age` | Age (format: `YY-DDD` years-days, e.g. `25-142`) | Age-weighted UV |
| `Born` | Birth year | Age fallback |
| `MP` | Matches played | Filter |
| `Starts` | Starts | Filter |
| `Min` | Minutes played | Min-minutes filter |
| `90s` | 90-minute equivalents | Alternative to Min |
| `Gls` | Goals | FW/MF/DF Attacking |
| `Ast` | Assists | FW/MF/DF Attacking/Creation |
| `G+A` | Goals + Assists | - |
| `G-PK` | Non-penalty goals | - |
| `PK` | Penalty kicks made | - |
| `PKatt` | Penalty kicks attempted | - |
| `CrdY` | Yellow cards | - |
| `CrdR` | Red cards | - |
| `xG` | Expected goals (StatsBomb) | FW/MF/DF Attacking |
| `npxG` | Non-penalty expected goals | FW/MF/DF Attacking |
| `xAG` | Expected assisted goals (was `xA` before 2022-23) | Creation |
| `npxG+xAG` | Combined non-penalty xG + xAG | - |
| `PrgC` | Progressive carries | FW/DF Progression |
| `PrgP` | Progressive passes | MF Progression |
| `PrgR` | Progressive passes received | - |

**Critical column rename warning:** `xA` was renamed to `xAG` in the 2022-23 season. Use `xAG` throughout.

#### `stats_shooting` — Shooting

| FBref column | Description | Pillar relevance |
|-------------|-------------|-----------------|
| `Gls` | Goals | - |
| `Sh` | Total shots | FW Attacking |
| `SoT` | Shots on target | FW Attacking |
| `SoT%` | Shots on target % | - |
| `Sh/90` | Shots per 90 | - |
| `SoT/90` | SoT per 90 | - |
| `G/Sh` | Goals per shot | - |
| `G/SoT` | Goals per shot on target | - |
| `Dist` | Average shot distance | - |
| `FK` | Shots from free kicks | - |
| `PK` | Penalty kicks | - |
| `PKatt` | Penalty attempts | - |
| `xG` | Expected goals | - |
| `npxG` | Non-penalty xG | - |
| `npxG/Sh` | Non-penalty xG per shot | - |
| `G-xG` | Goals minus xG | - |
| `np:G-xG` | Non-penalty G minus npxG | - |

#### `stats_passing` — Passing

| FBref column | Description | Pillar relevance |
|-------------|-------------|-----------------|
| `Cmp` | Passes completed | - |
| `Att` | Passes attempted | - |
| `Cmp%` | Pass completion % | Retention pillar |
| `TotDist` | Total passing distance | - |
| `PrgDist` | Progressive passing distance | - |
| `Cmp` (Short) | Short pass completions | - |
| `Att` (Short) | Short pass attempts | - |
| `Cmp%` (Short) | Short pass completion % | - |
| `Cmp` (Medium) | Medium pass completions | - |
| `Att` (Medium) | Medium pass attempts | - |
| `Cmp%` (Medium) | Medium pass completion % | - |
| `Cmp` (Long) | Long pass completions | - |
| `Att` (Long) | Long pass attempts | - |
| `Cmp%` (Long) | Long pass completion % | - |
| `Ast` | Assists | Creation |
| `xAG` | Expected assisted goals | Creation |
| `xA` | Expected assists (may appear in older seasons) | Creation |
| `A-xAG` | Assists minus xAG | - |
| `KP` | Key passes | Creation |
| `1/3` | Passes into final third | - |
| `PPA` | Passes into penalty area | - |
| `CrsPA` | Crosses into penalty area | - |
| `PrgP` | Progressive passes | MF Progression |

**Note on duplicate column names after multi-level flattening:** The passing table has sub-groups (Short/Medium/Long/Total) each with `Cmp`, `Att`, `Cmp%`. After header=1 flattening, these will appear as duplicated column names. Use `header=0` to preserve group context, or use `df.iloc[:, col_index]` positional access for `Cmp%` (total). The overall `Cmp%` is typically in the first group (columns 4-6 in the table). Alternatively, reconstruct `Cmp%` from total `Cmp` / total `Att * 100`.

#### `stats_defense` — Defensive Actions

| FBref column | Description | Pillar relevance |
|-------------|-------------|-----------------|
| `Tkl` | Tackles | DF/MF Defense |
| `TklW` | Tackles won | DF/MF Defense (alternative to Tkl) |
| `Def 3rd` | Tackles in defensive third | - |
| `Mid 3rd` | Tackles in midfield third | - |
| `Att 3rd` | Tackles in attacking third | - |
| `Tkl` (challenges) | Dribblers tackled | - |
| `Att` (challenges) | Dribbles challenged | - |
| `Tkl%` | Tackle success % | - |
| `Lost` | Dribbles lost | - |
| `Blocks` | Total blocks | DF/MF Defense |
| `Sh` (blocks) | Shots blocked | - |
| `Pass` (blocks) | Passes blocked | - |
| `Int` | Interceptions | DF/MF Defense |
| `Tkl+Int` | Combined Tkl + Int | - |
| `Clr` | Clearances | - |
| `Err` | Errors leading to shot | - |

**Note:** The defense table has sub-groups for "Tackles" and "Challenges" that each have a `Tkl` column. After header=1 flattening you get two `Tkl` columns. Use the first `Tkl` (overall tackles) not the challenges `Tkl` (dribblers tackled). Best approach: use `header=0` to get group context, then select `("Tackles", "Tkl")` for total tackles.

#### `stats_possession` — Possession

| FBref column | Description | Pillar relevance |
|-------------|-------------|-----------------|
| `Touches` | Total touches | - |
| `Def Pen` | Touches in defensive penalty area | - |
| `Def 3rd` | Touches in defensive third | - |
| `Mid 3rd` | Touches in midfield third | - |
| `Att 3rd` | Touches in attacking third | - |
| `Att Pen` | Touches in attacking penalty area | - |
| `Live` | Live-ball touches | - |
| `Att` (take-ons) | Take-ons attempted | FW Progression (DrbAttempts) |
| `Succ` (take-ons) | Take-ons successful | FW Progression (DrbSucc) |
| `Succ%` (take-ons) | Take-on success % | - |
| `Tkld` | Times tackled during take-on | - |
| `Tkld%` | Times tackled % | - |
| `Carries` | Total ball carries | - |
| `TotDist` (carries) | Total carry distance | - |
| `PrgDist` (carries) | Progressive carry distance | - |
| `PrgC` | Progressive carries | FW/DF Progression |
| `1/3` (carries) | Carries into final third | - |
| `CPA` | Carries into penalty area | - |
| `Mis` | Miscontrols | - |
| `Dis` | Dispossessed | - |
| `Rec` | Passes received | - |
| `PrgR` | Progressive passes received | - |

**FBref column name for dribbles:** In the possession table, take-ons are the dribbles equivalent. `Att` = `DrbAttempts` (old API-Football name); `Succ` = `DrbSucc`. After header flattening these appear without group prefix — use positional or group-keyed access.

#### `stats_misc` — Miscellaneous

| FBref column | Description | Pillar relevance |
|-------------|-------------|-----------------|
| `CrdY` | Yellow cards | - |
| `CrdR` | Red cards | - |
| `2CrdY` | Second yellow | - |
| `Fls` | Fouls committed | - |
| `Fld` | Fouls drawn | FW Retention |
| `Off` | Offsides | - |
| `Crs` | Crosses | - |
| `TklW` | Tackles won | - |
| `PKwon` | Penalty kicks won | - |
| `PKcon` | Penalty kicks conceded | - |
| `OG` | Own goals | - |
| `Recov` | Ball recoveries | - |
| `Won` (aerial) | Aerial duels won | DF Aerial / GK Aerial |
| `Lost` (aerial) | Aerial duels lost | DF Aerial |
| `Won%` (aerial) | Aerial duel win % | DF Aerial |

#### `stats_keeper` — Goalkeeper Basic

| FBref column | Description | Pillar relevance |
|-------------|-------------|-----------------|
| `GA` | Goals against | GK Shot Stopping |
| `GA90` | Goals against per 90 | GK Shot Stopping |
| `SoTA` | Shots on target against | GK Shot Stopping |
| `Saves` | Saves | GK Shot Stopping |
| `Save%` | Save % | GK Shot Stopping |
| `W` | Wins | - |
| `D` | Draws | - |
| `L` | Losses | - |
| `CS` | Clean sheets | GK Shot Stopping |
| `CS%` | Clean sheet % | - |
| `PKatt` | Penalty kicks attempted against | - |
| `PKA` | Penalty kicks allowed | - |
| `PKsv` | Penalty kicks saved | - |
| `PKm` | Penalty kicks missed | - |
| `Save%` (PK) | Penalty save % | - |

**Column name mapping for existing code:**
- Old `Saves` → FBref `Saves` (same name, direct use)
- Old `GoalsConceded` → FBref `GA`
- Old `SavePct` (derived: saves/(saves+conceded)) → FBref `Save%` (direct column) or derive from `Saves` + `GA`

#### `stats_keeper_adv` — Goalkeeper Advanced

| FBref column | Description | Pillar relevance |
|-------------|-------------|-----------------|
| `GA` | Goals against | - |
| `PSxG` | Post-shot expected goals | GK Shot Stopping quality |
| `PSxG/SoT` | PSxG per shot on target | - |
| `PSxG+/-` | PSxG minus goals allowed | GK Shot Stopping quality |
| `/90` | PSxG+/- per 90 | - |
| `Cmp` (launched) | Launched passes completed | GK Distribution |
| `Att` (launched) | Launched passes attempted | GK Distribution |
| `Cmp%` (launched) | Launched pass completion % | GK Distribution |
| `Att` (passes) | Passes attempted | GK Distribution |
| `Thr` | Throws attempted | - |
| `Launch%` | % of passes launched | - |
| `AvgLen` | Average pass length | - |
| `Att` (goal kicks) | Goal kicks attempted | - |
| `Launch%` (goal kicks) | % of goal kicks launched | - |
| `AvgLen` (goal kicks) | Average goal kick length | - |
| `Opp` (crosses) | Crosses faced | GK Sweeping |
| `Stp` (crosses) | Crosses stopped | GK Sweeping |
| `Stp%` (crosses) | Cross stop % | GK Sweeping |
| `#OPA` | Defensive actions outside penalty area | GK Sweeping |
| `#OPA/90` | Defensive actions OPA per 90 | GK Sweeping |
| `AvgDist` | Average distance of defensive actions | GK Sweeping |

---

## Column Name Mapping (Old → FBref)

This is the complete translation from existing Understat + API-Football column names to FBref equivalents. This mapping drives the `config.py` pillar model updates in Phase 2.

| Old column (Understat/API-Football) | FBref table | FBref column | Notes |
|-------------------------------------|-------------|--------------|-------|
| `xG` | `stats_standard` | `xG` | Direct match |
| `xA` | `stats_standard` | `xAG` | Renamed 2022-23; use `xAG` |
| `npxG` | `stats_standard` | `npxG` | Direct match |
| `xGChain` | *Not available* | `PrgP` + `SCA` | See progression replacement below |
| `xGBuildup` | *Not available* | `PrgC` | See progression replacement below |
| `Gls` | `stats_standard` | `Gls` | Direct match |
| `Ast` | `stats_standard` | `Ast` | Direct match |
| `Sh` (shots) | `stats_shooting` | `Sh` | Direct match |
| `SoT` (shots on target) | `stats_shooting` | `SoT` | Direct match |
| `KP` (key passes) | `stats_passing` | `KP` | Direct match |
| `Cmp%` (pass completion) | `stats_passing` | `Cmp%` | Total row (not short/medium/long) |
| `Tkl` (tackles) | `stats_defense` | `Tkl` | First `Tkl` col (total tackles) |
| `Blocks` | `stats_defense` | `Blocks` | Direct match |
| `Int` (interceptions) | `stats_defense` | `Int` | Direct match |
| `DrbAttempts` | `stats_possession` | `Att` (take-ons) | Group label is "Take-Ons" |
| `DrbSucc` | `stats_possession` | `Succ` (take-ons) | Group label is "Take-Ons" |
| `DuelsTotal` | `stats_misc` | Derived: `Won` + `Lost` (aerial) | Only aerial duels in FBref |
| `DuelsWon` | `stats_misc` | `Won` (aerial) | Only aerial duels in FBref |
| `Fld` (fouls drawn) | `stats_misc` | `Fld` | Direct match |
| `Saves` | `stats_keeper` | `Saves` | Direct match |
| `GoalsConceded` | `stats_keeper` | `GA` | Renamed |
| `Min` | `stats_standard` | `Min` | Direct match |
| `Pos` | `stats_standard` | `Pos` | Direct match (may include multiple positions e.g. "FW,MF") |
| `Squad` | `stats_standard` | `Squad` | Direct match |

### FBref-Only Columns (new, no old equivalent)

| FBref column | Table | Pillar use |
|-------------|-------|-----------|
| `PrgP` | `stats_standard` | MF Progression (replaces `xGChain`) |
| `PrgC` | `stats_standard` or `stats_possession` | FW/DF Progression (replaces `xGBuildup`) |
| `SCA` | `stats_gca` (goal_shot_creation) | MF Progression blend |
| `Save%` | `stats_keeper` | GK Shot Stopping (replaces derived `SavePct`) |
| `PSxG+/-` | `stats_keeper_adv` | GK Shot Stopping quality |
| `Won` (aerial) | `stats_misc` | DF Aerial / GK Aerial Command |
| `Won%` (aerial) | `stats_misc` | DF Aerial / GK Aerial Command |

### Progression Pillar Replacement (Critical Model Change)

The existing pillar model references `xGChain_p90` (MF) and `xGBuildup_p90` (FW/DF), which are Understat-proprietary and unavailable on FBref. REQUIREMENTS.md (SCORE-02, SCORE-03) defines the replacements:

- **MF Progression (30% weight):** `0.6 × PrgP_p90 + 0.4 × SCA_p90`
- **FW Progression and DF Progression:** `PrgC_p90`

This is a model change that belongs to Phase 2. Phase 1 must ensure `PrgP`, `PrgC`, and `SCA` columns are present in the cached output.

### FBref Position Format

FBref `Pos` column can contain comma-separated values: `"FW,MF"`, `"DF,MF"`, `"GK"`. The existing `_map_understat_pos()` function logic (first token determines primary position) is the correct approach. Take the first position before the comma.

---

## Rate Limiting Strategy

### What FBref Enforces

- **429 Too Many Requests** triggers at approximately 20–25 requests within 60 seconds (roughly >1 request per 2.5s sustained).
- **HTTP 403** can occur from Cloudflare if requests lack browser headers or use overly uniform intervals. As of August 2025, FBref does not actively use Cloudflare, but defensive headers are still recommended.
- Cloudflare bans can persist hours even after requests stop.

### Recommended Delay Strategy

```python
import random
import time

# Between every FBref request
time.sleep(random.uniform(3.5, 6.0))
```

- **3.5–6.0 seconds randomized** — matches DATA-06 requirement and avoids bot fingerprinting from uniform intervals.
- Do NOT parallelize FBref requests. Serial only.
- Cold run for Phase 1 (EPL, 8 tables × 2 seasons = 16 requests): ~16 × 5s average = ~80 seconds.

### Exponential Backoff on 429

DATA-06 specifies: 30s → 60s → 120s.

```python
BACKOFF_DELAYS = [30, 60, 120]

def _fetch_with_backoff(url: str, headers: dict) -> requests.Response:
    for attempt, delay in enumerate(BACKOFF_DELAYS + [None]):
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 429:
            if delay is None:
                raise RuntimeError(f"429 after {len(BACKOFF_DELAYS)} retries: {url}")
            print(f"  [warn] 429 on {url} — backing off {delay}s (attempt {attempt+1})")
            time.sleep(delay)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError("Unreachable")
```

### What a 429 Looks Like from FBref

- HTTP status code: `429`
- Response body: HTML page with text similar to "Too Many Requests" or a Cloudflare challenge page
- `resp.status_code == 429` is the correct check
- Do NOT rely on response body text — check status code only

### User-Agent Header

FBref requires a plausible User-Agent to avoid 403. Use:

```python
FBREF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
```

This is consistent with the existing TM headers pattern in the codebase.

---

## Cache Architecture

### Naming Convention (DATA-05)

```
cache/fbref_{league}_{table}_{season}.csv
```

**League key:** lowercase slug — `EPL` (or `epl` per ARCHITECTURE.md — confirm with project decision)
**Season key:** `YYYY-YY` format matching ROADMAP.md success criteria: `2024-25`
**Table key:** exact FBref table type string

**Confirmed examples from ROADMAP.md success criteria:**
```
cache/fbref_EPL_stats_standard_2024-25.csv
cache/fbref_EPL_stats_shooting_2024-25.csv
cache/fbref_EPL_stats_passing_2024-25.csv
cache/fbref_EPL_stats_defense_2024-25.csv
cache/fbref_EPL_stats_possession_2024-25.csv
cache/fbref_EPL_stats_misc_2024-25.csv
cache/fbref_EPL_stats_keeper_2024-25.csv
cache/fbref_EPL_stats_keeper_adv_2024-25.csv
```

**Note:** ROADMAP.md uses `stats_standard` (with `stats_` prefix) and uppercase `EPL`. ARCHITECTURE.md uses lowercase `epl` and no `stats_` prefix. The ROADMAP.md success criteria are the binding source of truth for Phase 1 — use the exact format `fbref_EPL_stats_standard_2024-25.csv`.

### TTL

Retain existing **7-day mtime check** from `_is_fresh()`. No change required to the TTL logic.

```python
def _is_fresh(path: str, max_age_days: int = 7) -> bool:
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) / 86400 < max_age_days
```

### Rationale for One File Per Table

Isolates scrape failures — a network error on `stats_keeper_adv` does not invalidate a good `stats_standard` cache. Each of the 8 tables can fail/succeed independently and be re-run selectively.

### Cache Key Construction

```python
def _fbref_cache_key(league: str, table: str, season: str) -> str:
    # league: "EPL", table: "stats_standard", season: "2024-25"
    return f"fbref_{league}_{table}_{season}"
    # → "fbref_EPL_stats_standard_2024-25"
```

### Season Scope for Phase 1

Phase 1 targets **2 seasons**: `2023-24` and `2024-25` (per ROADMAP.md: "both seasons"). This replaces the old 3-season scope from CLAUDE.md (`2022-23, 2023-24, 2024-25`). Confirm final season list before implementing.

---

## Multi-Table Join Strategy

### Player Identity Column

All 8 FBref tables share `Player` and `Squad` columns on the same page, scoped to the same league and season. The join key is `Player` + `Squad` (handles mid-season transfers).

### Join Approach

Left-join all 7 supplemental tables onto `stats_standard` as the base:

```python
# stats_standard is authoritative for: Player, Squad, Pos, Age, Min
base = standard_df  # has Player, Squad, Pos, Age, Born, Min, xG, npxG, xAG, PrgP, PrgC

# Join each supplemental table
merged = base.merge(shooting_df[["Player", "Squad", "Sh", "SoT"]], on=["Player", "Squad"], how="left")
merged = merged.merge(passing_df[["Player", "Squad", "Cmp%", "KP", "PrgP"]], on=["Player", "Squad"], how="left")
# ... etc for all 8 tables
```

**Why left-join on standard:** `stats_standard` has all outfield players. GK-only tables (`stats_keeper`, `stats_keeper_adv`) have only goalkeepers — outfield players get NaN for keeper columns, which is correct.

### Player Deduplication: Multi-Club Mid-Season Transfers

FBref creates **three rows** for players who transferred mid-season:
1. Row for Club A (partial season)
2. Row for Club B (partial season)
3. A summary row with `Squad` = `"2 Clubs"` (or `"3 Clubs"` etc.)

**Strategy:**
- For per-90 stats and scoring: use the **aggregate summary row** (`Squad == "2 Clubs"`) — it has full-season totals
- For team-strength adjustment (Phase 4): use per-club rows
- **Phase 1 filter:** Drop rows where `Squad` matches the pattern `r"\d+ Clubs?"`:

```python
df = df[~df["Squad"].str.contains(r"\d+ Clubs?", na=False, regex=True)]
```

Wait — this drops the aggregate. The correct behavior depends on downstream use:

**Phase 1 recommendation:** Keep all rows in the raw cache. Apply deduplication in the merger (Phase 2). The scraper's job is to capture the data faithfully.

**Alternatively:** Keep only the aggregate row per player (dropping per-club rows) to simplify Phase 1. This works for scoring but breaks team-strength adjustment in Phase 4.

**Decision needed:** ARCHITECTURE.md says "only aggregate row for scoring" and "per-club rows for team strength." Phase 1 is scraper only — cache the raw table as-is, and document that deduplication happens in the merger.

### Column Conflicts Across Tables

Multiple tables have `Gls`, `Ast` etc. When joining, suffix conflicts with pandas merge:

```python
# Avoid column conflicts by selecting only needed columns before joining
shooting_cols = ["Player", "Squad", "Sh", "SoT"]  # no Gls/Ast
passing_cols  = ["Player", "Squad", "Cmp%", "KP", "PrgP"]
```

Explicitly select only required columns from each table before merging to avoid `_x`/`_y` suffixes.

### Keeper Join

`stats_keeper` and `stats_keeper_adv` contain only GK rows. Join onto the full `stats_standard` base — outfield players get NaN keeper columns. GKs should have matching `Player` + `Squad` across all tables.

---

## Age Data

### FBref Age Format

The `Age` column in `stats_standard` uses format `YY-DDD` where:
- `YY` = years
- `DDD` = days since last birthday

Examples: `"25-142"` = 25 years and 142 days old; `"21-003"` = 21 years and 3 days old.

### Extraction Pattern

```python
def _parse_age(age_str: str) -> float:
    """Extract numeric age from FBref YY-DDD format. Returns float years."""
    if pd.isna(age_str) or not isinstance(age_str, str):
        return float("nan")
    parts = str(age_str).split("-")
    if len(parts) >= 1:
        try:
            years = int(parts[0])
            days = int(parts[1]) if len(parts) > 1 else 0
            return years + days / 365.25
        except (ValueError, IndexError):
            pass
    return float("nan")
```

For the pillar scorer and age-weighted UV, integer age (years only) is sufficient:

```python
df["Age"] = df["Age"].str.split("-").str[0].apply(pd.to_numeric, errors="coerce")
```

### Where Age Is Used

- Age-weighted UV score formula (Phase 2): `age_weight` computed from `df["Age"]`
- PROFILE-01 display (Phase 6): player age in header block

---

## Risks and Gotchas

### 1. xA vs xAG Column Name Change

FBref renamed `xA` to `xAG` starting with the 2022-23 season. If scraping 2023-24 and 2024-25 only (Phase 1 scope), `xAG` is correct throughout. If ever scraping 2022-23 or older, the scraper must check for both names:

```python
xa_col = "xAG" if "xAG" in df.columns else "xA"
```

### 2. Passing Table Duplicate Column Names

The passing table has Short/Medium/Long/Total sub-groups each containing `Cmp`, `Att`, `Cmp%`. After `header=1` flattening, pandas appends `.1`, `.2`, `.3` suffixes to deduplicate. The total `Cmp%` is typically the first occurrence (no suffix). Confirm by checking column position: total passing columns appear before the Short group.

### 3. Defense Table Duplicate `Tkl`

The defense table has "Tackles" group (with `Tkl` = total tackles) and "Challenges" group (with `Tkl` = dribblers tackled). After header=1 flattening these become `Tkl` and `Tkl.1`. Use the first `Tkl` (total tackles) for the defense pillar.

### 4. Possession Table Sub-Group Ambiguity

The possession table has multiple sub-groups (Touches, Take-Ons, Carries, Receiving). After flattening, `Att`, `Succ` appear from the Take-Ons group. `PrgC` appears from Carries group. Position-based column access or `header=0` with `MultiIndex` is more reliable than relying on deduplication suffixes.

### 5. `stats_gca` Not in the 8 Required Tables

The 8 required tables listed in REQUIREMENTS.md (DATA-02) do not include `stats_gca` (goal/shot creation). However, the `SCA` stat (shot-creating actions) needed for the MF Progression replacement formula (SCORE-02) comes from `stats_gca`. Phase 1 must include this table even though it's not in the DATA-02 list, **or** confirm that `SCA` is available in another table.

**Check:** The `stats_standard` table does NOT include SCA. The `stats_gca` page is required. Either add it to the Phase 1 table list or defer SCA to Phase 2 and use `PrgP` only for the MF Progression replacement.

**Recommendation:** Scrape `stats_gca` in Phase 1 and cache it as `fbref_EPL_stats_gca_2024-25.csv`. It is one additional HTTP request and enables the full SCORE-02 implementation in Phase 2.

### 6. `header=0` vs `header=1` Inconsistency

FBref tables are inconsistent: some tables render with the group row as a true header (requiring `header=0` for the `MultiIndex` representation), while others produce better results with `header=1` (skipping the group row). The recommended pattern is:

1. Try `pd.read_html(str(table), header=1)[0]` first
2. If columns are still tuples, flatten with join
3. If column names are wrong, fall back to `header=0` with MultiIndex handling

### 7. "Players Who Moved Clubs" Aggregate Row Squad Name

The aggregate row for transferred players uses `"2 Clubs"` as the `Squad` value. The exact format has been observed as both `"2 Clubs"` and `"2 teams"`. The regex pattern `r"\d+ Clubs?"` may miss `"2 teams"`. Use a broader filter: `df[df["Squad"].str.match(r"^\d+", na=False)]` to catch any squad name starting with a digit.

### 8. soccerdata vs Direct Scraping Decision

The STACK.md recommends `soccerdata` as the primary FBref abstraction. However, Phase 1 is rewriting `scraper.py` — using the direct requests+BeautifulSoup approach means:
- No new dependency beyond what already exists
- Full control over caching, column naming, and error handling
- Consistent with existing TM scraper pattern
- Requires maintaining HTML comment extraction and column flattening manually

Using `soccerdata`:
- Handles comment extraction and multi-level headers automatically
- But requires disabling its internal cache and managing the 7-day TTL ourselves
- Adds a new dependency with potential upstream breakage
- Rate limit is 7s (soccerdata default) vs 3.5–6s (project requirement)

**Phase 1 recommendation:** Use direct requests+BeautifulSoup (Option B from STACK.md). This minimizes dependencies and keeps the scraper consistent with the existing codebase pattern. Add `soccerdata` as an optional fallback reference only.

### 9. FBref Returns 403 for Scripted Requests Without Delay

FBref blocks requests with no delay or minimal delay. Even with a valid User-Agent, making requests too quickly triggers 403. The 3.5–6s random delay is mandatory from the first request.

### 10. `test_scraper.py` Already Imports `scrape_fbref_stat` and `run_fbref_scrapers`

The existing `test_scraper.py` (line 1) already imports `scrape_fbref_stat` and `run_fbref_scrapers` from `scraper.py`. These functions don't exist yet. Phase 1 must implement both:
- `scrape_fbref_stat(table_type: str, season_label: str, league: str = "EPL") -> pd.DataFrame`
- `run_fbref_scrapers(league: str = "EPL") -> dict`

---

## Validation Architecture

Phase 1 success criteria (ROADMAP.md) define five verifiable checkpoints. Here is how to validate each:

### Criterion 1: Cache Files Populated

```python
import os
from pathlib import Path

CACHE_DIR = "cache"
LEAGUES = ["EPL"]
TABLES = ["stats_standard", "stats_shooting", "stats_passing", "stats_defense",
          "stats_possession", "stats_misc", "stats_keeper", "stats_keeper_adv"]
SEASONS = ["2023-24", "2024-25"]

for league in LEAGUES:
    for table in TABLES:
        for season in SEASONS:
            path = os.path.join(CACHE_DIR, f"fbref_{league}_{table}_{season}.csv")
            assert os.path.exists(path), f"Missing cache: {path}"
            df = pd.read_csv(path)
            assert len(df) > 0, f"Empty cache: {path}"
```

### Criterion 2: All Required Columns Present and Non-Empty

```python
REQUIRED_COLS_BY_TABLE = {
    "stats_standard": ["Player", "Squad", "Pos", "Age", "Min", "Gls", "Ast", "xG", "npxG", "xAG", "PrgP", "PrgC"],
    "stats_shooting": ["Player", "Squad", "Sh", "SoT"],
    "stats_passing": ["Player", "Squad", "Cmp%", "KP"],
    "stats_defense": ["Player", "Squad", "Tkl", "Int", "Blocks"],
    "stats_possession": ["Player", "Squad", "PrgC"],  # DrbAttempts/DrbSucc via Att/Succ
    "stats_misc": ["Player", "Squad", "Won", "Lost"],  # aerial duels
    "stats_keeper": ["Player", "Squad", "Saves", "GA", "Save%"],
    "stats_keeper_adv": ["Player", "Squad", "PSxG"],
}

for table, required_cols in REQUIRED_COLS_BY_TABLE.items():
    for season in SEASONS:
        path = f"cache/fbref_EPL_{table}_{season}.csv"
        df = pd.read_csv(path)
        for col in required_cols:
            assert col in df.columns, f"Missing column {col} in {path}"
            assert df[col].notna().sum() > 0, f"Column {col} is all NaN in {path}"
```

### Criterion 3: Min-Minutes Filter Applied

```python
for season in SEASONS:
    df = pd.read_csv(f"cache/fbref_EPL_stats_standard_{season}.csv")
    min_col = pd.to_numeric(df["Min"], errors="coerce")
    assert (min_col >= 900).all() or min_col.isna().sum() == 0, \
        f"Players with < 900 min in {season}"
```

### Criterion 4: Cache Hit — No Network on Second Run

Validate by:
1. Running `python scraper.py` once (cold, takes ~80s)
2. Checking all 16 cache files exist and have mtime within last 10 minutes
3. Running `python scraper.py` again — should complete in <2 seconds
4. All output lines should show `[cache]` prefix, no `[fetch]` lines

### Criterion 5: 429 Backoff Behavior

Manual integration test:
- Temporarily reduce `random.uniform` to `(0.1, 0.2)` to force a 429
- Confirm output shows `[warn] 429 — backing off 30s`
- Confirm second retry shows `[warn] 429 — backing off 60s`
- Confirm third retry shows `[warn] 429 — backing off 120s`
- Confirm fourth consecutive 429 raises `RuntimeError` rather than crashing silently

---

## Open Questions for Planning

1. **Season scope:** ROADMAP.md says "both seasons" for Phase 1. The config.py SEASONS dict currently has `2023-24, 2024-25, 2025-26`. Should Phase 1 scrape `2023-24` and `2024-25` only, or all three? The ROADMAP.md success criteria reference `2024-25` and equivalents — confirm whether `2025-26` is in Phase 1 scope.

2. **`stats_gca` inclusion:** The SCA column (needed for SCORE-02's MF Progression formula) comes from `stats_gca`, which is not in the DATA-02 required table list. Should Phase 1 include `stats_gca` as a 9th table, or should SCORE-02 use PrgP only (deferred SCA blend to Phase 2)?

3. **League key casing:** ROADMAP.md success criteria use uppercase `EPL` in the filename (`fbref_EPL_stats_standard_2024-25.csv`). ARCHITECTURE.md uses lowercase. Phase 1 must match ROADMAP.md exactly since those are the acceptance tests.

4. **Min-minutes filter location:** Should the 900-minute filter be applied in the scraper (so cached CSVs only contain qualifying players), or in the merger? Phase 1 success criterion 3 says "absent from the cached DataFrame" — filter must happen in the scraper.

5. **Transfermarkt scraper:** Phase 1 scope description says "retire Understat and API-Football scrapers entirely." The TM scraper should be retained as-is. Confirm: does Phase 1 touch the TM scraper at all?

---

*Research compiled: 2026-03-16. Based on: .planning/research/ (PITFALLS.md, ARCHITECTURE.md, STACK.md), soccerdata library source analysis, FBref URL pattern knowledge, existing codebase analysis (scraper.py, config.py, merger.py).*
