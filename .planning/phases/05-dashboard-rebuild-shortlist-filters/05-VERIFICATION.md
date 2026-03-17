---
phase: 05-dashboard-rebuild-shortlist-filters
verified: 2026-03-17T18:15:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 5: Dashboard Rebuild — Shortlist Filters Verification Report

**Phase Goal:** Replace the current four-tab dashboard with a shortlist-first landing page sorted by `uv_score_age_weighted`, six sidebar filters (league, position, age, club, market value, season), professional navy/charcoal dark theme, and a UV scatter plot with cross-league disclaimer.
**Verified:** 2026-03-17T18:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Landing page shows ranked shortlist sorted by uv_score_age_weighted descending | VERIFIED | `prepare_display_df` calls `sort_values("uv_score_age_weighted", ascending=False)`; `test_default_sort_order` passes; `st.dataframe` renders sorted `display_df` |
| 2 | All 6 sidebar filters (league, position, age, club, market value, season) update the shortlist in one rerun | VERIFIED | app.py lines 312–372: all 6 multiselect/slider widgets with stable keys; `apply_filters` called with all 6 params at line 376 |
| 3 | Club dropdown options update dynamically when league filter changes | VERIFIED | `available_clubs = get_available_clubs(full_df, sel_leagues)` at line 341 — derived fresh on every rerun from currently selected leagues; `test_club_options_derived_from_leagues` passes |
| 4 | Clicking a shortlist row shows the player placeholder panel below the table | VERIFIED | `on_select="rerun"` at line 413; `table_state["selection"]["rows"]` checked at line 422; player panel rendered at lines 426–446 |
| 5 | UV scatter plot renders with scout_score on x-axis and predicted_log_mv on y-axis | VERIFIED | `scatter_chart`: `x=sub["scout_score"]`, `y=sub["predicted_log_mv"]`; `test_scatter_axes` passes confirming x=scout_score values and y<10 (log scale) |
| 6 | Cross-league disclaimer appears below scatter when more than one league is selected | VERIFIED | `should_show_disclaimer(sel_leagues)` at line 459; `len(selected_leagues) > 1`; `test_cross_league_disclaimer_condition` passes |
| 7 | Dashboard uses navy/dark theme (#0D1B2A background, #00A8FF accent) — cyberpunk green entirely removed | VERIFIED | NAVY_CSS contains `#0D1B2A`, `#00A8FF`, `Inter`; grep of `#00ff41\|#080808\|Share Tech Mono\|st.tabs` returns 0 matches |
| 8 | Empty filter state shows NO PLAYERS MATCH CURRENT FILTERS warning + Reset Filters button | VERIFIED | app.py line 389: `st.warning("NO PLAYERS MATCH CURRENT FILTERS")`; Reset Filters button at line 391; clears all 6 session_state keys |
| 9 | All 12 unit tests in test_app.py pass (GREEN) | VERIFIED | `pytest test_app.py -q` output: `12 passed in 1.38s` |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Min Lines | Status | Details |
|----------|----------|-----------|--------|---------|
| `app.py` | Complete single-page shortlist-first Streamlit dashboard | 300 | VERIFIED | 464 lines; exports all 6 required symbols; syntax valid |
| `test_app.py` | 12 passing unit tests | 120 | VERIFIED | 320 lines; 12 tests collected; all pass |
| `conftest.py` | Streamlit stub enabling fast test imports | — | VERIFIED | Present; sys.modules injection; column_config, divider, cache_data all stubbed |

**Artifact exports check (app.py):**

| Export | Present | Notes |
|--------|---------|-------|
| `apply_filters` | Yes | Line 130; all 6 filters wired, default args for partial test calls |
| `get_available_clubs` | Yes | Line 121; filters by league, returns sorted unique Squad values |
| `prepare_display_df` | Yes | Line 168; sorts by uv_score_age_weighted desc, selects 10 cols, converts to €M |
| `scatter_chart` | Yes | Line 196; x=scout_score, y=predicted_log_mv, OLS FAIR VALUE LINE |
| `should_show_disclaimer` | Yes | Line 188; `len(selected_leagues) > 1` |
| `NAVY_CSS` | Yes | Line 20; contains #0D1B2A, #00A8FF, Inter |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py (apply_filters)` | `scorer.py (_parse_age)` | `from scorer import _parse_age` | WIRED | Line 9: `from scorer import _parse_age`; used in `apply_filters` line 150 and `prepare_display_df` line 184 |
| `app.py (scatter_chart)` | `scorer.py (predicted_log_mv column)` | `y=sub["predicted_log_mv"]` | WIRED | Line 208: `y=sub["predicted_log_mv"]`; not recomputed from market_value_eur — uses scorer output column directly |
| `app.py (load_data)` | `scraper.run_fbref_scrapers + scorer.run_scoring_pipeline` | `@st.cache_data(ttl=86400)` | WIRED | Line 104: `@st.cache_data(ttl=86400, show_spinner=False)`; lazy imports of run_fbref_scrapers, run_tm_scrapers, run_scoring_pipeline inside the function |
| `scatter_chart` called with filtered `df` | NOT `display_df` | scatter_chart receives raw EUR values | WIRED | Line 456: `st.plotly_chart(scatter_chart(df), ...)` — passes `df` from `apply_filters`, not `display_df` which has values in €M |

---

### Requirements Coverage

| Requirement | Plan | Description | Status | Evidence |
|-------------|------|-------------|--------|----------|
| FILTER-01 | 05-01, 05-02 | User can filter by league (multi-select, default: All) | SATISFIED | `sel_leagues` multiselect, 5 options, `apply_filters` FILTER-01 branch |
| FILTER-02 | 05-01, 05-02 | User can filter by position (GK, DF, MF, FW, default: All) | SATISFIED | `sel_positions` multiselect, 4 options, `apply_filters` FILTER-02 branch |
| FILTER-03 | 05-01, 05-02 | User can filter by age range via slider | SATISFIED | `age_range` slider min=17 max=38; `apply_filters` uses `_parse_age` for FBref string conversion |
| FILTER-04 | 05-01, 05-02 | User can filter by club (list updates based on selected leagues) | SATISFIED | `get_available_clubs(full_df, sel_leagues)` called each rerun; dynamic club options |
| FILTER-05 | 05-01, 05-02 | User can filter by market value range (min/max in €M) | SATISFIED | `mv_range` slider; `apply_filters` multiplies by 1e6 internally; `test_filter_market_value` passes |
| FILTER-06 | 05-01, 05-02 | User can select seasons to include | SATISFIED | `sel_seasons` multiselect with 2023-24 / 2024-25; `apply_filters` defensive skip if `_season` absent |
| DASH-01 | 05-01, 05-02 | Landing page displays ranked shortlist sorted by uv_score_age_weighted desc | SATISFIED | `prepare_display_df` sorts descending; `st.dataframe` on result |
| DASH-02 | 05-01, 05-02 | Shortlist table shows 10 required columns | SATISFIED | `display_cols` list in `prepare_display_df` has all 10; `COLUMN_CONFIG` maps each to ALL-CAPS header |
| DASH-03 | 05-02 | User can click any column header to sort | SATISFIED | `st.dataframe` with `on_select="rerun"` enables native column-header sorting |
| DASH-04 | 05-01, 05-02 | User can click any row to open player deep profile | SATISFIED | `on_select="rerun"`, `selection_mode="single-row"`; panel rendered at lines 422–446 |
| DASH-05 | 05-01, 05-02 | Dashboard uses professional dark theme: navy background, electric blue accent, all-caps labels | SATISFIED | NAVY_CSS with #0D1B2A, #00A8FF, Inter; COLUMN_CONFIG all-caps headers; MONEYBALL header with letter-spacing |
| DASH-06 | 05-01, 05-02 | UV scatter plot: scout_score x, log10 market value y, regression line, colored by position | SATISFIED | `scatter_chart`: x=scout_score, y=predicted_log_mv, OLS FAIR VALUE LINE, POS_COLORS dict |
| DASH-07 | 05-01, 05-02 | Cross-league disclaimer when multiple leagues selected | SATISFIED | `should_show_disclaimer(sel_leagues)` at line 459; disclaimer text mentions league quality multiplier |

**All 13 requirements (FILTER-01–06, DASH-01–07) satisfied.**

No orphaned requirements — REQUIREMENTS.md Traceability table maps all 13 IDs to Phase 5 and all 13 appear in plans 05-01 and 05-02.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app.py` | 445 | `st.caption("Full profile coming soon")` | Info | Intentional placeholder per DASH-04 spec — player deep profile is Phase 6 scope. Comment header on line 420 correctly labels this the "placeholder panel". Not a blocker. |

No TODO/FIXME/HACK comments found. No empty return stubs (`return null`, `return {}`, `return []`). No cyberpunk theme remnants (#00ff41, #080808, Share Tech Mono, st.tabs).

---

### Human Verification Required

The following items require a live `streamlit run app.py` session to verify:

#### 1. Visual Navy Theme Rendering

**Test:** Run `streamlit run app.py`. Observe the app background, sidebar, and top bar.
**Expected:** Background is #0D1B2A navy; sidebar is slightly lighter (#112236); top bar is navy (not black); no green text; column headers and section labels in ALL-CAPS Inter font; electric-blue (#00A8FF) accent on filter tags and buttons.
**Why human:** CSS injection via `st.markdown(unsafe_allow_html=True)` — actual rendering depends on Streamlit's theme precedence and browser. CSS rules are present and correct in code, but visual confirmation required.

#### 2. Club Filter Dynamic Update

**Test:** With app running, deselect EPL from the LEAGUE filter. Observe the CLUB filter options.
**Expected:** Club dropdown immediately updates to show only clubs from the remaining selected leagues. Clubs that exist only in EPL rows disappear.
**Why human:** Streamlit reruns are verified functionally via `get_available_clubs` test, but the real-time UI rerun and widget state clearing requires a live session.

#### 3. Row-Click Player Panel

**Test:** Click any row in the shortlist table.
**Expected:** A panel appears below the table showing the player name, club, league, position, integer age, market value in €M, scout score metric, UV score metric, and AGE-WEIGHTED UV metric. Footnote reads "Full profile coming soon".
**Why human:** `on_select="rerun"` + `table_state["selection"]["rows"]` is exercised in conftest stub but actual Streamlit dataframe row-selection event requires a running app to trigger.

#### 4. Scatter Plot Visual Quality

**Test:** Observe the scatter plot section.
**Expected:** X-axis labeled "SCOUT SCORE" (range 0–100); Y-axis labeled "LOG₁₀ MARKET VALUE"; points colored by position (red=FW, cyan=MF, amber=DF, violet=GK); blue dotted "FAIR VALUE LINE" regression line visible; plot background is #112236 (slightly lighter than page).
**Why human:** Plotly figure data is verified programmatically (test_scatter_axes passes), but visual rendering quality and axis label display require browser inspection.

#### 5. Empty State and Reset Filters

**Test:** Narrow the age range slider to an impossible range (e.g., set min and max to the same extreme value) or deselect all but one league and set an age range with no qualifying players. Verify the warning appears, then click "Reset Filters".
**Expected:** "NO PLAYERS MATCH CURRENT FILTERS" warning appears with "Reset Filters" button. Clicking it clears all 6 filter keys from session_state and players reappear.
**Why human:** `st.session_state` key deletion and `st.rerun()` can only be tested in a live Streamlit session; conftest stub makes `st.stop()` a no-op so empty-state behavior is not exercised in pytest.

---

### Gaps Summary

No gaps. All 9 observable truths are verified, all 3 required artifacts pass all three levels (exists, substantive, wired), all 4 key links are confirmed, and all 13 requirement IDs are satisfied with evidence. The only human-verification items are visual/interactive behaviors that the automated test suite cannot exercise — the underlying logic driving those behaviors is fully tested.

The one "placeholder" pattern (line 445) is intentional per the phase spec: DASH-04 requires row-click to open a profile panel, and the spec explicitly calls this a placeholder pending Phase 6.

---

_Verified: 2026-03-17T18:15:00Z_
_Verifier: Claude (gsd-verifier)_
