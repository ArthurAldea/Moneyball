"""
test_scraper.py — Phase 1 FBref Scraper test suite.

All tests run without network access. Tests use monkeypatching, mock fixtures,
and file-system checks where network is not required.

Run with:
    cd /Users/ArthurAldea/ClaudeProjects/Moneyball
    python -m pytest test_scraper.py -x -q
"""

import os
import time
import tempfile

import pandas as pd
import pytest

from scraper import (
    scrape_tm_season,
    scrape_fbref_stat,
    run_fbref_scrapers,
    _fbref_cache_path,
    _is_fresh,
    _playwright_fetch,
    _do_playwright_get,
    _extract_fbref_table,
)
from config import (
    FBREF_BACKOFF_SEQUENCE,
    FBREF_RATE_MIN,
    FBREF_RATE_MAX,
    FBREF_TABLES,
    FBREF_SEASONS,
    FBREF_MIN_MINUTES,
    build_fbref_url,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

MINIMAL_FBREF_TABLE_HTML = """
<html><body>
<!-- stats_standard_9 table wrapped in a comment -->
<!--
<table id="stats_standard_9">
  <thead>
    <tr>
      <th>Unnamed: 0_level_0</th>
      <th>Unnamed: 1_level_0</th>
      <th colspan="2">Performance</th>
    </tr>
    <tr>
      <th>Rk</th>
      <th>Player</th>
      <th>Min</th>
      <th>Gls</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>1</td><td>Erling Haaland</td><td>2800</td><td>22</td></tr>
    <tr><td>Rk</td><td>Player</td><td>Min</td><td>Gls</td></tr>
    <tr><td>2</td><td>Low Minutes Player</td><td>200</td><td>1</td></tr>
    <tr><td>3</td><td>Qualifying Player</td><td>1500</td><td>8</td></tr>
  </tbody>
</table>
-->
</body></html>
"""


# ── test_cache_fresh (DATA-05) ─────────────────────────────────────────────────

def test_cache_fresh(tmp_path):
    """_is_fresh returns True for a file modified within 7 days, False otherwise."""
    fresh_file = tmp_path / "fresh.csv"
    fresh_file.write_text("player,goals\nHaaland,22\n")

    # Just-created file should be fresh
    assert _is_fresh(str(fresh_file)) is True

    # Non-existent file should not be fresh
    assert _is_fresh(str(tmp_path / "nonexistent.csv")) is False

    # File modified 8 days ago should not be fresh
    stale_file = tmp_path / "stale.csv"
    stale_file.write_text("data")
    eight_days_ago = time.time() - (8 * 86400)
    os.utime(str(stale_file), (eight_days_ago, eight_days_ago))
    assert _is_fresh(str(stale_file)) is False


# ── test_rate_limit_delay (DATA-06) ───────────────────────────────────────────

def test_rate_limit_delay():
    """FBREF_RATE_MIN and FBREF_RATE_MAX are within the required 3.5–6.0s range."""
    assert FBREF_RATE_MIN >= 3.5, f"FBREF_RATE_MIN={FBREF_RATE_MIN} must be >= 3.5"
    assert FBREF_RATE_MAX <= 6.0, f"FBREF_RATE_MAX={FBREF_RATE_MAX} must be <= 6.0"
    assert FBREF_RATE_MIN < FBREF_RATE_MAX, "FBREF_RATE_MIN must be < FBREF_RATE_MAX"


# ── test_backoff_on_429 (DATA-06) ─────────────────────────────────────────────

def test_backoff_on_429(monkeypatch):
    """
    _playwright_fetch raises RuntimeError after FBREF_BACKOFF_SEQUENCE exhausted.
    Verifies: Cloudflare challenge HTML triggers backoff; 4th consecutive challenge raises RuntimeError.
    Monkeypatches _do_playwright_get (the inner browser call) to return challenge HTML every time.
    """
    import scraper as scraper_module

    call_count = {"n": 0}
    sleep_calls = []

    def fake_do_playwright_get(url):
        call_count["n"] += 1
        return "Just a moment..."  # simulate Cloudflare challenge page

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(scraper_module, "_do_playwright_get", fake_do_playwright_get)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="Cloudflare challenge not resolved"):
        _playwright_fetch("https://fbref.com/test")

    # Should have attempted len(FBREF_BACKOFF_SEQUENCE) + 1 times (3 retries + final attempt)
    assert call_count["n"] == len(FBREF_BACKOFF_SEQUENCE) + 1, (
        f"Expected {len(FBREF_BACKOFF_SEQUENCE) + 1} attempts, got {call_count['n']}"
    )
    # Should have slept for each backoff delay in sequence (not the final None)
    assert sleep_calls == FBREF_BACKOFF_SEQUENCE, (
        f"Expected sleep calls {FBREF_BACKOFF_SEQUENCE}, got {sleep_calls}"
    )


# ── test_url_construction (DATA-01) ───────────────────────────────────────────

def test_url_construction():
    """build_fbref_url generates correct URLs for EPL comp_id=9."""
    url = build_fbref_url("EPL", "stats_standard", "2024-25")
    assert url == (
        "https://fbref.com/en/comps/9/2024-2025/stats/2024-2025-Premier-League-Stats"
    ), f"Unexpected URL: {url}"

    url2 = build_fbref_url("EPL", "stats_keeper_adv", "2023-24")
    assert url2 == (
        "https://fbref.com/en/comps/9/2023-2024/keepersadv/2023-2024-Premier-League-Stats"
    ), f"Unexpected URL: {url2}"

    url3 = build_fbref_url("EPL", "stats_defense", "2023-24")
    assert "defense" in url3
    assert "2023-2024" in url3


# ── test_table_extraction (DATA-01) ───────────────────────────────────────────

def test_table_extraction():
    """
    _extract_fbref_table finds a table inside an HTML comment block,
    flattens multi-level headers, and removes repeat Rk header rows.
    """
    df = _extract_fbref_table(MINIMAL_FBREF_TABLE_HTML, "stats_standard_9")

    assert isinstance(df, pd.DataFrame), "Should return a DataFrame"
    assert len(df) > 0, "DataFrame should have rows"

    # Repeat header row (Rk == "Rk") should have been removed
    if "Rk" in df.columns:
        assert not (df["Rk"] == "Rk").any(), "Repeat header rows must be removed"

    # Player column must be present with actual player names
    assert "Player" in df.columns, "Player column must be present"

    # Raises ValueError when table_id is not found
    with pytest.raises(ValueError, match="not found"):
        _extract_fbref_table(MINIMAL_FBREF_TABLE_HTML, "stats_nonexistent_9")


# ── test_column_presence (DATA-02) ────────────────────────────────────────────

def test_column_presence(monkeypatch, tmp_path):
    """
    scrape_fbref_stat returns a DataFrame containing at least Player, Min columns
    when given mock HTML via _playwright_fetch returning the minimal FBref table fixture.
    """
    import scraper as scraper_module

    # Point CACHE_DIR to tmp_path to avoid polluting real cache
    monkeypatch.setattr(scraper_module, "CACHE_DIR", str(tmp_path))

    # Monkeypatch _playwright_fetch (not requests.get) — returns HTML string directly
    monkeypatch.setattr(scraper_module, "_playwright_fetch",
                        lambda url: MINIMAL_FBREF_TABLE_HTML)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    df = scrape_fbref_stat("stats_standard", "2024-25", league="EPL")

    assert isinstance(df, pd.DataFrame)
    assert "Player" in df.columns, f"Player column missing. Columns: {df.columns.tolist()}"
    assert "Min" in df.columns, f"Min column missing. Columns: {df.columns.tolist()}"


# ── test_cache_naming (DATA-05) ───────────────────────────────────────────────

def test_cache_naming():
    """
    _fbref_cache_path returns paths matching the required naming convention:
        cache/fbref_{league}_{table}_{season}.csv
    """
    path = _fbref_cache_path("EPL", "stats_standard", "2024-25")
    assert path.endswith("fbref_EPL_stats_standard_2024-25.csv"), (
        f"Cache path does not match convention: {path}"
    )

    path2 = _fbref_cache_path("EPL", "stats_keeper_adv", "2023-24")
    assert path2.endswith("fbref_EPL_stats_keeper_adv_2023-24.csv"), (
        f"Cache path does not match convention: {path2}"
    )

    # All 9 required tables must produce unique cache paths
    paths = [
        _fbref_cache_path("EPL", table, "2024-25")
        for table in FBREF_TABLES
    ]
    assert len(paths) == len(set(paths)), "Cache paths must be unique per table"


# ── test_run_scrapers_epl (DATA-01, DATA-02) ──────────────────────────────────

def test_run_scrapers_epl(monkeypatch, tmp_path):
    """
    run_fbref_scrapers returns a nested dict with all 9 tables for each season,
    calling scrape_fbref_stat for every league/season/table combination.
    """
    import scraper as scraper_module

    call_log = []

    def fake_scrape(table_type, season_label, league="EPL"):
        call_log.append((league, season_label, table_type))
        return pd.DataFrame({"Player": ["Test Player"], "Min": [1000]})

    monkeypatch.setattr(scraper_module, "scrape_fbref_stat", fake_scrape)

    results = run_fbref_scrapers(leagues=["EPL"], seasons=["2024-25"])

    assert "EPL" in results
    assert "2024-25" in results["EPL"]

    for table_type in FBREF_TABLES:
        assert table_type in results["EPL"]["2024-25"], (
            f"Table {table_type} missing from results"
        )

    # Should have been called once per table (9 tables × 1 season = 9 calls)
    assert len(call_log) == len(FBREF_TABLES), (
        f"Expected {len(FBREF_TABLES)} calls, got {len(call_log)}"
    )


# ── test_cache_hit_is_fast (SC4) ───────────────────────────────────────────────

def test_cache_hit_is_fast(tmp_path, monkeypatch):
    """
    run_fbref_scrapers returns in < 2.0 seconds when all 9 tables × 2 seasons
    already have fresh CSV files in the cache directory (warm cache path).

    This validates SC4: cold run is ~80s; warm run must be sub-2-second.
    """
    import scraper as scraper_module

    # Pre-populate fake CSV files for all 9 tables × 2 seasons
    for table in FBREF_TABLES:
        for season in FBREF_SEASONS:
            cache_file = tmp_path / f"fbref_EPL_{table}_{season}.csv"
            cache_file.write_text("Player,Min\nTest Player,1000\n")

    # Redirect CACHE_DIR so _fbref_cache_path points to tmp_path
    monkeypatch.setattr(scraper_module, "CACHE_DIR", str(tmp_path))

    start = time.perf_counter()
    results = run_fbref_scrapers(leagues=["EPL"], seasons=list(FBREF_SEASONS))
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, (
        f"Warm cache run took {elapsed:.2f}s — must be < 2.0s (SC4). "
        f"Check that _is_fresh() short-circuits before any sleep() calls."
    )
    # Verify all tables returned DataFrames (even if minimal)
    for season in FBREF_SEASONS:
        for table in FBREF_TABLES:
            assert table in results["EPL"][season], f"Missing {table} for {season}"


# ── Phase 3: Multi-league scraper tests ──────────────────────────────────────

def test_url_construction_new_leagues():
    """build_fbref_url generates correct URLs for all 4 new leagues (comp IDs and slugs)."""
    # LaLiga: comp_id=12, slug=La-Liga
    url = build_fbref_url("LaLiga", "stats_standard", "2024-25")
    assert url == "https://fbref.com/en/comps/12/2024-2025/stats/2024-2025-La-Liga-Stats", (
        f"LaLiga URL wrong: {url}"
    )

    # Bundesliga: comp_id=20, slug=Bundesliga
    url2 = build_fbref_url("Bundesliga", "stats_standard", "2024-25")
    assert url2 == "https://fbref.com/en/comps/20/2024-2025/stats/2024-2025-Bundesliga-Stats", (
        f"Bundesliga URL wrong: {url2}"
    )

    # SerieA: comp_id=11, slug=Serie-A
    url3 = build_fbref_url("SerieA", "stats_standard", "2024-25")
    assert url3 == "https://fbref.com/en/comps/11/2024-2025/stats/2024-2025-Serie-A-Stats", (
        f"SerieA URL wrong: {url3}"
    )

    # Ligue1: comp_id=13, slug=Ligue-1
    url4 = build_fbref_url("Ligue1", "stats_standard", "2024-25")
    assert url4 == "https://fbref.com/en/comps/13/2024-2025/stats/2024-2025-Ligue-1-Stats", (
        f"Ligue1 URL wrong: {url4}"
    )

    # keeper_adv URL for LaLiga uses keepersadv segment
    url5 = build_fbref_url("LaLiga", "stats_keeper_adv", "2023-24")
    assert "keepersadv" in url5
    assert "12" in url5
    assert "2023-2024" in url5


def test_cache_naming_new_leagues():
    """_fbref_cache_path for new leagues produces correct convention: fbref_{LEAGUE}_{table}_{season}.csv"""
    path = _fbref_cache_path("LaLiga", "stats_standard", "2024-25")
    assert path.endswith("fbref_LaLiga_stats_standard_2024-25.csv"), (
        f"LaLiga cache path wrong: {path}"
    )

    path2 = _fbref_cache_path("Bundesliga", "stats_gca", "2023-24")
    assert path2.endswith("fbref_Bundesliga_stats_gca_2023-24.csv"), (
        f"Bundesliga cache path wrong: {path2}"
    )

    path3 = _fbref_cache_path("SerieA", "stats_keeper_adv", "2024-25")
    assert path3.endswith("fbref_SerieA_stats_keeper_adv_2024-25.csv"), (
        f"SerieA cache path wrong: {path3}"
    )

    path4 = _fbref_cache_path("Ligue1", "stats_defense", "2023-24")
    assert path4.endswith("fbref_Ligue1_stats_defense_2023-24.csv"), (
        f"Ligue1 cache path wrong: {path4}"
    )

    # All 5 leagues × 9 tables × 2 seasons must produce unique paths
    all_leagues = ["EPL", "LaLiga", "Bundesliga", "SerieA", "Ligue1"]
    paths = [
        _fbref_cache_path(league, table, season)
        for league in all_leagues
        for table in FBREF_TABLES
        for season in FBREF_SEASONS
    ]
    assert len(paths) == len(set(paths)), "Cache paths must be unique per league/table/season combination"


def test_run_fbref_scrapers_all_leagues(monkeypatch):
    """run_fbref_scrapers() with no args returns all 5 league keys; scrape_fbref_stat called 90 times."""
    import scraper as scraper_module
    from config import FBREF_LEAGUES, FBREF_SEASONS, FBREF_TABLES

    call_log = []

    def fake_scrape(table_type, season_label, league="EPL"):
        call_log.append((league, season_label, table_type))
        return pd.DataFrame({"Player": ["Test Player"], "Min": [1000]})

    monkeypatch.setattr(scraper_module, "scrape_fbref_stat", fake_scrape)

    results = run_fbref_scrapers()  # no args — should use all 5 leagues

    # All 5 league keys must be present
    expected_leagues = list(FBREF_LEAGUES.keys())
    assert set(results.keys()) == set(expected_leagues), (
        f"Expected leagues {expected_leagues}, got {list(results.keys())}"
    )

    # Must have been called exactly 5 leagues × 2 seasons × 9 tables = 90 times
    expected_calls = len(FBREF_LEAGUES) * len(FBREF_SEASONS) * len(FBREF_TABLES)
    assert len(call_log) == expected_calls, (
        f"Expected {expected_calls} scrape_fbref_stat calls, got {len(call_log)}"
    )

    # Every league must have all seasons and all tables in the result
    for league in expected_leagues:
        assert league in results
        for season in FBREF_SEASONS:
            assert season in results[league], f"Season {season} missing for {league}"
            for table in FBREF_TABLES:
                assert table in results[league][season], f"Table {table} missing for {league}/{season}"


def test_run_tm_scrapers_multi_league(monkeypatch):
    """run_tm_scrapers() with no args calls scrape_tm_season for all 5 leagues × 2 FBREF seasons."""
    import scraper as scraper_module
    from config import TM_LEAGUE_URLS, FBREF_SEASONS

    call_log = []

    def fake_scrape_tm(season_year, season_label, league="EPL"):
        call_log.append((league, season_label))
        return pd.DataFrame({
            "player_name_tm": [f"Player_{league}_{season_label}"],
            "club_tm": ["Test Club"],
            "market_value_eur": [1_000_000.0],
            "season": [season_label],
        })

    monkeypatch.setattr(scraper_module, "scrape_tm_season", fake_scrape_tm)

    result = scraper_module.run_tm_scrapers()  # no args — all 5 leagues

    expected_leagues = list(TM_LEAGUE_URLS.keys())
    leagues_called = set(league for league, _ in call_log)
    assert leagues_called == set(expected_leagues), (
        f"Expected leagues {expected_leagues}, got {sorted(leagues_called)}"
    )

    # Called once per league per FBREF season (5 leagues × 2 seasons = 10 calls)
    expected_calls = len(expected_leagues) * len(FBREF_SEASONS)
    assert len(call_log) == expected_calls, (
        f"Expected {expected_calls} scrape_tm_season calls, got {len(call_log)}"
    )

    # Result is a combined DataFrame (not empty)
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0, "Combined TM DataFrame should have rows"
    assert "player_name_tm" in result.columns
    assert "market_value_eur" in result.columns


def test_tm_cache_naming_league_keyed(tmp_path, monkeypatch):
    """scrape_tm_season with league param writes cache to tm_values_{LEAGUE}_{season}.csv, not league-free name."""
    import scraper as scraper_module
    from scraper import _cache_path as orig_cache_path

    written_paths = []

    def fake_cache_path(key):
        path = str(tmp_path / f"{key}.csv")
        written_paths.append(key)
        return path

    # Patch _cache_path to capture the key used
    monkeypatch.setattr(scraper_module, "_cache_path", fake_cache_path)

    # Patch the HTTP/session calls so scrape_tm_season doesn't actually fetch
    def fake_get_clubs(league, season_year, session):
        return []  # no clubs → returns empty DataFrame early

    monkeypatch.setattr(scraper_module, "_get_tm_club_list", fake_get_clubs)

    scraper_module.scrape_tm_season(2024, "2024-25", league="LaLiga")

    # The cache key must include the league name
    assert any("LaLiga" in key for key in written_paths), (
        f"Expected cache key containing 'LaLiga', got keys: {written_paths}"
    )
    assert any("2024-25" in key for key in written_paths), (
        f"Expected cache key containing '2024-25', got keys: {written_paths}"
    )

    # Verify the OLD key format (league-free) is NOT used
    assert not any(key == "tm_values_202425" for key in written_paths), (
        "Old league-free cache key 'tm_values_202425' must not be used"
    )
