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
try:
    import nodriver as uc
    _NODRIVER_AVAILABLE = True
except Exception:
    uc = None
    _NODRIVER_AVAILABLE = False
import pandas as pd
from curl_cffi import requests as cf_requests
from bs4 import BeautifulSoup, Comment
from dotenv import load_dotenv

load_dotenv()

from config import (
    SEASONS, API_FOOTBALL_BASE, API_FOOTBALL_LEAGUE, API_FOOTBALL_RATE_S,
    TM_BASE, TM_HEADERS, TM_RATE_LIMIT_S, TM_LEAGUE_URLS,
    FBREF_LEAGUES, FBREF_TABLES, FBREF_SEASONS, FBREF_RATE_MIN, FBREF_RATE_MAX,
    FBREF_BACKOFF_SEQUENCE, FBREF_TABLE_URL_SEGMENTS, FBREF_MIN_MINUTES,
    build_fbref_url,
    UNDERSTAT_LEAGUE_NAMES,
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


def _do_playwright_get(url: str) -> str:
    """
    Navigate the persistent nodriver Chrome session to url, return page HTML.

    nodriver uses the real Chrome binary without setting navigator.webdriver or any
    automation markers, making it undetectable to Cloudflare Bot Management.
    A single browser instance is reused across all requests to avoid hitting the
    macOS open-file-descriptor limit when scraping 90+ pages.

    This is the thin inner wrapper called by _playwright_fetch. Isolated here so tests can
    monkeypatch it without launching a real browser.
    """
    global _uc_browser

    if not _NODRIVER_AVAILABLE:
        raise RuntimeError("nodriver is not available in this environment; run scraper.py locally to pre-populate the cache.")

    async def _fetch() -> str:
        browser = await uc.start(headless=False)
        try:
            page = await asyncio.wait_for(browser.get(url), timeout=60)
            await asyncio.sleep(12)  # allow Cloudflare challenge + full page to load
            return await page.get_content()
        finally:
            try:
                browser.stop()
            except Exception:
                pass
            await asyncio.sleep(2)  # let OS release file descriptors before next launch

    return uc.loop().run_until_complete(_fetch())


def _playwright_fetch(url: str) -> str:
    """
    Fetch a URL using Playwright headless Chromium, bypassing Cloudflare JS challenge.

    Replaces _fetch_with_backoff. Returns full page HTML as string.
    Preserves backoff semantics: retries up to len(FBREF_BACKOFF_SEQUENCE) times when a
    Cloudflare challenge page is detected in the returned HTML.

    Args:
        url: Full URL to fetch.

    Returns:
        Full page HTML string after JS execution.

    Raises:
        RuntimeError: If Cloudflare challenge persists after all retries.
    """
    from config import FBREF_BACKOFF_SEQUENCE
    delays = FBREF_BACKOFF_SEQUENCE  # [30, 60, 120]

    for attempt, delay in enumerate(delays + [None]):
        html = _do_playwright_get(url)

        if "Just a moment" not in html and "cf-browser-verification" not in html:
            return html

        if delay is None:
            raise RuntimeError(
                f"Cloudflare challenge not resolved after {len(delays)} retries — "
                f"aborting fetch of: {url}"
            )
        print(
            f"  [warn] Cloudflare challenge — backing off {delay}s "
            f"(attempt {attempt + 1}/{len(delays)}): {url}"
        )
        time.sleep(delay)

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

    def _flatten_multiindex(raw_df: pd.DataFrame) -> pd.DataFrame:
        """Flatten MultiIndex columns produced by pd.read_html(header=[0,1])."""
        raw_df.columns = [
            col[1] if (isinstance(col, tuple) and col[1]
                       and not str(col[1]).startswith("Unnamed")) else (
                col[0] if isinstance(col, tuple) else col
            )
            for col in raw_df.columns
        ]
        if "Rk" in raw_df.columns:
            raw_df = raw_df[raw_df["Rk"] != "Rk"].reset_index(drop=True)
        return raw_df

    table_html = str(table)

    # Strategy: try header=[0,1] first (multi-level — captures Expected/Progression sections).
    # Fall back to header=1 (single-level) if multi-level parse fails or gives fewer cols.
    df = None
    try:
        from io import StringIO as _SIO
        raw = pd.read_html(_SIO(table_html), header=[0, 1])[0]
        df = _flatten_multiindex(raw)
    except Exception:
        pass

    # Try header=1 and keep whichever gives more columns
    try:
        from io import StringIO as _SIO
        raw1 = pd.read_html(_SIO(table_html), header=1)[0]
        if isinstance(raw1.columns[0], tuple):
            raw1 = _flatten_multiindex(raw1)
        if "Rk" in raw1.columns:
            raw1 = raw1[raw1["Rk"] != "Rk"].reset_index(drop=True)
        if df is None or len(raw1.columns) > len(df.columns):
            df = raw1
    except Exception:
        pass

    if df is None:
        raise ValueError(
            f"FBref table '{table_id}' could not be parsed with any header strategy."
        )

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
        each HTTP request. Uses _playwright_fetch for Cloudflare bypass and backoff.

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
        FBREF_RATE_MIN, FBREF_RATE_MAX, build_fbref_url,
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
    table_id = table_type   # FBref no longer appends comp_id suffix (e.g. "stats_standard", not "stats_standard_9")

    print(f"  [fetch] FBref {league} {table_type} {season_label}")
    print(f"    URL: {url}")

    # Polite delay before request (DATA-06)
    delay = random.uniform(FBREF_RATE_MIN, FBREF_RATE_MAX)
    time.sleep(delay)

    try:
        html = _playwright_fetch(url)
    except Exception as e:
        print(f"  [warn] FBref fetch failed for {table_type} {season_label}: {e}")
        return pd.DataFrame()

    try:
        df = _extract_fbref_table(html, table_id)
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


_FDCO_LEAGUE_CODES = {
    "EPL":        "E0",
    "LaLiga":     "SP1",
    "Bundesliga": "D1",
    "SerieA":     "I1",
    "Ligue1":     "F1",
}

# Minor name fixes: football-data.co.uk → FBref squad names
# Only add entries that differ; most names are identical or close enough for fuzzy matching.
_FDCO_TEAM_NAME_MAP = {
    # EPL
    "Man United":      "Manchester Utd",
    "Man City":        "Manchester City",
    "Leeds":           "Leeds United",
    "Leicester":       "Leicester City",
    "Wolves":          "Wolverhampton Wanderers",
    "Newcastle":       "Newcastle Utd",
    "Nottingham Forest": "Nott'ham Forest",
    "West Brom":       "West Brom",
    "Norwich":         "Norwich City",
    "Brentford":       "Brentford",
    # LaLiga (generally fine)
    "Ath Bilbao":      "Athletic Club",
    "Ath Madrid":      "Atlético Madrid",
    "Betis":           "Real Betis",
    "La Coruna":       "Deportivo de La Coruña",
    "Espanol":         "Espanyol",
    "Sociedad":        "Real Sociedad",
    "Vallecano":       "Rayo Vallecano",
    # Bundesliga
    "Greuther Furth":  "Greuther Fürth",
    "Leverkusen":      "Bayer Leverkusen",
    "Ein Frankfurt":   "Eintracht Frankfurt",
    "Hertha":          "Hertha BSC",
    "Koln":            "Köln",
    "Fortuna Dusseldorf": "Fortuna Düsseldorf",
    "Nurnberg":        "Nürnberg",
    "Schalke 04":      "Schalke 04",
    "Paderborn":       "Paderborn 07",
    "Dusseldorf":      "Fortuna Düsseldorf",
    # SerieA
    "Hellas Verona":   "Hellas Verona",
    "Inter":           "Internazionale",
    "Verona":          "Hellas Verona",
    # Ligue1
    "Paris SG":        "Paris S-G",
    "St Etienne":      "Saint-Étienne",
    "Marseille":       "Marseille",
}


def _standings_from_football_data(league: str, season: str) -> pd.DataFrame:
    """
    Compute league standings from football-data.co.uk match results CSV.

    No Cloudflare — plain CSV download via requests. Used as fallback when
    FBref standings scraping fails (Lit migration / bot protection).

    Args:
        league: League key, e.g. "EPL"
        season: Short season label, e.g. "2024-25"

    Returns:
        DataFrame with columns ['Squad', 'Rk'] (Rk 1 = top of table).

    Raises:
        RuntimeError: If download fails or league/season not supported.
    """
    league_code = _FDCO_LEAGUE_CODES.get(league)
    if not league_code:
        raise RuntimeError(f"No football-data.co.uk code for league: {league}")

    # Convert "2024-25" → "2425"
    parts = season.split("-")
    if len(parts) != 2:
        raise RuntimeError(f"Unexpected season format: {season}")
    season_code = parts[0][-2:] + parts[1][-2:]  # "2024-25" → "2425"

    url = f"https://www.football-data.co.uk/mmz4281/{season_code}/{league_code}.csv"
    print(f"  [standings-fdco] Downloading {url}")

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"football-data.co.uk download failed for {league} {season}: {e}")

    from io import StringIO
    try:
        df_matches = pd.read_csv(StringIO(resp.text))
    except Exception as e:
        raise RuntimeError(f"Failed to parse football-data.co.uk CSV: {e}")

    required = {"HomeTeam", "AwayTeam", "FTR"}
    if not required.issubset(df_matches.columns):
        raise RuntimeError(
            f"football-data.co.uk CSV missing columns {required - set(df_matches.columns)}"
        )

    # Drop rows without a result (mid-season or postponed)
    df_matches = df_matches.dropna(subset=["FTR", "HomeTeam", "AwayTeam"])
    df_matches = df_matches[df_matches["FTR"].isin(["H", "A", "D"])]

    # Goal columns: FTHG / FTAG (Full Time Home/Away Goals)
    has_goals = "FTHG" in df_matches.columns and "FTAG" in df_matches.columns
    if has_goals:
        df_matches["FTHG"] = pd.to_numeric(df_matches["FTHG"], errors="coerce").fillna(0)
        df_matches["FTAG"] = pd.to_numeric(df_matches["FTAG"], errors="coerce").fillna(0)

    teams: dict = {}

    def _team(name: str) -> dict:
        if name not in teams:
            teams[name] = {"W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0}
        return teams[name]

    for _, row in df_matches.iterrows():
        home = row["HomeTeam"]
        away = row["AwayTeam"]
        result = row["FTR"]
        hg = int(row["FTHG"]) if has_goals else 0
        ag = int(row["FTAG"]) if has_goals else 0

        _team(home)["GF"] += hg
        _team(home)["GA"] += ag
        _team(away)["GF"] += ag
        _team(away)["GA"] += hg

        if result == "H":
            _team(home)["W"] += 1
            _team(away)["L"] += 1
        elif result == "A":
            _team(away)["W"] += 1
            _team(home)["L"] += 1
        else:  # D
            _team(home)["D"] += 1
            _team(away)["D"] += 1

    rows = []
    for team_name, stats in teams.items():
        pts = stats["W"] * 3 + stats["D"]
        gd  = stats["GF"] - stats["GA"]
        mapped = _FDCO_TEAM_NAME_MAP.get(team_name, team_name)
        rows.append({"Squad": mapped, "Pts": pts, "GD": gd, "GF": stats["GF"]})

    standings = (
        pd.DataFrame(rows)
        .sort_values(["Pts", "GD", "GF"], ascending=False)
        .reset_index(drop=True)
    )
    standings["Rk"] = standings.index + 1
    return standings[["Squad", "Rk"]]


def scrape_fbref_standings(league: str = "EPL", season: str = "2024-25") -> pd.DataFrame:
    """
    Get league standings for the given league and season.
    Returns DataFrame with Squad and Rk columns.
    Cached at cache/fbref_{league}_standings_{season}.csv with 7-day TTL.

    Source priority:
    1. football-data.co.uk CSV (instant, no browser, all 5 supported leagues)
    2. FBref (Playwright browser) — fallback for leagues not in _FDCO_LEAGUE_CODES
    """
    cache_path = _fbref_cache_path(league, "standings", season)
    if _is_fresh(cache_path):
        return pd.read_csv(cache_path)

    # Primary: football-data.co.uk — instant plain HTTP, no Cloudflare
    if league in _FDCO_LEAGUE_CODES:
        df = _standings_from_football_data(league, season)
        df.to_csv(cache_path, index=False)
        return df

    # Fallback: FBref via Playwright (only for leagues not on football-data.co.uk)
    league_cfg = FBREF_LEAGUES[league]
    comp_id = league_cfg["comp_id"]
    slug    = league_cfg["slug"]
    parts   = season.split("-")
    start   = int(parts[0])
    season_long = f"{start}-{start + 1}"
    url = f"https://fbref.com/en/comps/{comp_id}/{season_long}/{season_long}-{slug}-Stats"

    html = _playwright_fetch(url)
    df   = None

    # Try known table ID, then comment scan, then direct DOM scan
    table_id = f"results{season_long}{comp_id}1_home"
    try:
        df = _extract_fbref_table(html, table_id)
    except Exception:
        pass

    if df is None or df.empty or "Rk" not in df.columns:
        soup = BeautifulSoup(html, "lxml")
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            if "<table" not in comment:
                continue
            try:
                from io import StringIO as _SIO
                for t in pd.read_html(_SIO(str(comment)), header=0):
                    if "Rk" in t.columns and "Squad" in t.columns:
                        df = t
                        break
            except Exception:
                pass
            if df is not None:
                break

    if df is None or df.empty or "Rk" not in df.columns:
        soup = BeautifulSoup(html, "lxml")
        for table_tag in soup.find_all("table"):
            try:
                from io import StringIO as _SIO
                t = pd.read_html(_SIO(str(table_tag)), header=0)[0]
                if "Rk" in t.columns and "Squad" in t.columns and len(t) >= 10:
                    df = t
                    break
            except Exception:
                pass

    if df is None or df.empty:
        raise RuntimeError(f"Could not find standings table for {league} {season}")

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
    before each HTTP request. Total cold run: 9 tables × 2 seasons × 5 leagues = 90
    requests ≈ 315–540 seconds (5–9 minutes).

    Args:
        leagues: List of league keys to scrape (default: all 5 leagues from FBREF_LEAGUES).
                 Supported: EPL, LaLiga, Bundesliga, SerieA, Ligue1.
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

        # Pre-cache standings so Streamlit never launches a browser during load_data()
        current_season = seasons[-1]
        try:
            scrape_fbref_standings(league, current_season)
            print(f"  [standings] {league} {current_season} cached")
        except Exception as e:
            print(f"  [standings] {league} {current_season} failed (league_position will be NaN): {e}")

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


async def _fetch_understat_league(league: str, season_year: int, season_label: str) -> pd.DataFrame:
    """
    Fetch Understat player data for one league+season.
    Generalized from _fetch_understat_season (EPL-only) to support all 5 leagues.

    Args:
        league:       Project league key, e.g. "EPL", "LaLiga"
        season_year:  Understat start year, e.g. 2024 (= 2024-25 season)
        season_label: Short label, e.g. "2024-25"

    Returns:
        DataFrame with columns: Player, Squad, Pos, Min, xG, xA, season
    """
    import aiohttp
    from understat import Understat

    understat_slug = UNDERSTAT_LEAGUE_NAMES[league]

    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        players = await understat.get_league_players(understat_slug, season_year)

    rows = []
    for p in players:
        rows.append({
            "Player":  p.get("player_name", ""),
            "Squad":   p.get("team_title", ""),
            "Pos":     _map_understat_pos(p.get("position", "")),
            "Min":     float(p.get("time",  0) or 0),
            "xG":      float(p.get("xG",    0) or 0),
            "xA":      float(p.get("xA",    0) or 0),
            "season":  season_label,
        })
    return pd.DataFrame(rows)


def scrape_understat_league(league: str, season_year: int, season_label: str) -> pd.DataFrame:
    """
    Scrape Understat xG/xA for one league+season with 7-day cache.

    Cache naming convention (DATA-05):
        cache/understat_{league}_{season_label}.csv
        e.g. cache/understat_EPL_2024-25.csv
             cache/understat_LaLiga_2023-24.csv

    Rate limiting: no explicit delay needed — Understat is a single JSON endpoint
    with no known bot protection. Polite usage already covered by aiohttp session.

    Args:
        league:       Project league key, e.g. "EPL", "LaLiga"
        season_year:  Understat start year integer, e.g. 2024
        season_label: Short season label, e.g. "2024-25"

    Returns:
        DataFrame with Player, Squad, Pos, Min, xG, xA, season columns.
        Returns empty DataFrame on failure (logs warning).
    """
    cache_key = f"understat_{league}_{season_label}"
    path = _cache_path(cache_key)

    if _is_fresh(path):
        print(f"  [cache] {cache_key}")
        return pd.read_csv(path)

    print(f"  [fetch] Understat {league} {season_label}")
    try:
        df = asyncio.run(_fetch_understat_league(league, season_year, season_label))
        if not df.empty:
            df.to_csv(path, index=False)
            print(f"    -> {len(df)} players cached to {path}")
        return df
    except Exception as e:
        print(f"  [warn] Understat {league} {season_label} failed: {e}")
        return pd.DataFrame()


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


def run_understat_scrapers(leagues=None, seasons=None) -> dict:
    """
    Scrape Understat xG/xA for all leagues x seasons.

    Args:
        leagues: List of league keys (default: all 5 from FBREF_LEAGUES)
        seasons: List of season labels (default: FBREF_SEASONS = ["2023-24", "2024-25"])

    Returns:
        Nested dict: {league: {season_label: DataFrame}}
        Each DataFrame has Player, Squad, Pos, Min, xG, xA, season columns.
    """
    from config import FBREF_LEAGUES, FBREF_SEASONS, SEASONS as SEASON_YEARS

    if leagues is None:
        leagues = list(FBREF_LEAGUES.keys())
    if seasons is None:
        seasons = FBREF_SEASONS

    results = {}
    for league in leagues:
        print(f"\n[Understat] League: {league}")
        results[league] = {}
        for season_label in seasons:
            season_year = SEASON_YEARS[season_label]
            df = scrape_understat_league(league, season_year, season_label)
            results[league][season_label] = df
            status = f"{len(df)} players" if not df.empty else "EMPTY"
            print(f"  {season_label}: {status}")

    return results


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
# Scrapes each club's kader (squad) page instead of the league ranking,
# giving full coverage of all registered players (~500/season) not just top-100.


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


def _get_tm_club_list(league: str, season_year: int, session) -> list:
    """Scrape league clubs page → [{slug, id, name}]. One request."""
    url = f"{TM_LEAGUE_URLS[league]}/saison_id/{season_year}"
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


def scrape_tm_season(season_year: int, season_label: str, league: str = "EPL") -> pd.DataFrame:
    cache_key = f"tm_values_{league}_{season_label}"
    path = _cache_path(cache_key)

    if _is_fresh(path):
        print(f"  [cache] {cache_key}")
        return pd.read_csv(path)

    print(f"  [fetch] Transfermarkt {season_label} (club squad pages)")
    session = cf_requests.Session()
    time.sleep(TM_RATE_LIMIT_S)  # warm-up pause before first request

    clubs = _get_tm_club_list(league, season_year, session)
    if not clubs:
        print(f"  [warn] No {league} clubs found — cannot scrape TM")
        return pd.DataFrame()
    print(f"    {len(clubs)} {league} clubs found")

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


def run_tm_scrapers(leagues: list | None = None) -> pd.DataFrame:
    """
    Scrape Transfermarkt market values for all given leagues and seasons.

    Args:
        leagues: List of league keys to scrape (default: all 5 from TM_LEAGUE_URLS).
                 None = all 5 leagues.

    Returns:
        Combined DataFrame across all leagues with columns:
        player_name_tm, club_tm, market_value_eur, season, league_tm
    """
    if leagues is None:
        leagues = list(TM_LEAGUE_URLS.keys())

    frames = []
    for league in leagues:
        print(f"\n[TM] League: {league}")
        for season_label, season_year in SEASONS.items():
            if season_label not in FBREF_SEASONS:
                continue  # only scrape seasons we have FBref data for
            df = scrape_tm_season(season_year, season_label, league=league)
            if not df.empty:
                df = df.copy()
                df["league_tm"] = league
                frames.append(df)

    if not frames:
        return pd.DataFrame()

    # Concatenate all leagues; do NOT deduplicate across leagues — same player name
    # can appear in multiple leagues (e.g. a player who transferred leagues between seasons).
    # match_market_values uses club cross-check (Pass 3) to disambiguate.
    combined = pd.concat(frames, ignore_index=True)
    # Keep only rows with valid market values; drop duplicates within same player+league
    combined = combined.dropna(subset=["market_value_eur"])
    return combined[["player_name_tm", "club_tm", "market_value_eur", "season", "league_tm"]]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== FBref Scraper — Phase 3 (All 5 Leagues) ===")
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
