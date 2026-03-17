"""
scorer.py — Position-specific scout scoring and undervaluation formula.

Each position group uses a tailored pillar model:
  FW  — Attacking 45 / Progression 20 / Creation 20 / Defense 5  / Retention 10
  MF  — Attacking 20 / Progression 30 / Creation 25 / Defense 15 / Retention 10
  DF  — Attacking 10 / Progression 15 / Creation 10 / Defense 45 / Retention 20
  GK  — Shot Stopping 50 / Distribution 20 / Aerial 15 / Sweeping 10 / Composure 5

UV Score uses position-aware regression residuals:
  fit log10(market_value) ~ scout_score + position_dummies
  UV = percentile rank of (predicted − actual log-value); 100 = most undervalued.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression

from config import PILLARS_FW, PILLARS_MF, PILLARS_DF, GK_PILLARS


# ── Team Strength Adjustment constants (SCORE-04) ─────────────────────────────
_DF_DEFENSIVE_STATS = ["Tkl_p90", "Int_p90", "Blocks_p90", "DuelsWon_p90", "Pres_p90"]
_GK_RATE_STATS = ["Save%", "PSxG/SoT"]
_TEAM_STRENGTH_MAGNITUDE = 0.10  # ±10%


def apply_team_strength_adjustment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adjust defensive per-90 stats for DF and GK based on team league position.

    Logic (SCORE-04):
    - DF bottom-half (league_position > n_clubs/2): multiply _DF_DEFENSIVE_STATS by 1.10
    - DF top-half (league_position <= n_clubs/2): multiply _DF_DEFENSIVE_STATS by 0.90
    - GK bottom-half: multiply Save% and PSxG/SoT by 1.10
    - GK top-half: multiply Save% and PSxG/SoT by 0.90
    - FW/MF attacking stats: NEVER modified
    - NaN league_position: skip (consistent with merger soft-fail pattern)
    - n_clubs derived dynamically per league from max(league_position) — handles both
      20-club (EPL/LaLiga/SerieA) and 18-club (Bundesliga/Ligue1) correctly.
    """
    if "League" not in df.columns or "league_position" not in df.columns:
        return df
    df = df.copy()
    for league in df["League"].unique():
        league_mask = df["League"] == league
        valid_pos = df.loc[league_mask, "league_position"].dropna()
        if valid_pos.empty:
            continue
        n_clubs = valid_pos.max()
        threshold = n_clubs / 2

        # DF adjustment — defensive per-90 stats only
        df_mask = league_mask & (df["Pos"] == "DF") & df["league_position"].notna()
        bottom_df = df_mask & (df["league_position"] > threshold)
        top_df    = df_mask & (df["league_position"] <= threshold)
        for col in _DF_DEFENSIVE_STATS:
            if col in df.columns:
                df.loc[bottom_df, col] = df.loc[bottom_df, col] * (1 + _TEAM_STRENGTH_MAGNITUDE)
                df.loc[top_df,    col] = df.loc[top_df,    col] * (1 - _TEAM_STRENGTH_MAGNITUDE)

        # GK adjustment — rate stats only (Pres_p90 is NOT adjusted for GK)
        gk_mask   = league_mask & (df["Pos"] == "GK") & df["league_position"].notna()
        bottom_gk = gk_mask & (df["league_position"] > threshold)
        top_gk    = gk_mask & (df["league_position"] <= threshold)
        for col in _GK_RATE_STATS:
            if col in df.columns:
                df.loc[bottom_gk, col] = df.loc[bottom_gk, col] * (1 + _TEAM_STRENGTH_MAGNITUDE)
                df.loc[top_gk,    col] = df.loc[top_gk,    col] * (1 - _TEAM_STRENGTH_MAGNITUDE)

    return df


def _score_group(df: pd.DataFrame, pillars: dict) -> pd.DataFrame:
    """
    Normalise stat columns (MinMax within this position group), then compute
    weighted pillar scores and total scout score (0–100).
    """
    if df.empty:
        return df

    all_stat_cols = []
    for p in pillars.values():
        all_stat_cols.extend(p["stats"].keys())

    available = [c for c in all_stat_cols if c in df.columns]
    missing   = set(all_stat_cols) - set(available)
    if missing:
        print(f"  [scorer] Missing columns (scored 0): {missing}")

    if not available:
        df["scout_score"] = 0.0
        for pillar_name in pillars:
            df[f"score_{pillar_name}"] = 0.0
        return df

    scaler = MinMaxScaler()
    df[available] = scaler.fit_transform(df[available].fillna(0))

    df["scout_score"] = 0.0
    for pillar_name, pillar_data in pillars.items():
        pillar_score = pd.Series(0.0, index=df.index)
        for stat, stat_weight in pillar_data["stats"].items():
            if stat in df.columns:
                pillar_score += df[stat] * stat_weight
        df[f"score_{pillar_name}"] = pillar_score * pillar_data["weight"]
        df["scout_score"] += df[f"score_{pillar_name}"]

    return df


def compute_scout_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score each position group with its own pillar model, then recombine.

    Normalization scope (SCORE-01, Phase 3): MinMaxScaler is fitted per
    league+position group independently. This ensures the top forward in
    La Liga and the top forward in EPL both receive scout_score near 100,
    even if their absolute per-90 stats differ.

    If df has no 'League' column (EPL-only legacy mode), falls back to
    scoring the full DataFrame as a single group (Phase 2 behavior).
    """
    df = df.copy()
    # Ensure primary position only (take first token of 'DF,MF' etc.)
    df["Pos"] = df["Pos"].astype(str).str.split(",").str[0].str.strip()

    all_frames = []

    if "League" not in df.columns:
        # backward compat: pre-Phase-3 callers may not include League column
        leagues_to_score = [None]
    else:
        leagues_to_score = list(df["League"].unique())

    for league in leagues_to_score:
        if league is None:
            league_df = df
        else:
            league_df = df[df["League"] == league].copy()

        if league_df.empty:
            continue

        groups = {
            "GK": (league_df["Pos"] == "GK", GK_PILLARS),
            "FW": (league_df["Pos"] == "FW", PILLARS_FW),
            "MF": (league_df["Pos"] == "MF", PILLARS_MF),
            "DF": (league_df["Pos"] == "DF", PILLARS_DF),
        }

        for pos, (mask, pillars) in groups.items():
            if mask.any():
                all_frames.append(_score_group(league_df[mask].copy(), pillars))

    return pd.concat(all_frames, ignore_index=True) if all_frames else df


def _parse_age(age_val) -> float:
    """
    Parse FBref Age column to float years.
    FBref format: '25-201' (years-days). Also handles plain '25' or 25 (int/float).
    Returns NaN for unparseable values.
    """
    try:
        s = str(age_val).strip()
        if "-" in s:
            return float(s.split("-")[0])
        return float(s)
    except (ValueError, TypeError):
        return float("nan")


def compute_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """
    UV Score via position-aware regression residuals.

    Fits: log10(market_value) ~ scout_score + position_dummies
    Residual = actual_log_mv − predicted_log_mv
    Negative residual → player is cheaper than expected for their output → undervalued.
    UV Score = percentile rank of (−residual); 100 = most undervalued.
    Value Gap = predicted_mv − actual_mv (€).
    """
    df = df.copy()
    df["market_value_eur"] = pd.to_numeric(df["market_value_eur"], errors="coerce")
    df = df[df["market_value_eur"] > 0].copy()

    log_mv = np.log10(df["market_value_eur"])

    # Position one-hot encoding as regression features alongside scout_score
    pos_dummies = pd.get_dummies(df["Pos"], prefix="pos").astype(float)
    X = pd.concat([df[["scout_score"]].reset_index(drop=True),
                   pos_dummies.reset_index(drop=True)], axis=1).fillna(0)

    reg = LinearRegression().fit(X, log_mv.values)
    df["predicted_log_mv"] = reg.predict(X)
    df["predicted_mv_eur"] = 10 ** df["predicted_log_mv"]

    # Residual: negative = actual price below model expectation = undervalued
    df["residual"]     = log_mv.values - df["predicted_log_mv"]
    df["uv_score"]     = (-df["residual"]).rank(pct=True) * 100
    df["value_gap_eur"] = df["predicted_mv_eur"] - df["market_value_eur"]

    return df.sort_values("uv_score", ascending=False).reset_index(drop=True)


def compute_age_weighted_uv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add uv_score_age_weighted column per SCORE-07.

    Formula:
        age_weight = max(0.0, log(29 - age) / log(12))   # natural log base 12; 0 at age 29+
        multiplier = min(1.5, 1 + 0.30 * age_weight)
        uv_score_age_weighted = uv_score * multiplier

    Age values:
        17 → weight 1.00 → multiplier 1.30
        21 → weight 0.84 → multiplier 1.25
        25 → weight 0.56 → multiplier 1.17
        29+ → weight 0.00 → multiplier 1.00
    """
    import math
    df = df.copy()

    if "Age" not in df.columns or "uv_score" not in df.columns:
        df["uv_score_age_weighted"] = df.get("uv_score", 0.0)
        return df

    def _age_multiplier(age_val: float) -> float:
        age = _parse_age(age_val)
        if np.isnan(age) or age >= 29:
            return 1.0
        delta = 29.0 - age
        if delta <= 0:
            return 1.0
        age_weight = max(0.0, math.log(delta) / math.log(12))
        return min(1.5, 1.0 + 0.30 * age_weight)

    multipliers = df["Age"].apply(_age_multiplier)
    df["uv_score_age_weighted"] = df["uv_score"] * multipliers
    return df


def get_top_undervalued(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    return df.head(n)


def run_scoring_pipeline(fbref_data: dict,
                         tm_data: pd.DataFrame) -> pd.DataFrame:
    """
    Full scoring pipeline: merge FBref tables → scout scores → UV regression → age-weighted UV.

    Args:
        fbref_data: {league: {season: {table_type: DataFrame}}} from run_fbref_scrapers
        tm_data: Transfermarkt DataFrame from run_tm_scrapers
    """
    from merger import build_dataset
    df = build_dataset(fbref_data, tm_data)
    if df.empty:
        return df
    print("[scorer] Applying team strength adjustment (SCORE-04)...")
    df = apply_team_strength_adjustment(df)
    print("[scorer] Computing scout scores...")
    df = compute_scout_scores(df)
    print("[scorer] Computing UV scores (regression on full pool)...")
    df = compute_efficiency(df)   # UV regression — always on full unfiltered pool (SCORE-06)
    print("[scorer] Computing age-weighted UV scores...")
    df = compute_age_weighted_uv(df)
    return df
