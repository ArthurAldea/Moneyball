---
phase: 1
slug: fbref-scraper-epl
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `Moneyball/test_scraper.py` (existing) |
| **Quick run command** | `cd /Users/ArthurAldea/ClaudeProjects/Moneyball && python -m pytest test_scraper.py -x -q` |
| **Full suite command** | `cd /Users/ArthurAldea/ClaudeProjects/Moneyball && python -m pytest test_scraper.py -v` |
| **Estimated runtime** | ~5 seconds (cache-only tests, no network) |

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
| 1-01-01 | 01 | 1 | DATA-05 | unit | `pytest test_scraper.py::test_cache_fresh -xq` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | DATA-06 | unit | `pytest test_scraper.py::test_rate_limit_delay -xq` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | DATA-07 | unit | `pytest test_scraper.py::test_backoff_on_429 -xq` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | DATA-01 | unit | `pytest test_scraper.py::test_url_construction -xq` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | DATA-01 | integration | `pytest test_scraper.py::test_table_extraction -xq` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 2 | DATA-02 | unit | `pytest test_scraper.py::test_column_presence -xq` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | DATA-01 | integration | `pytest test_scraper.py::test_run_scrapers_epl -xq` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | DATA-05 | unit | `pytest test_scraper.py::test_cache_naming -xq` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `test_scraper.py` — update/expand stubs for `scrape_fbref_stat`, `run_fbref_scrapers`, cache helpers
- [ ] Fixtures: a small mock HTML response containing an FBref comment-wrapped table
- [ ] Fixtures: a fake 429 response for backoff testing
- [ ] `pytest` installed in venv (likely already present — verify)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full EPL cold scrape populates all 8 table CSVs | DATA-01, DATA-02 | Requires live FBref network access; rate-limited | Run `python scraper.py`, verify 16 CSV files created in `cache/` with non-empty row counts |
| Second run within 7 days produces no network requests | DATA-05 | Hard to mock 100% in unit test | Run `python scraper.py` twice; confirm second run completes in <2s and no new HTTP calls in logs |
| min-minutes filter removes <900 min players | DATA-01 SC3 | Requires real or realistic data fixture | Inspect cached CSV: `python -c "import pandas as pd; df=pd.read_csv('cache/fbref_EPL_stats_standard_2024-25.csv'); print((df['Min']<900).sum())"` — should be 0 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
