---
phase: 5
slug: dashboard-rebuild-shortlist-filters
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` or `pyproject.toml` (Wave 0 creates if missing) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | DASH-01 | unit | `pytest tests/test_dashboard.py::test_shortlist_columns -x -q` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | FILTER-01 | unit | `pytest tests/test_dashboard.py::test_league_filter -x -q` | ❌ W0 | ⬜ pending |
| 5-01-03 | 01 | 1 | FILTER-02 | unit | `pytest tests/test_dashboard.py::test_position_filter -x -q` | ❌ W0 | ⬜ pending |
| 5-01-04 | 01 | 1 | FILTER-03 | unit | `pytest tests/test_dashboard.py::test_age_filter -x -q` | ❌ W0 | ⬜ pending |
| 5-01-05 | 01 | 1 | FILTER-04 | unit | `pytest tests/test_dashboard.py::test_club_filter_dynamic -x -q` | ❌ W0 | ⬜ pending |
| 5-01-06 | 01 | 1 | FILTER-05 | unit | `pytest tests/test_dashboard.py::test_market_value_filter -x -q` | ❌ W0 | ⬜ pending |
| 5-01-07 | 01 | 1 | FILTER-06 | unit | `pytest tests/test_dashboard.py::test_season_filter -x -q` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 2 | DASH-05 | manual | Visual inspection of dark theme | N/A | ⬜ pending |
| 5-02-02 | 02 | 2 | DASH-06 | unit | `pytest tests/test_dashboard.py::test_scatter_plot_data -x -q` | ❌ W0 | ⬜ pending |
| 5-02-03 | 02 | 2 | DASH-07 | unit | `pytest tests/test_dashboard.py::test_cross_league_disclaimer -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard.py` — stubs for DASH-01 through DASH-07 and FILTER-01 through FILTER-06
- [ ] `tests/conftest.py` — shared fixtures (sample DataFrame with all required columns)

*If framework already present in `requirements.txt` no install task needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dark theme visual appearance | DASH-05 | CSS/Streamlit styling cannot be asserted via pytest headlessly | Launch `streamlit run app.py`, verify background `#0D1B2A`, accent `#00A8FF`, Inter font, ALL-CAPS headers |
| Row-click detail panel display | DASH-04 | Requires browser interaction with Streamlit selection event | Select a row, verify player detail panel appears below table |
| Scatter plot legend + OLS line render | DASH-06 | Plotly chart render requires browser | Verify scatter renders with position-colored dots and regression line |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
