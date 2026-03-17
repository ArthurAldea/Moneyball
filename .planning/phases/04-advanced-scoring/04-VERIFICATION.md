---
phase: 04-advanced-scoring
verified: 2026-03-17T00:00:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
human_verification:
  - test: "Run the full pipeline end-to-end with live or cached FBref data"
    expected: "similar_players column present on every row; EPL players show ~10% higher uv_score_age_weighted than equivalent Ligue1 players; bottom-half DFs show inflated Tkl_p90 vs top-half DFs at same raw stat"
    why_human: "Pipeline wiring verified by test, but behavioral correctness on real FBref data (which has multi-column Succ naming in the wild) can only be confirmed with an actual scrape run"
---

# Phase 4: Advanced Scoring Verification Report

**Phase Goal:** Apply the ±10% team strength adjustment to defensive per-90 stats (DF and GK only) based on league position; apply UEFA-coefficient league quality multiplier to uv_score_age_weighted after scoring; compute cosine-similarity similar players (top 5 per player, same position group, cross-league) stored as a JSON column.
**Verified:** 2026-03-17
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SCORE-04 | 04-01-PLAN.md | Team strength adjustment ±10% on DF/GK defensive per-90 stats | SATISFIED | `apply_team_strength_adjustment` in scorer.py (line 37); wired in `run_scoring_pipeline` (line 342) before `compute_scout_scores`; 5 stats adjusted; 3 passing tests confirm behavior |
| SCORE-05 | 04-02-PLAN.md | League quality multiplier applied to uv_score_age_weighted after age-weighting | SATISFIED | `apply_league_quality_multiplier` in scorer.py (line 253); LEAGUE_QUALITY_MULTIPLIERS dict in config.py (line 125); wired after `compute_age_weighted_uv` (line 350); 2 passing tests confirm values and in-place multiplication |
| SCORE-08 | 04-03-PLAN.md | Top-5 similar players via cosine similarity on score_* columns, same position group, cross-league, stored as JSON | SATISFIED | `compute_similar_players` in scorer.py (line 272); wired as final step (line 352); 4 passing tests confirm JSON structure, position scoping, self-exclusion, and cross-league matches |

**Note on SCORE-04 magnitude:** REQUIREMENTS.md §SCORE-04 states ±20%. The phase CONTEXT.md (line 17) explicitly designates this as a typo in REQUIREMENTS.md and declares the authoritative decision is ±10% per the ROADMAP success criteria. The implementation correctly applies `_TEAM_STRENGTH_MAGNITUDE = 0.10` (±10%). The REQUIREMENTS.md document itself was not updated as part of this phase. This is a documentation debt, not a code defect — the CONTEXT.md records the deliberate decision.

---

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pres_p90 column exists in the merged DataFrame after build_dataset | VERIFIED | `"Pres"` in SUM_STATS (config.py:292) and PER90_STATS (config.py:302); `compute_per90s` loop creates `Pres_p90`; `test_pres_p90_present_after_per90s` passes |
| 2 | DrbSucc% is derived from possession Succ, not defense Succ | VERIFIED | `"Succ"` added to stats_defense drop_cols (merger.py:141); `test_drbsucc_uses_possession_succ` passes confirming 50.0 not 250.0 |
| 3 | A DF at a bottom-half club receives higher adjusted defensive stats than the same raw stats at a top-half club | VERIFIED | `apply_team_strength_adjustment` multiplies by 1.10 (bottom) / 0.90 (top); `test_team_strength_bottom_half_inflates_df_score` passes; asserts 1.10 and 0.90 on all 5 stats |
| 4 | A FW's xG_p90, Gls_p90, Ast_p90, SoT_p90 are unchanged by apply_team_strength_adjustment | VERIFIED | Only DF/GK masks are mutated; FW position never enters the adjustment block; `test_team_strength_does_not_affect_fw_attacking` passes |
| 5 | A player with NaN league_position passes through apply_team_strength_adjustment with no stat change | VERIFIED | `df["league_position"].notna()` guard in mask construction (scorer.py:63); `test_team_strength_skips_nan_league_position` passes |
| 6 | GK Save% and PSxG/SoT are adjusted by team strength; Pres_p90 is NOT adjusted for GK | VERIFIED | `_GK_RATE_STATS = ["Save%", "PSxG/SoT"]` (scorer.py:27); Pres_p90 absent from this list; GK adjustment block (lines 72-78) uses `_GK_RATE_STATS` only |
| 7 | Every player row has a league_quality_multiplier consistent with the locked coefficients | VERIFIED | `LEAGUE_QUALITY_MULTIPLIERS = {EPL: 1.10, LaLiga: 1.08, Bundesliga: 1.05, SerieA: 1.03, Ligue1: 1.00}` (config.py:125-131); `test_league_quality_multiplier_values` passes; unknown leagues fallna(1.0) |
| 8 | EPL players end up with 10% higher uv_score_age_weighted than equivalent Ligue1 players | VERIFIED | `df["uv_score_age_weighted"] *= df["league_quality_multiplier"]` (scorer.py:268); `test_league_quality_multiplier_applied_in_place` asserts EPL=55.0, Ligue1=50.0 from base 50.0 |
| 9 | Every player row has a similar_players column containing valid JSON | VERIFIED | `json.dumps(similar)` per player (scorer.py:319); `test_similar_players_column_is_valid_json` passes; asserts 5 entries with required keys |
| 10 | All 5 similar players are from the same position group | VERIFIED | Loop over `["GK","FW","MF","DF"]` positions (scorer.py:289); similarity matrix computed per group; `test_similar_players_same_position_group` passes |
| 11 | No player appears in their own similar_players list | VERIFIED | `sims[i] = -1` sets self-similarity to minimum (scorer.py:301); `test_similar_players_excludes_self` passes |
| 12 | Similar players span multiple leagues | VERIFIED | No league filter inside `compute_similar_players`; cross-league matching is natural; `test_similar_players_cross_league` passes |

**Score: 12/12 truths verified**

---

## Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `config.py` | `"Pres"` in SUM_STATS and PER90_STATS; PILLARS_DF defense with Pres_p90=0.10; LEAGUE_QUALITY_MULTIPLIERS dict | VERIFIED | Line 292 (SUM_STATS), line 302 (PER90_STATS), lines 223-234 (PILLARS_DF defense), lines 125-131 (LEAGUE_QUALITY_MULTIPLIERS). Weights sum: 0.30+0.25+0.20+0.15+0.10=1.00. _DEFENSE unchanged at Tkl 0.35, Int 0.30, Blocks 0.20, DuelsWon 0.15. |
| `merger.py` | stats_defense drop_cols includes "Succ" | VERIFIED | Line 141: `drop_cols=["Tkl.1", "Succ", "Rk", "Nation", "Comp", "Matches"]` |
| `scorer.py` | `apply_team_strength_adjustment`, `apply_league_quality_multiplier`, `compute_similar_players`; all wired in `run_scoring_pipeline` | VERIFIED | All three functions defined (lines 37, 253, 272); pipeline order correct: team adjustment (342) → scout scores (344) → UV regression (346) → age-weighted UV (348) → league multiplier (350) → similar players (352) |
| `test_scorer.py` | 9 new passing tests for SCORE-04/05/08 | VERIFIED | 3 SCORE-04 tests (lines 373-441), 2 SCORE-05 tests (lines 446-491), 4 SCORE-08 tests (lines 523-612); all substantive implementations (no xfail stubs remain) |
| `test_merger.py` | 2 new passing tests for SCORE-04 (Pres_p90 and DrbSucc%) | VERIFIED | `test_pres_p90_present_after_per90s` (line 488), `test_drbsucc_uses_possession_succ` (line 508); full implementations, no stubs |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `config.py SUM_STATS` | `merger._aggregate_fbref_seasons agg dict` | SUM_STATS import — Pres in SUM_STATS means groupby sums it | WIRED | merger.py:11 imports SUM_STATS; line 206 iterates SUM_STATS for agg dict; Pres present in SUM_STATS at config.py:292 |
| `config.py PER90_STATS` | `merger.compute_per90s loop` | PER90_STATS import — Pres listed produces Pres_p90 | WIRED | merger.py:11 imports PER90_STATS; compute_per90s (line 259) loops PER90_STATS producing `{stat}_p90`; Pres produces Pres_p90 |
| `scorer.apply_team_strength_adjustment` | `scorer.run_scoring_pipeline` | called between build_dataset and compute_scout_scores | WIRED | run_scoring_pipeline line 342: `df = apply_team_strength_adjustment(df)` immediately before line 344: `df = compute_scout_scores(df)` |
| `PILLARS_DF defense stats` | `scorer._score_group` | Pres_p90 in PILLARS_DF defense only (not _DEFENSE shared dict) | WIRED | config.py lines 223-234: PILLARS_DF "defense" is a standalone dict with Pres_p90=0.10; _DEFENSE (line 164) has no Pres_p90; _score_group reads pillars["defense"]["stats"] |
| `config.py LEAGUE_QUALITY_MULTIPLIERS` | `scorer.apply_league_quality_multiplier` | imported and used in df["League"].map(LEAGUE_QUALITY_MULTIPLIERS) | WIRED | scorer.py:22 imports LEAGUE_QUALITY_MULTIPLIERS; line 263: `df["League"].map(LEAGUE_QUALITY_MULTIPLIERS).fillna(1.0)` |
| `scorer.apply_league_quality_multiplier` | `scorer.run_scoring_pipeline` | called AFTER compute_age_weighted_uv | WIRED | Line 348: compute_age_weighted_uv; line 350: apply_league_quality_multiplier — correct order confirmed |
| `scorer.compute_similar_players` | `scorer.run_scoring_pipeline` | called LAST — after apply_league_quality_multiplier | WIRED | Line 352: `df = compute_similar_players(df)` is the final operation before `return df` |
| `sklearn.metrics.pairwise.cosine_similarity` | `scorer.compute_similar_players` | vectorized NxN similarity matrix per position group | WIRED | scorer.py:20 imports cosine_similarity; line 297: `sim_matrix = cosine_similarity(matrix)` |

---

## Test Suite

Full suite result: **37 passed, 0 failed, 5 warnings** (warnings are pandas/BeautifulSoup deprecation notices, not failures).

Breakdown by phase/plan:
- Pre-phase 4 baseline: 26 tests
- Plan 04-01 (SCORE-04): +5 tests (2 merger, 3 scorer) — total 31
- Plan 04-02 (SCORE-05): +2 tests — total 33
- Plan 04-03 (SCORE-08): +4 tests — total 37

---

## Anti-Patterns Found

No anti-patterns found in the phase 4 modified files (scorer.py, config.py, merger.py, test_scorer.py, test_merger.py). No TODO/FIXME comments, no empty implementations, no xfail stubs remaining.

---

## Documentation Debt Noted

REQUIREMENTS.md §SCORE-04 still reads "±20% multiplier". CONTEXT.md (line 17) records the deliberate correction to ±10% as an authoritative decision superseding the requirement text. The REQUIREMENTS.md document was not updated as part of this phase. This should be corrected in a future housekeeping commit but is not a code defect.

---

## Human Verification Required

### 1. End-to-end pipeline with real FBref data

**Test:** Run `python scraper.py` (or use warm cache) then call `run_scoring_pipeline` and inspect a sample of DF rows from bottom-half vs top-half clubs.
**Expected:** Bottom-half DFs have Tkl_p90, Int_p90, Blocks_p90, DuelsWon_p90, Pres_p90 approximately 10% higher than equivalent top-half DFs with the same raw counts; EPL players have `league_quality_multiplier == 1.10`; `similar_players` column parses to valid JSON lists of 5 entries.
**Why human:** The Succ column naming in live FBref HTML can vary across scrape years/browsers — the collision fix is unit-tested on synthetic data but real-world column naming needs a smoke-test run.

---

## Gaps Summary

No gaps. All 12 observable truths verified, all artifacts substantive and wired, all key links confirmed. Phase goal achieved.

---

_Verified: 2026-03-17_
_Verifier: Claude (gsd-verifier)_
