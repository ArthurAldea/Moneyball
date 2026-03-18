# Phase 6: Player Deep Profile — Research

**Researched:** 2026-03-18
**Domain:** Streamlit + Plotly radar/scatter charts, session state navigation, percentile visualization
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Profile section placement**
- Profile appears inline below the shortlist table, above the UV scatter chart — same single-page layout as Phase 5, no page navigation
- Phase 5 placeholder panel (lines ~440–466 in app.py) is replaced entirely by the full profile
- Section label: `PLAYER PROFILE` (ALL-CAPS, using existing `.section-header` CSS class) above the header block

**Profile internal layout (single player mode)**
- Two-column layout: radar chart on the left (~40% width), per-90 stat table on the right (~60% width)
- Both visible at the same time without scrolling within the profile section
- Similar players panel: full-width row below the two-column radar + stat table

**Comparison mode (2–3 players selected)**
- Max 3 players — enforced programmatically; if user selects a 4th row, show a warning and ignore the 4th selection
- Table selection mode changes from `"single-row"` to `"multi-row"` (Streamlit ≥1.35 API)
- Header block: one mini header card per selected player, arranged side-by-side horizontally (name, club, league, position, market value)
- Radar chart: one filled polygon per player overlaid on the same chart, with distinct colors per player and a legend. Position-peer median polygon still shown for reference.
- Per-90 stat table: side-by-side columns — rows = stats (grouped by pillar), columns = players. Each player gets a per-90 value and a percentile bar per stat row.
- Similar players panel: one `SIMILAR TO [NAME]` row per selected player, stacked vertically below the radar + stat table

**Player name search filter (FILTER-07)**
- Position in sidebar: top of sidebar, above the LEAGUE filter — first item the user sees
- Search scope: applied after the existing 6 filters (searches within the already-filtered pool, not the full dataset)
- Implementation: `st.text_input` with label "PLAYER SEARCH", case-insensitive `str.contains()` on the `Player` column. Empty input = no filter applied.

**Similar players interactivity**
- Each similar player card is clickable — clicking navigates to that player's profile
- Clicking a similar player: profile area updates to show the clicked player, shortlist table selection deselects (clears `st.session_state` selection)
- Navigation implemented via `st.session_state` (store the clicked player name, trigger rerun, profile section reads from session state as override)

### Claude's Discretion
- Exact Plotly radar chart configuration (fill opacity, line width, hover text format)
- Exact percentile bar implementation (HTML progress bars via `st.dataframe` column config, or custom HTML via `st.markdown`)
- Color assignment per player in comparison mode (reuse `POS_COLORS` for single-player single-color, or use a fixed comparison palette of 3 distinct colors)
- How to display the `Nation` column (3-letter FBref code e.g. "ENG") — either display as-is or attempt a mapping to full country name
- Exact pixel heights for the radar and stat table in the two-column layout

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROFILE-01 | Player profile header block: full name, age, nationality, current club, league, primary position, market value | `Nation` column confirmed present on every row (3-letter FBref code). `_parse_age()` available for integer display. `market_value_eur` in raw EUR — divide by 1e6 for display. |
| PROFILE-02 | Radar chart of 5 pillar scores vs. cross-league position-peer median, rendered as filled polygon | `score_attacking`, `score_progression`, `score_creation`, `score_defense`, `score_retention` columns present on every row. Median computed on-the-fly from `full_df` filtered to matching `Pos`. Plotly `go.Scatterpolar` with `fill="toself"` is the standard approach. |
| PROFILE-03 | Per-90 stat table grouped by pillar, stat name / raw value / per-90 value / percentile bar (red→amber→green) vs. cross-league position peers | Per-90 columns: `Gls_p90`, `Ast_p90`, `SoT_p90`, `Sh_p90`, `Int_p90`, `TklW_p90`, `Fld_p90`, `Crs_p90`, `Saves_p90` (GK only). Percentile: `scipy.stats.percentileofscore` or pandas `.rank(pct=True)` against position-peer pool. Pillar grouping driven by `config.py` `PILLARS_FW/MF/DF/GK_PILLARS`. |
| PROFILE-04 | Player highlighted on UV scatter chart with distinct marker | Extend `scatter_chart(df)` with optional `highlighted_players: list[str]` param. Add a second trace per highlighted player with larger marker size + white border. |
| PROFILE-05 | Similar players panel: top 5 by cosine similarity — Player, Club, League, Age, Market Value, Age-Weighted UV Score | `similar_players` JSON parsed with `json.loads()`. Age and market_value_eur joined from `full_df` by player+club key. Each card clickable via `st.button()` + `st.session_state["profile_player"]`. |
| PROFILE-06 | Multi-player comparison mode: overlaid radar, per-player stat columns, multi-highlight on scatter | `selection_mode="multi-row"` on `st.dataframe`. 4th selection ignored with `st.warning()`. Comparison palette `["#00A8FF", "#FF5757", "#F5A623"]`. |
| FILTER-07 | Player name search text input in sidebar (case-insensitive partial match, applied after 6 existing filters) | `st.text_input(label="PLAYER SEARCH", key="player_search")`. Applied inline on `display_df` after `apply_filters()`. Cleared on "Reset Filters" by adding `"player_search"` to the key deletion loop. |
</phase_requirements>

---

## Summary

Phase 6 is a pure `app.py` modification — no changes to scraper, merger, or scorer. All required data columns (`score_*`, per-90 stats, `similar_players` JSON, `Nation`) are already computed and present on the pipeline output DataFrame. The implementation is additive: replace the placeholder block at lines 440–466, extend the scatter chart function, add `selection_mode="multi-row"` to the shortlist table, and insert the PLAYER SEARCH input at the top of the sidebar.

The core technical challenges are: (1) the Plotly radar chart using `go.Scatterpolar` with `fill="toself"` for each polygon, (2) percentile bar rendering in the stat table, (3) session state management for similar-player click navigation, and (4) keeping the 3-player selection cap enforcement clean without breaking Streamlit's reactive re-run model.

The existing test infrastructure (pytest + Streamlit stub in conftest.py) covers the pure-Python functions in app.py. New pure-Python helpers introduced in Phase 6 (profile data extraction, percentile computation, similar-player join) should follow the same exportable function pattern as `apply_filters` and `scatter_chart`.

**Primary recommendation:** Implement in three sub-tasks — (1) FILTER-07 + table multi-row change, (2) single-player profile (PROFILE-01 through 05), (3) comparison mode (PROFILE-06).

---

## Standard Stack

### Core (all already installed in project venv)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | ≥1.35 | `selection_mode="multi-row"`, `st.dataframe`, `st.session_state`, `st.text_input` | Project UI framework; `multi-row` requires ≥1.35 |
| plotly | current | `go.Scatterpolar` (radar), extended `go.Scatter` (scatter highlight) | Already used for scatter chart in Phase 5 |
| pandas | current | Percentile rank (`rank(pct=True)`), group filtering, similar-player join | Already used throughout pipeline |
| numpy | current | Median computation for position-peer radar baseline | Already used in scorer |

### Supporting (no new installs needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | — | `json.loads(similar_players)` to parse JSON string column | Every profile render |
| config.py | — | `PILLARS_FW/MF/DF/GK_PILLARS` for radar axis labels and stat table grouping | Radar + stat table construction |
| scorer._parse_age | — | Convert FBref "25-201" age format to integer | Header block age display |

### No New Installs Required
All required libraries are already present. Do not add scipy — pandas `.rank(pct=True)` is sufficient for percentile computation.

---

## Architecture Patterns

### Recommended Code Structure in app.py

The new code slots into app.py in three locations. Keep all new logic as module-level pure functions (same pattern as `apply_filters`, `scatter_chart`) so tests can import them directly.

```
app.py additions:
├── Pure helper functions (new, testable):
│   ├── get_pillar_stats(pos)             → ordered list of (pillar_label, [stat_cols]) for position
│   ├── compute_percentile(val, series)   → 0–100 float, peer group series
│   ├── build_radar_figure(players_data)  → go.Figure with Scatterpolar traces
│   ├── parse_similar_players(row, df)    → list of dicts with Age + market_value_eur joined
│   └── filter_by_name(df, query)         → df filtered by case-insensitive partial match
├── Sidebar section (FILTER-07):
│   └── st.text_input("PLAYER SEARCH", key="player_search") — inserted BEFORE LEAGUE filter
├── Shortlist table change:
│   └── selection_mode="multi-row" + 3-player cap enforcement
├── Profile section (replaces lines 440–466):
│   ├── Resolve active players list (session_state override OR table selection)
│   ├── render_profile_header(players)
│   ├── col_left, col_right = st.columns([0.4, 0.6])
│   │   ├── col_left: build_radar_figure(players) → st.plotly_chart
│   │   └── col_right: stat table with percentile bars → st.markdown (HTML)
│   └── render_similar_players(players, full_df)
└── scatter_chart() extension:
    └── highlighted_players: list[str] = None param
```

### Pattern 1: Plotly Radar Chart (go.Scatterpolar)

**What:** Filled polygon on polar axes, one trace per player + one for position-peer median.
**When to use:** Single player mode (player + median) and comparison mode (N players + median).

```python
# Source: Plotly official docs — go.Scatterpolar
import plotly.graph_objects as go

PILLAR_LABELS = ["Attacking", "Progression", "Creation", "Defense", "Retention"]
SCORE_COLS = ["score_attacking", "score_progression", "score_creation",
              "score_defense", "score_retention"]
COMPARISON_PALETTE = ["#00A8FF", "#FF5757", "#F5A623"]

def build_radar_figure(players_data: list[dict], peer_median: list[float]) -> go.Figure:
    """
    players_data: list of {"name": str, "scores": [5 floats 0-100], "color": str}
    peer_median:  list of 5 floats (median score_* across position peers in full_df)
    """
    fig = go.Figure()
    # Position-peer median polygon (reference baseline)
    fig.add_trace(go.Scatterpolar(
        r=peer_median + [peer_median[0]],           # close the polygon
        theta=PILLAR_LABELS + [PILLAR_LABELS[0]],
        fill="toself",
        fillcolor="rgba(255,255,255,0.06)",
        line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"),
        name="PEER MEDIAN",
        hoverinfo="skip",
    ))
    # One trace per selected player
    for i, p in enumerate(players_data):
        scores = p["scores"]
        fig.add_trace(go.Scatterpolar(
            r=scores + [scores[0]],
            theta=PILLAR_LABELS + [PILLAR_LABELS[0]],
            fill="toself",
            fillcolor=f"rgba({_hex_to_rgb(p['color'])}, 0.15)",
            line=dict(color=p["color"], width=2),
            name=p["name"],
        ))
    fig.update_layout(
        **NAVY_LAYOUT,
        height=360,
        polar=dict(
            bgcolor="#112236",
            radialaxis=dict(visible=True, range=[0, 100],
                           gridcolor="rgba(255,255,255,0.1)",
                           tickfont=dict(color="#8DA4B8", size=9)),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)",
                            tickfont=dict(color="#E8EDF2", size=11)),
        ),
        showlegend=True,
        legend=dict(bgcolor="#112236", bordercolor="rgba(0,168,255,0.2)",
                   borderwidth=1, font=dict(color="#E8EDF2")),
    )
    return fig
```

### Pattern 2: Percentile Bars via HTML Markdown

**What:** Colored horizontal bar representing a player's percentile vs. position peers.
**When to use:** Per-90 stat table — each row gets a bar colored red (low) → amber (mid) → green (high).

Use `st.markdown(..., unsafe_allow_html=True)` for the stat table. Build an HTML table string rather than `st.dataframe` — this gives full control over the bar colors without fighting Streamlit's column config.

```python
def _pct_bar_html(pct: float) -> str:
    """Return inline HTML for a colored progress bar (0–100)."""
    if pct < 33:
        color = "#FF5757"   # red — bottom third
    elif pct < 66:
        color = "#F5A623"   # amber — middle third
    else:
        color = "#2ECC71"   # green — top third
    return (
        f"<div style='background:rgba(255,255,255,0.08);border-radius:3px;height:8px;'>"
        f"<div style='width:{pct:.0f}%;background:{color};height:8px;border-radius:3px;'>"
        f"</div></div>"
    )
```

### Pattern 3: Session State Navigation for Similar Players

**What:** Clicking a similar player card updates `st.session_state["profile_player"]` and calls `st.rerun()`, causing the profile section to render the clicked player without touching the shortlist table selection.
**When to use:** Similar player card click handler.

```python
# In the similar players panel:
if st.button(f"{sp['player']} — {sp['club']}", key=f"sim_{sp['player']}_{sp['club']}"):
    st.session_state["profile_player"] = sp["player"]
    st.session_state["profile_player_club"] = sp["club"]  # disambiguate same-name players
    st.rerun()

# In the profile section resolver (runs before rendering):
if "profile_player" in st.session_state and st.session_state["profile_player"]:
    # Look up player row from full_df (not display_df — they may be filtered out)
    override_name = st.session_state["profile_player"]
    override_club = st.session_state.get("profile_player_club", "")
    mask = full_df["Player"] == override_name
    if override_club:
        mask = mask & (full_df["Squad"] == override_club)
    active_rows = full_df[mask]
    # Clear table selection visual (session state key for dataframe)
    # st.dataframe selection state is in table_state["selection"]["rows"] — set via session_state
else:
    # Use shortlist table selection
    active_rows = df.iloc[selected_rows]
```

### Pattern 4: 3-Player Selection Cap

**What:** Enforce max 3 rows selected. On each rerun, if `len(selected_rows) > 3`, show warning and truncate.
**When to use:** After `table_state = st.dataframe(..., selection_mode="multi-row", ...)`.

```python
selected_rows = table_state["selection"]["rows"]
if len(selected_rows) > 3:
    st.warning("MAX 3 PLAYERS — Selection limited to first 3.")
    selected_rows = selected_rows[:3]
```

### Pattern 5: Similar Players Join (Age + Market Value)

**What:** `similar_players` JSON only stores `player`, `club`, `league`, `uv_score_age_weighted`. To display Age and Market Value, join from `full_df` by player+club.
**When to use:** Rendering the Similar Players panel.

```python
import json

def parse_similar_players(row: pd.Series, full_df: pd.DataFrame) -> list[dict]:
    """Parse similar_players JSON and enrich with Age + market_value_eur from full_df."""
    raw = row.get("similar_players", "[]")
    try:
        peers = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    enriched = []
    for p in peers:
        match = full_df[
            (full_df["Player"] == p["player"]) & (full_df["Squad"] == p["club"])
        ]
        age = int(_parse_age(match["Age"].iloc[0])) if not match.empty else "—"
        mv = match["market_value_eur"].iloc[0] / 1e6 if not match.empty else None
        enriched.append({**p, "age": age, "market_value_m": mv})
    return enriched
```

### Pattern 6: Scatter Chart Highlight Extension

**What:** Add `highlighted_players` param to `scatter_chart()`. For each highlighted player, add a dedicated trace with larger marker size, white border, and text label.
**When to use:** Profile section active — pass list of player names.

```python
def scatter_chart(df: pd.DataFrame,
                  highlighted_players: list[str] | None = None) -> go.Figure:
    # ... existing code ...
    if highlighted_players:
        palette = ["#00A8FF", "#FF5757", "#F5A623"]
        for i, name in enumerate(highlighted_players):
            sub = df[df["Player"] == name]
            if sub.empty:
                continue
            color = palette[i % len(palette)]
            fig.add_trace(go.Scatter(
                x=sub["scout_score"],
                y=sub["market_value_eur"],
                mode="markers+text",
                name=name,
                text=[name],
                textposition="top center",
                textfont=dict(color=color, size=10),
                marker=dict(
                    size=14,
                    color=color,
                    line=dict(width=2, color="#FFFFFF"),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>Scout: %{x:.1f}<br>Value: €%{customdata:.1f}M"
                    "<extra></extra>"
                ),
                customdata=sub["market_value_eur"].values / 1e6,
            ))
    return fig
```

### Anti-Patterns to Avoid

- **Using `st.dataframe` column_config ProgressColumn for percentile bars:** Streamlit's `ProgressColumn` renders bars but doesn't support the red/amber/green color gradient. Use `st.markdown` with HTML instead.
- **Computing position-peer percentile against `display_df` (filtered) instead of `full_df`:** The filtered shortlist may have very few peers, collapsing percentile variance. Always compute against full cross-league position peers from `full_df`.
- **Storing entire player row in session_state:** Store only `player_name` + `club` (disambiguation key). Never store the full DataFrame row — it breaks Streamlit's serialization and creates stale state bugs.
- **Using player name alone as disambiguation key for similar-player navigation:** Multiple players can share a name across seasons or clubs. Store both `player` and `club` in session state.
- **Calling `st.rerun()` inside a `st.button` callback without updating session state first:** In Streamlit, `st.rerun()` terminates execution immediately — ensure state is written before the call.
- **Forgetting `+ [scores[0]]` to close the radar polygon:** Plotly Scatterpolar does NOT auto-close — the first value must be repeated as the last element of `r` and `theta`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Radar chart polygon | Custom SVG or canvas | `go.Scatterpolar` with `fill="toself"` | Plotly handles polar projection, scaling, hover, legend |
| Percentile computation | Manual rank loop | `pd.Series.rank(pct=True) * 100` | Handles ties, NaN, one-liner |
| JSON parsing of similar_players | String splitting | `json.loads()` | Already JSON-formatted by scorer.py |
| Color interpolation for bars | Linear RGB gradient function | Three fixed threshold colors (red/amber/green at 33/66) | Simpler, visually clear, no edge cases |
| Player name fuzzy matching for navigation | rapidfuzz | Exact name+club match on `full_df` | Similar players already computed by exact identity; no fuzzy needed at display time |

---

## Common Pitfalls

### Pitfall 1: Stale Profile When Filters Change
**What goes wrong:** User selects a player, then changes a filter — the shortlist table clears selection but `st.session_state["profile_player"]` still holds the previous player. Profile renders a player not visible in the current shortlist.
**Why it happens:** Session state persists across reruns; filter changes don't automatically clear it.
**How to avoid:** After resolving `active_rows`, check if the player exists in `display_df`. If not, and the override came from session_state, either clear session state or show a "player filtered out" notice.
**Warning signs:** Profile showing a player not visible in the table above it.

### Pitfall 2: Radar Score Values Not in 0–100 Range
**What goes wrong:** The `score_*` pillar columns are weighted sub-scores (e.g. `score_attacking` for a FW = raw pillar score * 0.45 weight = values like 3.2, not 0–100).
**Why it happens:** `_score_group()` computes `pillar_score * pillar_data["weight"]` before storing to `score_{name}`. So `score_attacking` for a FW tops out at ~45, not 100.
**How to avoid:** The radar should show the normalized pillar score before weighting. Either divide `score_attacking` by `pillar_data["weight"] / 100` to recover 0–100, or compute a fresh normalized value. **Verify actual column ranges before assuming 0–100.** Alternative: use the 5 `score_*` values as-is and label the radial axis with the actual max observed in the position group — still meaningful for relative comparison.
**Warning signs:** All radar polygons look tiny (scores are 0–45 range but axis is 0–100).

### Pitfall 3: `selection_mode="multi-row"` Returns Row Indices Into display_df, Not full_df
**What goes wrong:** `selected_rows` from `table_state["selection"]["rows"]` are integer indices into `display_df` (the filtered, sorted table). Confusing these with `full_df` indices causes wrong player lookup.
**Why it happens:** `display_df` is a `reset_index(drop=True)` copy of the filtered+sorted df. Its index 0 is not the same row as `full_df` index 0.
**How to avoid:** Always do `df.iloc[row_idx]` (using the filtered `df`, not `full_df`) to get the player row from table selection. For session_state navigation (similar player click), look up by `Player`+`Squad` against `full_df`.
**Warning signs:** Profile showing the wrong player after selection.

### Pitfall 4: Similar Player Cards Break on Duplicate st.button Keys
**What goes wrong:** `st.button` requires unique `key` argument. If two similar players have the same name (different clubs), duplicate keys cause a Streamlit `DuplicateWidgetID` error.
**Why it happens:** Using only `player_name` as the key.
**How to avoid:** Use `key=f"sim_{player_name}_{club}_{i}"` (include index `i` as tiebreaker).
**Warning signs:** Streamlit DuplicateWidgetID exception at runtime.

### Pitfall 5: Percentile Computed Against Filtered Pool Instead of Full Cross-League Peers
**What goes wrong:** If user has filtered to one league, `df` contains only that league's players. Computing `df[df["Pos"]==pos]["stat"].rank(pct=True)` gives percentile within that one league, not cross-league. Bars look different based on active filters.
**Why it happens:** Using `df` (filtered) instead of `full_df` for peer pool.
**How to avoid:** Always compute percentile against `full_df[full_df["Pos"] == pos]["stat_col"]`.
**Warning signs:** A player's percentile bars change value when the league filter is changed.

### Pitfall 6: conftest.py Streamlit Stub Needs Extension for New st.* Calls
**What goes wrong:** New `st.text_input`, `st.button` (in profile section), `st.columns` with `[0.4, 0.6]` float ratios, etc. may not all be handled by the existing stub.
**Why it happens:** conftest.py has `_noop` stubs for most st.* functions, but `st.columns` with float list ratios and `st.dataframe` returning a selection object need specific behavior.
**How to avoid:** Review conftest.py before writing tests. `st.text_input` already returns `""` (line 104). `st.dataframe` returns `_noop()` — tests that check selection behavior need to mock `table_state["selection"]["rows"]` directly. Float-list columns (e.g. `st.columns([0.4, 0.6])`) pass through `_columns(n)` which checks `isinstance(n, int)` — add a `len(n)` path (already present: `len(n)` is used when not int).
**Warning signs:** Tests that import app.py raise AttributeError on `st.*` calls.

---

## Code Examples

Verified patterns from codebase inspection:

### Pillar Label Extraction from config.py
```python
# Source: config.py PILLARS_FW/MF/DF/GK_PILLARS structure
from config import PILLARS_FW, PILLARS_MF, PILLARS_DF, GK_PILLARS

POS_PILLARS = {"FW": PILLARS_FW, "MF": PILLARS_MF, "DF": PILLARS_DF, "GK": GK_PILLARS}

def get_pillar_stats(pos: str) -> list[tuple[str, list[str]]]:
    """
    Returns ordered list of (pillar_label, [stat_col, ...]) for the given position.
    Pillar order preserved from config dict insertion order (Python 3.7+).
    """
    pillars = POS_PILLARS.get(pos, PILLARS_MF)
    return [(p["label"], list(p["stats"].keys())) for p in pillars.values()]

# Example output for "FW":
# [("Attacking", ["Gls_p90", "SoT_p90", "Ast_p90"]),
#  ("Progression", ["Sh_p90", "Fld_p90"]),
#  ("Creation", ["Ast_p90", "Crs_p90"]),
#  ("Defense", ["Int_p90", "TklW_p90"]),
#  ("Retention", ["Fld_p90"])]
```

### Per-90 Stat Column Availability by Position
```python
# Source: config.py PER90_STATS + GK_PILLARS — derived from FBref Lit migration
OUTFIELD_PER90_COLS = ["Gls_p90", "Ast_p90", "SoT_p90", "Sh_p90",
                       "Int_p90", "TklW_p90", "Fld_p90", "Crs_p90"]
GK_EXTRA_PER90_COLS = ["Saves_p90"]  # GK only; Save% is rate, not per-90

# All positions have OUTFIELD_PER90_COLS (even GKs have TklW_p90, Int_p90 from misc table)
# GKs additionally use Save% (rate) and Saves_p90
```

### Player Resolution Logic (Table Selection vs. Session State)
```python
# Pattern for resolving which player(s) to show in profile
selected_rows = table_state["selection"]["rows"]
if len(selected_rows) > 3:
    st.warning("MAX 3 PLAYERS — Selection limited to first 3.")
    selected_rows = selected_rows[:3]

override = st.session_state.get("profile_player")
if override:
    mask = full_df["Player"] == override
    club_override = st.session_state.get("profile_player_club", "")
    if club_override:
        mask = mask & (full_df["Squad"] == club_override)
    active_players = full_df[mask].head(1)  # one player from session override
elif selected_rows:
    active_players = df.iloc[selected_rows]  # df = filtered df, not full_df
else:
    active_players = pd.DataFrame()           # no selection — hide profile section
```

### PLAYER SEARCH Filter (FILTER-07)
```python
# Sidebar — insert BEFORE the LEAGUE filter block
player_search = st.text_input(
    "PLAYER SEARCH", placeholder="Search by name...",
    label_visibility="visible", key="player_search",
)

# After apply_filters(), apply name search on display_df:
if player_search and player_search.strip():
    display_df = display_df[
        display_df["Player"].str.contains(player_search.strip(), case=False, na=False)
    ]

# Reset Filters — add "player_search" to key deletion list:
for key in ["sel_leagues", "sel_positions", "age_range", "sel_clubs",
            "mv_range", "sel_seasons", "player_search"]:
    if key in st.session_state:
        del st.session_state[key]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `selection_mode="single-row"` | `selection_mode="multi-row"` | Streamlit ≥1.35 (2024) | Enables comparison mode without workarounds |
| Plotly ProgressBar column config | Custom HTML table via st.markdown | Phase 6 design | Required for red/amber/green gradient control |
| `st.experimental_rerun()` | `st.rerun()` | Streamlit 1.27 (2023) | `experimental_rerun` is deprecated; use `st.rerun()` |

**Deprecated/outdated:**
- `st.experimental_rerun()`: Removed in Streamlit 1.40+. Use `st.rerun()`. The conftest stub already mocks `st.rerun = _noop` (line 65).
- `st.dataframe` with `ProgressColumn` for gradient bars: Doesn't support custom color thresholds — use HTML instead.

---

## Open Questions

1. **Actual range of score_* pillar columns**
   - What we know: `_score_group()` computes `pillar_score * pillar_data["weight"]`, so `score_attacking` for FW tops out at ~45 (weight=45), not 100.
   - What's unclear: Whether the radar should show raw `score_*` values (0–45/30/etc.) or normalize them back to 0–100 per pillar.
   - Recommendation: Normalize each `score_{pillar}` by dividing by `pillar["weight"] / 100` to recover the underlying 0–1 normalized pillar value, then multiply by 100. This gives a true 0–100 range for radar axes. Alternatively, scale all traces by the same factor (position-group max) so relative shape is preserved. Confirm by inspecting actual `score_*` values in a live session before implementation.

2. **Similar player cards: button or clickable container?**
   - What we know: `st.button` works for click detection; `st.session_state` + `st.rerun()` handles navigation.
   - What's unclear: Whether `st.button` renders acceptably as a "card" in the navy theme.
   - Recommendation: Use `st.button` with a formatted label (`f"{name} — {club} ({league})"`) styled via the existing `.stButton > button` CSS. Keep it simple; full card styling via HTML + `st.button` overlap is fragile.

3. **Player SEARCH filter placement relative to section-header**
   - What we know: Decision is locked — top of sidebar, above LEAGUE.
   - What's unclear: Whether to show a `.section-header` label above the text input (consistent with other filters) or just the input label directly.
   - Recommendation: Use `st.markdown("<div class='section-header'>PLAYER SEARCH</div>", unsafe_allow_html=True)` for consistency with the 6 existing filters, then `st.text_input` with `label_visibility="collapsed"`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, no version pin in requirements.txt) |
| Config file | none — pytest auto-discovers `test_*.py` |
| Quick run command | `pytest test_app.py -x -q` |
| Full suite command | `pytest test_app.py test_scorer.py test_merger.py test_scraper.py -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FILTER-07 | `filter_by_name(df, "son")` returns only players with "son" in name (case-insensitive) | unit | `pytest test_app.py::test_filter_by_name -x` | ❌ Wave 0 |
| FILTER-07 | Empty query returns full df unchanged | unit | `pytest test_app.py::test_filter_by_name_empty -x` | ❌ Wave 0 |
| PROFILE-01 | Header block data extraction returns correct name/age/club/position/nation/mv | unit | `pytest test_app.py::test_profile_header_data -x` | ❌ Wave 0 |
| PROFILE-02 | `build_radar_figure()` returns go.Figure with ≥2 Scatterpolar traces (player + median) | unit | `pytest test_app.py::test_radar_figure -x` | ❌ Wave 0 |
| PROFILE-02 | Radar median trace uses position-peer full_df values, not filtered df | unit | `pytest test_app.py::test_radar_median_source -x` | ❌ Wave 0 |
| PROFILE-03 | `compute_percentile(val, series)` returns float in [0, 100] | unit | `pytest test_app.py::test_compute_percentile -x` | ❌ Wave 0 |
| PROFILE-04 | `scatter_chart(df, highlighted_players=["X"])` adds a trace named "X" with marker size > 7 | unit | `pytest test_app.py::test_scatter_highlight -x` | ❌ Wave 0 |
| PROFILE-05 | `parse_similar_players(row, full_df)` returns list of dicts with age and market_value_m keys | unit | `pytest test_app.py::test_parse_similar_players -x` | ❌ Wave 0 |
| PROFILE-05 | `parse_similar_players` with malformed JSON returns empty list (no crash) | unit | `pytest test_app.py::test_parse_similar_players_malformed -x` | ❌ Wave 0 |
| PROFILE-06 | Selection cap: len > 3 truncates to 3 (tested via pure function, not Streamlit widget) | unit | `pytest test_app.py::test_selection_cap -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest test_app.py -x -q`
- **Per wave merge:** `pytest test_app.py test_scorer.py test_merger.py test_scraper.py -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `test_app.py` — new test functions listed above (append to existing file, do not replace)
- [ ] `make_pipeline_df()` fixture in `test_app.py` already includes `similar_players`, `score_*`, `Nation` — verify `Nation` column is present or add it to the fixture

*(Existing test infrastructure covers Phase 5 requirements; Phase 6 tests extend `test_app.py` with additional functions.)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `app.py` (484 lines), `scorer.py` (354 lines), `config.py` (301 lines), `conftest.py` (194 lines), `test_app.py` (325 lines)
- `CLAUDE.md` — tech stack, pillar model, available stats post-FBref Lit migration
- `.planning/phases/06-player-deep-profile/06-CONTEXT.md` — locked implementation decisions

### Secondary (MEDIUM confidence)
- Plotly documentation pattern for `go.Scatterpolar` — standard `fill="toself"` usage confirmed from prior Plotly experience; radar polygon closing (`r[0]` repeat) is a known requirement
- Streamlit `selection_mode="multi-row"` — confirmed available in Streamlit ≥1.35 (2024 release); conftest.py already stubs `st.dataframe` returning `_NoopCtx()` which supports dict-style `["selection"]["rows"]` access

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use in the project
- Architecture: HIGH — patterns derived directly from existing app.py code; no guesswork
- Pitfalls: HIGH — derived from careful reading of scorer.py `_score_group()` logic, conftest.py stub behavior, and Streamlit reactive model constraints
- Radar score range: MEDIUM — `_score_group()` confirms weighted values, but actual runtime range should be verified before choosing radar scale

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable stack — Streamlit/Plotly APIs change slowly)
