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


# ── FBref stubs (implemented in Plan 01-02) ───────────────────────────────────

def scrape_fbref_stat(table_type: str, season_label: str, league: str = "EPL") -> "pd.DataFrame":
    """Stub — full implementation in Plan 01-02."""
    return pd.DataFrame()


def run_fbref_scrapers(league: str = "EPL") -> dict:
    """Stub — full implementation in Plan 01-02."""
    return {}


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
    """Returns {season_label: DataFrame} for all seasons."""
    data = {}
    for season_label, season_year in SEASONS.items():
        print(f"\n[Understat] Season: {season_label}")
        data[season_label] = scrape_understat_season(season_year, season_label)
    return data


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
    """Returns {season_label: DataFrame} for all seasons."""
    data = {}
    for season_label, season_year in SEASONS.items():
        print(f"\n[API-Football] Season: {season_label}")
        data[season_label] = scrape_api_football_season(season_year, season_label)
    return data


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
    print("=== Scraping Understat ===")
    us_data = run_understat_scrapers()
    ok = sum(1 for df in us_data.values() if not df.empty)
    print(f"\nUnderstat seasons fetched: {ok}/3")

    print("\n=== Scraping API-Football ===")
    af_data = run_api_football_scrapers()
    ok = sum(1 for df in af_data.values() if not df.empty)
    print(f"\nAPI-Football seasons fetched: {ok}/3")

    print("\n=== Scraping Transfermarkt ===")
    tm_data = run_tm_scrapers()
    print(f"Transfermarkt players: {len(tm_data)}")
    print("\nDone.")
