"""
merger.py — Joins 9 FBref stat tables into one player DataFrame per season,
aggregates across seasons, and attaches Transfermarkt market values.
"""

import unicodedata
import numpy as np
import pandas as pd
from rapidfuzz import process, fuzz

from config import SUM_STATS, MEAN_STATS, PER90_STATS, MIN_MINUTES, MIN_MINUTES_PER_SEASON, FUZZY_THRESHOLD, FUZZY_THRESHOLD_PASS3


# ── Name normalisation ────────────────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """Strip accents, lowercase, collapse whitespace."""
    if not isinstance(name, str):
        return ""
    nfd = unicodedata.normalize("NFD", name)
    ascii_name = nfd.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_name.lower().split())


def normalize_club(name: str) -> str:
    """
    Normalize club name for cross-check in Pass 3 TM matching.
    Strips accents, lowercases, removes common prefixes/suffixes:
    FC, CF, AFC (e.g. 'FC Barcelona' → 'barcelona', 'Arsenal AFC' → 'arsenal').
    """
    import re
    if not isinstance(name, str):
        return ""
    nfd = unicodedata.normalize("NFD", name)
    ascii_name = nfd.encode("ascii", "ignore").decode("ascii")
    normalized = " ".join(ascii_name.lower().split())
    # Strip leading/trailing FC, CF, AFC (with or without dot)
    normalized = re.sub(r'\bfc\.?\b', '', normalized).strip()
    normalized = re.sub(r'\bcf\.?\b', '', normalized).strip()
    normalized = re.sub(r'\bafc\.?\b', '', normalized).strip()
    return " ".join(normalized.split())  # collapse any extra whitespace


# ── Multi-club deduplication ──────────────────────────────────────────────────

def _deduplicate_multiclub(df: pd.DataFrame) -> pd.DataFrame:
    """
    For players who transferred mid-season, FBref has both per-club rows AND a
    season-total row where Squad is '2 Clubs' (or '2 teams' in some seasons).
    Keep ONLY the season-total row for those players; drop per-club rows.
    Players with a single club keep their single row.
    """
    if df.empty:
        return df

    def _is_summary(squad: str) -> bool:
        if not isinstance(squad, str):
            return False
        import re
        return bool(re.match(r"^\d+\s+[Cc]lub", squad) or re.match(r"^\d+\s+[Tt]eam", squad))

    has_summary = df.groupby("Player")["Squad"].transform(
        lambda x: x.apply(_is_summary).any()
    )
    # Keep the summary row for players who have one; keep everything for others
    keep = ~has_summary | df["Squad"].apply(_is_summary)
    return df[keep].reset_index(drop=True)


# ── Single-season 9-table join ────────────────────────────────────────────────

def merge_fbref_tables(season_data: dict) -> pd.DataFrame:
    """
    Join 9 FBref tables for a single season into one wide row per player.

    season_data: {table_type: DataFrame}
    Returns: one row per player with all columns; missing tables fill with NaN.

    Key collision handling per RESEARCH.md:
    - PrgC: use stats_possession as canonical; drop PrgC from stats_standard
    - PrgP: use stats_passing as canonical; drop PrgP from stats_standard
    - xAG: drop from stats_passing (same as xA from stats_standard, already renamed)
    - Att: rename stats_possession Att → Att_drb before join (dribble attempts)
    - Won/Lost (stats_misc aerial): rename → AerWon, AerLost immediately post-join
    - Tkl: use first (unsuffixed) from stats_defense = total tackles; drop Tkl.1
    - Cmp%: use first (unsuffixed) from stats_passing = overall completion rate
    """
    join_key = ["Player", "Squad", "Pos", "Age"]

    # ── stats_standard (base table) ──────────────────────────────────────────
    base = season_data.get("stats_standard", pd.DataFrame())
    if base.empty:
        return pd.DataFrame()

    base = _deduplicate_multiclub(base.copy())

    # Drop pre-computed per-90 columns (suffixed duplicates) from stats_standard
    drop_standard = [c for c in base.columns if c.endswith(".1") or c.endswith(".2")]
    # Also drop PrgC and PrgP from standard — possession and passing are canonical
    drop_standard += [c for c in ["PrgC", "PrgP"] if c in base.columns]
    base = base.drop(columns=[c for c in drop_standard if c in base.columns])

    result = base.copy()

    # ── Helper: left-join one table ───────────────────────────────────────────
    def _join_table(table_type: str, drop_cols: list = None, rename_cols: dict = None):
        nonlocal result
        df = season_data.get(table_type, pd.DataFrame())
        if df.empty:
            return
        df = _deduplicate_multiclub(df.copy())

        # Drop unwanted columns before join
        if drop_cols:
            df = df.drop(columns=[c for c in drop_cols if c in df.columns])
        # Rename columns before join to avoid collisions
        if rename_cols:
            df = df.rename(columns=rename_cols)

        # Remove join keys from right side (keep only new stat cols + join key)
        right_cols = join_key + [c for c in df.columns if c not in result.columns and c not in join_key]
        df = df[[c for c in right_cols if c in df.columns]]

        result = result.merge(df, on=join_key, how="left")

    # ── stats_shooting ────────────────────────────────────────────────────────
    _join_table("stats_shooting",
                drop_cols=["Gls", "xG", "Rk", "Nation", "Comp", "Matches"] +
                          [c for c in season_data.get("stats_shooting", pd.DataFrame()).columns
                           if c.endswith(".1") or c.endswith(".2")])

    # ── stats_passing ─────────────────────────────────────────────────────────
    _join_table("stats_passing",
                drop_cols=["xAG",  # same as xA in stats_standard; drop to avoid duplicate
                           "Rk", "Nation", "Comp", "Matches", "Ast"] +
                          [c for c in season_data.get("stats_passing", pd.DataFrame()).columns
                           if c.endswith(".1") or c.endswith(".2") or c.endswith(".3")])

    # ── stats_defense ─────────────────────────────────────────────────────────
    _join_table("stats_defense",
                drop_cols=["Tkl.1", "Succ", "Rk", "Nation", "Comp", "Matches"] +
                          [c for c in season_data.get("stats_defense", pd.DataFrame()).columns
                           if c.endswith(".1") or c.endswith(".2")])

    # ── stats_possession ─────────────────────────────────────────────────────
    _join_table("stats_possession",
                drop_cols=["Rk", "Nation", "Comp", "Matches"],
                rename_cols={"Att": "Att_drb"})   # dribble attempts → Att_drb

    # ── stats_misc ────────────────────────────────────────────────────────────
    _join_table("stats_misc",
                drop_cols=["Rk", "Nation", "Comp", "Matches", "Won%"],
                rename_cols={"Won": "AerWon", "Lost": "AerLost"})

    # ── stats_gca ─────────────────────────────────────────────────────────────
    _join_table("stats_gca",
                drop_cols=["SCA90", "GCA", "GCA90", "Rk", "Nation", "Comp", "Matches"] +
                          [c for c in season_data.get("stats_gca", pd.DataFrame()).columns
                           if c.endswith(".1")])

    # ── stats_keeper ─────────────────────────────────────────────────────────
    _join_table("stats_keeper",
                drop_cols=["MP", "Starts", "Min", "90s", "GA90", "CS%", "Rk", "Nation",
                           "Comp", "Matches", "W", "D", "L"])

    # ── stats_keeper_adv ─────────────────────────────────────────────────────
    _join_table("stats_keeper_adv",
                drop_cols=["GA", "Rk", "Nation", "Comp", "Matches",
                           "Cmp%",   # keeper_adv Cmp% = launched passes only; use passing Cmp%
                           "PSxG+/-", "/90"] +
                          [c for c in season_data.get("stats_keeper_adv", pd.DataFrame()).columns
                           if c.endswith(".1") or c.endswith(".2")])

    return result


# ── Cross-season aggregation ──────────────────────────────────────────────────

def _aggregate_fbref_seasons(fbref_league_data: dict) -> pd.DataFrame:
    """
    Aggregate across seasons for one league.

    fbref_league_data: {season_label: {table_type: DataFrame}}
    Returns: one row per player, summed raw counts, re-derived rate stats.
    """
    season_frames = []
    for season_label, season_data in fbref_league_data.items():
        df = merge_fbref_tables(season_data)
        if not df.empty:
            df["_season"] = season_label
            season_frames.append(df)

    if not season_frames:
        return pd.DataFrame()

    combined = pd.concat(season_frames, ignore_index=True)

    # Convert all numeric columns
    id_cols = {"Player", "Squad", "Pos", "Age", "_season"}
    for col in combined.columns:
        if col not in id_cols:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    # Build aggregation dict
    agg = {}
    for col in SUM_STATS:
        if col in combined.columns:
            agg[col] = "sum"
    agg["Squad"] = "last"
    agg["Pos"]   = "last"
    agg["Age"]   = "last"

    grouped = combined.groupby("Player", as_index=False).agg(agg)

    # Re-derive rate stats from summed counts
    # Cmp% = sum(Cmp) / sum(Att) * 100  (total pass completion)
    if "Cmp" in grouped.columns and "Att" in grouped.columns:
        att = grouped["Att"].replace(0, np.nan)
        grouped["Cmp%"] = grouped["Cmp"] / att * 100

    # DrbSucc% = sum(Succ) / sum(Att_drb) * 100
    if "Succ" in grouped.columns and "Att_drb" in grouped.columns:
        att_drb = grouped["Att_drb"].replace(0, np.nan)
        grouped["DrbSucc%"] = grouped["Succ"] / att_drb * 100

    # DuelsWon% = AerWon / (AerWon + AerLost) * 100
    if "AerWon" in grouped.columns and "AerLost" in grouped.columns:
        total_aerial = (grouped["AerWon"] + grouped["AerLost"]).replace(0, np.nan)
        grouped["DuelsWon%"] = grouped["AerWon"] / total_aerial * 100

    # Save% = Saves / (Saves + GA) * 100  (GK only — others will be NaN)
    if "Saves" in grouped.columns and "GA" in grouped.columns:
        shots_faced = (grouped["Saves"] + grouped["GA"]).replace(0, np.nan)
        grouped["Save%"] = grouped["Saves"] / shots_faced * 100

    # PSxG/SoT = sum(PSxG) / sum(SoTA)  (GK only)
    if "PSxG" in grouped.columns and "SoTA" in grouped.columns:
        sota = grouped["SoTA"].replace(0, np.nan)
        grouped["PSxG/SoT"] = grouped["PSxG"] / sota

    # single_season flag: True if player only appeared in one season
    season_count = combined.groupby("Player")["_season"].nunique()
    grouped["single_season"] = grouped["Player"].map(season_count) == 1

    return grouped


# ── Per-90 derivations ────────────────────────────────────────────────────────

def compute_per90s(df: pd.DataFrame) -> pd.DataFrame:
    """Derive _p90 columns from raw counts and total Min."""
    if df.empty:
        return df
    if "Min" not in df.columns:
        return df
    df = df.copy()
    min_col = pd.to_numeric(df["Min"], errors="coerce").replace(0, np.nan)

    for stat in PER90_STATS:
        if stat in df.columns:
            df[f"{stat}_p90"] = pd.to_numeric(df[stat], errors="coerce") / min_col * 90

    # Alias: DuelsWon_p90 from AerWon (aerial duels won per 90)
    if "AerWon" in df.columns:
        df["DuelsWon_p90"] = pd.to_numeric(df["AerWon"], errors="coerce") / min_col * 90

    return df


# ── Primary position extraction ───────────────────────────────────────────────

def extract_primary_position(df: pd.DataFrame) -> pd.DataFrame:
    """Convert 'DF,MF' → 'DF'; 'GK' → 'GK'. Takes first token of comma-separated Pos."""
    df = df.copy()
    df["Pos"] = df["Pos"].astype(str).str.split(",").str[0].str.strip()
    return df


# ── League position attachment ────────────────────────────────────────────────

def attach_league_position(df: pd.DataFrame, league: str = "EPL",
                           season: str = "2024-25") -> pd.DataFrame:
    """
    Attach league_position column by joining on Squad.
    Multi-club players (Squad contains digit + 'Club'/'team') get NaN.
    Calls scrape_fbref_standings — uses cache on warm runs.
    """
    from scraper import scrape_fbref_standings, _fbref_cache_path, _is_fresh
    # Only use cached standings — never launch a browser from within the pipeline.
    # Standings are pre-populated by running `python scraper.py`.
    if not _is_fresh(_fbref_cache_path(league, "standings", season)):
        df = df.copy()
        df["league_position"] = np.nan
        return df
    try:
        standings = scrape_fbref_standings(league, season)
    except Exception as e:
        print(f"  [merger] Warning: standings scrape failed ({e}); league_position will be NaN")
        df = df.copy()
        df["league_position"] = np.nan
        return df

    df = df.copy()
    squad_to_pos = dict(zip(standings["Squad"], standings["Rk"]))
    df["league_position"] = df["Squad"].map(squad_to_pos)
    # Multi-club players won't match any squad → NaN (correct behaviour)
    return df


# ── Market value matching ─────────────────────────────────────────────────────

def match_market_values(df: pd.DataFrame, tm_df: pd.DataFrame) -> pd.DataFrame:
    """Attach Transfermarkt market values via two-pass name matching."""
    if tm_df.empty:
        df = df.copy()
        df["market_value_eur"] = float("nan")
        return df

    df = df.copy()
    tm = tm_df.copy()

    df["_norm"] = df["Player"].apply(normalize_name)
    tm["_norm"] = tm["player_name_tm"].apply(normalize_name)

    tm_lookup = dict(zip(tm["_norm"], tm["market_value_eur"]))
    tm_norms  = list(tm_lookup.keys())

    df["market_value_eur"] = df["_norm"].map(tm_lookup)

    # Build TM club lookup for Pass 3 cross-check (graceful if club_tm column absent)
    tm_club_lookup = dict(zip(tm["_norm"], tm["club_tm"])) if "club_tm" in tm.columns else {}

    # Pass 2: Fuzzy WRatio >= FUZZY_THRESHOLD (80)
    unmatched = df["market_value_eur"].isna()
    for idx, row in df[unmatched].iterrows():
        result = process.extractOne(
            row["_norm"], tm_norms,
            scorer=fuzz.WRatio,
            score_cutoff=FUZZY_THRESHOLD,
        )
        if result:
            df.at[idx, "market_value_eur"] = tm_lookup[result[0]]

    # Pass 3: Fuzzy WRatio >= FUZZY_THRESHOLD_PASS3 (70) + club name must match
    # For players still unmatched, accept a lower-confidence name match ONLY if
    # the TM club name also matches the FBref Squad after normalization.
    unmatched_p3 = df["market_value_eur"].isna()
    squad_col = "Squad" if "Squad" in df.columns else None
    if squad_col:
        for idx, row in df[unmatched_p3].iterrows():
            result = process.extractOne(
                row["_norm"], tm_norms,
                scorer=fuzz.WRatio,
                score_cutoff=FUZZY_THRESHOLD_PASS3,
            )
            if result:
                candidate_norm = result[0]
                # Only accept if club names match after normalization
                fbref_club = normalize_club(str(row.get(squad_col, "")))
                tm_club = normalize_club(str(tm_club_lookup.get(candidate_norm, "")))
                if fbref_club and tm_club and fbref_club == tm_club:
                    df.at[idx, "market_value_eur"] = tm_lookup[candidate_norm]

    df.drop(columns=["_norm"], inplace=True)
    return df


# ── Understat xG/xA join ──────────────────────────────────────────────────────

def attach_understat_xg(df: pd.DataFrame, understat_data: dict) -> pd.DataFrame:
    """
    Join Understat xG and xA onto the FBref merged DataFrame.

    Strategy:
    - Aggregate understat_data across all seasons per player per league (sum xG, xA, Min)
    - Pass 1: exact match on normalized Player name within same League
    - Pass 2: rapidfuzz WRatio >= FUZZY_THRESHOLD for still-unmatched players (same League)
    - Unmatched players get NaN for xG/xA — NOT dropped
    - Logs WARNING if match rate < 70% for any league

    Args:
        df:             FBref merged DataFrame (one row per player, already aggregated
                        across seasons). Must have "Player" and "League" columns.
        understat_data: {league: {season_label: DataFrame}} from run_understat_scrapers().
                        Each inner DataFrame has Player, Squad, xG, xA, Min columns.

    Returns:
        Copy of df with "xG" and "xA" columns added (NaN for unmatched players).
    """
    import logging

    if not understat_data:
        df = df.copy()
        df["xG"] = float("nan")
        df["xA"] = float("nan")
        return df

    df = df.copy()
    df["xG"] = float("nan")
    df["xA"] = float("nan")

    # Process each league independently
    for league in (df["League"].unique() if "League" in df.columns else []):
        # Collect all seasons for this league into one DataFrame
        league_frames = []
        league_seasons = understat_data.get(league, {})
        for season_label, season_df in league_seasons.items():
            if not season_df.empty:
                league_frames.append(season_df)

        if not league_frames:
            continue

        # Aggregate across seasons: sum xG and xA per player
        us_combined = pd.concat(league_frames, ignore_index=True)
        # Ensure numeric
        us_combined["xG"] = pd.to_numeric(us_combined["xG"], errors="coerce").fillna(0)
        us_combined["xA"] = pd.to_numeric(us_combined["xA"], errors="coerce").fillna(0)

        us_agg = (
            us_combined
            .groupby("Player", as_index=False)
            .agg({"xG": "sum", "xA": "sum"})
        )

        # Normalize names for matching
        us_agg["_norm"] = us_agg["Player"].apply(normalize_name)
        us_lookup_xg = dict(zip(us_agg["_norm"], us_agg["xG"]))
        us_lookup_xa = dict(zip(us_agg["_norm"], us_agg["xA"]))
        us_norms = list(us_lookup_xg.keys())

        league_mask = df["League"] == league
        df.loc[league_mask, "_norm"] = df.loc[league_mask, "Player"].apply(normalize_name)

        # Pass 1: exact name match
        df.loc[league_mask, "xG"] = df.loc[league_mask, "_norm"].map(us_lookup_xg)
        df.loc[league_mask, "xA"] = df.loc[league_mask, "_norm"].map(us_lookup_xa)

        # Pass 2: fuzzy WRatio >= FUZZY_THRESHOLD for still-unmatched players.
        # Secondary gate: token_sort_ratio >= 60 prevents false positives where
        # one name is a substring of another (e.g. "Known Player" inside "Unknown Player").
        _FUZZY_TOKEN_SORT_MIN = 60
        still_unmatched = league_mask & df["xG"].isna()
        for idx, row in df[still_unmatched].iterrows():
            query = row.get("_norm", "")
            if not query:
                continue
            result = process.extractOne(
                query, us_norms,
                scorer=fuzz.WRatio,
                score_cutoff=FUZZY_THRESHOLD,
            )
            if result:
                matched_norm = result[0]
                # Reject if token-sorted similarity is too low (substring containment false positive)
                if fuzz.token_sort_ratio(query, matched_norm) < _FUZZY_TOKEN_SORT_MIN:
                    continue
                df.at[idx, "xG"] = us_lookup_xg[matched_norm]
                df.at[idx, "xA"] = us_lookup_xa.get(matched_norm, float("nan"))

        # Log warning if match rate < 70%
        total_league = league_mask.sum()
        matched_league = (league_mask & df["xG"].notna()).sum()
        match_rate = matched_league / total_league if total_league > 0 else 0
        if match_rate < 0.70:
            logging.warning(
                f"[merger] Understat match rate for {league} is {match_rate:.1%} "
                f"({matched_league}/{total_league} players). "
                "Check for name format changes or missing Understat coverage."
            )

    # Clean up temp column
    if "_norm" in df.columns:
        df.drop(columns=["_norm"], inplace=True)

    return df


# ── Main pipeline ─────────────────────────────────────────────────────────────

def build_dataset(fbref_data: dict, tm_data: pd.DataFrame) -> pd.DataFrame:
    """
    Full merge pipeline: 9-table join → cross-season aggregation → filters →
    per-90s → league position → market values.

    fbref_data: {league: {season: {table_type: DataFrame}}}
    tm_data: Transfermarkt DataFrame with player_name_tm and market_value_eur
    """
    all_frames = []

    for league, league_data in fbref_data.items():
        print(f"[merger] Processing {league} ({len(league_data)} seasons)...")
        df = _aggregate_fbref_seasons(league_data)
        if df.empty:
            print(f"  No data for {league}")
            continue

        # Primary position extraction: 'DF,MF' → 'DF'
        df = extract_primary_position(df)

        # 1. Min-minutes filter: 1800 total minutes (900 × 2 seasons)
        min_threshold = MIN_MINUTES_PER_SEASON * len(league_data)
        df = df[df["Min"].fillna(0) >= min_threshold].copy().reset_index(drop=True)
        print(f"  After {min_threshold}-min filter: {len(df)} players")

        # 2. Current-season filter: keep only players active in most recent season
        seasons_sorted = sorted(league_data.keys(), reverse=True)
        current_season = seasons_sorted[0]
        current_season_data = league_data.get(current_season, {})
        current_standard = current_season_data.get("stats_standard", pd.DataFrame())
        if not current_standard.empty:
            current_players = set(current_standard["Player"].dropna())
            df = df[df["Player"].isin(current_players)].copy().reset_index(drop=True)
            print(f"  After current-season ({current_season}) filter: {len(df)} players")

        # 3. Per-90 derivations
        df = compute_per90s(df)

        # 4. League position (uses scrape_fbref_standings with cache)
        df = attach_league_position(df, league=league, season=current_season)

        df["League"] = league
        all_frames.append(df)

    if not all_frames:
        return pd.DataFrame()

    combined = pd.concat(all_frames, ignore_index=True)

    print("[merger] Matching market values...")
    combined = match_market_values(combined, tm_data)
    matched = combined["market_value_eur"].notna().sum()
    print(f"  Market values matched: {matched}/{len(combined)}")

    return combined
