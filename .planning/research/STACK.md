# Stack Research

*Written: 2026-03-16. Based on training knowledge (cutoff August 2025). Where version numbers or
2025-specific site behaviour is unverified by live fetch, a [UNVERIFIED] tag is used. Core
architecture recommendations are solid; version pinning should be confirmed at install time.*

---

## Recommended Approach

**Use `soccerdata` as the primary FBref abstraction layer, with a direct
`requests` + `lxml` fallback for any table `soccerdata` does not expose.**

Rationale:

- `soccerdata` wraps FBref's comment-embedded tables, handles the per-request delay
  requirement, and surfaces data via clean pandas DataFrames. It covers all five target
  leagues and all stat categories needed by the pillar model.
- Direct scraping via `requests` + `lxml` / `BeautifulSoup` is reliable but requires
  per-project maintenance every time FBref changes a table ID. Using `soccerdata` shifts
  that maintenance burden to the library maintainer for the standard tables.
- The existing stack (`requests`, `beautifulsoup4`, `lxml`, `curl_cffi`) is almost entirely
  preserved. The only new dependency is `soccerdata` itself.
- `understat` and `aiohttp` are the only removals (EPL-only sources being replaced).
- Team strength data: use FBref's own league-table scrape via `soccerdata` — zero extra dependency.

---

## FBref Scraping Options

### Option A — `soccerdata` (recommended primary)

**What it is:** A Python library (PyPI: `soccerdata`) that provides a unified interface to
multiple football data sources including FBref, Sofascore, ESPN, and others. The FBref
scraper is the most mature component.

**FBref tables exposed** [UNVERIFIED: exact method names as of late 2025 — confirm against
current docs at `soccerdata.readthedocs.io`]:

| soccerdata method | FBref stat category | Pillar relevance |
|---|---|---|
| `FBref.read_player_season_stats("standard")` | Standard stats: goals, assists, npxG, xAG, minutes, age | All positions |
| `FBref.read_player_season_stats("shooting")` | Shots, SoT, npxG, G-xG | FW Attack pillar |
| `FBref.read_player_season_stats("passing")` | xAG, key passes, prog passes, pass completion | MF Creation + Prog pillars |
| `FBref.read_player_season_stats("goal_shot_creation")` | SCA, GCA per 90 | FW/MF Creation pillar |
| `FBref.read_player_season_stats("defense")` | Tackles, interceptions, blocks, pressures | DF/MF Defense pillar |
| `FBref.read_player_season_stats("possession")` | Progressive carries, dribbles, touches in final third | FW/MF Prog + Retention pillars |
| `FBref.read_player_season_stats("misc")` | Aerial duels won/lost, fouls, cards | DF Aerial pillar |
| `FBref.read_player_season_stats("keepers")` | Save%, PSxG, clean sheets | GK Shot-Stopping pillar |
| `FBref.read_player_season_stats("keepers_adv")` | PSxG-GA, launched passes, sweeper actions | GK Distribution + Sweeping pillars |
| `FBref.read_league_table()` | League standings, points, position | Team strength adjustment |

**League support:** EPL (`ENG-Premier League`), La Liga (`ESP-La Liga`), Bundesliga
(`GER-Bundesliga`), Serie A (`ITA-Serie A`), Ligue 1 (`FRA-Ligue 1`) — all supported.
[UNVERIFIED: exact league slug strings — confirm from soccerdata docs before coding.]

**Rate limiting behaviour:**
- `soccerdata` enforces a configurable delay between requests. Default is ~3 seconds.
- Disable soccerdata's internal cache; manage caching at the project level (7-day CSV cache).
- FBref does not currently use CloudFlare — standard `requests` with browser User-Agent works.
  [UNVERIFIED: CloudFlare status as of early 2026 — if 403s appear, fall back to `curl_cffi`.]
- A 3–6 second delay between fetches is sufficient. Full refresh = ~15 requests ≈ 75 seconds.

**Pros:** No manual HTML comment unwrapping. Consistent column names. Multi-season support.
**Cons:** Dependency on upstream maintenance. Internal cache must be disabled. Silent failures possible.

**Version:** [UNVERIFIED: latest stable ~0.9.x as of August 2025 — run `pip index versions soccerdata`.]

---

### Option B — Direct `requests` + `lxml` / `BeautifulSoup` (fallback / override)

**The core gotcha: FBref serves most stat tables inside HTML comments.**

```python
import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd

def get_fbref_table(url: str, table_id: str) -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", {"id": table_id})
    if table is None:
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            if table_id in comment:
                comment_soup = BeautifulSoup(comment, "lxml")
                table = comment_soup.find("table", {"id": table_id})
                if table is not None:
                    break
    if table is None:
        raise ValueError(f"Table '{table_id}' not found on {url}")
    return pd.read_html(str(table), header=1)[0]
```

Key points:
- Use `lxml` as the BeautifulSoup parser (faster, more robust than html.parser).
- `pd.read_html(str(table), header=1)` — FBref uses two-row headers; `header=1` is usually correct.
- `pd.read_html(url)` directly will NOT work — tables are inside comments.

---

## Team Strength Data

**Recommendation: FBref league table (zero extra dependency)**

`soccerdata`'s `read_league_table()` returns position, points, GD for all five leagues.
Map league position (1–20) to a strength scalar (e.g. 0.8–1.2) applied before pillar scoring.

**Alternative: ClubElo API** — `http://api.clubelo.com/{YYYY-MM-DD}` returns CSV of all club
Elo ratings. No auth required. More nuanced than position but adds a dependency. Defer to v2.

---

## Key Dependencies to Add/Remove

### Add
| Package | Reason |
|---|---|
| `soccerdata` | Primary FBref abstraction — replaces manual scraping of all stat categories |

### Remove
| Package | Reason |
|---|---|
| `understat` | EPL-only xG source being replaced by FBref |
| `aiohttp` | Only present as a dependency of `understat`; not used elsewhere |

### Retain
`requests`, `curl_cffi`, `beautifulsoup4`, `lxml`, `pandas`, `numpy`, `scikit-learn`,
`rapidfuzz`, `python-dotenv`, `streamlit`, `plotly`, `statsmodels`

### Proposed requirements.txt
```
soccerdata
requests
curl_cffi
beautifulsoup4
lxml
pandas
numpy
scikit-learn
rapidfuzz
python-dotenv
streamlit
plotly
statsmodels
```

---

## FBref 2025-Specific Gotchas

1. **Two-row column headers.** Columns appear as tuples like `("Expected", "xG")`. `soccerdata` flattens automatically. Raw parsing: `df.columns = ['_'.join(c).strip() for c in df.columns]`.
2. **"Unnamed" multi-index columns.** Player/Squad/Age columns lack a group header — parse as `("Unnamed:...", "Player")`. Strip the unnamed prefix.
3. **Duplicate player rows.** Players who moved clubs mid-season appear twice plus a summary row (`Squad == "2 Clubs"`). Filter these before scoring.
4. **CloudFlare.** Not currently used by FBref as of August 2025. [UNVERIFIED for early 2026.]
5. **Request pacing.** ~3s minimum between requests. Project's 7-day cache = ~15 total requests per full refresh.
6. **GK stats split.** Basic GK (`keepers`) and advanced GK (`keepers_adv`) are separate table fetches. Both required for the full GK pillar model.
7. **Season strings.** FBref uses `"2024-2025"` format. Cache keys: `"{season}_{league}_{table}"`.

---

## Confidence Levels

| Topic | Confidence |
|---|---|
| soccerdata covers all required FBref stat categories | High |
| FBref comment-table pattern and two-row header handling | High |
| Remove `understat` + `aiohttp`, add `soccerdata` | High |
| FBref pacing requirement (~3s between requests) | High |
| Duplicate player rows (multi-club) gotcha | High |
| GK stats require two separate table fetches | High |
| FBref not behind CloudFlare as of 2026 | Medium |
| Exact `soccerdata` version and method signatures | Medium |
| No post-August-2025 FBref table structural changes | Low |
