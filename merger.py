"""
merger.py — Merges Understat + API-Football stats across seasons,
then attaches Transfermarkt market values via fuzzy name matching.
"""

import unicodedata
import numpy as np
import pandas as pd
from rapidfuzz import process, fuzz

from config import SUM_STATS, MEAN_STATS, PER90_STATS, MIN_MINUTES, MIN_MINUTES_PER_SEASON, FUZZY_THRESHOLD


# ── Name normalisation ────────────────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """Strip accents, lowercase, collapse whitespace."""
    if not isinstance(name, str):
        return ""
    nfd = unicodedata.normalize("NFD", name)
    ascii_name = nfd.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_name.lower().split())


# ── Season aggregation ────────────────────────────────────────────────────────

def _aggregate_seasons(data: dict, sum_cols: list, mean_cols: list) -> pd.DataFrame:
    """
    Concatenate per-season DataFrames and aggregate by Player.
    data: {season_label: DataFrame}
    """
    frames = [df for df in data.values() if not df.empty]
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)

    # Convert all numeric columns
    skip = {"Player", "Squad", "Pos", "season"}
    for col in combined.columns:
        if col not in skip:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    agg = {}
    for col in sum_cols:
        if col in combined.columns:
            agg[col] = "sum"
    for col in mean_cols:
        if col in combined.columns:
            agg[col] = "mean"
    agg["Squad"] = "last"
    agg["Pos"]   = "last"

    return combined.groupby("Player", as_index=False).agg(agg)


def aggregate_understat(data: dict, min_minutes: int = MIN_MINUTES) -> pd.DataFrame:
    """Aggregate Understat seasons into a single per-player DataFrame."""
    from config import UNDERSTAT_SUM
    df = _aggregate_seasons(data, sum_cols=UNDERSTAT_SUM, mean_cols=[])
    if df.empty:
        return df

    # Minimum minutes filter
    df = df[df["Min"].fillna(0) >= min_minutes].copy()
    return df.reset_index(drop=True)


def aggregate_api_football(data: dict) -> pd.DataFrame:
    """Aggregate API-Football seasons into a single per-player DataFrame."""
    from config import API_FOOTBALL_SUM
    return _aggregate_seasons(data, sum_cols=API_FOOTBALL_SUM, mean_cols=MEAN_STATS)


# ── Merge the two stat sources ────────────────────────────────────────────────

def merge_stat_sources(understat_df: pd.DataFrame,
                       api_df: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join API-Football physical stats onto Understat base.
    Uses fuzzy name matching where exact match fails.
    Understat is authoritative for minutes and the min-minutes filter.
    """
    if understat_df.empty:
        return understat_df

    if api_df.empty:
        # Return understat only — defense/retention pillars will score 0
        return understat_df

    base = understat_df.copy()
    af   = api_df.copy()

    base["_norm"] = base["Player"].apply(normalize_name)
    af["_norm"]   = af["Player"].apply(normalize_name)

    # Build lookup: norm_name → row index in af
    af_lookup = {row["_norm"]: idx for idx, row in af.iterrows()}
    af_norms  = list(af_lookup.keys())

    af_cols = [c for c in af.columns if c not in ("Player", "Squad", "Pos", "season", "_norm")]

    matched_rows = []
    for _, row in base.iterrows():
        norm = row["_norm"]
        # Pass 1: exact
        idx = af_lookup.get(norm)
        if idx is None:
            # Pass 2: fuzzy
            result = process.extractOne(norm, af_norms, scorer=fuzz.WRatio,
                                        score_cutoff=FUZZY_THRESHOLD)
            if result:
                idx = af_lookup[result[0]]

        if idx is not None:
            matched_rows.append({col: af.at[idx, col] for col in af_cols})
        else:
            matched_rows.append({col: np.nan for col in af_cols})

    af_matched = pd.DataFrame(matched_rows, index=base.index)
    merged = pd.concat([base.drop(columns=["_norm"]), af_matched], axis=1)
    return merged.reset_index(drop=True)


# ── Per-90 derivations ────────────────────────────────────────────────────────

def compute_per90s(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if "Min" not in df.columns:
        return df
    min_col = pd.to_numeric(df["Min"], errors="coerce").replace(0, np.nan)

    for stat in PER90_STATS:
        if stat in df.columns:
            df[f"{stat}_p90"] = pd.to_numeric(df[stat], errors="coerce") / min_col * 90

    # Duel win rate (retention pillar)
    if "DuelsWon" in df.columns and "DuelsTotal" in df.columns:
        total = pd.to_numeric(df["DuelsTotal"], errors="coerce").replace(0, np.nan)
        df["DuelsWon%"] = pd.to_numeric(df["DuelsWon"], errors="coerce") / total * 100

    # GK save percentage: saves / (saves + goals_conceded).
    # Rewards shot-stopping quality independent of team defensive strength.
    if "Saves" in df.columns and "GoalsConceded" in df.columns:
        saves    = pd.to_numeric(df["Saves"],         errors="coerce").fillna(0)
        conceded = pd.to_numeric(df["GoalsConceded"], errors="coerce").fillna(0)
        shots_faced = (saves + conceded).replace(0, np.nan)
        df["SavePct"] = saves / shots_faced * 100

    return df


# ── Market value matching ─────────────────────────────────────────────────────

def match_market_values(df: pd.DataFrame, tm_df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach Transfermarkt market values via two-pass name matching:
      Pass 1: Exact match on normalized name
      Pass 2: rapidfuzz WRatio >= FUZZY_THRESHOLD
    """
    if tm_df.empty:
        df["market_value_eur"] = float("nan")
        return df

    df = df.copy()
    tm = tm_df.copy()

    df["_norm"] = df["Player"].apply(normalize_name)
    tm["_norm"] = tm["player_name_tm"].apply(normalize_name)

    tm_lookup = dict(zip(tm["_norm"], tm["market_value_eur"]))
    tm_norms  = list(tm_lookup.keys())

    # Pass 1
    df["market_value_eur"] = df["_norm"].map(tm_lookup)

    # Pass 2
    unmatched = df["market_value_eur"].isna()
    for idx, row in df[unmatched].iterrows():
        result = process.extractOne(
            row["_norm"], tm_norms,
            scorer=fuzz.WRatio,
            score_cutoff=FUZZY_THRESHOLD,
        )
        if result:
            df.at[idx, "market_value_eur"] = tm_lookup[result[0]]

    df.drop(columns=["_norm"], inplace=True)
    return df


# ── Main pipeline ─────────────────────────────────────────────────────────────

def build_dataset(understat_data: dict,
                  api_data: dict,
                  tm_data: pd.DataFrame) -> pd.DataFrame:
    """Full merge pipeline: aggregate → merge sources → per-90s → market values."""
    print("[merger] Aggregating Understat seasons...")
    n_seasons = max(1, len(understat_data))
    min_min = MIN_MINUTES_PER_SEASON * n_seasons
    print(f"  Min minutes threshold: {min_min} ({n_seasons} season(s) × {MIN_MINUTES_PER_SEASON})")
    us_df = aggregate_understat(understat_data, min_minutes=min_min)
    print(f"  Players after min-minutes filter: {len(us_df)}")

    # Keep only players currently in the EPL (appeared in 2025-26 season)
    current_season = understat_data.get("2025-26")
    if current_season is not None and not current_season.empty:
        current_players = set(current_season["Player"])
        us_df = us_df[us_df["Player"].isin(current_players)].copy().reset_index(drop=True)
        print(f"  After current-season filter: {len(us_df)}")

    print("[merger] Aggregating API-Football seasons...")
    af_df = aggregate_api_football(api_data)
    print(f"  API-Football players: {len(af_df)}")

    print("[merger] Merging stat sources...")
    df = merge_stat_sources(us_df, af_df)

    print("[merger] Computing per-90 stats...")
    df = compute_per90s(df)

    print("[merger] Matching market values...")
    df = match_market_values(df, tm_data)
    matched = df["market_value_eur"].notna().sum()
    print(f"  Market values matched: {matched}/{len(df)}")

    return df
