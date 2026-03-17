"""
app.py — Moneyball Scouting Intelligence
Professional navy dashboard — shortlist-first single-page layout.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from scorer import _parse_age

st.set_page_config(
    page_title="Moneyball — Scouting Intelligence",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────

NAVY_CSS = """
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
  .stCaption { color: #8DA4B8 !important; }
  .stMultiSelect [data-baseweb="tag"] {
      background-color: rgba(0, 168, 255, 0.15);
      color: #00A8FF;
      border: 1px solid #00A8FF;
  }
  [data-testid="stHeader"],
  [data-testid="stToolbar"] {
      background-color: #0D1B2A !important;
  }
  .stDataFrame,
  [data-testid="stDataFrameResizable"] {
      background: #0D1B2A !important;
      color: #E8EDF2 !important;
  }
  .stDataFrame iframe {
      background: #0D1B2A !important;
  }
  .stDataFrame table {
      background: #0D1B2A !important;
      color: #E8EDF2 !important;
  }
  [data-testid="stDataFrame"] tr[aria-selected="true"] {
      border-left: 3px solid #00A8FF;
  }
</style>
"""

# ── Plotly theme ───────────────────────────────────────────────────────────────

NAVY_LAYOUT = dict(
    paper_bgcolor="#0D1B2A",
    plot_bgcolor="#112236",
    font=dict(family="Inter, system-ui, sans-serif", color="#E8EDF2", size=12),
    margin=dict(t=48, b=48, l=56, r=24),
)

POS_COLORS = {
    "FW": "#FF5757",
    "MF": "#4CC9F0",
    "DF": "#F5A623",
    "GK": "#A78BFA",
}

# ── Data loading ───────────────────────────────────────────────────────────────


@st.cache_data(ttl=86400, show_spinner=False)
def load_data() -> pd.DataFrame:
    from scraper import run_fbref_scrapers, run_tm_scrapers
    from scorer import run_scoring_pipeline
    fbref_data = run_fbref_scrapers()
    tm_data = run_tm_scrapers()
    return run_scoring_pipeline(fbref_data, tm_data)


# ── Pure-Python filter functions (exported for tests) ─────────────────────────


def get_available_clubs(df: pd.DataFrame, leagues: list) -> list:
    """Return sorted unique Squad values for rows where League is in leagues."""
    if df.empty or "League" not in df.columns or "Squad" not in df.columns:
        return []
    return sorted(
        df[df["League"].isin(leagues)]["Squad"].dropna().unique().tolist()
    )


def apply_filters(
    df: pd.DataFrame,
    leagues: list = None,
    positions: list = None,
    age_range: tuple = (17, 38),
    clubs: list = None,
    mv_range: tuple = (0, 200),    # in €M — multiplied by 1e6 internally
    seasons: list = None,
) -> pd.DataFrame:
    """Apply all 6 filters sequentially. Returns filtered, reset-indexed DataFrame."""
    result = df.copy()
    if result.empty:
        return result
    # FILTER-01 league
    if leagues and "League" in result.columns:
        result = result[result["League"].isin(leagues)]
    # FILTER-02 position
    if positions:
        result = result[result["Pos"].isin(positions)]
    # FILTER-03 age (FBref "years-days" string format — use _parse_age)
    age_float = result["Age"].apply(_parse_age)
    result = result[(age_float >= age_range[0]) & (age_float <= age_range[1])]
    # FILTER-04 club
    if clubs:
        result = result[result["Squad"].isin(clubs)]
    # FILTER-05 market value — slider in €M, column in raw EUR
    mv_min_eur = mv_range[0] * 1_000_000
    mv_max_eur = mv_range[1] * 1_000_000
    result = result[
        (result["market_value_eur"] >= mv_min_eur) &
        (result["market_value_eur"] <= mv_max_eur)
    ]
    # FILTER-06 season — defensive: skip if _season column absent
    if "_season" in result.columns and seasons:
        result = result[result["_season"].isin(seasons)]
    return result.reset_index(drop=True)


def prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by uv_score_age_weighted desc, select 10 display columns, convert values to €M."""
    display_cols = [
        "Player", "Squad", "League", "Pos", "Age",
        "scout_score", "uv_score", "uv_score_age_weighted",
        "market_value_eur", "value_gap_eur",
    ]
    available = [c for c in display_cols if c in df.columns]
    out = df.sort_values("uv_score_age_weighted", ascending=False)[available].copy()
    # Convert EUR to €M for display
    if "market_value_eur" in out.columns:
        out["market_value_eur"] = out["market_value_eur"] / 1_000_000
    if "value_gap_eur" in out.columns:
        out["value_gap_eur"] = out["value_gap_eur"] / 1_000_000
    # Parse FBref "years-days" age format to integer year
    if "Age" in out.columns:
        out["Age"] = out["Age"].apply(_parse_age).astype("Int64")
    return out.reset_index(drop=True)


def should_show_disclaimer(selected_leagues: list) -> bool:
    """Return True when more than one league is selected (DASH-07)."""
    return len(selected_leagues) > 1


# ── Scatter chart ──────────────────────────────────────────────────────────────


def scatter_chart(df: pd.DataFrame) -> go.Figure:
    """UV scatter: x=scout_score, y=predicted_log_mv. OLS regression line."""
    fig = go.Figure()
    # Add a temporary market_value_eur_m column for hovertemplate
    df = df.copy()
    df["_mv_m"] = df["market_value_eur"] / 1_000_000 if df["market_value_eur"].max() > 1000 else df["market_value_eur"]
    for pos, color in POS_COLORS.items():
        sub = df[df["Pos"] == pos]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["scout_score"],
            y=sub["predicted_log_mv"],
            mode="markers",
            name=pos,
            marker=dict(
                size=7,
                color=color,
                opacity=0.75,
                line=dict(width=0.5, color="rgba(0,0,0,0.4)"),
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Club: %{customdata[1]}<br>"
                "Position: %{customdata[2]}<br>"
                "Scout Score: %{x:.1f}<br>"
                "Market Value: €%{customdata[3]:.1f}M<br>"
                "UV Score: %{customdata[4]:.1f}"
                "<extra></extra>"
            ),
            customdata=sub[["Player", "Squad", "Pos", "_mv_m", "uv_score"]].values,
        ))
    # OLS regression line in log-space (x=scout_score, y=predicted_log_mv)
    valid = df.dropna(subset=["scout_score", "predicted_log_mv"])
    if len(valid) >= 2:
        x_arr = valid["scout_score"].values
        y_arr = valid["predicted_log_mv"].values
        coeffs = np.polyfit(x_arr, y_arr, 1)
        x_range = np.linspace(x_arr.min(), x_arr.max(), 100)
        fig.add_trace(go.Scatter(
            x=x_range,
            y=np.polyval(coeffs, x_range),
            mode="lines",
            name="FAIR VALUE LINE",
            line=dict(color="#00A8FF", width=1.5, dash="dot"),
        ))
    fig.update_layout(
        **NAVY_LAYOUT,
        height=480,
        xaxis=dict(
            title="SCOUT SCORE",
            range=[0, 100],
            gridcolor="rgba(255,255,255,0.06)",
            linecolor="rgba(255,255,255,0.1)",
            title_font=dict(color="#8DA4B8", size=11),
            tickfont=dict(color="#8DA4B8"),
        ),
        yaxis=dict(
            title="LOG\u2081\u2080 MARKET VALUE",
            gridcolor="rgba(255,255,255,0.06)",
            linecolor="rgba(255,255,255,0.1)",
            title_font=dict(color="#8DA4B8", size=11),
            tickfont=dict(color="#8DA4B8"),
        ),
        legend=dict(
            bgcolor="#112236",
            bordercolor="rgba(0,168,255,0.2)",
            borderwidth=1,
            font=dict(color="#E8EDF2"),
        ),
    )
    return fig


# ── Column config ──────────────────────────────────────────────────────────────

COLUMN_CONFIG = {
    "Player":                st.column_config.TextColumn("PLAYER"),
    "Squad":                 st.column_config.TextColumn("CLUB"),
    "League":                st.column_config.TextColumn("LEAGUE"),
    "Pos":                   st.column_config.TextColumn("POSITION"),
    "Age":                   st.column_config.TextColumn("AGE"),
    "scout_score":           st.column_config.NumberColumn("SCOUT SCORE", format="%.1f"),
    "uv_score":              st.column_config.NumberColumn("UV SCORE", format="%.1f"),
    "uv_score_age_weighted": st.column_config.NumberColumn("AGE-WEIGHTED UV", format="%.1f"),
    "market_value_eur":      st.column_config.NumberColumn("VALUE (€M)", format="%.1f"),
    "value_gap_eur":         st.column_config.NumberColumn("VALUE GAP (€M)", format="%.1f"),
}

# ── Inject CSS ─────────────────────────────────────────────────────────────────

st.markdown(NAVY_CSS, unsafe_allow_html=True)

# ── Load data ──────────────────────────────────────────────────────────────────

with st.spinner("Loading data pipeline..."):
    try:
        full_df = load_data()
    except Exception as e:
        st.error(
            f"Data pipeline failed: {e}. Try refreshing — if the problem persists, "
            "check your internet connection and run `python scraper.py` to pre-populate the cache."
        )
        st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<div style='font-size:20px;font-weight:600;color:#E8EDF2;letter-spacing:0.05em;'>MONEYBALL</div>"
        "<div style='font-size:11px;font-weight:600;color:#8DA4B8;letter-spacing:0.12em;"
        "text-transform:uppercase;margin-top:2px;'>SCOUTING INTELLIGENCE v2.0</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # FILTER-01: League
    st.markdown("<div class='section-header'>LEAGUE</div>", unsafe_allow_html=True)
    LEAGUE_OPTIONS = ["EPL", "LaLiga", "Bundesliga", "SerieA", "Ligue1"]
    sel_leagues = st.multiselect(
        "league", options=LEAGUE_OPTIONS, default=LEAGUE_OPTIONS,
        label_visibility="collapsed", key="sel_leagues",
    )
    if not sel_leagues:
        sel_leagues = LEAGUE_OPTIONS

    # FILTER-02: Position
    st.markdown("<div class='section-header'>POSITION</div>", unsafe_allow_html=True)
    POS_OPTIONS = ["GK", "DF", "MF", "FW"]
    sel_positions = st.multiselect(
        "position", options=POS_OPTIONS, default=POS_OPTIONS,
        label_visibility="collapsed", key="sel_positions",
    )
    if not sel_positions:
        sel_positions = POS_OPTIONS

    # FILTER-03: Age range
    st.markdown("<div class='section-header'>AGE RANGE</div>", unsafe_allow_html=True)
    age_range = st.slider(
        "age_range", min_value=17, max_value=38, value=(17, 38), step=1,
        label_visibility="collapsed", key="age_range",
    )

    # FILTER-04: Club — derived dynamically from selected leagues
    st.markdown("<div class='section-header'>CLUB</div>", unsafe_allow_html=True)
    available_clubs = get_available_clubs(full_df, sel_leagues)
    sel_clubs = st.multiselect(
        "club", options=available_clubs, default=[],
        label_visibility="collapsed", key="sel_clubs",
    )
    if not sel_clubs:
        sel_clubs = available_clubs

    # FILTER-05: Market value (€M)
    st.markdown("<div class='section-header'>VALUE (€M)</div>", unsafe_allow_html=True)
    mv_max_m = max(
        int(np.ceil(full_df["market_value_eur"].max() / 1e7)) * 10, 200
    ) if not full_df.empty else 200
    mv_range = st.slider(
        "mv_range", min_value=0, max_value=mv_max_m, value=(0, mv_max_m), step=1,
        label_visibility="collapsed", key="mv_range",
    )

    # FILTER-06: Season
    st.markdown("<div class='section-header'>SEASON</div>", unsafe_allow_html=True)
    SEASON_OPTIONS = ["2023-24", "2024-25"]
    sel_seasons = st.multiselect(
        "season", options=SEASON_OPTIONS, default=SEASON_OPTIONS,
        label_visibility="collapsed", key="sel_seasons",
    )
    if not sel_seasons:
        sel_seasons = SEASON_OPTIONS

    st.divider()
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ── Apply filters ──────────────────────────────────────────────────────────────

df = apply_filters(
    full_df,
    leagues=sel_leagues,
    positions=sel_positions,
    age_range=age_range,
    clubs=sel_clubs,
    mv_range=mv_range,
    seasons=sel_seasons,
)

# ── Empty state ────────────────────────────────────────────────────────────────

if df.empty:
    st.warning("NO PLAYERS MATCH CURRENT FILTERS")
    st.caption("Try widening your age range, adding more leagues, or adjusting the market value limits.")
    if st.button("Reset Filters"):
        for key in ["sel_leagues", "sel_positions", "age_range", "sel_clubs", "mv_range", "sel_seasons"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    st.stop()

# ── Main area header ───────────────────────────────────────────────────────────

st.markdown(
    "<div class='section-header' style='font-size:20px;padding:8px 16px;margin-bottom:24px;'>"
    "MONEYBALL — SHORTLIST</div>",
    unsafe_allow_html=True,
)

# ── Shortlist table (DASH-01, DASH-02, DASH-03, DASH-04) ──────────────────────

display_df = prepare_display_df(df)
st.caption(f"Showing {len(display_df)} players")

table_state = st.dataframe(
    display_df,
    on_select="rerun",
    selection_mode="single-row",
    use_container_width=True,
    hide_index=True,
    column_config=COLUMN_CONFIG,
)

# ── Row-click placeholder panel (DASH-04) ─────────────────────────────────────

selected_rows = table_state["selection"]["rows"]
if selected_rows:
    row_idx = selected_rows[0]
    player = display_df.iloc[row_idx]
    with st.container():
        st.markdown(
            "<div style='border:1px solid rgba(0,168,255,0.25);border-left:3px solid #00A8FF;"
            "background:#112236;padding:16px;margin-top:16px;'>",
            unsafe_allow_html=True,
        )
        st.markdown(f"### Player Profile")
        mv_display = f"€{player['market_value_eur']:.1f}M" if pd.notna(player.get('market_value_eur')) else "N/A"
        raw_age = player.get('Age', '—')
        age_display = int(_parse_age(raw_age)) if pd.notna(_parse_age(raw_age)) else raw_age
        st.markdown(
            f"**{player['Player']}** · {player.get('Squad','—')} · "
            f"{player.get('League','—')} · {player.get('Pos','—')} · "
            f"Age {age_display} · {mv_display}"
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("SCOUT SCORE", f"{player.get('scout_score', 0):.1f}")
        c2.metric("UV SCORE", f"{player.get('uv_score', 0):.1f}")
        c3.metric("AGE-WEIGHTED UV", f"{player.get('uv_score_age_weighted', 0):.1f}")
        st.caption("Full profile coming soon")
        st.markdown("</div>", unsafe_allow_html=True)

# ── UV scatter plot (DASH-06) ─────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-header'>SCOUT SCORE vs MARKET VALUE</div>",
    unsafe_allow_html=True,
)
# scatter_chart expects raw EUR market_value_eur and predicted_log_mv — use filtered df (not display_df)
st.plotly_chart(scatter_chart(df), use_container_width=True)

# DASH-07: cross-league disclaimer
if should_show_disclaimer(sel_leagues):
    st.caption(
        "Scout scores are normalized per league. Cross-league comparison uses a league quality "
        "multiplier (EPL 1.10× — Ligue 1 1.00×). Direct per-90 comparisons across leagues are "
        "not equivalent."
    )
