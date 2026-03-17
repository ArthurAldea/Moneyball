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
    pytest.skip("stub — implemented in Plan 02-03")


def test_age_column_parsing():
    """FBref '25-201' format parses to integer 25; plain '25' also works."""
    pytest.skip("stub — implemented in Plan 02-03")


def test_uv_score_age_weighted_column_exists():
    """run_scoring_pipeline output contains uv_score and uv_score_age_weighted columns."""
    pytest.skip("stub — implemented in Plan 02-03")


def test_uv_regression_full_pool():
    """UV regression is fit on full unfiltered pool — uv_score values unchanged when position filter applied."""
    pytest.skip("stub — implemented in Plan 02-03")
