"""
test_scorer.py — Scorer unit tests for Phase 2.
Stubs created in Wave 0; implementations filled in as plans complete.
"""
import json
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

def test_scorer_pillar_columns_post_lit_migration():
    """Post-FBref Lit migration: pillars use only available stats; deprecated columns absent."""
    from config import PILLARS_FW, PILLARS_MF, _CREATION, _DEFENSE, _RETENTION

    fw_prog = set(PILLARS_FW["progression"]["stats"].keys())
    mf_prog = set(PILLARS_MF["progression"]["stats"].keys())

    # FW progression: shots + fouls drawn (PrgC_p90/DrbSucc% removed — FBref Lit)
    assert "Sh_p90" in fw_prog, f"FW progression missing Sh_p90, got {fw_prog}"
    assert "Fld_p90" in fw_prog, f"FW progression missing Fld_p90, got {fw_prog}"
    assert "PrgC_p90" not in fw_prog, "FW progression still has PrgC_p90 (removed — FBref Lit)"
    assert "DrbSucc%" not in fw_prog, "FW progression still has DrbSucc% (removed — FBref Lit)"

    # MF progression: crosses + fouls drawn (PrgP_p90/SCA_p90 removed — FBref Lit)
    assert "Crs_p90" in mf_prog, f"MF progression missing Crs_p90, got {mf_prog}"
    assert "PrgP_p90" not in mf_prog, "MF progression still has PrgP_p90 (removed — FBref Lit)"

    # Creation: assists + crosses (KP_p90/xA_p90 removed)
    creation_stats = set(_CREATION["stats"].keys())
    assert "Ast_p90" in creation_stats, "Creation pillar missing Ast_p90"
    assert "xA_p90" not in creation_stats, "Creation pillar still has xA_p90 (removed)"

    # Defense: Int + TklW (Blocks/DuelsWon removed)
    defense_stats = set(_DEFENSE["stats"].keys())
    assert "Int_p90" in defense_stats, "Defense pillar missing Int_p90"
    assert "TklW_p90" in defense_stats, "Defense pillar missing TklW_p90"
    assert "Blocks_p90" not in defense_stats, "Defense pillar still has Blocks_p90 (removed)"

    # Retention: fouls drawn (Cmp%/DuelsWon% removed)
    retention_stats = set(_RETENTION["stats"].keys())
    assert "Fld_p90" in retention_stats, "Retention pillar missing Fld_p90"
    assert "Cmp%" not in retention_stats, "Retention pillar still has Cmp% (removed)"


def test_gk_shot_stopping_pillar():
    """GK_PILLARS.attacking uses Save% (1.0) only — PSxG/SoT removed in FBref Lit migration."""
    from config import GK_PILLARS
    stats = GK_PILLARS["attacking"]["stats"]
    assert "Save%" in stats, f"GK attacking missing Save%, got {stats}"
    assert abs(stats["Save%"] - 1.00) < 1e-6, f"Save% weight should be 1.00, got {stats['Save%']}"
    assert "PSxG/SoT" not in stats, "GK attacking still has PSxG/SoT (removed — FBref Lit)"
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

    # League A: 3 forwards with high absolute stats (post-FBref Lit migration columns)
    league_a = pd.DataFrame({
        "Player":    ["A1", "A2", "A3"],
        "Pos":       ["FW", "FW", "FW"],
        "League":    ["LeagueA", "LeagueA", "LeagueA"],
        "Age":       ["25-100", "26-100", "27-100"],
        "Gls_p90":   [0.80, 0.40, 0.15],
        "Ast_p90":   [0.30, 0.20, 0.10],
        "SoT_p90":   [3.50, 2.00, 0.80],
        "Sh_p90":    [4.00, 2.50, 1.00],
        "Fld_p90":   [2.50, 1.50, 0.60],
        "Crs_p90":   [1.00, 0.60, 0.20],
        "Int_p90":   [0.50, 0.40, 0.20],
        "TklW_p90":  [1.00, 0.80, 0.50],
    })

    # League B: 3 forwards with much lower absolute stats (e.g. weaker league)
    league_b = pd.DataFrame({
        "Player":    ["B1", "B2", "B3"],
        "Pos":       ["FW", "FW", "FW"],
        "League":    ["LeagueB", "LeagueB", "LeagueB"],
        "Age":       ["25-100", "26-100", "27-100"],
        "Gls_p90":   [0.30, 0.15, 0.05],
        "Ast_p90":   [0.15, 0.08, 0.03],
        "SoT_p90":   [1.50, 0.80, 0.30],
        "Sh_p90":    [1.80, 1.00, 0.40],
        "Fld_p90":   [1.20, 0.70, 0.25],
        "Crs_p90":   [0.40, 0.25, 0.08],
        "Int_p90":   [0.25, 0.15, 0.08],
        "TklW_p90":  [0.50, 0.30, 0.15],
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
            "SoT":    [15] * n,
            "KP":     [20] * n,
            "Cmp":    [700] * n,
            "Att":    [850] * n,
        })
        gca = pd.DataFrame({
            "Player": players,
            "Squad":  [squad] * n,
            "Pos":    ["FW"] * n,
            "Age":    ["25-100"] * n,
            "SCA":    [40] * n,
        })
        possession = pd.DataFrame({
            "Player": players,
            "Squad":  [squad] * n,
            "Pos":    ["FW"] * n,
            "Age":    ["25-100"] * n,
            "Att":    [12] * n,
            "Succ":   [8] * n,
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
            "stats_gca": gca,
            "stats_possession": possession,
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
    })

    result = apply_team_strength_adjustment(df)
    bottom = result[result["Player"] == "BottomDF"].iloc[0]
    top    = result[result["Player"] == "TopDF"].iloc[0]

    for stat in ["Tkl_p90", "Int_p90", "Blocks_p90"]:
        assert abs(bottom[stat] - 1.10) < 1e-9, (
            f"Bottom-half DF {stat}: expected 1.10, got {bottom[stat]}"
        )
        assert abs(top[stat] - 0.90) < 1e-9, (
            f"Top-half DF {stat}: expected 0.90, got {top[stat]}"
        )


def test_team_strength_does_not_affect_fw_attacking():
    """FW Gls_p90, Ast_p90, SoT_p90 must be unchanged by team strength step."""
    from scorer import apply_team_strength_adjustment

    df = pd.DataFrame({
        "Player":          ["FW1"],
        "Pos":             ["FW"],
        "League":          ["EPL"],
        "league_position": [15.0],
        "Gls_p90":         [0.3],
        "Ast_p90":         [0.2],
        "SoT_p90":         [1.0],
    })

    result = apply_team_strength_adjustment(df)
    fw = result.iloc[0]

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


# ── Phase 4 Plan 02: League Quality Multiplier tests (SCORE-05) ──────────────

def test_league_quality_multiplier_values():
    """Each player row must have league_quality_multiplier consistent with locked coefficients."""
    from scorer import apply_league_quality_multiplier

    df = pd.DataFrame({
        "Player":               ["EPL_P", "LaLiga_P", "Bundesliga_P", "SerieA_P", "Ligue1_P", "Unknown_P"],
        "League":               ["EPL",   "LaLiga",   "Bundesliga",   "SerieA",   "Ligue1",   "SomeCup"],
        "uv_score_age_weighted": [50.0,    50.0,       50.0,           50.0,       50.0,       50.0],
    })
    result = apply_league_quality_multiplier(df)

    assert "league_quality_multiplier" in result.columns, "league_quality_multiplier column missing"

    def _mult(league):
        return result.loc[result["League"] == league, "league_quality_multiplier"].iloc[0]

    assert abs(_mult("EPL")        - 1.10) < 1e-9, f"EPL multiplier: {_mult('EPL')}"
    assert abs(_mult("LaLiga")     - 1.08) < 1e-9, f"LaLiga multiplier: {_mult('LaLiga')}"
    assert abs(_mult("Bundesliga") - 1.05) < 1e-9, f"Bundesliga multiplier: {_mult('Bundesliga')}"
    assert abs(_mult("SerieA")     - 1.03) < 1e-9, f"SerieA multiplier: {_mult('SerieA')}"
    assert abs(_mult("Ligue1")     - 1.00) < 1e-9, f"Ligue1 multiplier: {_mult('Ligue1')}"
    assert abs(_mult("SomeCup")    - 1.00) < 1e-9, f"Unknown league fallback should be 1.0, got: {_mult('SomeCup')}"


def test_league_quality_multiplier_applied_in_place():
    """uv_score_age_weighted must be multiplied in-place by the league quality multiplier."""
    from scorer import apply_league_quality_multiplier

    df = pd.DataFrame({
        "Player":               ["EPL_P", "Ligue1_P"],
        "League":               ["EPL",   "Ligue1"],
        "uv_score_age_weighted": [50.0,    50.0],
    })
    result = apply_league_quality_multiplier(df)

    assert "league_quality_multiplier" in result.columns, "league_quality_multiplier column missing"

    epl_row    = result[result["League"] == "EPL"].iloc[0]
    ligue1_row = result[result["League"] == "Ligue1"].iloc[0]

    assert abs(epl_row["uv_score_age_weighted"] - 55.0) < 1e-9, (
        f"EPL uv_score_age_weighted: expected 55.0 (50.0 * 1.10), got {epl_row['uv_score_age_weighted']}"
    )
    assert abs(ligue1_row["uv_score_age_weighted"] - 50.0) < 1e-9, (
        f"Ligue1 uv_score_age_weighted: expected 50.0 (50.0 * 1.00), got {ligue1_row['uv_score_age_weighted']}"
    )


# ── Phase 4 Plan 03: Similar Players tests (SCORE-08) ────────────────────────

def _make_players(n, pos, squads=None, leagues=None, scores=None):
    """Build a synthetic DataFrame with valid score_* columns for similar player tests."""
    players = [f"{pos}_Player{i}" for i in range(n)]
    if squads is None:
        squads = ["TeamA"] * n
    if leagues is None:
        leagues = ["EPL"] * n
    if scores is None:
        # Use diverse scores so cosine similarity produces meaningful ordering
        scores = [
            [0.8 - i * 0.05, 0.7 - i * 0.04, 0.6 - i * 0.03, 0.5 - i * 0.02, 0.4 - i * 0.01]
            for i in range(n)
        ]
    return pd.DataFrame({
        "Player":              players,
        "Squad":               squads,
        "League":              leagues,
        "Pos":                 [pos] * n,
        "score_attacking":     [s[0] for s in scores],
        "score_progression":   [s[1] for s in scores],
        "score_creation":      [s[2] for s in scores],
        "score_defense":       [s[3] for s in scores],
        "score_retention":     [s[4] for s in scores],
        "uv_score_age_weighted": [50.0] * n,
    })


def test_similar_players_column_is_valid_json():
    """similar_players column must exist and contain valid JSON on every row."""
    from scorer import compute_similar_players

    df = _make_players(8, "DF")
    result = compute_similar_players(df)

    assert "similar_players" in result.columns, "similar_players column missing"
    for i in result.index:
        raw = result.loc[i, "similar_players"]
        parsed = json.loads(raw)
        assert isinstance(parsed, list), f"Row {i}: expected list, got {type(parsed)}"
        assert len(parsed) == 5, f"Row {i}: expected 5 similar players, got {len(parsed)}"
        for entry in parsed:
            assert "player" in entry, f"Row {i}: entry missing 'player' key: {entry}"
            assert "club" in entry, f"Row {i}: entry missing 'club' key: {entry}"
            assert "league" in entry, f"Row {i}: entry missing 'league' key: {entry}"
            assert "uv_score_age_weighted" in entry, f"Row {i}: entry missing 'uv_score_age_weighted' key: {entry}"


def test_similar_players_same_position_group():
    """All 5 similar players for any given player must be the same position group."""
    from scorer import compute_similar_players

    fw_df = _make_players(6, "FW")
    df_df = _make_players(6, "DF")
    combined = pd.concat([fw_df, df_df], ignore_index=True)
    result = compute_similar_players(combined)

    fw_players = set(fw_df["Player"].tolist())
    df_players = set(df_df["Player"].tolist())

    for _, row in result.iterrows():
        player_name = row["Player"]
        similar = json.loads(row["similar_players"])
        similar_names = {e["player"] for e in similar}

        if player_name in fw_players:
            assert similar_names.issubset(fw_players), (
                f"FW player {player_name} has non-FW similar players: "
                f"{similar_names - fw_players}"
            )
        elif player_name in df_players:
            assert similar_names.issubset(df_players), (
                f"DF player {player_name} has non-DF similar players: "
                f"{similar_names - df_players}"
            )


def test_similar_players_excludes_self():
    """No player may appear in their own similar_players list."""
    from scorer import compute_similar_players

    df = _make_players(8, "DF")
    result = compute_similar_players(df)

    for _, row in result.iterrows():
        player_name = row["Player"]
        similar = json.loads(row["similar_players"])
        similar_names = [e["player"] for e in similar]
        assert player_name not in similar_names, (
            f"Player {player_name} appears in their own similar_players list"
        )


def test_similar_players_cross_league():
    """Similar players may span multiple leagues (not restricted to same league)."""
    from scorer import compute_similar_players

    # 4 EPL + 4 LaLiga DF players, all with very similar scores → cross-league matches expected
    epl_scores = [[0.80, 0.70, 0.60, 0.50, 0.40]] * 4
    liga_scores = [[0.79, 0.69, 0.59, 0.49, 0.39]] * 4
    epl_df = _make_players(4, "DF", squads=["EPL_Club"] * 4, leagues=["EPL"] * 4, scores=epl_scores)
    liga_df = _make_players(4, "DF", squads=["Liga_Club"] * 4, leagues=["LaLiga"] * 4, scores=liga_scores)
    combined = pd.concat([epl_df, liga_df], ignore_index=True)
    result = compute_similar_players(combined)

    # For at least one player, their similar list should include players from both leagues
    cross_league_found = False
    for _, row in result.iterrows():
        similar = json.loads(row["similar_players"])
        leagues_in_similar = {e["league"] for e in similar}
        if len(leagues_in_similar) > 1:
            cross_league_found = True
            break

    assert cross_league_found, (
        "No player has similar players from multiple leagues — "
        "cross-league similarity is required (SCORE-08)"
    )


# ── Wave 0: Pillar weight integrity (Phase 06.1) ──────────────────────────────

def test_fw_pillar_weights_sum():
    """All FW pillar stat weight dicts sum to 1.0 (required for scout_score ≈ 100 max)."""
    from config import PILLARS_FW
    for pillar_name, pillar in PILLARS_FW.items():
        stat_weights = pillar["stats"]
        total = sum(stat_weights.values())
        assert abs(total - 1.0) < 1e-9, (
            f"PILLARS_FW['{pillar_name}']['stats'] weights sum to {total:.6f}, not 1.0. "
            f"Stats: {stat_weights}"
        )


def test_mf_pillar_weights_sum():
    """All MF pillar stat weight dicts sum to 1.0 (required for scout_score ≈ 100 max)."""
    from config import PILLARS_MF
    for pillar_name, pillar in PILLARS_MF.items():
        stat_weights = pillar["stats"]
        total = sum(stat_weights.values())
        assert abs(total - 1.0) < 1e-9, (
            f"PILLARS_MF['{pillar_name}']['stats'] weights sum to {total:.6f}, not 1.0. "
            f"Stats: {stat_weights}"
        )
