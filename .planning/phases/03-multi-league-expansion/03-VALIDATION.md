---
phase: 3
slug: multi-league-expansion
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-17
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `test_scraper.py`, `test_merger.py`, `test_scorer.py` (extend existing files, no new files) |
| **Quick run command** | `cd /Users/ArthurAldea/ClaudeProjects/Moneyball && source venv/bin/activate && python -m pytest test_scraper.py test_merger.py test_scorer.py -x -q` |
| **Full suite command** | `cd /Users/ArthurAldea/ClaudeProjects/Moneyball && source venv/bin/activate && python -m pytest test_scraper.py test_merger.py test_scorer.py -v` |
| **Estimated runtime** | ~8 seconds (all no-network, synthetic fixtures; 40 tests total after Phase 3) |

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
| 3-01-01 | 01 | 1 | DATA-01, DATA-05 | unit | `pytest test_scraper.py::test_url_construction_new_leagues -xq` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | DATA-05 | unit | `pytest test_scraper.py::test_cache_naming_new_leagues -xq` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | DATA-01 | unit | `pytest test_scraper.py::test_run_fbref_scrapers_all_leagues -xq` | ❌ W0 | ⬜ pending |
| 3-01-04 | 01 | 1 | DATA-04, DATA-05 | unit | `pytest test_scraper.py::test_run_tm_scrapers_multi_league -xq` | ❌ W0 | ⬜ pending |
| 3-01-05 | 01 | 1 | DATA-05 | unit | `pytest test_scraper.py::test_tm_cache_naming_league_keyed -xq` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 2 | DATA-01 | unit | `pytest test_merger.py::test_league_column_present_multi_league -xq` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 2 | DATA-01 | unit | `pytest test_merger.py::test_per_league_min_minutes_filter -xq` | ❌ W0 | ⬜ pending |
| 3-02-03 | 02 | 2 | DATA-04 | unit | `pytest test_merger.py::test_pass3_tm_matching -xq` | ❌ W0 | ⬜ pending |
| 3-02-04 | 02 | 2 | DATA-01 | unit | `pytest test_merger.py::test_single_season_flag -xq` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 3 | DATA-01 | unit | `pytest test_scorer.py::test_per_league_normalization_isolation -xq` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 3 | DATA-01 | unit | `pytest test_scorer.py::test_uv_regression_on_full_pool_multi_league -xq` | ❌ W0 | ⬜ pending |
| 3-03-03 | 03 | 3 | DATA-01 | unit | `pytest test_scorer.py::test_league_column_preserved_through_pipeline -xq` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Add 5 stub tests to `test_scraper.py` (test_url_construction_new_leagues through test_tm_cache_naming_league_keyed) — implement stubs in Plan 03-01 Task 1 before implementation begins
- [ ] Add 4 stub tests to `test_merger.py` (test_league_column_present_multi_league through test_single_season_flag) — implement stubs in Plan 03-02 Task 1
- [ ] Add 3 stub tests to `test_scorer.py` (test_per_league_normalization_isolation through test_league_column_preserved_through_pipeline) — implement stubs in Plan 03-03 Task 1

*No new test files or framework installs needed — pytest already installed in venv.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cold scrape for all 5 leagues completes without crash | DATA-01 | Requires ~25 min live FBref + TM requests | Run `python scraper.py`; verify 90 FBref CSVs + 10 TM CSVs created in `cache/` |
| FBref table IDs are consistent for non-EPL leagues | DATA-01 | Requires live network hit per league | After scrape, verify `cache/fbref_LaLiga_stats_gca_2024-25.csv` has > 50 rows |
| Pass 3 TM matching reduces NaN market values | DATA-04 | Requires real player names + real TM data | After scoring, run `df['market_value_eur'].isna().sum()` — compare to Phase 2 EPL NaN count |
| Per-league normalization: top La Liga FW ≈ 100 scout_score | DATA-01 | Requires real multi-league scored output | Run `df[df['Pos']=='FW'].groupby('League')['scout_score'].max()` — all leagues near 100 |
| `League` column non-null on every scored row | DATA-01 | Requires real pipeline run | Run `df['League'].isna().sum()` — must be 0 |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands in their PLAN.md tasks
- [x] Sampling continuity: pytest runs after every plan's final task
- [x] Wave 0 test stubs created at start of each plan before implementation
- [x] No watch-mode flags
- [x] Feedback latency < 10s (all synthetic fixture tests, no network)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-17 — Plans 03-01 through 03-03 to be written
