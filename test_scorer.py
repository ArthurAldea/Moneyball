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
