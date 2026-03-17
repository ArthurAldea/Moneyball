---
phase: 4
slug: advanced-scoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project venv) |
| **Config file** | none — run from project root |
| **Quick run command** | `python -m pytest test_scorer.py test_merger.py -q` |
| **Full suite command** | `python -m pytest test_scorer.py test_merger.py test_scraper.py -q` |
| **Estimated runtime** | ~5 seconds (scorer + merger suite) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest test_scorer.py test_merger.py -q`
- **After every plan wave:** Run `python -m pytest test_scorer.py test_merger.py -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | SCORE-04 | unit | `python -m pytest test_merger.py::test_pres_p90_present_after_per90s -x` | ❌ Wave 0 | ⬜ pending |
| 4-01-02 | 01 | 0 | SCORE-04 | unit | `python -m pytest test_merger.py::test_drbsucc_uses_possession_succ -x` | ❌ Wave 0 | ⬜ pending |
| 4-01-03 | 01 | 0 | SCORE-04 | unit | `python -m pytest test_scorer.py::test_team_strength_bottom_half_inflates_df_score -x` | ❌ Wave 0 | ⬜ pending |
| 4-01-04 | 01 | 0 | SCORE-04 | unit | `python -m pytest test_scorer.py::test_team_strength_does_not_affect_fw_attacking -x` | ❌ Wave 0 | ⬜ pending |
| 4-01-05 | 01 | 0 | SCORE-04 | unit | `python -m pytest test_scorer.py::test_team_strength_skips_nan_league_position -x` | ❌ Wave 0 | ⬜ pending |
| 4-02-01 | 02 | 0 | SCORE-05 | unit | `python -m pytest test_scorer.py::test_league_quality_multiplier_values -x` | ❌ Wave 0 | ⬜ pending |
| 4-02-02 | 02 | 0 | SCORE-05 | unit | `python -m pytest test_scorer.py::test_league_quality_multiplier_applied_in_place -x` | ❌ Wave 0 | ⬜ pending |
| 4-03-01 | 03 | 0 | SCORE-08 | unit | `python -m pytest test_scorer.py::test_similar_players_column_is_valid_json -x` | ❌ Wave 0 | ⬜ pending |
| 4-03-02 | 03 | 0 | SCORE-08 | unit | `python -m pytest test_scorer.py::test_similar_players_same_position_group -x` | ❌ Wave 0 | ⬜ pending |
| 4-03-03 | 03 | 0 | SCORE-08 | unit | `python -m pytest test_scorer.py::test_similar_players_excludes_self -x` | ❌ Wave 0 | ⬜ pending |
| 4-03-04 | 03 | 0 | SCORE-08 | unit | `python -m pytest test_scorer.py::test_similar_players_cross_league -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `test_merger.py` — add `test_pres_p90_present_after_per90s` and `test_drbsucc_uses_possession_succ` stubs
- [ ] `test_scorer.py` — add stubs for all SCORE-04, SCORE-05, SCORE-08 tests listed above (9 stubs total)

*Existing test infrastructure: 26 passing tests in test_scorer.py + test_merger.py cover prior requirements. Only new stubs needed for Phase 4.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
