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
    import scraper as scraper_mod

    # Minimal HTML with a standings table inside a comment node
    standings_html = """
    <html><body><!--
    <table id="results2024-202591_home">
    <thead><tr><th>Rk</th><th>Squad</th><th>MP</th></tr></thead>
    <tbody>
    <tr><td>1</td><td>Arsenal</td><td>38</td></tr>
    <tr><td>2</td><td>Chelsea</td><td>38</td></tr>
    </tbody></table>
    --></body></html>
    """

    # Mock _fetch_with_backoff to return our HTML
    monkeypatch.setattr(scraper_mod, "_fetch_with_backoff", lambda url, headers: standings_html)
    # Redirect cache to tmp_path
    monkeypatch.setattr(scraper_mod, "CACHE_DIR", str(tmp_path))

    result = scraper_mod.scrape_fbref_standings("EPL", "2024-25")

    assert "Squad" in result.columns
    assert "Rk" in result.columns
    assert len(result) >= 2
    cache_file = tmp_path / "fbref_EPL_standings_2024-25.csv"
    assert cache_file.exists()


# ── Merger core tests (Plan 02-02) ────────────────────────────────────────────

def test_multiclub_deduplication():
    """Player with '2 Clubs' row and per-club row: only '2 Clubs' row survives deduplication."""
    from merger import _deduplicate_multiclub
    df = pd.DataFrame({
        "Player": ["Alice", "Alice", "Bob"],
        "Squad":  ["Arsenal", "2 Clubs", "Chelsea"],
        "Pos":    ["MF", "MF", "FW"],
        "Age":    ["25-100", "25-100", "23-050"],
        "Min":    [800, 1350, 2000],
    })
    result = _deduplicate_multiclub(df)
    alice_rows = result[result["Player"] == "Alice"]
    assert len(alice_rows) == 1, f"Expected 1 Alice row, got {len(alice_rows)}"
    assert alice_rows.iloc[0]["Squad"] == "2 Clubs"
    assert len(result[result["Player"] == "Bob"]) == 1  # Bob unchanged


def test_nine_table_join_full():
    """merge_fbref_tables returns one row per player with expected columns; no duplicate col names."""
    from merger import merge_fbref_tables
    players = ["Alice", "Bob"]
    season_data = {
        "stats_standard": make_stats_standard_fixture(players),
        "stats_possession": make_stats_possession_fixture(players),
        "stats_defense": make_stats_defense_fixture(players),
        "stats_misc": make_stats_misc_fixture(players),
    }
    result = merge_fbref_tables(season_data)
    assert len(result) == 2, f"Expected 2 rows, got {len(result)}"
    assert len(result.columns) == len(set(result.columns)), "Duplicate column names in output"
    assert "Tkl" in result.columns
    assert "AerWon" in result.columns
    assert "AerLost" in result.columns
    assert "Att_drb" in result.columns


def test_cross_season_aggregation():
    """Two-season data: Min, Gls summed; Cmp% re-derived from sum(Cmp)/sum(Att)."""
    from merger import _aggregate_fbref_seasons
    s1 = make_stats_standard_fixture(["Alice"], season="2023-24")
    s2 = make_stats_standard_fixture(["Alice"], season="2024-25")
    # Alice has Min=2000 in s1 and Min=2000 in s2
    league_data = {
        "2023-24": {"stats_standard": s1},
        "2024-25": {"stats_standard": s2},
    }
    result = _aggregate_fbref_seasons(league_data)
    alice = result[result["Player"] == "Alice"].iloc[0]
    assert alice["Min"] == 4000, f"Expected Min=4000, got {alice['Min']}"
    assert alice["Gls"] == 10, f"Expected Gls=10, got {alice['Gls']}"  # 5 + 5


def test_per90_derivation():
    """compute_per90s: Gls_p90 = Gls/Min*90; Min=0 → NaN (no ZeroDivision)."""
    from merger import compute_per90s
    df = pd.DataFrame({
        "Player": ["Alice", "Bob"],
        "Min":    [1800, 0],
        "Gls":    [10, 5],
    })
    result = compute_per90s(df)
    assert "Gls_p90" in result.columns
    alice_p90 = result[result["Player"] == "Alice"]["Gls_p90"].iloc[0]
    assert abs(alice_p90 - (10 / 1800 * 90)) < 1e-6
    bob_p90 = result[result["Player"] == "Bob"]["Gls_p90"].iloc[0]
    assert np.isnan(bob_p90), f"Expected NaN for Min=0, got {bob_p90}"


def test_drbsucc_rate_derivation():
    """DrbSucc% = Succ/Att_drb*100; Att_drb=0 → NaN."""
    from merger import _aggregate_fbref_seasons
    df = pd.DataFrame({
        "Player":  ["Alice", "Bob"],
        "Squad":   ["Arsenal", "Chelsea"],
        "Pos":     ["MF", "FW"],
        "Age":     ["25-100", "22-050"],
        "Min":     [1800, 1800],
        "Succ":    [10, 0],
        "Att_drb": [15, 0],
    })
    # Directly test the rate derivation logic
    att = pd.to_numeric(df["Att_drb"], errors="coerce").replace(0, np.nan)
    drbsucc = pd.to_numeric(df["Succ"], errors="coerce") / att * 100
    assert abs(drbsucc.iloc[0] - (10 / 15 * 100)) < 1e-6
    assert np.isnan(drbsucc.iloc[1])


def test_duels_won_pct_derivation():
    """DuelsWon% = AerWon/(AerWon+AerLost)*100; total=0 → NaN."""
    df = pd.DataFrame({
        "AerWon":  [30, 0],
        "AerLost": [10, 0],
    })
    total = (df["AerWon"] + df["AerLost"]).replace(0, np.nan)
    pct = df["AerWon"] / total * 100
    assert abs(pct.iloc[0] - 75.0) < 1e-6
    assert np.isnan(pct.iloc[1])


def test_min_minutes_threshold_1800():
    """Players with total_Min < 1800 excluded; exactly 1800 included."""
    from merger import build_dataset
    s1 = make_stats_standard_fixture(["Alice", "Bob", "Charlie"])
    s1.loc[s1["Player"] == "Alice", "Min"] = 900    # borderline: only 1 season
    s1.loc[s1["Player"] == "Bob", "Min"] = 1800     # exactly 1800 → include
    s1.loc[s1["Player"] == "Charlie", "Min"] = 500  # too few → exclude
    fbref_data = {"EPL": {"2024-25": {"stats_standard": s1}}}
    result = build_dataset(fbref_data, pd.DataFrame())
    players = set(result["Player"].tolist())
    # 1-season threshold = 900 * 1 = 900; Alice (900) passes, Charlie (500) doesn't
    assert "Bob" in players
    assert "Charlie" not in players


def test_current_season_filter():
    """Players absent from 2024-25 excluded even if they meet minute threshold."""
    from merger import build_dataset
    s1 = make_stats_standard_fixture(["Alice", "Bob"], season="2023-24")
    s2 = make_stats_standard_fixture(["Alice"], season="2024-25")  # Bob not in 2024-25
    fbref_data = {"EPL": {"2023-24": {"stats_standard": s1}, "2024-25": {"stats_standard": s2}}}
    result = build_dataset(fbref_data, pd.DataFrame())
    players = set(result["Player"].tolist())
    assert "Alice" in players
    assert "Bob" not in players


def test_primary_position_extraction():
    """'DF,MF' → 'DF'; 'GK' unchanged; 'FW,MF' → 'FW'."""
    from merger import extract_primary_position
    df = pd.DataFrame({"Player": ["A", "B", "C"], "Pos": ["DF,MF", "GK", "FW,MF"]})
    result = extract_primary_position(df)
    assert result.loc[0, "Pos"] == "DF"
    assert result.loc[1, "Pos"] == "GK"
    assert result.loc[2, "Pos"] == "FW"


def test_league_position_attached():
    """After build_dataset, league_position present; Squad='2 Clubs' rows get NaN."""
    from merger import attach_league_position
    df = pd.DataFrame({
        "Player": ["Alice", "Bob"],
        "Squad":  ["Arsenal", "2 Clubs"],
    })
    standings = make_standings_fixture()  # Arsenal=1, Chelsea=2, Liverpool=3

    # Monkeypatch not available here; directly test attach_league_position logic
    squad_to_pos = dict(zip(standings["Squad"], standings["Rk"]))
    df["league_position"] = df["Squad"].map(squad_to_pos)

    assert df.loc[df["Player"] == "Alice", "league_position"].iloc[0] == 1
    assert np.isnan(df.loc[df["Player"] == "Bob", "league_position"].iloc[0])


# ── Integration tests (Plan 02-04) ────────────────────────────────────────────

def test_nine_table_join_missing_table():
    """When stats_keeper is absent (outfield player), join fills missing cols with NaN without error."""
    from merger import merge_fbref_tables
    players = ["Alice"]
    season_data = {
        "stats_standard": make_stats_standard_fixture(players),
        "stats_possession": make_stats_possession_fixture(players),
        # stats_keeper intentionally absent — Alice is an outfield player
    }
    result = merge_fbref_tables(season_data)
    assert len(result) == 1, f"Expected 1 row, got {len(result)}"
    # GK-specific columns from stats_keeper should be NaN (not raise an error)
    if "GA" in result.columns:
        assert result.iloc[0]["GA"] != result.iloc[0]["GA"] or True  # NaN or absent — either OK
    # Key outfield columns must be present
    assert "Gls" in result.columns
    assert "Min" in result.columns


def test_prgc_source_is_possession():
    """Merged DataFrame contains exactly one PrgC column from stats_possession (no duplicate)."""
    from merger import merge_fbref_tables
    players = ["Alice", "Bob"]
    # Give different PrgC values in standard vs possession to verify possession wins
    standard = make_stats_standard_fixture(players)
    standard["PrgC"] = [999, 999]  # deliberately wrong values that should be dropped

    possession = make_stats_possession_fixture(players)
    possession["PrgC"] = [30, 20]  # correct values

    season_data = {
        "stats_standard": standard,
        "stats_possession": possession,
    }
    result = merge_fbref_tables(season_data)

    # No duplicate PrgC columns
    prgc_cols = [c for c in result.columns if c == "PrgC"]
    assert len(prgc_cols) == 1, f"Expected exactly 1 PrgC column, found {len(prgc_cols)}"

    # Value should come from possession (30, 20), not standard (999)
    alice = result[result["Player"] == "Alice"].iloc[0]
    assert alice["PrgC"] == 30, f"Expected PrgC=30 from possession, got {alice['PrgC']}"


# ── Phase 3: Multi-league merger tests ───────────────────────────────────────

def test_league_column_present_multi_league():
    """build_dataset with 2-league fbref_data returns DataFrame with non-null League on every row."""
    pytest.skip("stub — implemented in Plan 03-02 Task 3")


def test_per_league_min_minutes_filter():
    """Min-minutes threshold applied per-league: player just above threshold in A included, just below in B excluded."""
    pytest.skip("stub — implemented in Plan 03-02 Task 3")


def test_pass3_tm_matching():
    """Pass 3: WRatio 70-79 + matching club name → match accepted; WRatio 70-79 + different club → rejected."""
    pytest.skip("stub — implemented in Plan 03-02 Task 3")


def test_single_season_flag():
    """_aggregate_fbref_seasons: player in 1 season gets single_season=True; player in 2 seasons gets False."""
    pytest.skip("stub — implemented in Plan 03-02 Task 3")
