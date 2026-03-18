# INTEGRATIONS.md — External Data Sources

## 1. Understat

**Type:** Python library (async, wraps Understat's internal JSON API)
**Library:** `understat` (pip package) + `aiohttp` (async HTTP backend)
**Endpoint:** `understat.get_league_players("EPL", season_year)` where `season_year` is an integer (e.g. `2023`, `2024`, `2025`)

### What it provides
Per-player season totals for the EPL. Raw field names from the API response and how they are mapped:

| Understat field | Stored as | Description |
|---|---|---|
| `player_name` | `Player` | Player display name |
| `team_title` | `Squad` | Club name |
| `position` | `Pos` (mapped) | Raw position string (e.g. `"F M"`, `"GK"`) |
| `time` | `Min` | Total minutes played |
| `goals` | `Gls` | Goals |
| `assists` | `Ast` | Assists |
| `xG` | `xG` | Expected goals |
| `xA` | `xA` | Expected assists |
| `npxG` | `npxG` | Non-penalty expected goals |
| `xGChain` | `xGChain` | xG from all actions in a goal chain |
| `xGBuildup` | `xGBuildup` | xG buildup (excludes own shots/chances) |
| `shots` | `Sh` | Total shots |
| `key_passes` | `KP` | Key passes |

### Position mapping (Understat → internal)
Understat encodes position as space-separated tokens: `F`, `M`, `D`, `G`, `GK`, `S`.
- First token `G` or `GK` → `GK`
- Any token `F` present → `FW`
- Any token `D` present (no F) → `DF`
- Otherwise → `MF`

### Rate limiting / authentication
None. Understat is a public site; the library uses `aiohttp` internally. No API key needed.

### Async execution
The async coroutine `_fetch_understat_season` is executed synchronously via `asyncio.run(...)` in `scrape_understat_season`.

### Cache files
One CSV per season:
- `cache/understat_202324.csv`
- `cache/understat_202425.csv`
- `cache/understat_202526.csv`

---

## 2. API-Football (api-sports.io)

**Type:** REST API (JSON)
**Base URL:** `https://v3.football.api-sports.io`
**Authentication:** Header `x-apisports-key: <API_FOOTBALL_KEY>` (set in `.env`)
**League ID:** `39` (English Premier League)
**HTTP client:** `requests` (synchronous)

### Endpoints used

#### GET /teams
Fetches all teams in the EPL for a given season.
```
GET /teams?league=39&season=<year>
```
Returns an array of team objects; only `team.id` (integer) is extracted. One call per season = 1 request consumed.

#### GET /players
Fetches player statistics per team, paginated.
```
GET /players?league=39&season=<year>&team=<team_id>&page=<page>
```
Iterated per team, per page until `paging.total` is exhausted. Each page can return up to 20 players.

### Fields extracted from /players response

Each item has `player` (identity) and `statistics[0]` (stats for the season):

| JSON path | Stored as | Description |
|---|---|---|
| `player.name` | `Player` | Player name |
| `statistics[0].team.name` | `Squad` | Club name |
| `statistics[0].games.position` | `Pos` (mapped) | `"Goalkeeper"`, `"Defender"`, `"Midfielder"`, `"Attacker"` |
| `statistics[0].goals.saves` | `Saves` | GK saves |
| `statistics[0].goals.conceded` | `GoalsConceded` | Goals conceded (GK) |
| `statistics[0].shots.on` | `SoT` | Shots on target |
| `statistics[0].passes.accuracy` | `Cmp%` | Pass completion % (string or float) |
| `statistics[0].tackles.total` | `Tkl` | Tackles |
| `statistics[0].tackles.blocks` | `Blocks` | Blocks |
| `statistics[0].tackles.interceptions` | `Int` | Interceptions |
| `statistics[0].duels.total` | `DuelsTotal` | Total duels |
| `statistics[0].duels.won` | `DuelsWon` | Duels won |
| `statistics[0].dribbles.attempts` | `DrbAttempts` | Dribble attempts |
| `statistics[0].dribbles.success` | `DrbSucc` | Successful dribbles |
| `statistics[0].fouls.drawn` | `Fld` | Fouls drawn |

### Position mapping (API-Football → internal)
| API-Football | Internal |
|---|---|
| `"Goalkeeper"` | `GK` |
| `"Defender"` | `DF` |
| `"Midfielder"` | `MF` |
| `"Attacker"` | `FW` |
| anything else | `MF` |

### Rate limiting
- `API_FOOTBALL_RATE_S = 1.5` seconds of `time.sleep()` before every request (both `/teams` and each `/players` page).
- Free tier: 100 requests/day. With 20 EPL teams × ~2 pages each = ~40 requests per season, plus 3 seasons × 1 `/teams` call = ~123 requests for a full 3-season refresh. This exceeds the free tier limit in a single day, meaning the 2025-26 season's GK data (which requires `Saves`/`GoalsConceded`) is likely incomplete on a cold run.
- Deduplication: a `seen_players` set prevents double-counting players who appear for multiple teams.

### Cache files
One CSV per season:
- `cache/apifootball_202324.csv`

Note: at time of codebase snapshot, only the 2023-24 season had an API-Football cache file. The 2024-25 and 2025-26 caches were absent, meaning those seasons would trigger live API calls (subject to rate limits).

---

## 3. Transfermarkt

**Type:** Web scraper (HTML)
**HTTP client:** `curl_cffi` with Chrome TLS impersonation (`impersonate="chrome120"`)
**Session type:** Persistent `curl_cffi.requests.Session()` (reused across all club requests per season)

### Scraping strategy
Two-stage scrape per season:

**Stage 1 — Club list page:**
```
GET https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1/saison_id/<year>
```
Parses `table.items td.hauptlink a[href*="/verein/"]` to extract club slug and club ID from the href pattern `/verein/<id>/`.

**Stage 2 — Squad (kader) pages per club:**
```
GET https://www.transfermarkt.com/<club_slug>/kader/verein/<club_id>/saison_id/<year>/plus/1
```
The `/plus/1` parameter causes the page to show all registered players (not just the default short squad). Parses `table.items tr.odd` and `tr.even` rows. For each row:
- Player name: first `td.hauptlink a` with non-digit text
- Market value: text content of the last `td` cell

### Market value parsing (`_parse_tm_value`)
Raw strings like `"€45.00m"`, `"€500Th."`, `"€500k"` are converted to float euros:
- Suffix `m` → multiply by 1,000,000
- Suffix `Th.` or `k` → multiply by 1,000
- `-` or empty → `float("nan")`

### Headers used
```python
{
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,...",
    "Referer": "https://www.transfermarkt.com/",
}
```

### Rate limiting
`TM_RATE_LIMIT_S = 5` seconds of `time.sleep()` before every request (club list page, each squad page, plus a warm-up pause at session start). With 20 clubs + 1 list page = ~21 requests × 5s = ~105 seconds per season = ~5 minutes for all 3 seasons.

### Multi-season deduplication
`run_tm_scrapers()` concatenates all seasons, drops players with no market value, then groups by `player_name_tm` and takes `.last()` — meaning each player retains only their most recent market value entry.

### Output columns
After `run_tm_scrapers()`:
- `player_name_tm` — player name as it appears on Transfermarkt
- `club_tm` — club name from Transfermarkt
- `market_value_eur` — float, market value in euros

### Cache files
One CSV per season:
- `cache/tm_values_202324.csv`
- `cache/tm_values_202425.csv`
- `cache/tm_values_202526.csv`

---

## 4. Cache Layer

**Location:** `cache/` directory at project root (created automatically)
**Format:** CSV files written via `pandas.DataFrame.to_csv(path, index=False)` and read via `pd.read_csv(path)`
**TTL:** 7 days

### Freshness check
```python
def _is_fresh(path: str, max_age_days: int = 7) -> bool:
    if not os.path.exists(path): return False
    return (time.time() - os.path.getmtime(path)) / 86400 < max_age_days
```
Uses file modification time (`os.path.getmtime`). If fresh, returns the cached CSV. If stale or missing, re-fetches from the live source.

### Cache key naming convention
| Source | Season | Cache file |
|---|---|---|
| Understat | 2023-24 | `cache/understat_202324.csv` |
| Understat | 2024-25 | `cache/understat_202425.csv` |
| Understat | 2025-26 | `cache/understat_202526.csv` |
| API-Football | 2023-24 | `cache/apifootball_202324.csv` |
| API-Football | 2024-25 | `cache/apifootball_202425.csv` |
| API-Football | 2025-26 | `cache/apifootball_202526.csv` |
| Transfermarkt | 2023-24 | `cache/tm_values_202324.csv` |
| Transfermarkt | 2024-25 | `cache/tm_values_202425.csv` |
| Transfermarkt | 2025-26 | `cache/tm_values_202526.csv` |

Key construction: `f"{source}_{season_label.replace('-', '')}"` → e.g. `understat_202324`.

### Streamlit cache
`app.py` wraps `load_data()` with `@st.cache_data(ttl=86400)` — a 24-hour in-memory cache at the Streamlit layer, separate from and on top of the CSV cache. The "RESCAN DATA" button calls `st.cache_data.clear()` and `st.rerun()` to force a full refresh.
