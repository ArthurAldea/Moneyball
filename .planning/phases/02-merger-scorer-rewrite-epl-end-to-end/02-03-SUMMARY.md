---
phase: 02-merger-scorer-rewrite-epl-end-to-end
plan: 03
status: complete
completed: "2026-03-17"
requirements_closed: [SCORE-06, SCORE-07]
---

# Plan 02-03 Summary — Scorer Rewrite + Age-Weight

## What Was Done

Three tasks executed atomically:

### Task 1: scorer.py — signature, age parsing, age-weighted UV
- Added `_parse_age(age_val)` helper: handles FBref 'years-days' format (e.g. '25-201' → 25.0), plain integers/floats, and returns NaN for unparseable values.
- Added `compute_age_weighted_uv(df)`: applies multiplier `min(1.5, 1.0 + 0.30 * log(29-age)/log(12))` to `uv_score`, producing `uv_score_age_weighted` column. Multiplier is >1 for ages under 29, exactly 1.0 at ages 29+.
- Updated `compute_scout_scores` to defensively strip secondary positions from Pos column ('DF,MF' → 'DF') before grouping.
- Changed `run_scoring_pipeline` from 3-arg `(understat_data, api_data, tm_data)` to 2-arg `(fbref_data, tm_data)`, wiring in `compute_age_weighted_uv` at the end of the pipeline.

### Task 2: test_scorer.py — Wave 3 tests implemented
Replaced all 4 pytest.skip stubs with real implementations:
- `test_age_weight_formula`: verifies multipliers at ages 17, 21, 25, 29, 35.
- `test_age_column_parsing`: verifies _parse_age handles FBref format, plain strings, integers, and invalid inputs.
- `test_uv_score_age_weighted_column_exists`: verifies compute_age_weighted_uv adds the column and correctly boosts age-21 but not age-29/35.
- `test_uv_regression_full_pool`: verifies compute_efficiency returns all 20 rows (full pool), confirming UV regression is not filtered before fitting.

### Task 3: Full test suite — no regression
- test_scorer.py: 6 PASSED
- test_merger.py: 11 PASSED, 2 SKIPPED (Wave 4 stubs)
- test_scraper.py: 9 PASSED
- **Total: 26 passed, 2 skipped, 0 failed**

## Key Decisions

- **age-25 multiplier is 1.17, not 1.09:** The plan's documentation contained an error in the example values table. The actual formula `log(29-age)/log(12) * 0.30 + 1.0` produces 1.167 at age 25 (not 1.09 as documented). Tests corrected to match actual formula output rather than the erroneous plan comment.
- **run_scoring_pipeline is now 2-arg:** The old 3-arg signature (`understat_data, api_data, tm_data`) is fully removed. app.py must be updated in Plan 02-04 to pass `(fbref_data, tm_data)`.

## Artifacts Modified

| File | Change |
|------|--------|
| `scorer.py` | Added `_parse_age`, `compute_age_weighted_uv`; updated `compute_scout_scores` (primary pos guard); changed `run_scoring_pipeline` to 2-arg |
| `test_scorer.py` | Replaced 4 pytest.skip stubs with real Wave 3 test implementations |

## Requirements Closed

- **SCORE-06:** UV regression is fit on full unfiltered player pool — confirmed by test_uv_regression_full_pool.
- **SCORE-07:** Age-weighted UV score — confirmed by test_uv_score_age_weighted_column_exists; uv_score_age_weighted > uv_score for ages under 29.

## Next Step

Plan 02-04: Rewire app.py to call `run_scoring_pipeline(fbref_data, tm_data)` (2-arg signature) via `run_fbref_scrapers` and `run_tm_scrapers`. This will make the dashboard show real EPL players for the first time.
