---
phase: 06-player-deep-profile
verified: 2026-03-18T07:30:00Z
status: human_needed
score: 13/13 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 11/13
  gaps_closed:
    - "Per-90 stat table now has a 4-column layout: STAT | RAW | PER 90 | PERCENTILE (PROFILE-03)"
    - "REQUIREMENTS.md checkboxes for FILTER-07, PROFILE-01, PROFILE-02, PROFILE-03, PROFILE-04, PROFILE-05 are all marked [x]"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run streamlit run app.py, click any shortlist row"
    expected: "PLAYER PROFILE section appears with filled radar polygon + dotted PEER MEDIAN, 4-column stat table (STAT, RAW, PER 90, PERCENTILE) with red/amber/green bars, player highlighted on scatter, SIMILAR PLAYERS cards"
    why_human: "Streamlit rendering requires live browser; automated tests only cover pure-Python logic"
  - test: "Type a partial name (e.g. 'son') in the PLAYER SEARCH box at the top of the sidebar"
    expected: "Shortlist table narrows in real-time to only rows matching the query (case-insensitive)"
    why_human: "Streamlit widget interaction requires live browser"
  - test: "Ctrl/Cmd+click 2-3 rows in the shortlist table"
    expected: "View switches to PLAYER PROFILE - COMPARISON; mini header cards with distinct left-border colors; radar shows one polygon per player plus PEER MEDIAN; stat table has one column per player"
    why_human: "Multi-row selection requires browser interaction"
  - test: "Attempt to select a 4th row in the shortlist"
    expected: "Yellow warning banner 'MAX 3 PLAYERS - Selection limited to first 3.' appears; only 3 players profiled"
    why_human: "Row selection requires browser"
  - test: "Click View Profile on a similar player card"
    expected: "Profile header updates to show the clicked player's name, club, etc."
    why_human: "Button click triggers st.rerun() — needs live browser session"
---

# Phase 6: Player Deep Profile Verification Report

**Phase Goal:** Implement the drill-down player profile view triggered by clicking a shortlist row, displaying the full header block, radar chart vs. position-peer median, per-90 stat table with percentile bars, scatter chart highlight, and similar players panel. Extend the shortlist with a player name search filter and multi-player comparison mode.
**Verified:** 2026-03-18T07:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure

## Re-verification Summary

| Gap (Previous) | Fix Verified | Evidence |
|----------------|-------------|---------|
| PROFILE-03: raw value column missing | CLOSED | app.py lines 442-444: RAW header; lines 475-480: raw_col derivation logic; lines 494-495: raw_str cell rendered in each data row |
| REQUIREMENTS.md checkboxes unchecked | CLOSED | Lines 38, 55-59 all show `- [x]` for FILTER-07, PROFILE-01 through PROFILE-05 |

No regressions detected. All 13 truths now pass automated checks.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | filter_by_name() exists, case-insensitive, empty query returns full df | VERIFIED | app.py line 206; all filter tests pass |
| 2 | PLAYER SEARCH text_input above LEAGUE filter in sidebar | VERIFIED | app.py line 886 PLAYER SEARCH, line 893 LEAGUE |
| 3 | filter_by_name applied after apply_filters() on display_df | VERIFIED | app.py lines 970-971 |
| 4 | Reset Filters clears player_search from session state | VERIFIED | app.py line 979 includes "player_search" in key deletion list |
| 5 | selection_mode="multi-row" on shortlist table | VERIFIED | app.py line 1000 |
| 6 | Selecting >3 rows shows warning and caps at 3 | VERIFIED | app.py lines 1008-1010 |
| 7 | render_single_profile() renders header, radar, stat table, similar players | VERIFIED | app.py lines 373-527; wired at line 1043 |
| 8 | Per-90 stat table includes a separate raw value column (PROFILE-03) | VERIFIED | 4-column layout STAT/RAW/PER 90/PERCENTILE at lines 438-447; raw_col derived by stripping _p90 suffix (lines 475-480); raw_str cell rendered at lines 494-495; colspan updated to 4 at line 457 |
| 9 | render_comparison_profile() renders overlaid radar + per-player stat columns | VERIFIED | app.py lines 529-715; wired at line 1051 |
| 10 | Scatter chart highlights selected players with distinct markers (size=14, white border) | VERIFIED | app.py lines 780-803 |
| 11 | Similar player click navigates to that player via session state + st.rerun() | VERIFIED | app.py lines 524-525 (single), 709-710 (comparison) |
| 12 | Stale-profile guard shows st.info when override player filtered out | VERIFIED | app.py lines 1029-1037 |
| 13 | REQUIREMENTS.md checkboxes updated for PROFILE-01 through PROFILE-05 and FILTER-07 | VERIFIED | All 6 lines show `- [x]` (REQUIREMENTS.md lines 38, 55-59) |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app.py` | filter_by_name + PLAYER SEARCH + multi-row | VERIFIED | Lines 206, 886, 1000 |
| `app.py` | render_single_profile() with 4-column stat table | VERIFIED | Lines 373-503; RAW column at lines 438-500 |
| `app.py` | _pct_bar_html() | VERIFIED | Line 356 |
| `app.py` | render_comparison_profile() | VERIFIED | Line 529 |
| `test_app.py` | Phase 6 test functions | VERIFIED | 23/23 tests pass |
| `.planning/REQUIREMENTS.md` | Checkboxes for FILTER-07, PROFILE-01 through PROFILE-05 marked [x] | VERIFIED | Lines 38, 55-59 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| app.py sidebar | display_df | filter_by_name applied after apply_filters() | WIRED | Lines 970-971 |
| app.py shortlist table | selection_mode | st.dataframe argument | WIRED | Line 1000: `selection_mode="multi-row"` |
| app.py profile section | full_df | percentile computed against full_df[full_df['Pos']==pos] pool | WIRED | Lines 413, 433, 567, 658 |
| app.py similar player button | st.session_state['profile_player'] | st.button click + st.rerun() | WIRED | Lines 524-525, 519-520 |
| app.py radar traces | score_* columns normalized by pillar weight | divide score_x by pillar_weight/100 | WIRED | Lines 408, 420 |
| app.py comparison profile | COMPARISON_PALETTE | palette[i % len(palette)] per player | WIRED | Line 782 |
| app.py scatter | highlighted_players | active_players["Player"].tolist() | WIRED | Lines 1061, 1085 |
| app.py stat table raw cell | raw_col in player_row.index | strip _p90 suffix + index lookup | WIRED | Lines 475-480, 494-495 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| FILTER-07 | 06-01-PLAN | Player name search in sidebar, case-insensitive | SATISFIED | filter_by_name() + PLAYER SEARCH widget wired; REQUIREMENTS.md line 38 [x] |
| PROFILE-01 | 06-02-PLAN | Header block: name, age, nationality, club, league, position, market value | SATISFIED | render_single_profile() lines 382-395; REQUIREMENTS.md line 55 [x] |
| PROFILE-02 | 06-02-PLAN | Radar chart 5 pillars vs peer median, filled polygon | SATISFIED | build_radar_figure() with PEER MEDIAN trace; REQUIREMENTS.md line 56 [x] |
| PROFILE-03 | 06-02-PLAN | Per-90 stat table: stat name, raw value, per-90 value, percentile rank with colored bar | SATISFIED | 4-column table (STAT/RAW/PER 90/PERCENTILE) at lines 438-500; raw derived from _p90 suffix stripping; REQUIREMENTS.md line 57 [x] |
| PROFILE-04 | 06-02-PLAN | Scatter chart highlight with distinct marker | SATISFIED | size=14, white border at lines 796-798; REQUIREMENTS.md line 58 [x] |
| PROFILE-05 | 06-02-PLAN | Similar Players panel: Player, Club, League, Age, Market Value, UV Score | SATISFIED | render_single_profile() lines 494-527; REQUIREMENTS.md line 59 [x] |
| PROFILE-06 | 06-03-PLAN | Multi-player comparison: overlaid radar, per-player stat columns, multi-highlight scatter | SATISFIED | render_comparison_profile() lines 529-715; wired at line 1051 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | No TODOs, stubs, or empty implementations found in Phase 6 code |

### Human Verification Required

#### 1. Single-player profile rendering with RAW column

**Test:** Run `streamlit run app.py`, click any shortlist row
**Expected:** PLAYER PROFILE section appears with: filled radar polygon + dotted PEER MEDIAN, 4-column stat table (STAT | RAW | PER 90 | PERCENTILE) with red/amber/green bars, player highlighted on scatter, SIMILAR PLAYERS cards
**Why human:** Streamlit rendering requires live browser; automated tests only cover pure-Python logic

#### 2. PLAYER SEARCH real-time filter

**Test:** Type a partial name (e.g. "son") in the PLAYER SEARCH box at the top of the sidebar
**Expected:** Shortlist table narrows in real-time to only rows matching the query (case-insensitive)
**Why human:** Streamlit widget interaction requires live browser

#### 3. Comparison mode (2-3 row selection)

**Test:** Ctrl/Cmd+click 2-3 rows in the shortlist table
**Expected:** View switches to PLAYER PROFILE — COMPARISON; mini header cards with distinct left-border colors; radar shows one polygon per player plus PEER MEDIAN; stat table has one column per player
**Why human:** Multi-row selection requires browser interaction

#### 4. 4th row selection cap

**Test:** Attempt to select a 4th row in the shortlist
**Expected:** Yellow warning banner "MAX 3 PLAYERS — Selection limited to first 3." appears; only 3 players profiled
**Why human:** Row selection requires browser

#### 5. Similar player click navigation

**Test:** Click "View Profile" on a similar player card
**Expected:** Profile updates to show the clicked player (name in header changes)
**Why human:** Button click triggers st.rerun() — needs live browser session

### Gaps Summary

No gaps remain. Both previously identified gaps have been resolved:

1. **PROFILE-03 raw value column** — The stat table now renders 4 columns. The RAW header appears at `app.py` lines 442-443. Each data row strips the `_p90` suffix from the stat column name (`stat_col[:-4]`), looks up the resulting column in the player row, and formats it to 1 decimal place — or shows "—" if the column is absent or NaN (lines 475-480). The raw_str cell is rendered as the second `<td>` in each row (lines 494-495). The pillar group header `colspan` is set to 4 (line 457), matching the 4-column layout.

2. **REQUIREMENTS.md checkbox update** — All 6 requirements (FILTER-07, PROFILE-01, PROFILE-02, PROFILE-03, PROFILE-04, PROFILE-05) now show `- [x]` in `.planning/REQUIREMENTS.md`. The only remaining outstanding items are the 5 human-browser verification steps listed above, which are expected for any Streamlit application.

---

_Verified: 2026-03-18T07:30:00Z_
_Verifier: Claude (gsd-verifier)_
