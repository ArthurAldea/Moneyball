# Phase 6: Player Deep Profile - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the player deep profile panel in `app.py` — triggered by row selection in the shortlist table. Covers: header block, radar chart, per-90 stat table with percentile bars, UV scatter highlight, similar players panel, multi-player comparison mode (up to 3), and a player name search filter in the sidebar. No changes to scraper, merger, or scorer.

</domain>

<decisions>
## Implementation Decisions

### Profile section placement
- Profile appears **inline below the shortlist table, above the UV scatter chart** — same single-page layout as Phase 5, no page navigation
- Phase 5 placeholder panel (lines ~440–466 in app.py) is replaced entirely by the full profile
- Section label: `PLAYER PROFILE` (ALL-CAPS, using existing `.section-header` CSS class) above the header block

### Profile internal layout (single player mode)
- Two-column layout: radar chart on the **left (~40% width)**, per-90 stat table on the **right (~60% width)**
- Both visible at the same time without scrolling within the profile section
- Similar players panel: **full-width row below** the two-column radar + stat table

### Comparison mode (2–3 players selected)
- **Max 3 players** — enforced programmatically; if user selects a 4th row, show a warning and ignore the 4th selection
- Table selection mode changes from `"single-row"` to `"multi-row"` (Streamlit ≥1.35 API)
- **Header block**: one mini header card per selected player, arranged side-by-side horizontally (name, club, league, position, market value)
- **Radar chart**: one filled polygon per player overlaid on the same chart, with distinct colors per player and a legend. Position-peer median polygon still shown for reference.
- **Per-90 stat table**: side-by-side columns — rows = stats (grouped by pillar), columns = players. Each player gets a per-90 value and a percentile bar per stat row.
- **Similar players panel**: one `SIMILAR TO [NAME]` row per selected player, stacked vertically below the radar + stat table

### Player name search filter (FILTER-07)
- **Position in sidebar**: top of sidebar, above the LEAGUE filter — first item the user sees
- **Search scope**: applied **after** the existing 6 filters (searches within the already-filtered pool, not the full dataset)
- Implementation: `st.text_input` with label "PLAYER SEARCH", case-insensitive `str.contains()` on the `Player` column. Empty input = no filter applied.

### Similar players interactivity
- Each similar player card is **clickable** — clicking navigates to that player's profile
- Clicking a similar player: profile area updates to show the clicked player, shortlist table selection deselects (clears `st.session_state` selection)
- Navigation implemented via `st.session_state` (store the clicked player name, trigger rerun, profile section reads from session state as override)

### Claude's Discretion
- Exact Plotly radar chart configuration (fill opacity, line width, hover text format)
- Exact percentile bar implementation (HTML progress bars via `st.dataframe` column config, or custom HTML via `st.markdown`)
- Color assignment per player in comparison mode (reuse `POS_COLORS` for single-player single-color, or use a fixed comparison palette of 3 distinct colors)
- How to display the `Nation` column (3-letter FBref code e.g. "ENG") — either display as-is or attempt a mapping to full country name
- Exact pixel heights for the radar and stat table in the two-column layout

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements for this phase
- `.planning/REQUIREMENTS.md` §PROFILE-01 through PROFILE-06 — full player profile and comparison mode specs
- `.planning/REQUIREMENTS.md` §FILTER-07 — player name search filter spec

### Existing dashboard (Phase 5 output — primary file to modify)
- `app.py` — complete current implementation; Phase 6 modifies this file only. Key sections:
  - Lines ~431–438: `st.dataframe(selection_mode="single-row", ...)` → change to `"multi-row"`, add 3-player cap
  - Lines ~440–466: placeholder profile panel → replace with full profile implementation
  - Lines ~469–483: UV scatter chart → add `highlighted_players` param for selected player markers

### Scoring output consumed by profile
- `scorer.py` — `compute_similar_players()` (lines ~272–319): `similar_players` column is a **JSON string** containing a list of 5 dicts: `[{"player": str, "club": str, "league": str, "uv_score_age_weighted": float}, ...]`. **Note:** `Age` and `market_value_eur` are NOT in the JSON — must be joined from the full DataFrame by player+club key to satisfy PROFILE-05.
- `scorer.py` — pillar score columns present on every row: `score_attacking`, `score_progression`, `score_creation`, `score_defense`, `score_retention` (same 5 keys for all positions including GK)

### Pillar definitions (for radar axis labels and stat table grouping)
- `config.py` — `PILLARS_FW`, `PILLARS_MF`, `PILLARS_DF`, `GK_PILLARS` — each shares the same 5 pillar keys (`attacking`, `progression`, `creation`, `defense`, `retention`) but maps to different stats. Radar axes are always these 5 pillars regardless of position.

### Phase 5 context (prior design decisions)
- `.planning/phases/05-dashboard-rebuild-shortlist-filters/05-CONTEXT.md` — locked theme values, filter order, scatter chart design, scatter x/y axes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `NAVY_LAYOUT` dict (app.py ~line 88) — apply to all new Plotly charts (radar, modified scatter)
- `POS_COLORS` (app.py ~line 99): `{"FW": "#FF5757", "MF": "#4CC9F0", "DF": "#F5A623", "GK": "#A78BFA"}` — reuse for position-colored elements; in comparison mode, use a fixed 3-color palette instead (e.g. `#00A8FF`, `#FF5757`, `#F5A623`) so players are distinguishable regardless of position
- `.section-header` CSS class (NAVY_CSS ~line 42) — reuse for `PLAYER PROFILE` section label
- `_parse_age()` imported from scorer — use in header block to display integer age
- `scatter_chart(df)` — extend to accept an optional `highlighted_players: list[str]` param; highlighted rows get a distinct marker (larger size, white border, label)
- `apply_filters()` — name search is a 7th filter step appended after the existing 6; keep it as a separate inline filter (not inside `apply_filters`) since it operates on `display_df` not `df`
- `get_cache_timestamp()`, `should_show_disclaimer()` — unchanged

### Established Patterns
- `st.session_state` already used for filter keys (`sel_leagues`, `age_range`, etc.) — extend for profile navigation: store `st.session_state["profile_player"]` as the override when a similar player is clicked
- `st.dataframe(on_select="rerun", selection_mode=...)` — Phase 5 already uses this pattern; change `single-row` to `multi-row`
- Plotly charts use `fig.add_trace()` loop per position — radar will use the same loop pattern per selected player
- All section headers use `st.markdown("<div class='section-header'>LABEL</div>", unsafe_allow_html=True)`

### Integration Points
- Profile section sits between the shortlist table block and the scatter chart block in app.py (after ~line 438, before ~line 468)
- `Nation` column is available on every player row (survives from `stats_standard` base table in merger — NOT dropped). It contains a 3-letter FBref country code (e.g. "ENG", "ESP", "BRA").
- `similar_players` column must be parsed with `json.loads()` before use; `Age` and `market_value_eur` for the similar player cards must be looked up from `full_df` (the unfiltered DataFrame) by matching player name + club
- The per-90 stat columns available for the stat table: `Gls_p90`, `Ast_p90`, `SoT_p90`, `Sh_p90`, `Int_p90`, `TklW_p90`, `Fld_p90`, `Crs_p90`, `Saves_p90` (GK only) — all already computed by merger

</code_context>

<specifics>
## Specific Ideas

- Position-peer median for the radar chart: computed on-the-fly from `full_df` filtered to matching `Pos`, across all leagues — use the 5 `score_*` pillar columns
- In comparison mode, the stat table rows should still show the percentile bar for each player's value (relative to cross-league position peers), not just raw numbers
- The `PLAYER SEARCH` input at the top of the sidebar should use `key="player_search"` and be cleared on "Reset Filters"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-player-deep-profile*
*Context gathered: 2026-03-18*
