---
phase: 2
slug: merger-scorer-rewrite-epl-end-to-end
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-16
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `test_merger.py` + `test_scorer.py` (new files, Wave 0) |
| **Quick run command** | `cd /Users/ArthurAldea/ClaudeProjects/Moneyball && source venv/bin/activate && python -m pytest test_merger.py test_scorer.py -x -q` |
| **Full suite command** | `cd /Users/ArthurAldea/ClaudeProjects/Moneyball && source venv/bin/activate && python -m pytest test_merger.py test_scorer.py test_scraper.py -v` |
| **Estimated runtime** | ~5 seconds (all no-network, synthetic fixtures) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | SCORE-02, SCORE-03 | unit | `pytest test_scorer.py::test_scorer_new_pillar_columns -xq` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | SCORE-01 | unit | `pytest test_scorer.py::test_gk_shot_stopping_pillar -xq` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 2 | DATA-03 | unit | `pytest test_merger.py::test_standings_scraper_caches -xq` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 2 | SCORE-01 | unit | `pytest test_merger.py::test_multiclub_deduplication -xq` | ❌ W0 | ⬜ pending |
| 2-02-03 | 02 | 2 | SCORE-01 | unit | `pytest test_merger.py::test_nine_table_join_full -xq` | ❌ W0 | ⬜ pending |
| 2-02-04 | 02 | 2 | SCORE-01 | unit | `pytest test_merger.py::test_cross_season_aggregation -xq` | ❌ W0 | ⬜ pending |
| 2-02-05 | 02 | 2 | SCORE-01 | unit | `pytest test_merger.py::test_per90_derivation -xq` | ❌ W0 | ⬜ pending |
| 2-02-06 | 02 | 2 | SCORE-01 | unit | `pytest test_merger.py::test_drbsucc_rate_derivation -xq` | ❌ W0 | ⬜ pending |
| 2-02-07 | 02 | 2 | SCORE-01 | unit | `pytest test_merger.py::test_duels_won_pct_derivation -xq` | ❌ W0 | ⬜ pending |
| 2-02-08 | 02 | 2 | SCORE-01 | unit | `pytest test_merger.py::test_min_minutes_threshold_1800 -xq` | ❌ W0 | ⬜ pending |
| 2-02-09 | 02 | 2 | SCORE-01 | unit | `pytest test_merger.py::test_current_season_filter -xq` | ❌ W0 | ⬜ pending |
| 2-02-10 | 02 | 2 | SCORE-01 | unit | `pytest test_merger.py::test_primary_position_extraction -xq` | ❌ W0 | ⬜ pending |
| 2-02-11 | 02 | 2 | DATA-03 | unit | `pytest test_merger.py::test_league_position_attached -xq` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 3 | SCORE-07 | unit | `pytest test_scorer.py::test_age_weight_formula -xq` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 3 | SCORE-07 | unit | `pytest test_scorer.py::test_age_column_parsing -xq` | ❌ W0 | ⬜ pending |
| 2-03-03 | 03 | 3 | SCORE-07 | unit | `pytest test_scorer.py::test_uv_score_age_weighted_column_exists -xq` | ❌ W0 | ⬜ pending |
| 2-03-04 | 03 | 3 | SCORE-06 | unit | `pytest test_scorer.py::test_uv_regression_full_pool -xq` | ❌ W0 | ⬜ pending |
| 2-04-01 | 04 | 4 | DATA-03, SCORE-01 | integration | `pytest test_merger.py::test_nine_table_join_missing_table -xq` | ❌ W0 | ⬜ pending |
| 2-04-02 | 04 | 4 | SCORE-01 | integration | `pytest test_merger.py::test_prgc_source_is_possession -xq` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `test_merger.py` — created in Plan 02-01 (Task 2) with stubs for all merger tests
- [x] `test_scorer.py` — created in Plan 02-01 (Task 2) with stubs for all scorer tests
- [x] Synthetic FBref-format fixture DataFrames (make_stats_standard_fixture etc.) included in test_merger.py
- [x] `pytest` already installed in venv (confirmed in Phase 1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full EPL pipeline produces non-zero scout_score for all position groups | SCORE-01 | Requires real cached FBref CSVs | Run `python scorer.py` on warm cache; verify `df.groupby('Pos')['scout_score'].mean()` is non-zero for GK, FW, MF, DF |
| GK score_attacking is non-zero (FBref migration fix) | SCORE-01 | Requires real keeper CSV data | Check `df[df['Pos']=='GK']['score_attacking'].describe()` — min should be > 0 |
| app.py shows real EPL players after rewire | SCORE-01 | Requires Streamlit + warm cache | Run `streamlit run app.py`; confirm player shortlist is populated |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands in their PLAN.md tasks
- [x] Sampling continuity: pytest runs after every plan's final task
- [x] Wave 0 test stubs created in Plan 02-01 Task 2
- [x] No watch-mode flags
- [x] Feedback latency < 10s (all synthetic fixture tests, no network)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-16 — Plans 02-01 through 02-04 written
