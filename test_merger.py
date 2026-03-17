"""
test_merger.py — Merger unit tests for Phase 2.
Stubs created in Wave 0; implementations filled in as plans complete.
"""
import pytest
import pandas as pd
import numpy as np


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_stats_standard_fixture(players=None, season="2024-25"):
    """Synthetic FBref stats_standard DataFrame (post-scrape, 900-min filtered)."""
    if players is None:
        players = ["Alice", "Bob", "Charlie"]
    n = len(players)
    return pd.DataFrame({
        "Player": players,
        "Squad":  ["Arsenal"] * n,
        "Pos":    ["MF"] * n,
        "Age":    ["25-100"] * n,
        "Min":    [2000, 1500, 1100][:n],
        "Gls":    [5, 3, 2][:n],
        "Ast":    [4, 2, 1][:n],
        "xG":     [4.5, 2.8, 1.9][:n],
        "xA":     [3.1, 1.5, 0.9][:n],
        "SoT":    [20, 12, 8][:n],
        "PrgP":   [80, 60, 40][:n],
        "PrgC":   [30, 20, 15][:n],
        "SCA":    [50, 35, 25][:n],
        "KP":     [25, 18, 10][:n],
        "Cmp":    [900, 700, 500][:n],
        "Att":    [1000, 800, 600][:n],
        "season": [season] * n,
    })


def make_stats_possession_fixture(players=None, season="2024-25"):
    """Synthetic FBref stats_possession DataFrame."""
    if players is None:
        players = ["Alice", "Bob", "Charlie"]
    n = len(players)
    return pd.DataFrame({
        "Player": players,
        "Squad":  ["Arsenal"] * n,
        "Pos":    ["MF"] * n,
        "Age":    ["25-100"] * n,
        "Att":    [15, 10, 8][:n],    # dribble attempts (Take-Ons)
        "Succ":   [10, 6, 4][:n],     # successful dribbles
        "PrgC":   [30, 20, 15][:n],
        "season": [season] * n,
    })


def make_stats_defense_fixture(players=None, season="2024-25"):
    """Synthetic FBref stats_defense DataFrame."""
    if players is None:
        players = ["Alice", "Bob", "Charlie"]
    n = len(players)
    return pd.DataFrame({
        "Player": players,
        "Squad":  ["Arsenal"] * n,
        "Pos":    ["MF"] * n,
        "Age":    ["25-100"] * n,
        "Tkl":    [40, 30, 20][:n],
        "Int":    [20, 15, 10][:n],
        "Blocks": [10, 8, 5][:n],
        "season": [season] * n,
    })


def make_stats_misc_fixture(players=None, season="2024-25"):
    """Synthetic FBref stats_misc DataFrame with aerial duel columns."""
    if players is None:
        players = ["Alice", "Bob", "Charlie"]
    n = len(players)
    return pd.DataFrame({
        "Player": players,
        "Squad":  ["Arsenal"] * n,
        "Pos":    ["MF"] * n,
        "Age":    ["25-100"] * n,
        "Won":    [30, 20, 15][:n],   # aerial duels won
        "Lost":   [10, 8, 5][:n],     # aerial duels lost
        "season": [season] * n,
    })


def make_standings_fixture():
    """Synthetic EPL standings DataFrame."""
    return pd.DataFrame({
        "Squad": ["Arsenal", "Chelsea", "Liverpool"],
        "Rk":    [1, 2, 3],
    })


# ── Standings scraper tests (Plan 02-02) ──────────────────────────────────────

def test_standings_scraper_caches(tmp_path, monkeypatch):
    """scrape_fbref_standings() writes cache/fbref_EPL_standings_2024-25.csv with Squad and Rk cols."""
    pytest.skip("stub — implemented in Plan 02-02")


# ── Merger core tests (Plan 02-02) ────────────────────────────────────────────

def test_multiclub_deduplication():
    """Player with '2 Clubs' row and per-club row: only '2 Clubs' row survives deduplication."""
    pytest.skip("stub — implemented in Plan 02-02")


def test_nine_table_join_full():
    """merge_fbref_tables returns one row per player with all expected columns; no duplicate col names."""
    pytest.skip("stub — implemented in Plan 02-02")


def test_cross_season_aggregation():
    """Two-season aggregation sums Min, Gls, SoT; rate stat Cmp% is minutes-weighted."""
    pytest.skip("stub — implemented in Plan 02-02")


def test_per90_derivation():
    """compute_per90s: Gls_p90 = Gls / Min * 90; Min=0 produces NaN (no ZeroDivision)."""
    pytest.skip("stub — implemented in Plan 02-02")


def test_drbsucc_rate_derivation():
    """DrbSucc% = Succ / Att * 100; Att=0 produces NaN."""
    pytest.skip("stub — implemented in Plan 02-02")


def test_duels_won_pct_derivation():
    """DuelsWon% = Won / (Won + Lost) * 100; Won + Lost = 0 produces NaN."""
    pytest.skip("stub — implemented in Plan 02-02")


def test_min_minutes_threshold_1800():
    """Players with total_Min < 1800 excluded; players with exactly 1800 included."""
    pytest.skip("stub — implemented in Plan 02-02")


def test_current_season_filter():
    """Players absent from 2024-25 data excluded even with sufficient total minutes."""
    pytest.skip("stub — implemented in Plan 02-02")


def test_primary_position_extraction():
    """'DF,MF' → 'DF'; 'GK' unchanged; 'FW,MF' → 'FW'."""
    pytest.skip("stub — implemented in Plan 02-02")


def test_league_position_attached():
    """After build_dataset, merged DataFrame has league_position; Squad='2 Clubs' rows get NaN."""
    pytest.skip("stub — implemented in Plan 02-02")


# ── Integration tests (Plan 02-04) ────────────────────────────────────────────

def test_nine_table_join_missing_table():
    """When one of 9 tables is empty (e.g. stats_keeper for outfield), join fills missing cols with NaN."""
    pytest.skip("stub — implemented in Plan 02-04")


def test_prgc_source_is_possession():
    """Merged DataFrame contains exactly one PrgC column sourced from stats_possession."""
    pytest.skip("stub — implemented in Plan 02-04")
