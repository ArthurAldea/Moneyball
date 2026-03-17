"""
scraper.py — Fetches EPL player data from two sources:
  1. Understat (async Python library) — xG, xA, npxG, xGChain, goals, assists, shots, key passes
  2. API-Football (api-sports.io REST) — tackles, blocks, interceptions, dribbles, pass accuracy, duels
  3. Transfermarkt (curl_cffi Chrome impersonation with persistent session) — market values
Caches all results to cache/ for 7 days.
"""

import os
import re
import time
import asyncio
import requests
import pandas as pd
from curl_cffi import requests as cf_requests
from bs4 import BeautifulSoup, Comment
from dotenv import load_dotenv

load_dotenv()

from config import (
    SEASONS, API_FOOTBALL_BASE, API_FOOTBALL_LEAGUE, API_FOOTBALL_RATE_S,
    TM_BASE, TM_HEADERS, TM_RATE_LIMIT_S,
    FBREF_LEAGUES, FBREF_TABLES, FBREF_SEASONS, FBREF_RATE_MIN, FBREF_RATE_MAX,
    FBREF_BACKOFF_SEQUENCE, FBREF_TABLE_URL_SEGMENTS, FBREF_MIN_MINUTES, FBREF_HEADERS,
    build_fbref_url,
)

CACHE_DIR    = os.path.join(os.path.dirname(__file__), "cache")
IMPERSONATE  = "chrome120"


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{key}.csv")


def _is_fresh(path: str, max_age_days: int = 7) -> bool:
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) / 86400 < max_age_days


# ── FBref cache helpers ────────────────────────────────────────────────────────

def _fbref_cache_path(league: str, table: str, season: str) -> str:
    """
    Returns the full path to the FBref cache file for a given league/table/season.

    Naming convention (DATA-05):
        cache/fbref_{league}_{table}_{season}.csv
    Examples:
        cache/fbref_EPL_stats_standard_2024-25.csv
        cache/fbref_EPL_stats_keeper_adv_2023-24.csv

    Args:
        league: Uppercase league key, e.g. "EPL"
        table:  FBref table type, e.g. "stats_standard"
        season: Short season label, e.g. "2024-25"
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    filename = f"fbref_{league}_{table}_{season}.csv"
    return os.path.join(CACHE_DIR, filename)


# ── FBref HTTP helpers ────────────────────────────────────────────────────────

def _fetch_with_backoff(url: str, headers: dict) -> requests.Response:
    """
    Fetch a URL with exponential backoff on HTTP 429.

    Backoff sequence (DATA-06): 30s → 60s → 120s.
    After the third 429, raises RuntimeError rather than hanging indefinitely.

    Args:
        url:     Full URL to fetch.
        headers: HTTP request headers dict (must include User-Agent).

    Returns:
        requests.Response with status 200.

    Raises:
        RuntimeError: If 429 persists after all backoff attempts.
        requests.HTTPError: For non-200, non-429 responses.
    """
    from config import FBREF_BACKOFF_SEQUENCE
    delays = FBREF_BACKOFF_SEQUENCE  # [30, 60, 120]

    for attempt, delay in enumerate(delays + [None]):
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 429:
            if delay is None:
                raise RuntimeError(
                    f"FBref returned 429 after {len(delays)} retries — "
                    f"aborting fetch of: {url}"
                )
            print(f"  [warn] 429 Too Many Requests — backing off {delay}s "
                  f"(attempt {attempt + 1}/{len(delays)}): {url}")
            time.sleep(delay)
            continue
        resp.raise_for_status()
        return resp

    raise RuntimeError("Unreachable")


def _extract_fbref_table(html: str, table_id: str) -> pd.DataFrame:
    """
    Extract a stats table from FBref HTML, handling comment-wrapping and
    multi-level column headers.

    FBref embeds most stat tables inside HTML comments. A direct soup.find()
    returns None — this function searches Comment nodes as a fallback.

    Column header strategy:
      - Use pd.read_html(..., header=1) to skip the group-label row and use
        the stat-name row directly as column names.
      - If duplicate column names result (e.g. defense table has two "Tkl"
        columns for "Tackles" and "Challenges" groups), pandas auto-appends
        ".1", ".2" suffixes — the first occurrence is the authoritative total.
      - Repeat header rows (rows where Rk == "Rk") are removed.

    Args:
        html:     Full HTML page text.
        table_id: FBref table id attribute, e.g. "stats_standard_9".

    Returns:
        pd.DataFrame with flattened column names and no repeat header rows.

    Raises:
        ValueError: If the table_id is not found in the page or its comments.
    """
    soup = BeautifulSoup(html, "lxml")

    # Pass 1: direct lookup (some FBref tables are not comment-wrapped)
    table = soup.find("table", {"id": table_id})

    # Pass 2: search inside HTML comment blocks
    if table is None:
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            if table_id in comment:
                comment_soup = BeautifulSoup(str(comment), "lxml")
                table = comment_soup.find("table", {"id": table_id})
                if table is not None:
                    break

    if table is None:
        raise ValueError(
            f"FBref table '{table_id}' not found in page HTML. "
            f"The page structure may have changed or the wrong URL was requested."
        )

    # Parse with header=1 to use the stat-name row (row index 1) as column headers,
    # skipping the group-label row (row index 0).
    df = pd.read_html(str(table), header=1)[0]

    # If columns are still tuples (MultiIndex survived), flatten them.
    if isinstance(df.columns[0], tuple):
        df.columns = [
            col[1] if (col[1] and not str(col[1]).startswith("Unnamed")) else col[0]
            for col in df.columns
        ]

    # Remove repeated header rows (FBref repeats the header every ~20 rows).
    if "Rk" in df.columns:
        df = df[df["Rk"] != "Rk"].reset_index(drop=True)

    return df


# ── FBref scraper ─────────────────────────────────────────────────────────────

def scrape_fbref_stat(
    table_type: str,
    season_label: str,
    league: str = "EPL",
) -> pd.DataFrame:
    """
    Scrape a single FBref stat table for a given league and season, with
    7-day CSV caching and 900-minute player filter.

    Cache naming (DATA-05):
        cache/fbref_{league}_{table_type}_{season_label}.csv
        e.g. cache/fbref_EPL_stats_standard_2024-25.csv

    Rate limiting (DATA-06):
        Waits random.uniform(FBREF_RATE_MIN, FBREF_RATE_MAX) seconds before
        each HTTP request. Uses _fetch_with_backoff for 429 handling.

    Min-minutes filter (DATA-07):
        Removes players with fewer than FBREF_MIN_MINUTES (900) minutes
        before writing to cache.

    Args:
        table_type:   FBref table type key, e.g. "stats_standard".
                      If passed without "stats_" prefix (e.g. "standard"),
                      the prefix is added automatically for compatibility
                      with existing test_scraper.py call signature.
        season_label: Short season label, e.g. "2024-25".
        league:       League key, default "EPL".

    Returns:
        pd.DataFrame with player rows qualifying the 900-minute threshold.
        Returns empty DataFrame on fetch failure (logs warning).
    """
    import random
    from config import (
        FBREF_LEAGUES, FBREF_TABLE_URL_SEGMENTS, FBREF_MIN_MINUTES,
        FBREF_RATE_MIN, FBREF_RATE_MAX, FBREF_HEADERS, build_fbref_url,
    )

    # Normalise table_type: accept both "standard" and "stats_standard"
    if not table_type.startswith("stats_"):
        table_type = f"stats_{table_type}"

    path = _fbref_cache_path(league, table_type, season_label)

    if _is_fresh(path):
        print(f"  [cache] fbref_{league}_{table_type}_{season_label}")
        return pd.read_csv(path)

    # Build URL and table_id
    url = build_fbref_url(league, table_type, season_label)
    comp_id  = FBREF_LEAGUES[league]["comp_id"]
    table_id = f"{table_type}_{comp_id}"   # e.g. "stats_standard_9"

    print(f"  [fetch] FBref {league} {table_type} {season_label}")
    print(f"    URL: {url}")

    # Polite delay before request (DATA-06)
    delay = random.uniform(FBREF_RATE_MIN, FBREF_RATE_MAX)
    time.sleep(delay)

    try:
        resp = _fetch_with_backoff(url, FBREF_HEADERS)
    except Exception as e:
        print(f"  [warn] FBref fetch failed for {table_type} {season_label}: {e}")
        return pd.DataFrame()

    try:
        df = _extract_fbref_table(resp.text, table_id)
    except ValueError as e:
        print(f"  [warn] Table extraction failed: {e}")
        return pd.DataFrame()

    # Normalise xAG -> xA for stats_standard (FBref renamed xA to xAG in 2022-23).
    # Phase 2 pillar model and merger.py reference xA; rename here so downstream
    # code is consistent regardless of season. Only applies to stats_standard.
    if table_type == "stats_standard":
        if "xAG" in df.columns and "xA" not in df.columns:
            df = df.rename(columns={"xAG": "xA"})

    # Convert Min to numeric; drop non-player rows (e.g. squad totals have no Player)
    if "Player" in df.columns:
        df = df[df["Player"].notna() & (df["Player"] != "")].copy()

    if "Min" in df.columns:
        # FBref sometimes formats Min with commas: "1,234" -> 1234
        df["Min"] = (
            df["Min"].astype(str)
            .str.replace(",", "", regex=False)
        )
        df["Min"] = pd.to_numeric(df["Min"], errors="coerce")

        # DATA-07: filter out players below 900 minutes
        before = len(df)
        df = df[df["Min"].fillna(0) >= FBREF_MIN_MINUTES].copy()
        after = len(df)
        print(f"    Min-minutes filter: {before} -> {after} players (>= {FBREF_MIN_MINUTES} min)")

    df = df.reset_index(drop=True)
    df.to_csv(path, index=False)
    print(f"    -> {len(df)} players cached to {path}")
    return df


def scrape_fbref_standings(league: str = "EPL", season: str = "2024-25") -> pd.DataFrame:
    """
    Scrape EPL league standings from FBref. Returns DataFrame with Squad, Rk columns.
    Cached at cache/fbref_{league}_standings_{season}.csv with 7-day TTL.
    Reuses _extract_fbref_table and _fetch_with_backoff from scrape_fbref_stat.
    """
    cache_path = _fbref_cache_path(league, "standings", season)
    if _is_fresh(cache_path):
        return pd.read_csv(cache_path)

    # Build standings URL: same base as stats but no table_type segment
    # e.g. https://fbref.com/en/comps/9/2024-2025/2024-2025-Premier-League-Stats
    league_cfg = FBREF_LEAGUES[league]
    comp_id = league_cfg["comp_id"]
    slug    = league_cfg["slug"]
    parts   = season.split("-")
    start   = int(parts[0])
    season_long = f"{start}-{start + 1}"
    url = f"https://fbref.com/en/comps/{comp_id}/{season_long}/{season_long}-{slug}-Stats"

    html = _fetch_with_backoff(url, FBREF_HEADERS)

    # Try the known table ID first; fall back to scanning all comment nodes
    table_id = f"results{season_long}{comp_id}1_home"
    try:
        df = _extract_fbref_table(html, table_id)
    except (ValueError, Exception):
        df = None

    if df is None or df.empty or "Rk" not in df.columns:
        # Fallback: scan all HTML comment nodes for a table with Rk + Squad columns
        from bs4 import BeautifulSoup, Comment
        soup = BeautifulSoup(html, "lxml")
        df = None
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            if "<table" not in comment:
                continue
            try:
                tables = pd.read_html(str(comment), header=0)
                for t in tables:
                    if "Rk" in t.columns and "Squad" in t.columns:
                        df = t
                        break
            except Exception:
                continue
            if df is not None:
                break

    if df is None or df.empty:
        raise RuntimeError(f"Could not find standings table for {league} {season}")

    # Keep only Rk and Squad; drop summary rows (Rk is non-numeric in separator rows)
    df = df[["Rk", "Squad"]].copy()
    df["Rk"] = pd.to_numeric(df["Rk"], errors="coerce")
    df = df.dropna(subset=["Rk"]).reset_index(drop=True)
    df["Rk"] = df["Rk"].astype(int)

    df.to_csv(cache_path, index=False)
    return df


def run_fbref_scrapers(
    leagues: list | None = None,
    seasons: list | None = None,
) -> dict:
    """
    Scrape all FBref stat tables for the given leagues and seasons.

    Iterates serially over leagues → seasons → tables, calling scrape_fbref_stat
    for each combination. Each table is cached independently; a network failure
    on one table does not abort the remaining tables (DATA-05).

    Rate limiting (DATA-06): scrape_fbref_stat inserts a random 3.5–6.0s delay
    before each HTTP request. Total cold run: 8 tables × 2 seasons = 16 requests
    ≈ 80–100 seconds.

    Args:
        leagues: List of league keys to scrape (default: ["EPL"]).
                 Only "EPL" is supported in Phase 1.
        seasons: List of season labels to scrape (default: FBREF_SEASONS =
                 ["2023-24", "2024-25"]).

    Returns:
        Nested dict: {league: {season: {table_type: pd.DataFrame}}}
        Example: result["EPL"]["2024-25"]["stats_standard"] -> DataFrame
    """
    from config import FBREF_LEAGUES, FBREF_TABLES, FBREF_SEASONS

    if leagues is None:
        leagues = list(FBREF_LEAGUES.keys())   # ["EPL"]
    if seasons is None:
        seasons = FBREF_SEASONS                # ["2023-24", "2024-25"]

    results = {}

    for league in leagues:
        print(f"\n[FBref] League: {league}")
        results[league] = {}

        for season in seasons:
            print(f"\n  Season: {season}")
            results[league][season] = {}

            for table_type in FBREF_TABLES:
                df = scrape_fbref_stat(table_type, season, league)
                results[league][season][table_type] = df
                status = f"{len(df)} rows" if not df.empty else "EMPTY"
                print(f"    {table_type}: {status}")

    return results


# ── Position mappers ──────────────────────────────────────────────────────────

def _map_understat_pos(pos: str) -> str:
    # Understat uses space-separated tokens: 'F', 'M', 'D', 'G', 'S', or 'GK'
    # e.g. 'F M' = winger, 'D M' = defensive mid, 'GK' = goalkeeper
    if not pos:
        return "MF"
    tokens = pos.upper().split()
    if not tokens or tokens[0] in ("G", "GK"):
        return "GK"
    if "F" in tokens:
        return "FW"
    if "D" in tokens:
        return "DF"
    return "MF"


def _map_api_football_pos(pos: str) -> str:
    mapping = {
        "Goalkeeper": "GK",
        "Defender":   "DF",
        "Midfielder": "MF",
        "Attacker":   "FW",
    }
    return mapping.get(pos, "MF")


# ── Understat ─────────────────────────────────────────────────────────────────

async def _fetch_understat_season(season_year: int, season_label: str) -> pd.DataFrame:
    import aiohttp
    from understat import Understat

    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        players = await understat.get_league_players("EPL", season_year)

    rows = []
    for p in players:
        rows.append({
            "Player":    p.get("player_name", ""),
            "Squad":     p.get("team_title", ""),
            "Pos":       _map_understat_pos(p.get("position", "")),
            "Min":       float(p.get("time", 0) or 0),
            "Gls":       float(p.get("goals", 0) or 0),
            "Ast":       float(p.get("assists", 0) or 0),
            "xG":        float(p.get("xG", 0) or 0),
            "xA":        float(p.get("xA", 0) or 0),
            "npxG":      float(p.get("npxG", 0) or 0),
            "xGChain":   float(p.get("xGChain", 0) or 0),
            "xGBuildup": float(p.get("xGBuildup", 0) or 0),
            "Sh":        float(p.get("shots", 0) or 0),
            "KP":        float(p.get("key_passes", 0) or 0),
            "season":    season_label,
        })
    return pd.DataFrame(rows)


def scrape_understat_season(season_year: int, season_label: str) -> pd.DataFrame:
    cache_key = f"understat_{season_label.replace('-', '')}"
    path = _cache_path(cache_key)

    if _is_fresh(path):
        print(f"  [cache] {cache_key}")
        return pd.read_csv(path)

    print(f"  [fetch] Understat {season_label}")
    try:
        df = asyncio.run(_fetch_understat_season(season_year, season_label))
        df.to_csv(path, index=False)
        print(f"    → {len(df)} players")
        return df
    except Exception as e:
        print(f"  [warn] Understat failed {season_label}: {e}")
        return pd.DataFrame()


def run_understat_scrapers() -> dict:
    """
    DEPRECATED — replaced by run_fbref_scrapers() in Phase 1.
    Returns empty dict. app.py compatibility shim — will be removed in Phase 2
    when merger.py is rewritten to consume FBref data directly.
    """
    print(
        "[warn] run_understat_scrapers() is deprecated — "
        "FBref scraper now provides all stats. "
        "This stub exists for app.py backward compatibility."
    )
    return {}


# ── API-Football ──────────────────────────────────────────────────────────────

def _get_epl_team_ids(season_year: int, headers: dict) -> list:
    """Fetch EPL team IDs for a given season (1 API call)."""
    time.sleep(API_FOOTBALL_RATE_S)
    try:
        resp = requests.get(
            f"{API_FOOTBALL_BASE}/teams",
            headers=headers,
            params={"league": API_FOOTBALL_LEAGUE, "season": season_year},
            timeout=30,
        )
        if resp.status_code != 200:
            return []
        return [item["team"]["id"] for item in resp.json().get("response", [])]
    except Exception as e:
        print(f"  [warn] Could not fetch team IDs: {e}")
        return []


def _extract_player_row(item: dict, season_label: str) -> dict | None:
    p     = item.get("player", {})
    stats = (item.get("statistics") or [{}])[0]

    games    = stats.get("games", {})
    goals    = stats.get("goals", {})
    shots    = stats.get("shots", {})
    passes   = stats.get("passes", {})
    tackles  = stats.get("tackles", {})
    duels    = stats.get("duels", {})
    dribbles = stats.get("dribbles", {})
    fouls    = stats.get("fouls", {})

    raw_cmp = passes.get("accuracy")
    if isinstance(raw_cmp, str):
        raw_cmp = float(raw_cmp.replace("%", "")) if raw_cmp else None
    elif raw_cmp is not None:
        raw_cmp = float(raw_cmp)

    name = p.get("name", "")
    if not name:
        return None

    return {
        "Player":      name,
        "Squad":       stats.get("team", {}).get("name", ""),
        "Pos":         _map_api_football_pos(games.get("position", "")),
        "Saves":         goals.get("saves") or 0,
        "GoalsConceded": goals.get("conceded") or 0,
        "SoT":         shots.get("on") or 0,
        "Cmp%":        raw_cmp,
        "Tkl":         tackles.get("total") or 0,
        "Blocks":      tackles.get("blocks") or 0,
        "Int":         tackles.get("interceptions") or 0,
        "DuelsTotal":  duels.get("total") or 0,
        "DuelsWon":    duels.get("won") or 0,
        "DrbAttempts": dribbles.get("attempts") or 0,
        "DrbSucc":     dribbles.get("success") or 0,
        "Fld":         fouls.get("drawn") or 0,
        "season":      season_label,
    }


def scrape_api_football_season(season_year: int, season_label: str) -> pd.DataFrame:
    cache_key = f"apifootball_{season_label.replace('-', '')}"
    path = _cache_path(cache_key)

    if _is_fresh(path):
        print(f"  [cache] {cache_key}")
        return pd.read_csv(path)

    key = os.environ.get("API_FOOTBALL_KEY", "")
    if not key:
        print("  [warn] API_FOOTBALL_KEY not set — skipping API-Football")
        return pd.DataFrame()

    print(f"  [fetch] API-Football {season_label} (team-by-team)")
    headers = {"x-apisports-key": key}

    team_ids = _get_epl_team_ids(season_year, headers)
    if not team_ids:
        print("  [warn] No EPL team IDs returned")
        return pd.DataFrame()
    print(f"    {len(team_ids)} EPL teams found")

    seen_players: set = set()
    all_rows = []

    for team_id in team_ids:
        page = 1
        while True:
            time.sleep(API_FOOTBALL_RATE_S)
            try:
                resp = requests.get(
                    f"{API_FOOTBALL_BASE}/players",
                    headers=headers,
                    params={
                        "league": API_FOOTBALL_LEAGUE,
                        "season": season_year,
                        "team":   team_id,
                        "page":   page,
                    },
                    timeout=30,
                )
            except Exception as e:
                print(f"  [warn] team {team_id} p{page}: {e}")
                break

            if resp.status_code != 200:
                break

            data    = resp.json()
            results = data.get("response", [])
            if not results:
                break

            for item in results:
                row = _extract_player_row(item, season_label)
                if row and row["Player"] not in seen_players:
                    seen_players.add(row["Player"])
                    all_rows.append(row)

            paging = data.get("paging", {})
            if page >= paging.get("total", 1):
                break
            page += 1

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df.to_csv(path, index=False)
        print(f"    → {len(df)} unique players")
    return df


def run_api_football_scrapers() -> dict:
    """
    DEPRECATED — replaced by run_fbref_scrapers() in Phase 1.
    Returns empty dict. app.py compatibility shim — will be removed in Phase 2
    when merger.py is rewritten to consume FBref data directly.
    """
    print(
        "[warn] run_api_football_scrapers() is deprecated — "
        "FBref scraper now provides all stats. "
        "This stub exists for app.py backward compatibility."
    )
    return {}


# ── Transfermarkt via curl_cffi — club squad pages ────────────────────────────
# Scrapes each EPL club's kader (squad) page instead of the league ranking,
# giving full coverage of all registered players (~500/season) not just top-100.

TM_EPL_CLUBS_URL = "https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1"


def _parse_tm_value(raw: str) -> float:
    if not raw or raw in ("-", ""):
        return float("nan")
    raw = raw.replace("€", "").replace(",", ".").strip()
    if "m" in raw:
        try:
            return float(re.sub(r"[^\d.]", "", raw.split("m")[0])) * 1_000_000
        except ValueError:
            return float("nan")
    if "Th." in raw or "k" in raw.lower():
        try:
            return float(re.sub(r"[^\d.]", "", raw)) * 1_000
        except ValueError:
            return float("nan")
    try:
        return float(raw)
    except ValueError:
        return float("nan")


def _get_tm_club_list(season_year: int, session) -> list:
    """Scrape EPL clubs page → [{slug, id, name}]. One request."""
    url = f"{TM_EPL_CLUBS_URL}/saison_id/{season_year}"
    time.sleep(TM_RATE_LIMIT_S)
    try:
        resp = session.get(url, impersonate=IMPERSONATE, headers=TM_HEADERS, timeout=30)
        if resp.status_code != 200:
            print(f"  [warn] TM clubs page HTTP {resp.status_code}")
            return []
    except Exception as e:
        print(f"  [warn] TM clubs page failed: {e}")
        return []

    soup  = BeautifulSoup(resp.text, "lxml")
    clubs = []
    seen_ids: set = set()

    for a in soup.select("table.items td.hauptlink a[href*='/verein/']"):
        href = a.get("href", "")
        parts = href.split("/verein/")
        if len(parts) != 2:
            continue
        club_id   = parts[1].split("/")[0]
        club_slug = href.lstrip("/").split("/")[0]
        club_name = a.get_text(strip=True)
        if club_id and club_id not in seen_ids:
            seen_ids.add(club_id)
            clubs.append({"slug": club_slug, "id": club_id, "name": club_name})

    return clubs


def _scrape_tm_squad(club: dict, season_year: int, season_label: str, session) -> list:
    """Scrape one club's kader page → list of player dicts."""
    url = (f"https://www.transfermarkt.com/{club['slug']}"
           f"/kader/verein/{club['id']}/saison_id/{season_year}/plus/1")
    time.sleep(TM_RATE_LIMIT_S)
    try:
        resp = session.get(url, impersonate=IMPERSONATE, headers=TM_HEADERS, timeout=30)
        if resp.status_code != 200:
            return []
    except Exception as e:
        print(f"  [warn] Squad page {club['name']}: {e}")
        return []

    soup  = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", {"class": "items"})
    if not table:
        return []

    rows   = table.find_all("tr", {"class": ["odd", "even"]})
    result = []
    for row in rows:
        # Player name — first hauptlink anchor with non-digit text
        player_name = None
        for tag in row.find_all("td", {"class": "hauptlink"}):
            a = tag.find("a")
            if a:
                text = a.get_text(strip=True)
                if text and not text.isdigit():
                    player_name = text
                    break
        if not player_name:
            continue

        # Market value — last cell
        cells  = row.find_all("td")
        mv_raw = cells[-1].get_text(strip=True) if cells else ""

        result.append({
            "player_name_tm":  player_name,
            "club_tm":         club["name"],
            "market_value_raw": mv_raw,
            "season":          season_label,
        })
    return result


def scrape_tm_season(season_year: int, season_label: str) -> pd.DataFrame:
    cache_key = f"tm_values_{season_label.replace('-', '')}"
    path = _cache_path(cache_key)

    if _is_fresh(path):
        print(f"  [cache] {cache_key}")
        return pd.read_csv(path)

    print(f"  [fetch] Transfermarkt {season_label} (club squad pages)")
    session = cf_requests.Session()
    time.sleep(TM_RATE_LIMIT_S)  # warm-up pause before first request

    clubs = _get_tm_club_list(season_year, session)
    if not clubs:
        print("  [warn] No EPL clubs found — cannot scrape TM")
        return pd.DataFrame()
    print(f"    {len(clubs)} EPL clubs found")

    all_rows: list  = []
    seen_names: set = set()

    for club in clubs:
        rows = _scrape_tm_squad(club, season_year, season_label, session)
        new = 0
        for row in rows:
            if row["player_name_tm"] not in seen_names:
                seen_names.add(row["player_name_tm"])
                all_rows.append(row)
                new += 1
        print(f"    {club['name']}: {new} players")

    df = pd.DataFrame(all_rows)
    if df.empty:
        print(f"  [warn] No TM data for {season_label}")
        return df

    df["market_value_eur"] = df["market_value_raw"].apply(_parse_tm_value)
    df.drop(columns=["market_value_raw"], inplace=True)
    df.to_csv(path, index=False)
    print(f"  → {len(df)} total players saved")
    return df


def run_tm_scrapers() -> pd.DataFrame:
    frames = []
    for season_label, season_year in SEASONS.items():
        df = scrape_tm_season(season_year, season_label)
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True).sort_values("season")
    latest = (
        combined.dropna(subset=["market_value_eur"])
        .groupby("player_name_tm", as_index=False)
        .last()
    )
    return latest[["player_name_tm", "club_tm", "market_value_eur"]]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== FBref Scraper — Phase 1 (EPL) ===")
    results = run_fbref_scrapers()

    total_tables = 0
    total_rows   = 0
    for league, seasons_data in results.items():
        for season, tables_data in seasons_data.items():
            for table_type, df in tables_data.items():
                total_tables += 1
                total_rows   += len(df)

    print(f"\nDone. {total_tables} tables scraped, {total_rows} total player-rows.")

    print("\n=== Transfermarkt ===")
    tm_data = run_tm_scrapers()
    print(f"Transfermarkt players: {len(tm_data)}")
