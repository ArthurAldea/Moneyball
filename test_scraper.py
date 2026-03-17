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
import requests

from scraper import (
    scrape_tm_season,
    scrape_fbref_stat,
    run_fbref_scrapers,
    _fbref_cache_path,
    _is_fresh,
    _fetch_with_backoff,
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
    _fetch_with_backoff raises RuntimeError after FBREF_BACKOFF_SEQUENCE exhausted.
    Verifies: 429 triggers backoff; 4th consecutive 429 raises RuntimeError.
    """
    call_count = {"n": 0}
    sleep_calls = []

    def fake_get(url, headers, timeout):
        call_count["n"] += 1
        mock_resp = requests.models.Response()
        mock_resp.status_code = 429
        return mock_resp

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="429"):
        _fetch_with_backoff("https://fbref.com/test", {})

    # Should have attempted len(FBREF_BACKOFF_SEQUENCE) + 1 times
    assert call_count["n"] == len(FBREF_BACKOFF_SEQUENCE) + 1, (
        f"Expected {len(FBREF_BACKOFF_SEQUENCE) + 1} attempts, got {call_count['n']}"
    )
    # Should have slept for each backoff delay in sequence
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
    when given a mock HTTP response containing the minimal FBref table fixture.
    """
    import requests as req_module
    import scraper as scraper_module

    # Point CACHE_DIR to tmp_path to avoid polluting real cache
    monkeypatch.setattr(scraper_module, "CACHE_DIR", str(tmp_path))

    def fake_get(url, headers, timeout):
        mock_resp = req_module.models.Response()
        mock_resp.status_code = 200
        mock_resp._content = MINIMAL_FBREF_TABLE_HTML.encode("utf-8")
        return mock_resp

    monkeypatch.setattr(req_module, "get", fake_get)
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
    pytest.skip("stub — implemented in Plan 03-01 Task 3")


def test_cache_naming_new_leagues():
    """_fbref_cache_path for new leagues produces correct convention: fbref_{LEAGUE}_{table}_{season}.csv"""
    pytest.skip("stub — implemented in Plan 03-01 Task 3")


def test_run_fbref_scrapers_all_leagues():
    """run_fbref_scrapers() with no args returns all 5 league keys; scrape_fbref_stat called 90 times."""
    pytest.skip("stub — implemented in Plan 03-01 Task 3")


def test_run_tm_scrapers_multi_league():
    """run_tm_scrapers() with no args calls scrape_tm_season for all 5 leagues × 2 seasons."""
    pytest.skip("stub — implemented in Plan 03-01 Task 3")


def test_tm_cache_naming_league_keyed():
    """scrape_tm_season with league param writes cache to tm_values_{LEAGUE}_{season}.csv."""
    pytest.skip("stub — implemented in Plan 03-01 Task 3")
