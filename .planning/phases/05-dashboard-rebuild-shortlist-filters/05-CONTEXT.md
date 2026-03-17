# Phase 5: Dashboard Rebuild — Shortlist & Filters - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the existing 4-tab cyberpunk dashboard (app.py) with a single-page shortlist-first layout: professional dark theme, 6 sidebar filters, ranked shortlist table as the primary view, UV scatter plot below the table, and row-selection wired for Phase 6 deep profile. No scraper, merger, or scorer changes. All work in app.py.

</domain>

<decisions>
## Implementation Decisions

### Theme
- Background: `#0D1B2A` (navy/dark charcoal)
- Primary text: `#E8EDF2` (off-white)
- Accent: `#00A8FF` (electric blue) — used for buttons, borders, highlights, active filter states, selected row indicator
- Column headers and section labels: ALL-CAPS
- Replace existing cyberpunk green-on-black (`#080808` / `#00ff41` / Share Tech Mono) entirely
- Plotly charts updated to match new navy theme (replace `CYBER_LAYOUT` dict)

### Page Layout
- Single scrolling page — no tabs
- Sidebar: all 6 filters (league, position, age, club, market value, season)
- Main area top: shortlist table (ranked by `uv_score_age_weighted` descending by default)
- Main area below table: UV scatter plot (scout_score x-axis, log10 market_value y-axis, colored by position)
- Cross-league disclaimer appears below/on scatter when >1 league selected (DASH-07)
- All current content removed: top-5 player cards, radar chart, KPI strip, pillar bar chart — clean slate

### Shortlist Table
- Default sort: `uv_score_age_weighted` descending
- Columns: Player, Club, League, Position, Age, Scout Score, UV Score, Age-Weighted UV Score, Market Value (€M), Value Gap (€M)
- Column headers: ALL-CAPS
- Sortable by any column (Streamlit `st.dataframe` with `column_config` supports this natively)
- Row selection wired using `st.dataframe(selection_mode="single-row")` or equivalent Streamlit ≥1.35 API

### Row-Click Behavior (Phase 5 placeholder)
- Implement the row selection mechanism in Phase 5
- When a row is selected: show a placeholder panel below the table / in a `st.expander` or `st.container` — displays player name, position, club, league, age, market value, scout score, UV score, age-weighted UV score
- Phase 6 replaces this placeholder panel with the full deep profile (radar chart, stat table, similar players)
- Placeholder text: "Full profile coming soon" or similar minimal indicator

### Filters (Sidebar)
- **League** (FILTER-01): multi-select, options: EPL, LaLiga, Bundesliga, SerieA, Ligue1. Default: all 5 selected
- **Position** (FILTER-02): multi-select, options: GK, DF, MF, FW. Default: all 4 selected
- **Age range** (FILTER-03): range slider, min 17 / max 38. Default: 17–38
- **Club** (FILTER-04): multi-select, dynamically populated from clubs present in currently selected leagues. Default: all (no restriction). Updates on league filter change
- **Market value** (FILTER-05): range slider in €M, min 0. Default: no upper restriction (max = max in dataset). Display in €M
- **Season** (FILTER-06): multi-select, options: 2023-24, 2024-25. Default: both selected
- Filter order in sidebar: League → Position → Age → Club → Market Value → Season

### Empty State
- When all filters combine to 0 results: show warning message + a **Reset Filters** button that returns all filters to their defaults
- Prevents the dead-end blank screen of the current app

### Scatter Plot (DASH-06)
- X-axis: `scout_score` (0–100)
- Y-axis: `log10(market_value_eur)` (existing `predicted_log_mv` column available, or recompute)
- Points colored by position group (FW, MF, DF, GK) — reuse existing position color mapping
- OLS regression line shown
- Cross-league disclaimer (DASH-07): when >1 league selected, show visible note that cross-league comparison uses a league quality multiplier

### Claude's Discretion
- Exact Streamlit widget API for row selection (version-dependent — researcher to confirm)
- Exact CSS for navy theme (specific shades within the #0D1B2A range)
- Placeholder panel layout details (expander vs. inline container)
- Whether to show player count anywhere (e.g., "Showing 347 players") — informational only

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements for this phase
- `.planning/REQUIREMENTS.md` §FILTER-01 through FILTER-06 — filter specs
- `.planning/REQUIREMENTS.md` §DASH-01 through DASH-07 — shortlist table, design, and scatter specs

### Existing dashboard to replace
- `app.py` — full current implementation; Phase 5 rewrites this file. Researcher must read it to understand what to keep (`load_data`, `run_scoring_pipeline` imports, caching) vs. what to replace (all CSS, layout, tabs, charts).

### Existing scoring output columns (what the table/scatter will consume)
- `scorer.py` — `run_scoring_pipeline()` return columns: `Player`, `Squad`, `Pos`, `Age`, `League`, `market_value_eur`, `scout_score`, `uv_score`, `uv_score_age_weighted`, `value_gap_eur`, `league_quality_multiplier`, `similar_players`
- `config.py` — `PILLARS_FW`, `PILLARS_MF`, `PILLARS_DF`, `GK_PILLARS` — pillar color map needed for scatter legend

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `load_data()` + `@st.cache_data(ttl=86400)` — caching pattern is correct, keep as-is. Signature may need updating to accept league/season params if needed.
- `scatter_chart(df)` — exists but uses wrong axes (current: x=market_value_eur linear, y=scout_score). Phase 5 needs x=scout_score, y=log10(market_value). Rewrite rather than adapt.
- `fmt_value()` and `fmt_gap()` helpers — keep for table cell formatting
- `PILLAR_COLS` and position color map (`{"FW": "#ff3131", "MF": "#00ff41", "DF": "#f5a623", "GK": "#00cfff"}`) — reuse position colors, update MF color to fit new theme if green clashes

### Established Patterns
- Sidebar filter pattern: `st.multiselect` + `st.slider` already in use — same pattern, 4 more filters added
- `st.cache_data.clear()` on refresh button — keep
- All Plotly charts use a layout dict (`CYBER_LAYOUT`) — replace with new `NAVY_LAYOUT` dict for the new theme

### Integration Points
- `app.py` imports from `scraper`, `scorer` — these stay unchanged
- New columns from Phase 4 (`league_quality_multiplier`, `similar_players`) are available in the DataFrame; Phase 5 only needs `league_quality_multiplier` for the scatter disclaimer logic; `similar_players` is Phase 6
- `League` column now present on every player row (Phase 3) — enables the league filter

</code_context>

<specifics>
## Specific Ideas

- The placeholder panel for row click should be minimal but functional — enough for Phase 6 to know exactly where to inject the full profile component
- Scatter x-axis = scout_score (not market_value) matches the REQUIREMENTS spec: "scout score (x-axis) vs. log10 market value (y-axis)"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-dashboard-rebuild-shortlist-filters*
*Context gathered: 2026-03-17*
