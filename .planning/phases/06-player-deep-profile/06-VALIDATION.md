---
phase: 6
slug: player-deep-profile
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, no version pin) |
| **Config file** | none — pytest auto-discovers `test_*.py` |
| **Quick run command** | `pytest test_app.py -x -q` |
| **Full suite command** | `pytest test_app.py test_scorer.py test_merger.py test_scraper.py -q` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest test_app.py -x -q`
- **After every plan wave:** Run `pytest test_app.py test_scorer.py test_merger.py test_scraper.py -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | FILTER-07 | unit | `pytest test_app.py::test_filter_by_name test_app.py::test_filter_by_name_empty -x -q` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | PROFILE-06 | unit | `pytest test_app.py::test_selection_cap -x -q` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | PROFILE-01 | unit | `pytest test_app.py::test_profile_header_data -x -q` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | PROFILE-02 | unit | `pytest test_app.py::test_radar_figure test_app.py::test_radar_median_source -x -q` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 2 | PROFILE-03 | unit | `pytest test_app.py::test_compute_percentile -x -q` | ❌ W0 | ⬜ pending |
| 06-02-04 | 02 | 2 | PROFILE-04 | unit | `pytest test_app.py::test_scatter_highlight -x -q` | ❌ W0 | ⬜ pending |
| 06-02-05 | 02 | 2 | PROFILE-05 | unit | `pytest test_app.py::test_parse_similar_players test_app.py::test_parse_similar_players_malformed -x -q` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 3 | PROFILE-06 | unit | `pytest test_app.py -x -q` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 3 | PROFILE-06 | manual | Visual check: select 2-3 players, verify radar overlays + stat columns | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `test_app.py` — append new test functions (do NOT replace existing Phase 5 tests):
  - `test_filter_by_name` — FILTER-07 partial match
  - `test_filter_by_name_empty` — FILTER-07 empty query returns full df
  - `test_selection_cap` — PROFILE-06 truncates >3 selections to 3
  - `test_profile_header_data` — PROFILE-01 header data extraction
  - `test_radar_figure` — PROFILE-02 go.Figure with ≥2 Scatterpolar traces
  - `test_radar_median_source` — PROFILE-02 median from full_df position peers
  - `test_compute_percentile` — PROFILE-03 returns float in [0, 100]
  - `test_scatter_highlight` — PROFILE-04 highlighted trace present with larger marker
  - `test_parse_similar_players` — PROFILE-05 enriched list with age + market_value_m
  - `test_parse_similar_players_malformed` — PROFILE-05 malformed JSON → empty list
- [ ] Verify `make_pipeline_df()` fixture in `test_app.py` includes `Nation`, `score_*`, `similar_players` columns — add if missing

*Existing test infrastructure (pytest + conftest.py Streamlit stubs) covers Phase 5; Phase 6 extends `test_app.py` only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Profile renders inline between table and scatter | PROFILE-01 | Streamlit layout not testable in unit tests | Run `streamlit run app.py`, select a row, verify profile appears above scatter chart |
| Radar chart fills correctly (no gap at polygon close) | PROFILE-02 | Visual rendering only | Select a player, verify radar polygon is closed with no gap between last and first pillar |
| Percentile bar colors (red/amber/green) render correctly | PROFILE-03 | HTML rendering in browser | Check stat table: low-percentile stats show red bars, high-percentile show green |
| Scatter highlight: distinct marker for selected player(s) | PROFILE-04 | Visual rendering only | Select 1-3 players, verify each has a larger labeled marker on scatter chart |
| Similar player click navigates to clicked player's profile | PROFILE-05 | Session state interaction | Click a similar player button, verify profile updates to show that player |
| Comparison mode: 4th selection triggers warning | PROFILE-06 | Streamlit widget interaction | Select 4 rows, verify `st.warning` appears and only 3 profiles show |
| Name search: real-time filtering in sidebar | FILTER-07 | Streamlit widget interaction | Type "son" in PLAYER SEARCH, verify only matching players remain in shortlist |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
