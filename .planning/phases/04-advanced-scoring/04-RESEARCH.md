# Phase 4: Advanced Scoring - Research

**Researched:** 2026-03-17
**Domain:** Python scoring pipeline — team-strength adjustment, league quality multiplier, cosine similarity
**Confidence:** HIGH

## Summary

Phase 4 makes three additions to the existing scorer pipeline: a ±10% per-90 stat adjustment for DF/GK players based on their club's league position, a league quality multiplier applied to `uv_score_age_weighted` after the age-weighting step, and a cosine-similarity "similar players" computation stored as a JSON column.

All three changes live in `scorer.py` and `config.py`. One preparatory change in `merger.py` is required first: `Pres` (pressures raw count) must survive cross-season aggregation by adding it to `SUM_STATS` and `PER90_STATS`, and a latent `Succ` column collision between `stats_defense` and `stats_possession` must be fixed by adding `"Succ"` to the `drop_cols` list for the `stats_defense` join. There are no new library dependencies — `sklearn.metrics.pairwise.cosine_similarity` is already available in the project venv (scikit-learn 1.2.2).

The key ordering constraint is that team strength adjustment must precede `compute_scout_scores` (the normalization step), while the league quality multiplier must follow `compute_age_weighted_uv`. Cosine similarity can run last, after all scoring is complete.

**Primary recommendation:** Implement the three new functions — `apply_team_strength_adjustment`, `apply_league_quality_multiplier`, `compute_similar_players` — and insert them into `run_scoring_pipeline` in the order described below.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Team Strength Adjustment (SCORE-04)**
- Magnitude: ±10% (REQUIREMENTS.md SCORE-04 has a typo saying ±20%; ROADMAP success criteria are authoritative)
- Applies to: DF and GK only
- Stats adjusted: `Tkl_p90`, `Int_p90`, `Blocks_p90`, `DuelsWon_p90`, `Pres_p90` (DF); `Save%`, `PSxG/SoT` (GK)
- Direction: bottom-half club (league_position > half of clubs) → +10%; top-half → −10%
- Attacking per-90 stats are never adjusted — FW/MF attacking pillars untouched
- `league_position` column already attached in merger.py; NaN rows skip adjustment

**League Quality Multiplier (SCORE-05)**
- Applied to `uv_score_age_weighted` after `compute_age_weighted_uv()`
- Coefficients: EPL 1.10, LaLiga 1.08, Bundesliga 1.05, SerieA 1.03, Ligue1 1.00
- `uv_score_age_weighted` updated in-place; `league_quality_multiplier` stored as separate column

**Similar Players (SCORE-08)**
- Cosine similarity on 5 `score_*` pillar columns (score_attacking, score_progression, score_creation, score_defense, score_retention)
- Within same position group (GK/FW/MF/DF), across all 5 leagues
- Top 5 per player, self excluded
- Output: `similar_players` JSON column — list of dicts: `[{player, club, league, uv_score_age_weighted}, ...]`

### Claude's Discretion
- Exact formula for bottom-half vs. top-half threshold (e.g., midpoint of total clubs vs. fixed cutoff)
- How to handle NaN league_position (already soft-fails to NaN in merger — skip adjustment)
- How to handle ties in cosine similarity

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCORE-04 | ±10% multiplier on defensive per-90 stats (DF/GK) based on league position | Section: Team Strength Adjustment, Code Examples |
| SCORE-05 | League quality multiplier on `uv_score_age_weighted` using UEFA coefficients | Section: League Quality Multiplier, Code Examples |
| SCORE-08 | Top 5 similar players per player via cosine similarity on score_* columns | Section: Similar Players, Code Examples |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | (project venv) | DataFrame operations, column mutation | Already in use throughout pipeline |
| numpy | (project venv) | Vectorized multiplier computation | Already in use throughout pipeline |
| sklearn.metrics.pairwise.cosine_similarity | scikit-learn 1.2.2 | Pairwise cosine similarity matrix | Already installed; purpose-built for this |
| json (stdlib) | stdlib | Serialize similar_players dicts to JSON string | No install needed |

### No New Dependencies
All required libraries are already in `requirements.txt` and the project venv. Phase 4 adds no new packages.

---

## Architecture Patterns

### Revised Pipeline Order in `run_scoring_pipeline`

```
1. build_dataset(fbref_data, tm_data)           # merger — produces per-90s + league_position
2. apply_team_strength_adjustment(df)           # NEW — mutates _p90/rate stats for DF/GK
3. compute_scout_scores(df)                     # unchanged — normalizes per league+pos group
4. compute_efficiency(df)                       # unchanged — UV regression on full pool
5. compute_age_weighted_uv(df)                  # unchanged — produces uv_score_age_weighted
6. apply_league_quality_multiplier(df)          # NEW — multiplies uv_score_age_weighted
7. compute_similar_players(df)                  # NEW — adds similar_players JSON column
```

Step 2 MUST precede step 3: the team strength adjustment modifies the raw per-90 inputs that `_score_group` normalizes. Applying adjustment after normalization would have no effect.

Step 6 MUST follow step 5: league quality multiplier is applied to `uv_score_age_weighted`.

Step 7 can run last: it reads `score_*` columns (from step 3) and `uv_score_age_weighted` (from step 6).

### Pattern 1: Team Strength Adjustment

**What:** For each DF/GK row, look up `league_position` and apply a scalar multiplier to the listed defensive stats.

**When to use:** Inside `apply_team_strength_adjustment(df)`, called after `build_dataset` and before `compute_scout_scores`.

**Bottom-half threshold:** Use `max(league_position per league) / 2` derived dynamically from the DataFrame — no hardcoded constant needed. This is self-contained and handles both 20-club (EPL/LaLiga/SerieA) and 18-club (Bundesliga/Ligue1) leagues correctly.

**Skip condition:** If `league_position` is NaN, skip that player (consistent with merger soft-fail pattern).

```python
# Conceptual structure (not final implementation)
DF_GK_DEFENSIVE_STATS = ["Tkl_p90", "Int_p90", "Blocks_p90", "DuelsWon_p90", "Pres_p90"]
GK_RATE_STATS = ["Save%", "PSxG/SoT"]
TEAM_STRENGTH_MAGNITUDE = 0.10  # ±10%

def apply_team_strength_adjustment(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for league in df["League"].unique():
        league_mask = df["League"] == league
        league_df = df[league_mask]
        valid_pos = league_df["league_position"].dropna()
        if valid_pos.empty:
            continue
        n_clubs = valid_pos.max()
        threshold = n_clubs / 2
        # DF adjustment
        df_mask = league_mask & (df["Pos"] == "DF") & df["league_position"].notna()
        bottom_half = df_mask & (df["league_position"] > threshold)
        top_half = df_mask & (df["league_position"] <= threshold)
        for col in DF_GK_DEFENSIVE_STATS:
            if col in df.columns:
                df.loc[bottom_half, col] *= (1 + TEAM_STRENGTH_MAGNITUDE)
                df.loc[top_half, col] *= (1 - TEAM_STRENGTH_MAGNITUDE)
        # GK adjustment
        gk_mask = league_mask & (df["Pos"] == "GK") & df["league_position"].notna()
        bottom_gk = gk_mask & (df["league_position"] > threshold)
        top_gk = gk_mask & (df["league_position"] <= threshold)
        for col in GK_RATE_STATS:
            if col in df.columns:
                df.loc[bottom_gk, col] *= (1 + TEAM_STRENGTH_MAGNITUDE)
                df.loc[top_gk, col] *= (1 - TEAM_STRENGTH_MAGNITUDE)
    return df
```

### Pattern 2: League Quality Multiplier

**What:** Multiply `uv_score_age_weighted` by a per-league coefficient; store coefficient as separate column.

**When to use:** After `compute_age_weighted_uv`. The `League` column already exists on every row.

```python
LEAGUE_QUALITY_COEFFICIENTS = {
    "EPL": 1.10,
    "LaLiga": 1.08,
    "Bundesliga": 1.05,
    "SerieA": 1.03,
    "Ligue1": 1.00,
}

def apply_league_quality_multiplier(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["league_quality_multiplier"] = df["League"].map(LEAGUE_QUALITY_COEFFICIENTS).fillna(1.0)
    df["uv_score_age_weighted"] = df["uv_score_age_weighted"] * df["league_quality_multiplier"]
    return df
```

### Pattern 3: Similar Players (Cosine Similarity)

**What:** For each position group, compute pairwise cosine similarity on `score_*` columns. Store top-5 (excluding self) as JSON string in `similar_players` column.

**When to use:** After all scoring is complete (scores finalized, `uv_score_age_weighted` adjusted).

**Tie-breaking:** `np.argsort` is stable — ties are broken by original DataFrame order. This is acceptable behavior; no special tie-breaking required.

```python
from sklearn.metrics.pairwise import cosine_similarity
import json, numpy as np

SCORE_COLS = ["score_attacking", "score_progression", "score_creation", "score_defense", "score_retention"]

def compute_similar_players(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["similar_players"] = None
    for pos in ["GK", "FW", "MF", "DF"]:
        group_mask = df["Pos"] == pos
        group_idx = df.index[group_mask].tolist()
        if len(group_idx) < 2:
            continue
        group_df = df.loc[group_idx]
        matrix = group_df[SCORE_COLS].fillna(0).values
        sim_matrix = cosine_similarity(matrix)
        for i, idx in enumerate(group_idx):
            sims = sim_matrix[i].copy()
            sims[i] = -1  # exclude self
            top5_local = np.argsort(sims)[::-1][:5]
            similar = []
            for j in top5_local:
                peer = group_df.iloc[j]
                similar.append({
                    "player": str(peer["Player"]),
                    "club": str(peer["Squad"]),
                    "league": str(peer["League"]),
                    "uv_score_age_weighted": float(peer["uv_score_age_weighted"]),
                })
            df.at[idx, "similar_players"] = json.dumps(similar)
    return df
```

### Anti-Patterns to Avoid

- **Applying team strength after normalization:** The MinMaxScaler in `_score_group` is fitted on the stats. If you adjust stats after normalization, the adjustment has no effect on the score. Always adjust before `compute_scout_scores`.
- **Adjusting FW/MF attacking stats:** `xG_p90`, `Gls_p90`, `Ast_p90`, `SoT_p90` must not be touched. The adjustment function must explicitly limit to the listed defensive stat columns.
- **Cross-position cosine similarity:** Comparing FW `score_attacking` (weighted 45) to DF `score_attacking` (weighted 10) is meaningless. Scope similarity to same position group only.
- **numpy int64/float64 in JSON:** `np.argsort` indices are `int64`; `uv_score_age_weighted` is `float64`. Wrap with `int()` / `float()` casts if needed — the project venv (numpy) happens to serialize float64 directly, but cast defensively for `int64` indices used for lookup (they're never serialized, so this is not a live issue).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pairwise similarity matrix | Nested loop over player pairs | `sklearn.metrics.pairwise.cosine_similarity` | Returns vectorized NxN matrix in milliseconds; handles edge cases |
| JSON serialization of similar players | Custom dict-to-string formatting | `json.dumps` (stdlib) | Standard, readable, directly parseable by Phase 5 dashboard |
| League size detection | Hardcoded constant dict | `df.groupby("League")["league_position"].max()` | Self-contained; handles any league size without config changes |

---

## Common Pitfalls

### Pitfall 1: `Succ` Column Collision Between `stats_defense` and `stats_possession`

**What goes wrong:** FBref `stats_defense` has a `Succ` column (pressures succeeded). FBref `stats_possession` also has `Succ` (dribbles succeeded). In `merge_fbref_tables`, `stats_defense` is joined before `stats_possession`. The `_join_table` right-cols filter drops columns already in `result`. So `stats_possession.Succ` gets silently dropped, and `DrbSucc%` is computed as `pressure_successes / dribble_attempts` — wrong.

**Why it happens:** The existing `_join_table` for `stats_defense` does not include `"Succ"` in its `drop_cols`. The column only collides when `Pres` is retained (since Pres and Succ appear in the same Pressures section of the defense table).

**How to avoid:** Add `"Succ"` to `drop_cols` in the `stats_defense` `_join_table` call in `merger.py`. This must be done as part of the `Pres` retention task.

**Warning signs:** `DrbSucc%` values that are unusually low (pressure success rate is typically much higher than dribble success rate on a per-possession basis) or a test showing `DrbSucc% = pressure_Succ / Att_drb`.

### Pitfall 2: `Pres` Lost in Cross-Season Aggregation

**What goes wrong:** `Pres` survives the 9-table join (no drop rule for it), but `_aggregate_fbref_seasons` only aggregates columns in `SUM_STATS`. Since `Pres` is not in `SUM_STATS`, the `groupby.agg()` call silently drops it. The resulting DataFrame has no `Pres` column, so `compute_per90s` never produces `Pres_p90`.

**How to avoid:** Add `"Pres"` to `SUM_STATS` in `config.py`. Also add `"Pres"` to `PER90_STATS` so `compute_per90s` auto-produces `Pres_p90`.

### Pitfall 3: Team Strength Applied to Wrong Positions

**What goes wrong:** A loop that iterates over all rows and applies the multiplier without filtering by `Pos` would modify attacking stats for forwards.

**How to avoid:** The adjustment function must gate on `Pos == "DF"` or `Pos == "GK"` before touching any column. Verify ROADMAP success criterion 3: `score_attacking` for forwards must be identical before and after the adjustment step.

### Pitfall 4: League Quality Multiplier Applied Twice

**What goes wrong:** If `run_scoring_pipeline` is called more than once on the same DataFrame (e.g., from a cached result), `uv_score_age_weighted` is multiplied again. Each call compounds the adjustment.

**How to avoid:** `apply_league_quality_multiplier` receives a `.copy()` of the DataFrame; downstream callers should not pass already-scored data back through the full pipeline.

### Pitfall 5: Pillar Weight Sum Broken by Adding `Pres_p90`

**What goes wrong:** `Pres_p90` is added to `_DEFENSE` (the shared dict), causing weights to sum to more than 1.0 and inflating scores for FW and MF defense pillars unexpectedly.

**How to avoid:** `Pres_p90` must be added only to `PILLARS_DF["defense"]["stats"]`, not to the shared `_DEFENSE` dict. Override the `stats` key specifically in `PILLARS_DF`. The DF defense pillar weight rebalancing (proposed: Tkl 0.30, Int 0.25, Blocks 0.20, DuelsWon 0.15, Pres 0.10 — sum 1.00) is the planner's decision.

---

## Code Examples

Verified patterns from source code inspection and venv execution:

### Cosine Similarity Matrix (sklearn 1.2.2)
```python
# Source: verified in project venv
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

matrix = group_df[SCORE_COLS].fillna(0).values  # shape (n_players, 5)
sim_matrix = cosine_similarity(matrix)           # shape (n_players, n_players)
# sim_matrix[i][i] == 1.0 (self-similarity); exclude by setting to -1
sim_matrix_copy = sim_matrix[i].copy()
sim_matrix_copy[i] = -1
top5_indices = np.argsort(sim_matrix_copy)[::-1][:5]
```

Performance: 500 players → cosine_similarity in ~1ms; top-5 extraction for all 500 in ~10ms. Well within acceptable range for pipeline.

### JSON Column Storage Pattern
```python
# Source: verified in project venv — stdlib json handles float correctly
import json
similar_list = [
    {"player": "Name", "club": "Club", "league": "EPL", "uv_score_age_weighted": 92.5},
]
df.at[idx, "similar_players"] = json.dumps(similar_list)
# Phase 5 consumption: json.loads(row["similar_players"])
```

### Merger Fix: stats_defense drop_cols (line ~140 in merger.py)
```python
# BEFORE (current):
_join_table("stats_defense",
            drop_cols=["Tkl.1", "Rk", "Nation", "Comp", "Matches"] + ...)

# AFTER (Phase 4):
_join_table("stats_defense",
            drop_cols=["Tkl.1", "Succ", "Rk", "Nation", "Comp", "Matches"] + ...)
#                       ^^^^^^ ADD THIS — prevents defense.Succ from shadowing possession.Succ
```

### config.py SUM_STATS and PER90_STATS additions
```python
# Add "Pres" to SUM_STATS list
SUM_STATS = [
    ...,
    "Pres",   # pressures raw count from stats_defense — Phase 4
]

# Add "Pres" to PER90_STATS list (auto-produces Pres_p90 in compute_per90s)
PER90_STATS = [
    ...,
    "Pres",   # → Pres_p90
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No team context | ±10% adjustment on DF/GK defensive stats | Phase 4 | Bottom-half defenders get slight inflation; top-half get deflation |
| Raw UV score cross-league | League coefficient multiplied into `uv_score_age_weighted` | Phase 4 | EPL players +10%, Ligue1 players neutral |
| No similarity feature | Cosine similar players JSON column | Phase 4 | Enables Phase 6 Similar Players panel (PROFILE-05) |

**Note on REQUIREMENTS.md correction:** SCORE-04 currently says ±20%; per CONTEXT.md this is a typo. REQUIREMENTS.md should be updated to ±10% as part of this phase.

---

## Open Questions

1. **Whether `Pres_p90` should be in `PILLARS_DF["defense"]["stats"]`**
   - What we know: CONTEXT says retain `Pres` and add to `SUM_STATS`. The team strength adjustment adjusts `Pres_p90` before scoring.
   - What's unclear: If `Pres_p90` is not in any pillar, adjusting it has zero effect on the score. CONTEXT implies it should influence the score.
   - Recommendation: Add `Pres_p90` to `PILLARS_DF["defense"]["stats"]` with weight 0.10, reducing Tkl to 0.30 and Int to 0.25. Keep `_DEFENSE` shared dict unchanged so FW/MF defense pillars are unaffected.

2. **Whether to also adjust `Pres_p90` for GK**
   - What we know: CONTEXT lists "pressures" in the stats adjusted for DF, and `Save%`/`PSxG/SoT` for GK.
   - What's unclear: Is `Pres_p90` also adjusted for GK sweeping pillar?
   - Recommendation: Only adjust `Save%` and `PSxG/SoT` for GK (as stated in CONTEXT). `Pres_p90` is DF-only.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project venv) |
| Config file | none — run from project root |
| Quick run command | `python -m pytest test_scorer.py test_merger.py -q` |
| Full suite command | `python -m pytest test_scorer.py test_merger.py test_scraper.py -q` |

Note: `test_scraper.py` currently errors on collection due to missing `curl_cffi` module. Scorer and merger tests are the relevant suite for Phase 4. Current passing: 26 tests in test_scorer.py + test_merger.py.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCORE-04 | Bottom-half DF gets higher adjusted defensive pillar score than identical stats at top-half club | unit | `python -m pytest test_scorer.py::test_team_strength_bottom_half_inflates_df_score -x` | ❌ Wave 0 |
| SCORE-04 | FW `score_attacking` unchanged by team strength step | unit | `python -m pytest test_scorer.py::test_team_strength_does_not_affect_fw_attacking -x` | ❌ Wave 0 |
| SCORE-04 | NaN `league_position` → no adjustment applied | unit | `python -m pytest test_scorer.py::test_team_strength_skips_nan_league_position -x` | ❌ Wave 0 |
| SCORE-04 | `Pres_p90` present after merger (Pres in SUM_STATS) | unit | `python -m pytest test_merger.py::test_pres_p90_present_after_per90s -x` | ❌ Wave 0 |
| SCORE-04 | `defense.Succ` drop fix: DrbSucc% uses possession Succ not defense Succ | unit | `python -m pytest test_merger.py::test_drbsucc_uses_possession_succ -x` | ❌ Wave 0 |
| SCORE-05 | EPL player has `league_quality_multiplier` == 1.10 | unit | `python -m pytest test_scorer.py::test_league_quality_multiplier_values -x` | ❌ Wave 0 |
| SCORE-05 | `uv_score_age_weighted` increased by multiplier (EPL vs Ligue1 parity case) | unit | `python -m pytest test_scorer.py::test_league_quality_multiplier_applied_in_place -x` | ❌ Wave 0 |
| SCORE-08 | `similar_players` column exists and is valid JSON | unit | `python -m pytest test_scorer.py::test_similar_players_column_is_valid_json -x` | ❌ Wave 0 |
| SCORE-08 | Top-5 similar players are all same position group | unit | `python -m pytest test_scorer.py::test_similar_players_same_position_group -x` | ❌ Wave 0 |
| SCORE-08 | Player not in their own similar list | unit | `python -m pytest test_scorer.py::test_similar_players_excludes_self -x` | ❌ Wave 0 |
| SCORE-08 | Similar players can span multiple leagues | unit | `python -m pytest test_scorer.py::test_similar_players_cross_league -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest test_scorer.py test_merger.py -q`
- **Per wave merge:** `python -m pytest test_scorer.py test_merger.py -q`
- **Phase gate:** Full scorer + merger suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `test_merger.py` — add `test_pres_p90_present_after_per90s` and `test_drbsucc_uses_possession_succ` stubs
- [ ] `test_scorer.py` — add stubs for all SCORE-04, SCORE-05, SCORE-08 tests listed above

*(Existing test infrastructure covers prior requirements; only new stubs needed for Phase 4 requirements.)*

---

## Sources

### Primary (HIGH confidence)
- Source code inspection: `scorer.py`, `config.py`, `merger.py` — read directly from project root
- Venv execution: `sklearn.metrics.pairwise.cosine_similarity` verified working (scikit-learn 1.2.2)
- Venv execution: `json.dumps` verified working with float values
- Venv execution: Succ column collision between stats_defense and stats_possession reproduced and confirmed

### Secondary (MEDIUM confidence)
- FBref stats_defense column structure (Pressures section: Pres, Succ, %) — based on FBref table layout knowledge cross-referenced with CONTEXT.md description of available columns

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified in project venv, no new dependencies
- Architecture: HIGH — pipeline ordering confirmed from code inspection; cosine similarity prototype executed
- Pitfalls: HIGH — Succ collision reproduced in actual merger code; Pres aggregation gap confirmed

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable domain — no external API changes; internal code only)
