# Phase 5: Dashboard Rebuild — Shortlist & Filters - Research

**Researched:** 2026-03-17
**Domain:** Streamlit dashboard rewrite — layout, filters, dataframe row selection, Plotly theming
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Theme**
- Background: `#0D1B2A` (navy/dark charcoal)
- Primary text: `#E8EDF2` (off-white)
- Accent: `#00A8FF` (electric blue) — used for buttons, borders, highlights, active filter states, selected row indicator
- Column headers and section labels: ALL-CAPS
- Replace existing cyberpunk green-on-black (`#080808` / `#00ff41` / Share Tech Mono) entirely
- Plotly charts updated to match new navy theme (replace `CYBER_LAYOUT` dict)

**Page Layout**
- Single scrolling page — no tabs
- Sidebar: all 6 filters (league, position, age, club, market value, season)
- Main area top: shortlist table (ranked by `uv_score_age_weighted` descending by default)
- Main area below table: UV scatter plot (scout_score x-axis, log10 market_value y-axis, colored by position)
- Cross-league disclaimer appears below/on scatter when >1 league selected (DASH-07)
- All current content removed: top-5 player cards, radar chart, KPI strip, pillar bar chart — clean slate

**Shortlist Table**
- Default sort: `uv_score_age_weighted` descending
- Columns: Player, Club, League, Position, Age, Scout Score, UV Score, Age-Weighted UV Score, Market Value (€M), Value Gap (€M)
- Column headers: ALL-CAPS
- Sortable by any column (Streamlit `st.dataframe` with `column_config` supports this natively)
- Row selection wired using `st.dataframe(selection_mode="single-row")` or equivalent Streamlit ≥1.35 API

**Row-Click Behavior (Phase 5 placeholder)**
- Implement the row selection mechanism in Phase 5
- When a row is selected: show a placeholder panel below the table / in a `st.expander` or `st.container` — displays player name, position, club, league, age, market value, scout score, UV score, age-weighted UV score
- Phase 6 replaces this placeholder panel with the full deep profile (radar chart, stat table, similar players)
- Placeholder text: "Full profile coming soon" or similar minimal indicator

**Filters (Sidebar)**
- League (FILTER-01): multi-select, options: EPL, LaLiga, Bundesliga, SerieA, Ligue1. Default: all 5 selected
- Position (FILTER-02): multi-select, options: GK, DF, MF, FW. Default: all 4 selected
- Age range (FILTER-03): range slider, min 17 / max 38. Default: 17–38
- Club (FILTER-04): multi-select, dynamically populated from clubs present in currently selected leagues. Default: all (no restriction). Updates on league filter change
- Market value (FILTER-05): range slider in €M, min 0. Default: no upper restriction (max = max in dataset). Display in €M
- Season (FILTER-06): multi-select, options: 2023-24, 2024-25. Default: both selected
- Filter order in sidebar: League → Position → Age → Club → Market Value → Season

**Empty State**
- When all filters combine to 0 results: show warning message + a Reset Filters button that returns all filters to their defaults
- Prevents the dead-end blank screen of the current app

**Scatter Plot (DASH-06)**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FILTER-01 | User can filter by league (multi-select: EPL, LaLiga, Bundesliga, SerieA, Ligue1; default: All) | `st.multiselect` with league keys from `FBREF_LEAGUES` in config.py |
| FILTER-02 | User can filter by position (GK, DF, MF, FW; default: All) | `st.multiselect` against `Pos` column; position values are already normalized to first token by scorer.py |
| FILTER-03 | User can filter by age range via a slider (min/max; default: 17–38) | `st.slider` with tuple return; `Age` column requires `_parse_age()` float conversion before numeric compare |
| FILTER-04 | User can filter by club via a multi-select dropdown (list updates based on selected leagues) | `st.multiselect` with options derived from `full_df[full_df["League"].isin(sel_leagues)]["Squad"].unique()` — must re-derive options on every league filter change and handle club filter reset on league change |
| FILTER-05 | User can filter by market value range (min/max in €M; default: no restriction) | `st.slider` in €M units; `market_value_eur` column is in raw EUR — divide by 1e6 for display, multiply back for filtering |
| FILTER-06 | User can select seasons to include (2024-25, 2025-26, or both; default: both) | `st.multiselect`; `_season` column present in merged data (from `single_season_flag` decision in Phase 03) |
| DASH-01 | Landing page displays a ranked shortlist table sorted by `uv_score_age_weighted` (descending) by default | Pre-sort `df.sort_values("uv_score_age_weighted", ascending=False)` before passing to `st.dataframe` |
| DASH-02 | Shortlist table shows 10 specific columns | `column_config` with display name overrides; source columns confirmed in `run_scoring_pipeline` output |
| DASH-03 | User can click any column header to sort the shortlist by that column | Native to `st.dataframe` — no extra implementation needed |
| DASH-04 | User can click any row to open the player deep profile | `on_select="rerun"`, `selection_mode="single-row"` confirmed present in installed Streamlit 1.52.2 |
| DASH-05 | Dashboard uses professional dark theme | Full CSS replacement via `st.markdown(unsafe_allow_html=True)`; UI-SPEC provides all exact values |
| DASH-06 | Dashboard includes UV scatter plot: scout_score x-axis vs log10 market value y-axis | `predicted_log_mv` column already computed by `compute_efficiency()`; scatter axes confirmed; OLS line needed |
| DASH-07 | Cross-league disclaimer when multiple leagues selected | `st.caption()` below scatter; condition: `len(selected_leagues) > 1` |
</phase_requirements>

---

## Summary

Phase 5 is a full rewrite of `app.py` only — no changes to scraper, merger, scorer, or config. The existing file is the cyberpunk 4-tab dashboard; Phase 5 replaces it entirely with a single-page shortlist-first layout using a professional navy theme.

The Streamlit row-selection API has been verified against the installed version (1.52.2). The confirmed pattern is `st.dataframe(df, on_select="rerun", selection_mode="single-row")` which returns a `DataframeState` dict. Selection is accessed via `state["selection"]["rows"]` (a list of integer row indices). When the list is non-empty, `df.iloc[state["selection"]["rows"][0]]` retrieves the selected player Series.

The main structural challenge is the club filter (FILTER-04), which must re-derive its options dynamically whenever the league filter changes. The current app has no such dependency between filters; this pattern requires computing `available_clubs` after applying the league filter, and also handling the edge case where a previously selected club is no longer valid after a league change.

**Primary recommendation:** Rewrite app.py as a clean single-page layout. Keep `load_data()` caching pattern unchanged. Replace `CYBER_LAYOUT` with `NAVY_LAYOUT`. Wire `st.dataframe` selection for DASH-04. Implement the club filter as a derived multiselect computed after league filter is applied.

---

## Standard Stack

### Core (all installed, versions confirmed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | 1.52.2 | App framework, all widgets and layout | Already in use; confirmed API for this version |
| plotly | 6.6.0 | Interactive charts (scatter, trendline) | Already in use; `go.Figure` scatter pattern established |
| pandas | (existing) | DataFrame filtering, column manipulation | All data arrives as pandas DataFrame from pipeline |
| numpy | (existing) | `log10` for y-axis computation, OLS polyfit | Already used in `scatter_chart` |

### No New Dependencies

Phase 5 requires zero new library installations. All needed functionality is covered by the existing stack.

**Installation:**
```bash
# No new installs required
```

---

## Architecture Patterns

### Recommended Project Structure

Phase 5 is a single-file rewrite:
```
app.py           # Full replacement — single scrolling page, navy theme
                 # All other files unchanged (scorer.py, merger.py, scraper.py, config.py)
```

### Pattern 1: Filter Chain with Derived Club Options

**What:** Apply filters sequentially. Club options must be derived from the league-filtered full DataFrame, not from the display DataFrame.

**When to use:** Any time one filter's options depend on another filter's value.

```python
# Source: app.py filter logic pattern (verified against existing code)

# Step 1: compute available clubs from full_df filtered by selected leagues
available_clubs = sorted(
    full_df[full_df["League"].isin(sel_leagues)]["Squad"].dropna().unique()
)

# Step 2: club filter — default = all available (no restriction)
sel_clubs = st.multiselect("CLUB", options=available_clubs, default=available_clubs)

# Step 3: apply all filters sequentially
df = full_df.copy()
df = df[df["League"].isin(sel_leagues)]
df = df[df["Pos"].isin(sel_positions)]
age_float = df["Age"].apply(_parse_age)
df = df[(age_float >= age_min) & (age_float <= age_max)]
df = df[df["Squad"].isin(sel_clubs)]
mv_min_eur, mv_max_eur = mv_range[0] * 1e6, mv_range[1] * 1e6
df = df[(df["market_value_eur"] >= mv_min_eur) & (df["market_value_eur"] <= mv_max_eur)]
df = df[df["_season"].isin(sel_seasons)]  # if _season column exists
df = df.sort_values("uv_score_age_weighted", ascending=False).reset_index(drop=True)
```

**Critical note:** `_parse_age()` is already defined in scorer.py and can be imported. The `Age` column contains FBref "25-201" format strings that need float conversion before numeric comparison.

### Pattern 2: Streamlit Row Selection (verified Streamlit 1.52.2)

**What:** `st.dataframe` with `on_select="rerun"` and `selection_mode="single-row"` triggers a rerun on row click; the return value carries `state["selection"]["rows"]`.

```python
# Source: verified via inspect of installed streamlit 1.52.2 elements/arrow.py

state = st.dataframe(
    display_df,
    on_select="rerun",
    selection_mode="single-row",
    use_container_width=True,
    hide_index=True,
    column_config={...},
)

if state["selection"]["rows"]:
    row_idx = state["selection"]["rows"][0]
    selected = display_df.iloc[row_idx]
    # render placeholder panel
```

**Important:** `state` is a `DataframeState` TypedDict. Access via dict notation (`state["selection"]["rows"]`) or attribute notation (`state.selection.rows`) both work. The indices in `state["selection"]["rows"]` are positions in the DataFrame passed to `st.dataframe`, not original DataFrame indices. Since `display_df` is reset-indexed, `iloc[row_idx]` is safe.

### Pattern 3: NAVY_LAYOUT Plotly Dict

**What:** Replace `CYBER_LAYOUT` global dict with `NAVY_LAYOUT` matching the new theme.

```python
# Source: UI-SPEC.md — verified color values

NAVY_LAYOUT = dict(
    paper_bgcolor="#0D1B2A",
    plot_bgcolor="#112236",
    font=dict(family="Inter, system-ui, sans-serif", color="#E8EDF2", size=12),
    margin=dict(t=48, b=48, l=56, r=24),
)

# Position color map for scatter (updated from cyberpunk colors):
POS_COLORS = {
    "FW": "#FF5757",   # warm red
    "MF": "#4CC9F0",   # sky blue (replaces old #00ff41 green)
    "DF": "#F5A623",   # amber (unchanged)
    "GK": "#A78BFA",   # soft violet
}
```

### Pattern 4: OLS Regression Line on Log-Scale Scatter

**What:** The new scatter has x=scout_score, y=log10(market_value). The regression line must be computed in log-space (not linear) since y is already a log value.

```python
# Source: existing scatter_chart() in app.py — adapted for new axes

import numpy as np

# y is already predicted_log_mv (log10 scale) from compute_efficiency()
# x is scout_score (0–100 linear)
x_vals = df["scout_score"].values
y_vals = df["predicted_log_mv"].values  # or np.log10(df["market_value_eur"])

coeffs = np.polyfit(x_vals, y_vals, 1)
x_range = np.linspace(x_vals.min(), x_vals.max(), 100)
y_range = np.polyval(coeffs, x_range)

fig.add_trace(go.Scatter(
    x=x_range,
    y=y_range,
    mode="lines",
    name="FAIR VALUE LINE",
    line=dict(color="#00A8FF", width=1.5, dash="dot"),
))
```

**Critical note:** `predicted_log_mv` is already computed by `compute_efficiency()` in scorer.py. Do NOT recompute `np.log10(market_value_eur)` — use the existing column for y-axis data to keep the scatter consistent with the regression.

### Pattern 5: Empty State with Reset Filters

**What:** When `df.empty` after filtering, show a warning and a button that reruns with all filters reset to defaults.

```python
# Source: CONTEXT.md design decision + UI-SPEC copywriting contract

if df.empty:
    st.warning("NO PLAYERS MATCH CURRENT FILTERS")
    st.caption("Try widening your age range, adding more leagues, or adjusting the market value limits.")
    if st.button("Reset Filters"):
        # Clear all filter session state keys and rerun
        for key in ["sel_leagues", "sel_positions", "age_range", "sel_clubs", "mv_range", "sel_seasons"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    st.stop()
```

### Pattern 6: CSS for Navy Theme

**What:** Single `st.markdown` block at top of app replacing the entire cyberpunk CSS block.

```python
# Source: UI-SPEC.md color, typography, and spacing specifications

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

  html, body, [data-testid="stAppViewContainer"] {
      background-color: #0D1B2A;
      color: #E8EDF2;
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 14px;
      line-height: 1.5;
  }
  [data-testid="stSidebar"] {
      background-color: #112236;
  }
  /* ALL-CAPS column headers via text-transform — source text stays mixed-case in Python */
  .section-header {
      border-left: 3px solid #00A8FF;
      padding: 4px 12px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #E8EDF2;
      margin-bottom: 16px;
  }
  .stButton > button {
      background: transparent;
      color: #00A8FF;
      border: 1px solid #00A8FF;
      font-weight: 600;
      letter-spacing: 0.07em;
      width: 100%;
      min-height: 44px;
      font-family: 'Inter', system-ui, sans-serif;
  }
  .stButton > button:hover {
      background: rgba(0, 168, 255, 0.08);
  }
  /* Muted text for captions, helper copy */
  .stCaption { color: #8DA4B8 !important; }
  /* Multiselect chip accent */
  .stMultiSelect [data-baseweb="tag"] {
      background-color: rgba(0, 168, 255, 0.15);
      color: #00A8FF;
      border: 1px solid #00A8FF;
  }
</style>
""", unsafe_allow_html=True)
```

### Pattern 7: Column Config for Shortlist Table

**What:** Use `st.column_config` to set display names (ALL-CAPS), numeric formatting, and column widths. Source column names in the DataFrame differ from display names.

```python
# Source: UI-SPEC.md component inventory + CONTEXT.md column list

column_config = {
    "Player":                 st.column_config.TextColumn("PLAYER"),
    "Squad":                  st.column_config.TextColumn("CLUB"),
    "League":                 st.column_config.TextColumn("LEAGUE"),
    "Pos":                    st.column_config.TextColumn("POSITION"),
    "Age":                    st.column_config.TextColumn("AGE"),
    "scout_score":            st.column_config.NumberColumn("SCOUT SCORE", format="%.1f"),
    "uv_score":               st.column_config.NumberColumn("UV SCORE", format="%.1f"),
    "uv_score_age_weighted":  st.column_config.NumberColumn("AGE-WEIGHTED UV", format="%.1f"),
    "market_value_eur":       st.column_config.NumberColumn("VALUE (€M)", format="%.1f"),
    "value_gap_eur":          st.column_config.NumberColumn("VALUE GAP (€M)", format="%.1f"),
}
```

**Note:** `market_value_eur` and `value_gap_eur` are stored in raw EUR in the DataFrame. Convert to €M before displaying: `df["market_value_eur"] = df["market_value_eur"] / 1e6`. Do this on the display copy, not on `full_df`.

### Anti-Patterns to Avoid

- **Filtering on `full_df` for club options after league filter applied:** Must compute `available_clubs` from `full_df` filtered by league only — if you use the already-filtered `df`, clubs from other filter steps (position, age) will be incorrectly excluded from the options list.
- **Pre-sorting before `st.dataframe`:** Pre-sort by `uv_score_age_weighted` descending, but do NOT use `st.dataframe`'s built-in sort state as the default — Streamlit doesn't expose a way to set the initial sort column programmatically. Pre-sort in pandas.
- **Using `st.session_state` to persist filter values without keys:** Each `st.multiselect` and `st.slider` must have a stable `key` parameter so that the Reset Filters button can delete them from `st.session_state` and trigger a clean rerun.
- **Recomputing `predicted_log_mv` in scatter:** The column already exists from `compute_efficiency()`. Using it directly ensures the regression line and scatter points are consistent.
- **Passing raw EUR to column_config `format`:** Convert `market_value_eur` to €M on the display copy before passing to `st.dataframe`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Column-sortable table | Custom HTML sort | `st.dataframe` | Native — click any column header, handles sort state automatically |
| Row selection state | Manual click tracking | `on_select="rerun"` + `selection_mode="single-row"` | Built into Streamlit 1.52.2; returns `state["selection"]["rows"]` list |
| Numeric column formatting | String formatting in pandas | `st.column_config.NumberColumn(format="%.1f")` | Displays in table without mutating source values |
| OLS regression line | SciPy `linregress` | `numpy.polyfit` (degree 1) | Already used in existing `scatter_chart()`; no new dependency |
| Age filter numeric conversion | Custom regex | `_parse_age()` from `scorer.py` | Already handles FBref "25-201" format with NaN fallback |

**Key insight:** Streamlit's `st.dataframe` v1.52 handles sorting, selection, and column formatting natively. Building any of these manually would be significantly more brittle and would need to be removed in Phase 6.

---

## Common Pitfalls

### Pitfall 1: Club Filter Not Updating on League Change

**What goes wrong:** Club options remain from previously selected leagues; selecting a club from an unselected league causes no players to match.

**Why it happens:** `st.multiselect` for clubs was derived from `full_df` once at startup and cached.

**How to avoid:** Always compute `available_clubs` from `full_df[full_df["League"].isin(sel_leagues)]` — this runs on every Streamlit rerun when the league filter changes. Do not cache this computation.

**Warning signs:** User changes league filter and sees clubs that produce 0 results.

### Pitfall 2: Age Filter Fails on String Age Column

**What goes wrong:** `df[df["Age"] >= age_min]` raises TypeError because `Age` column is strings like "25-201".

**Why it happens:** FBref `Age` column is stored as string throughout the pipeline. `_parse_age()` is only called inside scorer.py during computation.

**How to avoid:** For filtering, compute `age_float = df["Age"].apply(_parse_age)` then filter on the float series. Import `_parse_age` from `scorer.py` or inline the logic.

**Warning signs:** TypeError or wrong filter results when age slider is moved.

### Pitfall 3: Market Value Filter in Wrong Units

**What goes wrong:** Slider shows 0–200 (€M) but filter applied against `market_value_eur` in raw EUR, so `mv_min = 10` (€M) compared to `10_000_000` (EUR) — no players match.

**Why it happens:** Slider returns €M; `market_value_eur` column is in EUR.

**How to avoid:** Always multiply slider values by `1e6` before filtering: `mv_min_eur = mv_range[0] * 1e6`.

**Warning signs:** Market value slider at any position returns 0 players.

### Pitfall 4: Reset Filters Button Causes Infinite Loop

**What goes wrong:** Reset button deletes session state keys and calls `st.rerun()` but the multiselects re-read their `key` values from session state on the next run — if keys are absent, they fall back to default correctly. However, if `st.stop()` is not called after the empty-state branch, the rest of the layout renders anyway.

**How to avoid:** Call `st.stop()` immediately after the empty state block. Use widget `key` parameters consistently so session state deletion actually works.

**Warning signs:** App re-renders partially after Reset; layout artifacts below the warning message.

### Pitfall 5: `st.dataframe` Selection Index Mismatch

**What goes wrong:** `state["selection"]["rows"][0]` is index 3; `df.iloc[3]` returns wrong player because the DataFrame passed to `st.dataframe` was not properly reset-indexed.

**Why it happens:** Pandas filters produce non-contiguous integer indices. If `reset_index(drop=True)` is not called before passing to `st.dataframe`, `iloc[3]` and the actual row at position 3 in the rendered table diverge.

**How to avoid:** Always call `.reset_index(drop=True)` on the filtered display DataFrame before passing to `st.dataframe`. Confirmed safe: the selected row index from `state["selection"]["rows"]` is a positional index in the rendered DataFrame.

**Warning signs:** Wrong player shown in placeholder panel after row click.

### Pitfall 6: Season Filter Column Name

**What goes wrong:** Filter by season fails because `_season` column does not exist or has different values.

**Why it happens:** The season column name and its exact values in the output DataFrame are determined by the merger/scorer pipeline.

**How to avoid:** At load time, check which season-related columns are present (`full_df.columns`) and what values they contain. Per STATE.md, a `single_season_flag` was noted for Phase 3, and FBREF_SEASONS=["2023-24", "2024-25"] is the configured set. The column may be named `_season` or may not exist. Apply season filter defensively: if `_season` not in `df.columns`, skip season filter silently.

**Warning signs:** Season filter has no effect, or KeyError on `_season` column.

---

## Code Examples

Verified patterns from the installed codebase:

### st.dataframe Row Selection (Streamlit 1.52.2)

```python
# Source: verified via inspect of /venv/lib/python3.11/site-packages/streamlit/elements/arrow.py

state = st.dataframe(
    display_df,
    on_select="rerun",
    selection_mode="single-row",
    use_container_width=True,
    hide_index=True,
    column_config=column_config,
)
# state is a DataframeState TypedDict
# state["selection"]["rows"] is a list of integer positional indices
# Empty list when nothing selected
if state["selection"]["rows"]:
    row_idx = state["selection"]["rows"][0]
    player = display_df.iloc[row_idx]
```

### Data Loading (keep as-is from existing app.py)

```python
# Source: existing app.py — caching pattern correct, keep unchanged

ALL_SEASONS = ("2023-24", "2024-25")

@st.cache_data(ttl=86400, show_spinner=False)
def load_data():
    from scraper import run_fbref_scrapers, run_tm_scrapers
    from scorer import run_scoring_pipeline
    fbref_data = run_fbref_scrapers()
    tm_data    = run_tm_scrapers()
    return run_scoring_pipeline(fbref_data, tm_data)
```

**Note:** The `seasons` parameter in the current app.py signature is not needed — `FBREF_SEASONS` in config.py already defines which seasons to scrape. Remove the seasons parameter from `load_data` to simplify; season filtering is a display-only filter in Phase 5.

### Scatter Chart — New Axes

```python
# Source: derived from existing scatter_chart() + CONTEXT.md spec

def scatter_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for pos, color in POS_COLORS.items():
        sub = df[df["Pos"] == pos]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["scout_score"],
            y=sub["predicted_log_mv"],   # log10(market_value_eur) — computed by scorer
            mode="markers",
            name=pos,
            marker=dict(size=7, color=color, opacity=0.75,
                        line=dict(width=0.5, color="rgba(0,0,0,0.4)")),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Club: %{customdata[1]}<br>"
                "Position: %{customdata[2]}<br>"
                "Scout Score: %{x:.1f}<br>"
                "Market Value: €%{customdata[3]:.1f}M<br>"
                "UV Score: %{customdata[4]:.1f}"
                "<extra></extra>"
            ),
            customdata=sub[["Player","Squad","Pos","market_value_eur_m","uv_score"]].values,
        ))
    # OLS line in log-space
    x_arr = df["scout_score"].values
    y_arr = df["predicted_log_mv"].values
    coeffs = np.polyfit(x_arr, y_arr, 1)
    x_range = np.linspace(x_arr.min(), x_arr.max(), 100)
    fig.add_trace(go.Scatter(
        x=x_range, y=np.polyval(coeffs, x_range),
        mode="lines", name="FAIR VALUE LINE",
        line=dict(color="#00A8FF", width=1.5, dash="dot"),
    ))
    fig.update_layout(
        **NAVY_LAYOUT,
        height=480,
        xaxis=dict(title="SCOUT SCORE", range=[0, 100],
                   gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.1)",
                   title_font=dict(color="#8DA4B8", size=11), tickfont=dict(color="#8DA4B8")),
        yaxis=dict(title="LOG\u2081\u2080 MARKET VALUE",
                   gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.1)",
                   title_font=dict(color="#8DA4B8", size=11), tickfont=dict(color="#8DA4B8")),
        legend=dict(bgcolor="#112236", bordercolor="rgba(0,168,255,0.2)", borderwidth=1,
                    font=dict(color="#E8EDF2")),
    )
    return fig
```

---

## What to Keep vs. Replace

| Element | Action | Reason |
|---------|--------|--------|
| `load_data()` + `@st.cache_data(ttl=86400)` | Keep (simplify seasons param) | Correct caching pattern; no change needed |
| `fmt_value()`, `fmt_gap()` | Keep or remove | Only needed if used in placeholder panel or sidebar info block; not needed for table (column_config handles formatting) |
| `_parse_age` (from scorer.py) | Import and use | Already handles FBref "years-days" format |
| `CYBER_LAYOUT` | Replace with `NAVY_LAYOUT` | Full theme replacement |
| `radar_chart()` | Delete | Not in Phase 5 scope |
| `pillar_bar_chart()` | Delete | Not in Phase 5 scope |
| `scatter_chart()` | Rewrite with new axes | Axes inverted; colors updated |
| All cyberpunk CSS | Delete entirely | Clean slate — new CSS block |
| Tab layout (`st.tabs`) | Delete | Single page, no tabs |
| KPI strip (`st.metric`) | Delete | Clean slate |
| Player cards (HTML blocks) | Delete | Clean slate |
| `get_pillar_labels()` | Delete | Only used by radar/pillar charts |
| `PILLAR_COLS`, `PILLAR_COLORS` | Delete | Replaced by `POS_COLORS` for scatter |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st.dataframe()` returns DeltaGenerator only | `st.dataframe(on_select="rerun")` returns `DataframeState` | Streamlit ~1.35 | Row click now a first-class feature |
| Filters independent of each other | Club filter dynamically derived from league filter | Phase 5 new requirement | More complex sidebar — sequential filter dependency |
| Cyberpunk theme (`#080808` / `#00ff41`) | Navy professional theme (`#0D1B2A` / `#00A8FF`) | Phase 5 | Full CSS replacement; no incremental migration |
| 4 tabs | Single scrolling page | Phase 5 | Simpler state management; no tab-switching |

---

## Open Questions

1. **Season filter column name in pipeline output**
   - What we know: `FBREF_SEASONS = ["2023-24", "2024-25"]` in config.py; STATE.md notes `single_season_flag` from Phase 3
   - What's unclear: Whether the pipeline output DataFrame has a `_season` column, and what its exact values are
   - Recommendation: Implement season filter defensively — at runtime, check `"_season" in full_df.columns`. If absent, disable the season filter widget with a note. The planner should include a task to verify this column exists in the actual pipeline output.

2. **Market value max for slider**
   - What we know: UI-SPEC says `max = dataset max rounded up to nearest 10 (€M)`
   - What's unclear: Computed at load time; if data hasn't been scraped yet (cold start), `full_df` may be empty and the slider max would be 0
   - Recommendation: Guard with `max(int(np.ceil(full_df["market_value_eur"].max() / 1e7)) * 10, 200)` with a fallback of 200 (€M) when DataFrame is empty.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (no config file — run from project root) |
| Config file | none — `pytest test_*.py` from `/Users/ArthurAldea/ClaudeProjects/Moneyball/` |
| Quick run command | `venv/bin/python -m pytest test_scorer.py -q --tb=short` |
| Full suite command | `venv/bin/python -m pytest test_scorer.py test_merger.py test_scraper.py -q --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FILTER-01 | League multiselect filters `full_df` to correct leagues | unit | `pytest test_app.py::test_filter_league -x` | ❌ Wave 0 |
| FILTER-02 | Position multiselect filters to correct positions | unit | `pytest test_app.py::test_filter_position -x` | ❌ Wave 0 |
| FILTER-03 | Age slider filters correctly using _parse_age float conversion | unit | `pytest test_app.py::test_filter_age -x` | ❌ Wave 0 |
| FILTER-04 | Club options derived from selected leagues only | unit | `pytest test_app.py::test_club_options_derived_from_leagues -x` | ❌ Wave 0 |
| FILTER-05 | Market value slider filters in €M units correctly | unit | `pytest test_app.py::test_filter_market_value -x` | ❌ Wave 0 |
| FILTER-06 | Season multiselect filters by season column | unit | `pytest test_app.py::test_filter_season -x` | ❌ Wave 0 |
| DASH-01 | Shortlist sorted by uv_score_age_weighted descending | unit | `pytest test_app.py::test_default_sort_order -x` | ❌ Wave 0 |
| DASH-02 | Display DataFrame has 10 correct columns | unit | `pytest test_app.py::test_display_columns -x` | ❌ Wave 0 |
| DASH-03 | Column sorting — native to st.dataframe, no test needed | manual | — | — |
| DASH-04 | Row selection returns correct player when index 0 selected | unit | `pytest test_app.py::test_row_selection_index -x` | ❌ Wave 0 |
| DASH-05 | CSS block contains #0D1B2A background and #00A8FF accent | unit | `pytest test_app.py::test_css_contains_navy_theme -x` | ❌ Wave 0 |
| DASH-06 | scatter_chart uses scout_score x-axis and predicted_log_mv y-axis | unit | `pytest test_app.py::test_scatter_axes -x` | ❌ Wave 0 |
| DASH-07 | Cross-league disclaimer shown when >1 league selected | unit | `pytest test_app.py::test_cross_league_disclaimer_condition -x` | ❌ Wave 0 |

**Note on Streamlit widget testing:** Streamlit widgets cannot be called outside a running Streamlit server (they raise `StreamlitAPIException`). Phase 5 tests should isolate the pure Python filter logic and chart construction functions — test those directly without running Streamlit. The pattern: extract filter logic and chart construction into importable functions that `app.py` calls; tests import those functions directly.

### Sampling Rate

- **Per task commit:** `venv/bin/python -m pytest test_app.py -q --tb=short`
- **Per wave merge:** `venv/bin/python -m pytest test_scorer.py test_merger.py test_scraper.py test_app.py -q --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `test_app.py` — 12 unit tests covering FILTER-01 through DASH-07
- [ ] `test_app.py::fixtures` — `make_pipeline_df(n)` synthetic DataFrame factory matching `run_scoring_pipeline` output schema
- [ ] Framework already installed: no new installs needed

---

## Sources

### Primary (HIGH confidence)

- Installed Streamlit 1.52.2 source — `/venv/lib/python3.11/site-packages/streamlit/elements/arrow.py` — verified `DataframeState`, `on_select`, `selection_mode`, `state["selection"]["rows"]` API
- Installed Streamlit 1.52.2 signature — `inspect.signature(st.dataframe)` — confirmed all parameters present
- `app.py` (project) — existing implementation; confirmed `CYBER_LAYOUT`, `scatter_chart`, `load_data`, `fmt_value`, `fmt_gap` structures
- `scorer.py` (project) — confirmed `run_scoring_pipeline` output columns: `Player, Squad, Pos, Age, League, market_value_eur, scout_score, uv_score, uv_score_age_weighted, value_gap_eur, league_quality_multiplier, predicted_log_mv, similar_players`
- `config.py` (project) — confirmed `FBREF_LEAGUES`, `LEAGUE_QUALITY_MULTIPLIERS`, `FBREF_SEASONS`
- `.planning/phases/05-dashboard-rebuild-shortlist-filters/05-UI-SPEC.md` — all CSS values, copywriting, component specs
- `.planning/phases/05-dashboard-rebuild-shortlist-filters/05-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)

- `st.column_config.NumberColumn`, `st.column_config.TextColumn` — verified importable from installed Streamlit (not source-inspected for full API)

### Tertiary (LOW confidence)

- Season column name `_season` in pipeline output — not verified by reading merger.py output; flagged as Open Question

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions confirmed by running venv Python
- Architecture: HIGH — `st.dataframe` selection API verified against installed source code
- Pitfalls: HIGH — derived from reading existing app.py and understanding the filter dependency chain
- Scatter axes: HIGH — `predicted_log_mv` column existence confirmed in scorer.py

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (Streamlit stable; 30-day window safe)
