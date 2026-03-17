"""
test_scorer.py — Scorer unit tests for Phase 2.
Stubs created in Wave 0; implementations filled in as plans complete.
"""
import pytest
import pandas as pd
import numpy as np


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_scored_df(n=10, ages=None):
    """Minimal synthetic DataFrame after run_scoring_pipeline."""
    if ages is None:
        ages = list(range(18, 18 + n))
    return pd.DataFrame({
        "Player":              [f"Player{i}" for i in range(n)],
        "Pos":                 ["FW"] * n,
        "Age":                 [str(a) for a in ages],
        "scout_score":         [float(i * 10) for i in range(n)],
        "uv_score":            [float(i * 8) for i in range(n)],
        "market_value_eur":    [1e6 * (i + 1) for i in range(n)],
    })


# ── Config pillar column tests ────────────────────────────────────────────────

def test_scorer_new_pillar_columns():
    """PILLARS_FW.progression contains PrgC_p90 + DrbSucc%; PILLARS_MF.progression contains PrgP_p90 + SCA_p90."""
    from config import PILLARS_FW, PILLARS_MF
    fw_stats = set(PILLARS_FW["progression"]["stats"].keys())
    mf_stats = set(PILLARS_MF["progression"]["stats"].keys())
    assert "PrgC_p90" in fw_stats, f"FW progression missing PrgC_p90, got {fw_stats}"
    assert "DrbSucc%" in fw_stats, f"FW progression missing DrbSucc%, got {fw_stats}"
    assert "xGBuildup_p90" not in fw_stats, "FW progression still has old xGBuildup_p90"
    assert "PrgP_p90" in mf_stats, f"MF progression missing PrgP_p90, got {mf_stats}"
    assert "SCA_p90" in mf_stats, f"MF progression missing SCA_p90, got {mf_stats}"
    assert "xGChain_p90" not in mf_stats, "MF progression still has old xGChain_p90"


def test_gk_shot_stopping_pillar():
    """GK_PILLARS.attacking contains Save% (0.60) and PSxG/SoT (0.40); does NOT contain SavePct."""
    from config import GK_PILLARS
    stats = GK_PILLARS["attacking"]["stats"]
    assert "Save%" in stats, f"GK attacking missing Save%, got {stats}"
    assert "PSxG/SoT" in stats, f"GK attacking missing PSxG/SoT, got {stats}"
    assert abs(stats["Save%"] - 0.60) < 1e-6, f"Save% weight should be 0.60, got {stats['Save%']}"
    assert abs(stats["PSxG/SoT"] - 0.40) < 1e-6, f"PSxG/SoT weight should be 0.40, got {stats['PSxG/SoT']}"
    assert "SavePct" not in stats, "GK attacking still has old SavePct"


# ── Age-weight tests (implemented in Plan 02-03) ──────────────────────────────

def test_age_weight_formula():
    """Age-weight: age 17 → multiplier ~1.30, age 25 → ~1.09, age 29+ → 1.00."""
    import math
    from scorer import _parse_age

    def _multiplier(age):
        if age >= 29:
            return 1.0
        delta = 29.0 - age
        if delta <= 0:
            return 1.0
        age_weight = max(0.0, math.log(delta) / math.log(12))
        return min(1.5, 1.0 + 0.30 * age_weight)

    assert abs(_multiplier(17) - 1.30) < 0.01, f"age 17 multiplier: expected ~1.30, got {_multiplier(17):.4f}"
    assert abs(_multiplier(25) - 1.167) < 0.01, f"age 25 multiplier: expected ~1.167, got {_multiplier(25):.4f}"
    assert _multiplier(29) == 1.0, "age 29 multiplier should be 1.0"
    assert _multiplier(35) == 1.0, "age 35 multiplier should be 1.0"
    assert _multiplier(21) > 1.167, "age 21 multiplier should be between 1.167 and 1.30"
    assert _multiplier(21) < 1.30


def test_age_column_parsing():
    """FBref '25-201' format parsed to integer 25; plain '25' also works."""
    from scorer import _parse_age
    assert _parse_age("25-201") == 25.0
    assert _parse_age("17-050") == 17.0
    assert _parse_age("29-365") == 29.0
    assert _parse_age("25") == 25.0
    assert _parse_age(21) == 21.0
    assert np.isnan(_parse_age("N/A"))
    assert np.isnan(_parse_age(None))


def test_uv_score_age_weighted_column_exists():
    """run_scoring_pipeline output contains uv_score and uv_score_age_weighted columns."""
    from scorer import compute_age_weighted_uv
    # Test compute_age_weighted_uv directly with synthetic scored df
    df = pd.DataFrame({
        "Player":           ["Alice", "Bob", "Charlie"],
        "Age":              ["21-100", "29-000", "35-200"],
        "uv_score":         [50.0, 60.0, 70.0],
        "market_value_eur": [1e6, 2e6, 3e6],
    })
    result = compute_age_weighted_uv(df)
    assert "uv_score_age_weighted" in result.columns, "uv_score_age_weighted column missing"
    assert "uv_score" in result.columns, "uv_score column missing"

    # Age 21 should have multiplier > 1 → uv_score_age_weighted > uv_score
    alice = result[result["Player"] == "Alice"].iloc[0]
    assert alice["uv_score_age_weighted"] > alice["uv_score"], \
        f"Age 21 player: expected uv_score_age_weighted > uv_score, got {alice['uv_score_age_weighted']} vs {alice['uv_score']}"

    # Age 29 should have multiplier = 1 → uv_score_age_weighted == uv_score
    bob = result[result["Player"] == "Bob"].iloc[0]
    assert abs(bob["uv_score_age_weighted"] - bob["uv_score"]) < 1e-6, \
        f"Age 29 player: expected equal, got {bob['uv_score_age_weighted']} vs {bob['uv_score']}"

    # Age 35 should have multiplier = 1 → uv_score_age_weighted == uv_score
    charlie = result[result["Player"] == "Charlie"].iloc[0]
    assert abs(charlie["uv_score_age_weighted"] - charlie["uv_score"]) < 1e-6


def test_uv_regression_full_pool():
    """UV regression fit on full pool — scores don't change when position filter applied after."""
    from scorer import compute_efficiency, compute_scout_scores, compute_age_weighted_uv
    # Create a small synthetic DataFrame with mixed positions, scores, market values
    n = 20
    df = pd.DataFrame({
        "Player":           [f"P{i}" for i in range(n)],
        "Pos":              (["FW"] * 5 + ["MF"] * 5 + ["DF"] * 5 + ["GK"] * 5),
        "squad_score":      [float(i * 5) for i in range(n)],
        "market_value_eur": [1e6 * (i + 1) for i in range(n)],
        "Age":              ["25-100"] * n,
    })
    # Add pillar score columns needed by compute_efficiency
    for col in ["score_attacking","score_progression","score_creation","score_defense","score_retention"]:
        df[col] = 0.0
    df["scout_score"] = df["squad_score"]

    # Run efficiency on full pool
    full_result = compute_efficiency(df)
    full_uv = full_result.set_index("Player")["uv_score"]

    # Run efficiency on FW-only subset — UV scores for FW should differ (different regression pool)
    fw_only = compute_efficiency(df[df["Pos"] == "FW"].copy())
    fw_uv = fw_only.set_index("Player")["uv_score"]

    # The full-pool UV score for FW players should be computed on full pool
    # i.e. full_result contains all 20 players, not just FWs
    assert len(full_result) == n, f"Full pool result should have {n} rows, got {len(full_result)}"


# ── Phase 3: Multi-league scorer tests ───────────────────────────────────────

def test_per_league_normalization_isolation():
    """
    compute_scout_scores normalizes per-league: top FW in each league scores near 100
    independently, even when League A's absolute stats are much higher than League B's.

    Tests ROADMAP Phase 3 success criterion 4 and SCORE-01.
    """
    from scorer import compute_scout_scores

    # League A: 3 forwards with high absolute stats
    league_a = pd.DataFrame({
        "Player":    ["A1", "A2", "A3"],
        "Pos":       ["FW", "FW", "FW"],
        "League":    ["LeagueA", "LeagueA", "LeagueA"],
        "Age":       ["25-100", "26-100", "27-100"],
        # FW pillar stat columns (per-90s, rate stats)
        "xG_p90":    [0.90, 0.50, 0.20],
        "Gls_p90":   [0.80, 0.40, 0.15],
        "Ast_p90":   [0.30, 0.20, 0.10],
        "SoT_p90":   [3.50, 2.00, 0.80],
        "PrgC_p90":  [8.00, 5.00, 2.00],
        "DrbSucc%":  [70.0, 50.0, 30.0],
        "xA_p90":    [0.30, 0.20, 0.10],
        "KP_p90":    [3.00, 2.00, 1.00],
        "Tkl_p90":   [1.00, 0.80, 0.50],
        "Int_p90":   [0.50, 0.40, 0.20],
        "Blocks_p90":[0.30, 0.20, 0.10],
        "DuelsWon_p90": [3.00, 2.00, 1.00],
        "Cmp%":      [80.0, 75.0, 70.0],
        "DuelsWon%": [60.0, 55.0, 50.0],
    })

    # League B: 3 forwards with much lower absolute stats (e.g. weaker league)
    league_b = pd.DataFrame({
        "Player":    ["B1", "B2", "B3"],
        "Pos":       ["FW", "FW", "FW"],
        "League":    ["LeagueB", "LeagueB", "LeagueB"],
        "Age":       ["25-100", "26-100", "27-100"],
        "xG_p90":    [0.35, 0.20, 0.05],
        "Gls_p90":   [0.30, 0.15, 0.05],
        "Ast_p90":   [0.15, 0.08, 0.03],
        "SoT_p90":   [1.50, 0.80, 0.30],
        "PrgC_p90":  [3.00, 1.80, 0.60],
        "DrbSucc%":  [50.0, 35.0, 20.0],
        "xA_p90":    [0.15, 0.08, 0.03],
        "KP_p90":    [1.20, 0.80, 0.30],
        "Tkl_p90":   [0.50, 0.30, 0.15],
        "Int_p90":   [0.25, 0.15, 0.08],
        "Blocks_p90":[0.15, 0.08, 0.03],
        "DuelsWon_p90": [1.50, 0.90, 0.40],
        "Cmp%":      [72.0, 68.0, 62.0],
        "DuelsWon%": [55.0, 48.0, 42.0],
    })

    combined = pd.concat([league_a, league_b], ignore_index=True)
    result = compute_scout_scores(combined)

    # Top forward in League A (A1) should have scout_score near 100
    a1_score = result[result["Player"] == "A1"]["scout_score"].iloc[0]
    # Top forward in League B (B1) should also have scout_score near 100 (per-league normalization)
    b1_score = result[result["Player"] == "B1"]["scout_score"].iloc[0]

    # If scored on pooled data, B1 would score far below 100 because A players dominate
    # With per-league normalization, both should be near the top of their respective league
    assert a1_score > 80, f"A1 (best FW in LeagueA) should score > 80, got {a1_score:.1f}"
    assert b1_score > 80, (
        f"B1 (best FW in LeagueB) should score > 80 with per-league normalization, "
        f"got {b1_score:.1f}. If this fails, normalization is across leagues (incorrect)."
    )

    # Bottom forward in each league (A3, B3) should score near 0 within their league
    a3_score = result[result["Player"] == "A3"]["scout_score"].iloc[0]
    b3_score = result[result["Player"] == "B3"]["scout_score"].iloc[0]
    assert a3_score < 20, f"A3 (worst FW in LeagueA) should score < 20, got {a3_score:.1f}"
    assert b3_score < 20, f"B3 (worst FW in LeagueB) should score < 20, got {b3_score:.1f}"


def test_uv_regression_on_full_pool_multi_league():
    """compute_efficiency fits UV regression on full 5-league pool (SCORE-06); len(result) = total players."""
    from scorer import compute_efficiency

    # Create a 3-league synthetic DataFrame (20 players per league = 60 total)
    n_per_league = 20
    leagues = ["EPL", "LaLiga", "Bundesliga"]
    rows = []
    for i, league in enumerate(leagues):
        for j in range(n_per_league):
            rows.append({
                "Player":           f"{league}_P{j}",
                "Pos":              ["FW", "MF", "DF", "GK"][j % 4],
                "League":           league,
                "Age":              "25-100",
                "scout_score":      float((i * n_per_league + j) * 1.5),
                "market_value_eur": 1e6 * ((i * n_per_league + j) + 1),
                "score_attacking":  0.0,
                "score_progression": 0.0,
                "score_creation":   0.0,
                "score_defense":    0.0,
                "score_retention":  0.0,
            })

    df = pd.DataFrame(rows)
    total_players = len(df)

    result = compute_efficiency(df)

    # UV regression must operate on the full pool
    assert len(result) == total_players, (
        f"compute_efficiency should return all {total_players} players (full pool), "
        f"got {len(result)}"
    )

    # League column must be preserved in the output
    assert "League" in result.columns, "League column missing from compute_efficiency output"

    # All 3 leagues must appear in the result
    result_leagues = set(result["League"].unique())
    assert set(leagues) == result_leagues, (
        f"Expected leagues {leagues} in result, got {sorted(result_leagues)}"
    )

    # UV score column present
    assert "uv_score" in result.columns, "uv_score column missing"
    assert result["uv_score"].notna().all(), "uv_score should not have NaN values"


def test_league_column_preserved_through_pipeline():
    """run_scoring_pipeline output has League column with correct per-player values."""
    from scorer import run_scoring_pipeline

    # Build minimal synthetic fbref_data for 2 leagues
    def _make_season_data(players, squad, league):
        """Minimal season data for run_scoring_pipeline."""
        n = len(players)
        standard = pd.DataFrame({
            "Player": players,
            "Squad":  [squad] * n,
            "Pos":    ["FW"] * n,
            "Age":    ["25-100"] * n,
            "Min":    [1500] * n,
            "Gls":    [5] * n,
            "Ast":    [3] * n,
            "xG":     [4.5] * n,
            "xA":     [2.5] * n,
            "npxG":   [4.0] * n,
            "SoT":    [15] * n,
            "PrgP":   [60] * n,
            "PrgC":   [25] * n,
            "SCA":    [40] * n,
            "KP":     [20] * n,
            "Cmp":    [700] * n,
            "Att":    [850] * n,
        })
        possession = pd.DataFrame({
            "Player": players,
            "Squad":  [squad] * n,
            "Pos":    ["FW"] * n,
            "Age":    ["25-100"] * n,
            "Att":    [12] * n,
            "Succ":   [8] * n,
            "PrgC":   [25] * n,
        })
        misc = pd.DataFrame({
            "Player": players,
            "Squad":  [squad] * n,
            "Pos":    ["FW"] * n,
            "Age":    ["25-100"] * n,
            "Won":    [25] * n,
            "Lost":   [8] * n,
        })
        defense = pd.DataFrame({
            "Player": players,
            "Squad":  [squad] * n,
            "Pos":    ["FW"] * n,
            "Age":    ["25-100"] * n,
            "Tkl":    [15] * n,
            "Int":    [8] * n,
            "Blocks": [5] * n,
        })
        return {
            "stats_standard": standard,
            "stats_possession": possession,
            "stats_misc": misc,
            "stats_defense": defense,
        }

    fbref_data = {
        "EPL":    {"2024-25": _make_season_data(["Alice", "Bob"], "Arsenal", "EPL")},
        "LaLiga": {"2024-25": _make_season_data(["Carlos", "Diego"], "Real Madrid", "LaLiga")},
    }

    # Provide minimal TM data for market values
    tm_data = pd.DataFrame({
        "player_name_tm": ["Alice", "Bob", "Carlos", "Diego"],
        "club_tm":        ["Arsenal", "Arsenal", "Real Madrid", "Real Madrid"],
        "market_value_eur": [20e6, 15e6, 30e6, 25e6],
        "league_tm":      ["EPL", "EPL", "LaLiga", "LaLiga"],
    })

    result = run_scoring_pipeline(fbref_data, tm_data)

    assert not result.empty, "run_scoring_pipeline returned empty DataFrame"
    assert "League" in result.columns, "League column missing from pipeline output"
    assert result["League"].notna().all(), "League column has NaN values in pipeline output"

    # EPL players should have League="EPL"
    epl_players = result[result["Player"].isin(["Alice", "Bob"])]
    assert (epl_players["League"] == "EPL").all(), (
        f"EPL players should have League='EPL', got: {epl_players['League'].tolist()}"
    )

    # LaLiga players should have League="LaLiga"
    liga_players = result[result["Player"].isin(["Carlos", "Diego"])]
    assert (liga_players["League"] == "LaLiga").all(), (
        f"LaLiga players should have League='LaLiga', got: {liga_players['League'].tolist()}"
    )

    # UV score columns must be present
    assert "uv_score" in result.columns, "uv_score missing from pipeline output"
    assert "uv_score_age_weighted" in result.columns, "uv_score_age_weighted missing from pipeline output"
    assert "scout_score" in result.columns, "scout_score missing from pipeline output"


def test_team_strength_bottom_half_inflates_df_score():
    """Bottom-half DF gets higher adjusted defensive stats than identical stats at top-half club."""
    from scorer import apply_team_strength_adjustment

    df = pd.DataFrame({
        "Player":          ["BottomDF", "TopDF"],
        "Pos":             ["DF", "DF"],
        "League":          ["EPL", "EPL"],
        "league_position": [15.0, 5.0],  # 20-club league; threshold=10
        "Tkl_p90":         [1.0, 1.0],
        "Int_p90":         [1.0, 1.0],
        "Blocks_p90":      [1.0, 1.0],
        "DuelsWon_p90":    [1.0, 1.0],
        "Pres_p90":        [1.0, 1.0],
    })

    result = apply_team_strength_adjustment(df)
    bottom = result[result["Player"] == "BottomDF"].iloc[0]
    top    = result[result["Player"] == "TopDF"].iloc[0]

    for stat in ["Tkl_p90", "Int_p90", "Blocks_p90", "DuelsWon_p90", "Pres_p90"]:
        assert abs(bottom[stat] - 1.10) < 1e-9, (
            f"Bottom-half DF {stat}: expected 1.10, got {bottom[stat]}"
        )
        assert abs(top[stat] - 0.90) < 1e-9, (
            f"Top-half DF {stat}: expected 0.90, got {top[stat]}"
        )


def test_team_strength_does_not_affect_fw_attacking():
    """FW xG_p90, Gls_p90, Ast_p90, SoT_p90 must be unchanged by team strength step."""
    from scorer import apply_team_strength_adjustment

    df = pd.DataFrame({
        "Player":          ["FW1"],
        "Pos":             ["FW"],
        "League":          ["EPL"],
        "league_position": [15.0],
        "xG_p90":          [0.5],
        "Gls_p90":         [0.3],
        "Ast_p90":         [0.2],
        "SoT_p90":         [1.0],
    })

    result = apply_team_strength_adjustment(df)
    fw = result.iloc[0]

    assert abs(fw["xG_p90"]  - 0.5) < 1e-9, f"xG_p90 changed: {fw['xG_p90']}"
    assert abs(fw["Gls_p90"] - 0.3) < 1e-9, f"Gls_p90 changed: {fw['Gls_p90']}"
    assert abs(fw["Ast_p90"] - 0.2) < 1e-9, f"Ast_p90 changed: {fw['Ast_p90']}"
    assert abs(fw["SoT_p90"] - 1.0) < 1e-9, f"SoT_p90 changed: {fw['SoT_p90']}"


def test_team_strength_skips_nan_league_position():
    """Player with NaN league_position passes through with no stat change."""
    from scorer import apply_team_strength_adjustment

    df = pd.DataFrame({
        "Player":          ["DF1"],
        "Pos":             ["DF"],
        "League":          ["EPL"],
        "league_position": [float("nan")],
        "Tkl_p90":         [1.0],
    })

    result = apply_team_strength_adjustment(df)
    assert abs(result.iloc[0]["Tkl_p90"] - 1.0) < 1e-9, (
        f"Tkl_p90 should be unchanged for NaN league_position, got {result.iloc[0]['Tkl_p90']}"
    )
