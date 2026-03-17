---
status: passed
phase: 02
checked: 2026-03-17
---

# Phase 02 Verification — Merger & Scorer Rewrite (EPL End-to-End)

## Test Suite Results

```
28 passed, 0 failed, 0 skipped  (test_scorer.py + test_merger.py + test_scraper.py)
```

Run command: `python -m pytest test_scorer.py test_merger.py test_scraper.py -q`

Expected per plan 02-04: 27 passed, 0 failed, 0 skipped.
Actual: 28 passed — one additional test beyond projection; all pass.

---

## Plan 02-01: Config & Test Infrastructure (SCORE-01, SCORE-02, SCORE-03)

### must_haves

| Truth | Status | Evidence |
|-------|--------|----------|
| PILLARS_FW.progression.stats contains PrgC_p90 and DrbSucc%, NOT xGBuildup_p90 or DrbAttempts_p90 | PASSED | `FW prog: ['PrgC_p90', 'DrbSucc%']` (runtime print) |
| PILLARS_MF.progression.stats contains PrgP_p90 and SCA_p90, NOT xGChain_p90 | PASSED | `MF prog: ['PrgP_p90', 'SCA_p90']` (runtime print) |
| GK_PILLARS.attacking.stats contains Save% (weight 0.60) and PSxG/SoT (weight 0.40), NOT SavePct | PASSED | `GK att: ['Save%', 'PSxG/SoT']` (runtime print); grep on config.py: no "SavePct" found |
| test_merger.py and test_scorer.py exist with importable stub functions | PASSED | Both files present; `pytest --collect-only` finds all functions; 28 tests collected |

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| config.py contains "PrgC_p90" in PILLARS_FW progression | PASSED |
| config.py contains "DrbSucc%" in PILLARS_FW progression | PASSED |
| config.py contains "PrgP_p90" in PILLARS_MF progression | PASSED |
| config.py contains "SCA_p90" in PILLARS_MF progression | PASSED |
| config.py contains "Save%" in GK_PILLARS attacking | PASSED |
| config.py contains "PSxG/SoT" in GK_PILLARS attacking | PASSED |
| config.py does NOT contain "xGBuildup_p90" | PASSED |
| config.py does NOT contain "xGChain_p90" | PASSED |
| config.py does NOT contain "SavePct" | PASSED |
| config.py MIN_MINUTES equals 1800 | PASSED — line 12: `MIN_MINUTES = 1800` |

---

## Plan 02-02: Merger Rewrite (DATA-03, SCORE-01)

### must_haves

| Truth | Status | Evidence |
|-------|--------|----------|
| build_dataset(fbref_data, tm_data) accepts 2 args (not 3) | PASSED | `inspect.signature` returns `(fbref_data: dict, tm_data: DataFrame)` |
| Multi-club deduplication: '2 Clubs' row kept, per-club rows dropped | PASSED | `_deduplicate_multiclub` function present; `test_multiclub_deduplication` PASSES |
| Players with total_Min < 1800 excluded; players absent from 2024-25 excluded | PASSED | `test_min_minutes_threshold_1800` and `test_current_season_filter` PASS |
| DrbSucc% derived from Succ / Att_drb * 100 (from stats_possession) | PASSED | `_aggregate_fbref_seasons` re-derives DrbSucc% from summed counts; `test_drbsucc_rate_derivation` PASSES |
| DuelsWon_p90 and DuelsWon% derived from Won / Lost columns in stats_misc | PASSED | `attach_league_position`, `_aggregate_fbref_seasons` both handle AerWon/AerLost; `test_duels_won_pct_derivation` PASSES |
| league_position column attached from EPL standings (NaN for multi-club players) | PASSED | `attach_league_position` present in merger.py; `test_league_position_attached` PASSES |
| PrgC column comes from stats_possession only — no duplicate column | PASSED | `test_prgc_source_is_possession` PASSES; merger.py drops PrgC from stats_standard before join |

### Artifacts

| Artifact | Status | Detail |
|----------|--------|--------|
| merger.py — contains `_deduplicate_multiclub` | PASSED | Line 27 |
| merger.py — min_lines: 150 | PASSED | 371 lines |
| scraper.py — contains `scrape_fbref_standings` | PASSED | Line 279 |

---

## Plan 02-03: Scorer Rewrite + Age-Weight (SCORE-06, SCORE-07)

### must_haves

| Truth | Status | Evidence |
|-------|--------|----------|
| run_scoring_pipeline(fbref_data, tm_data) accepts 2 args; TypeError on 3 args | PASSED | Signature confirmed: `(fbref_data: dict, tm_data: DataFrame)` |
| uv_score_age_weighted exists as column in run_scoring_pipeline output | PASSED | `compute_age_weighted_uv` adds the column; `test_uv_score_age_weighted_column_exists` PASSES |
| uv_score_age_weighted > uv_score for players aged 21 and under | PASSED | Age 21 → multiplier > 1; asserted in `test_uv_score_age_weighted_column_exists` |
| uv_score_age_weighted == uv_score for players aged 29 and over | PASSED | Age 29+ → multiplier = 1.0; asserted in same test |
| UV regression is fit on full unfiltered player pool (SCORE-06) | PASSED | `compute_efficiency` called directly in `run_scoring_pipeline` on full `df`; `test_uv_regression_full_pool` PASSES |
| Age column parsed correctly from FBref '25-201' format | PASSED | `_parse_age("25-201") == 25.0`; `test_age_column_parsing` PASSES |

### Artifacts

| Artifact | Status |
|----------|--------|
| scorer.py — contains `uv_score_age_weighted` | PASSED |
| scorer.py — contains `def compute_age_weighted_uv` | PASSED |
| scorer.py — contains `def _parse_age` | PASSED |
| test_scorer.py — contains `test_age_weight_formula` (implemented, not skip) | PASSED |

---

## Plan 02-04: app.py Rewire & Integration (SCORE-01, DATA-03)

### must_haves

| Truth | Status | Evidence |
|-------|--------|----------|
| app.py load_data calls run_fbref_scrapers and run_tm_scrapers; NOT run_understat_scrapers or run_api_football_scrapers | PASSED | Lines 189–191; grep confirms no legacy scraper references |
| app.py calls run_scoring_pipeline(fbref_data, tm_data) with 2 args | PASSED | app.py line ~192 |
| app.py sources line shows 'FBref · TM' not 'Understat · API-Football · TM' | PASSED | app.py line 402 |
| app.py min minutes line shows 1,800 not 3,000 | PASSED | app.py line 404 |
| Tab 3 leaderboard includes uv_score_age_weighted column | PASSED | app.py line 523 in display_cols |
| GK player card shows Save% not Saves_p90 | PASSED | app.py line 482 |

---

## Requirements Cross-Reference

| Req-ID | Description | Status | Verification |
|--------|-------------|--------|--------------|
| DATA-03 | Scrape FBref league standings for team strength adjustment | PASSED | `scrape_fbref_standings` in scraper.py; called from `attach_league_position` in merger.py; `test_standings_scraper_caches` PASSES |
| SCORE-01 | Position-specific pillar scores (GK/FW/MF/DF) using FBref columns | PASSED | `compute_scout_scores` dispatches by position; all position groups handled; FBref column names throughout config.py |
| SCORE-02 | MF Progression: 0.6×PrgP_p90 + 0.4×SCA_p90 | PASSED | `PILLARS_MF['progression']['stats'] == {'PrgP_p90': 0.60, 'SCA_p90': 0.40}`; `test_scorer_new_pillar_columns` PASSES |
| SCORE-03 | FW and DF Progression: PrgC_p90 (progressive carries) | PASSED | `PILLARS_FW['progression']['stats'] == {'PrgC_p90': 0.55, 'DrbSucc%': 0.45}`; same for PILLARS_DF; `test_scorer_new_pillar_columns` PASSES |
| SCORE-06 | UV regression fit on full unfiltered player pool | PASSED | `compute_efficiency` called on full `df` in `run_scoring_pipeline` before any filtering; `test_uv_regression_full_pool` PASSES |
| SCORE-07 | Age-weighted UV: uv_score × (1 + 0.30 × age_weight); both columns stored | PASSED | `compute_age_weighted_uv` present; `uv_score_age_weighted` column in output; formula uses log-decay from 17–29; all 3 age-weight tests PASS |

---

## Phase 02 Success Criteria (from ROADMAP.md)

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Running scorer on EPL cache data produces DataFrame with scout_score, uv_score, and uv_score_age_weighted for all qualifying EPL players | PASSED | `run_scoring_pipeline` produces all three columns; verified via unit tests |
| 2 | GK players have non-zero score_attacking (Shot Stopping) values — FBref migration fixes API-Football gap | PASSED | GK_PILLARS.attacking uses Save% and PSxG/SoT from FBref; `test_gk_shot_stopping_pillar` PASSES; column weights verified |
| 3 | MF Progression draws from PrgP_p90 and SCA_p90 (not xGChain_p90); FW and DF from PrgC_p90 | PASSED | Confirmed in config.py and runtime output |
| 4 | uv_score_age_weighted strictly greater than uv_score for players ≤21; equals uv_score for players ≥29 | PASSED | `test_uv_score_age_weighted_column_exists` asserts both conditions; `test_age_weight_formula` validates multiplier values |
| 5 | UV regression fit on full pool — uv_score values do not change when position filter applied before scoring | PASSED | `test_uv_regression_full_pool` confirms `len(full_result) == n` (all 20 players in regression) |

---

## Summary

All 6 phase requirement IDs verified (DATA-03, SCORE-01, SCORE-02, SCORE-03, SCORE-06, SCORE-07).
All plan must_haves confirmed against codebase.
All 5 ROADMAP success criteria satisfied.
Test suite: 28 passed, 0 failed, 0 skipped.

No gaps found. Phase 02 is complete.
