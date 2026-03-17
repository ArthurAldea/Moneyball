"""
app.py — Moneyball Intelligence System
Cybersecurity-themed Streamlit dashboard for EPL player undervaluation analysis.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from config import PILLARS_FW, PILLARS_MF, PILLARS_DF, GK_PILLARS

st.set_page_config(
    page_title="Moneyball // Intelligence System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Cybersecurity CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

  html, body, [data-testid="stAppViewContainer"] {
      background-color: #080808;
      color: #c8ffc8;
      font-family: 'Share Tech Mono', 'Courier New', monospace;
  }
  [data-testid="stSidebar"] {
      background-color: #050505;
      border-right: 1px solid rgba(0,255,65,0.18);
  }
  h1, h2, h3 {
      color: #00ff41;
      text-shadow: 0 0 12px rgba(0,255,65,0.45);
      letter-spacing: 0.07em;
  }
  [data-testid="metric-container"] {
      background: #0d0d0d;
      border: 1px solid rgba(0,255,65,0.2);
      border-left: 3px solid #00ff41;
      box-shadow: 0 0 10px rgba(0,255,65,0.07);
      border-radius: 2px;
      padding: 12px 16px;
  }
  [data-testid="stMetricValue"] {
      color: #00ff41;
      font-size: 1.45rem;
      font-weight: 700;
      text-shadow: 0 0 8px rgba(0,255,65,0.4);
  }
  [data-testid="stMetricLabel"] {
      color: #4a8a4a;
      font-size: 0.68rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
  }
  .stButton > button {
      background: transparent;
      color: #00ff41;
      font-weight: 700;
      border: 1px solid rgba(0,255,65,0.6);
      border-radius: 2px;
      letter-spacing: 0.07em;
      width: 100%;
      font-family: 'Share Tech Mono', 'Courier New', monospace;
      box-shadow: 0 0 8px rgba(0,255,65,0.2);
  }
  .stButton > button:hover {
      background: rgba(0,255,65,0.08);
      box-shadow: 0 0 18px rgba(0,255,65,0.4);
      color: #00ff41;
  }
  .stTabs [data-baseweb="tab"] {
      color: #3a7a3a;
      font-family: 'Share Tech Mono', 'Courier New', monospace;
      font-size: 0.78rem;
      letter-spacing: 0.07em;
      text-transform: uppercase;
  }
  .stTabs [aria-selected="true"] {
      color: #00ff41;
      border-bottom: 2px solid #00ff41;
      text-shadow: 0 0 6px rgba(0,255,65,0.5);
  }
  .stTabs [data-baseweb="tab-list"] {
      background: #080808;
      border-bottom: 1px solid rgba(0,255,65,0.12);
  }
  hr { border-color: rgba(0,255,65,0.1); }
  [data-testid="stDataFrame"] {
      border: 1px solid rgba(0,255,65,0.15);
  }
  /* Dataframe cell text */
  [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
      color: #c8ffc8 !important;
  }
  .stMultiSelect [data-baseweb="tag"] {
      background-color: rgba(0,255,65,0.12);
      color: #00ff41;
  }
  /* Slider */
  [data-baseweb="slider"] [data-testid="stTickBar"] { color: #4a8a4a; }

  /* ── Custom components ── */
  .cyber-header {
      border-left: 4px solid #00ff41;
      padding: 8px 16px;
      background: rgba(0,255,65,0.04);
      margin-bottom: 12px;
      box-shadow: inset 0 0 20px rgba(0,255,65,0.03);
  }
  .status-bar {
      display: flex; gap: 24px; align-items: center;
      padding: 6px 0; margin-bottom: 12px;
      border-bottom: 1px solid rgba(0,255,65,0.1);
  }
  .status-dot {
      display: inline-block; width: 8px; height: 8px;
      border-radius: 50%; background: #00ff41;
      box-shadow: 0 0 6px #00ff41;
      animation: pulse 2s infinite;
  }
  @keyframes pulse {
      0%,100% { opacity:1; } 50% { opacity:0.4; }
  }
  .player-card {
      background: #0d0d0d;
      border: 1px solid rgba(0,255,65,0.18);
      border-left: 4px solid #00ff41;
      border-radius: 2px;
      padding: 14px 18px;
      margin-bottom: 10px;
      box-shadow: 0 0 8px rgba(0,255,65,0.05);
      position: relative;
  }
  .player-card::before {
      content: '';
      position: absolute; top: 0; right: 0;
      width: 0; height: 0;
      border-style: solid;
      border-width: 0 16px 16px 0;
      border-color: transparent rgba(0,255,65,0.25) transparent transparent;
  }
  .player-rank { color: #3a7a3a; font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; }
  .player-name { color: #00ff41; font-size: 1rem; font-weight: 700; text-shadow: 0 0 6px rgba(0,255,65,0.35); }
  .player-meta { color: #4a8a4a; font-size: 0.72rem; margin-top: 3px; letter-spacing: 0.04em; }
  .stat-block { display: inline-block; margin-right: 20px; margin-top: 10px; }
  .stat-label { color: #3a7a3a; font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.12em; display: block; }
  .stat-value { color: #00ff41; font-weight: 700; font-size: 0.95rem; }
  .stat-value.red { color: #ff4444; }
  .stat-value.cyan { color: #00cfff; }
  .target-badge {
      display: inline-block; margin-top: 8px;
      background: transparent; color: #00ff41;
      border: 1px solid rgba(0,255,65,0.5);
      font-size: 0.72rem; padding: 2px 10px; border-radius: 2px;
      text-shadow: 0 0 5px rgba(0,255,65,0.4);
      box-shadow: 0 0 6px rgba(0,255,65,0.15);
      letter-spacing: 0.06em;
  }
  .gk-badge {
      display: inline-block; margin-left: 8px;
      background: rgba(0,207,255,0.08); color: #00cfff;
      border: 1px solid rgba(0,207,255,0.4);
      font-size: 0.62rem; padding: 1px 6px; border-radius: 2px;
      letter-spacing: 0.06em;
  }
  .section-label {
      color: #4a8a4a; font-size: 0.68rem;
      text-transform: uppercase; letter-spacing: 0.14em;
      margin-bottom: 8px; display: block;
  }
  .cyber-divider {
      border: none; border-top: 1px solid rgba(0,255,65,0.1);
      margin: 16px 0;
  }
</style>
""", unsafe_allow_html=True)

# ── Data loading ───────────────────────────────────────────────────────────────

ALL_SEASONS = ("2023-24", "2024-25", "2025-26")

@st.cache_data(ttl=86400, show_spinner=False)
def load_data(seasons: tuple = ALL_SEASONS):
    from scraper import run_fbref_scrapers, run_tm_scrapers
    from scorer import run_scoring_pipeline
    fbref_data = run_fbref_scrapers()
    tm_data    = run_tm_scrapers()
    return run_scoring_pipeline(fbref_data, tm_data)


# ── Pillar label helper ────────────────────────────────────────────────────────

def get_pillar_labels(pos: str) -> list:
    """Return display labels for a player's position group."""
    if pos == "GK":
        return [GK_PILLARS[k]["label"] for k in ["attacking","progression","creation","defense","retention"]]
    return [PILLARS_MF[k]["label"] for k in ["attacking","progression","creation","defense","retention"]]


# ── Plotly theme ───────────────────────────────────────────────────────────────

PILLAR_COLS   = ["score_attacking","score_progression","score_creation","score_defense","score_retention"]
PILLAR_COLORS = ["#ff3131","#00ff41","#00cfff","#f5a623","#c084fc"]

CYBER_LAYOUT = dict(
    paper_bgcolor="#080808",
    plot_bgcolor="#080808",
    font=dict(family="'Share Tech Mono', 'Courier New', monospace", color="#c8ffc8", size=11),
    margin=dict(t=48, b=40, l=40, r=40),
)


def radar_chart(players_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    colors = PILLAR_COLORS

    for i, (_, row) in enumerate(players_df.iterrows()):
        labels = get_pillar_labels(row.get("Pos", "MF"))
        values = [row.get(c, 0) for c in PILLAR_COLS]
        values_closed = values + [values[0]]
        labels_closed = labels + [labels[0]]
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill="toself",
            name=row["Player"],
            line=dict(color=color, width=2),
            fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)",
        ))
    fig.update_layout(
        **CYBER_LAYOUT,
        polar=dict(
            bgcolor="#0d0d0d",
            radialaxis=dict(
                visible=True, range=[0, 50],
                gridcolor="rgba(0,255,65,0.1)",
                linecolor="rgba(0,255,65,0.1)",
                tickfont=dict(color="#3a7a3a", size=8),
            ),
            angularaxis=dict(
                gridcolor="rgba(0,255,65,0.1)",
                linecolor="rgba(0,255,65,0.1)",
                tickfont=dict(color="#c8ffc8", size=10),
            ),
        ),
        legend=dict(bgcolor="#0d0d0d", bordercolor="rgba(0,255,65,0.2)", borderwidth=1,
                    font=dict(color="#c8ffc8")),
        height=440,
        title=dict(text="// CAPABILITY PROFILE — TOP 5 TARGETS",
                   font=dict(color="#00ff41", size=12)),
    )
    return fig


def scatter_chart(df: pd.DataFrame) -> go.Figure:
    pos_colors = {"FW": "#ff3131", "MF": "#00ff41", "DF": "#f5a623", "GK": "#00cfff"}
    fig = go.Figure()

    for pos, color in pos_colors.items():
        sub = df[df["Pos"] == pos]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["market_value_eur"],
            y=sub["scout_score"],
            mode="markers",
            name=pos,
            marker=dict(
                size=sub["uv_score"].clip(lower=4) / 6,
                color=color,
                opacity=0.75,
                line=dict(width=0.5, color="rgba(0,0,0,0.4)"),
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Club: %{customdata[1]}<br>"
                "Scout Score: %{y:.1f}<br>"
                "Asset Value: €%{x:,.0f}<br>"
                "UV Score: %{customdata[2]:.1f}"
                "<extra></extra>"
            ),
            customdata=sub[["Player","Squad","uv_score"]].values,
        ))

    # Trendline
    log_mv = np.log10(df["market_value_eur"].clip(lower=1))
    coeffs = np.polyfit(log_mv, df["scout_score"], 1)
    x_range = np.linspace(log_mv.min(), log_mv.max(), 100)
    y_range = np.polyval(coeffs, x_range)
    fig.add_trace(go.Scatter(
        x=10**x_range, y=y_range,
        mode="lines", name="// FAIR VALUE",
        line=dict(color="rgba(0,255,65,0.35)", width=1.5, dash="dot"),
    ))

    fig.update_layout(
        **CYBER_LAYOUT,
        height=500,
        xaxis=dict(
            type="log", title="ASSET VALUE (€, log scale)",
            gridcolor="rgba(0,255,65,0.07)", linecolor="rgba(0,255,65,0.15)",
            title_font=dict(color="#4a8a4a", size=10),
            tickfont=dict(color="#4a8a4a"),
        ),
        yaxis=dict(
            title="EXPLOIT INDEX (0–100)",
            gridcolor="rgba(0,255,65,0.07)", linecolor="rgba(0,255,65,0.15)",
            title_font=dict(color="#4a8a4a", size=10),
            tickfont=dict(color="#4a8a4a"),
        ),
        legend=dict(bgcolor="#0d0d0d", bordercolor="rgba(0,255,65,0.2)", borderwidth=1,
                    font=dict(color="#c8ffc8")),
        title=dict(text="// THREAT MATRIX — EXPLOIT INDEX vs ASSET VALUE",
                   font=dict(color="#00ff41", size=12)),
    )
    return fig


def pillar_bar_chart(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    top = df.head(top_n).copy()
    is_gk = (top["Pos"] == "GK").any()
    labels = get_pillar_labels(is_gk)
    fig = go.Figure()
    for col, label, color in zip(PILLAR_COLS, labels, PILLAR_COLORS):
        fig.add_trace(go.Bar(
            name=label, x=top["Player"], y=top[col],
            marker_color=color, marker_line_width=0,
        ))
    fig.update_layout(
        **CYBER_LAYOUT,
        barmode="stack", height=480,
        xaxis=dict(gridcolor="rgba(0,255,65,0.07)", linecolor="rgba(0,255,65,0.15)",
                   tickangle=-40, tickfont=dict(color="#4a8a4a", size=9)),
        yaxis=dict(gridcolor="rgba(0,255,65,0.07)", linecolor="rgba(0,255,65,0.15)",
                   title="SCORE", title_font=dict(color="#4a8a4a", size=10),
                   tickfont=dict(color="#4a8a4a")),
        legend=dict(bgcolor="#0d0d0d", bordercolor="rgba(0,255,65,0.2)", borderwidth=1,
                    font=dict(color="#c8ffc8")),
        title=dict(text=f"// CAPABILITY ANALYSIS — TOP {top_n} BY VULNERABILITY SCORE",
                   font=dict(color="#00ff41", size=12)),
    )
    return fig


def fmt_value(v: float) -> str:
    if pd.isna(v): return "N/A"
    if v >= 1_000_000: return f"€{v/1_000_000:.1f}m"
    return f"€{v/1_000:.0f}k"


def fmt_gap(v: float) -> str:
    if pd.isna(v): return "N/A"
    sign = "+" if v >= 0 else ""
    label = "UNDERVALUED" if v >= 0 else "OVERVALUED"
    return f"{sign}{fmt_value(abs(v))} {label}"


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='color:#00ff41;font-size:1.1rem;font-weight:700;"
        "text-shadow:0 0 10px rgba(0,255,65,0.5);letter-spacing:0.1em;'>"
        "⚡ MONEYBALL</div>"
        "<div style='color:#3a7a3a;font-size:0.65rem;letter-spacing:0.14em;"
        "margin-top:2px;'>INTELLIGENCE SYSTEM v2.0</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='cyber-divider'>", unsafe_allow_html=True)

    st.markdown("<span class='section-label'>// SEASON FILTER</span>", unsafe_allow_html=True)
    season_filter = st.multiselect(
        "Seasons", options=list(ALL_SEASONS),
        default=list(ALL_SEASONS), label_visibility="collapsed"
    )
    if not season_filter:
        season_filter = list(ALL_SEASONS)

    st.markdown("<span class='section-label' style='margin-top:12px;display:block;'>// POSITION FILTER</span>", unsafe_allow_html=True)
    pos_filter = st.multiselect(
        "Position", options=["GK", "DF", "MF", "FW"],
        default=["GK", "DF", "MF", "FW"], label_visibility="collapsed"
    )

    st.markdown("<span class='section-label' style='margin-top:12px;display:block;'>// MAX ASSET VALUE (€m)</span>", unsafe_allow_html=True)
    max_mv = st.slider("Max Market Value", 1, 200, 100, label_visibility="collapsed")

    st.markdown("<hr class='cyber-divider'>", unsafe_allow_html=True)
    refresh = st.button("↻  RESCAN DATA")
    if refresh:
        st.cache_data.clear()
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div style='color:#3a7a3a;font-size:0.68rem;line-height:2.0;letter-spacing:0.04em;'>"
        "SOURCES &nbsp;&nbsp; FBref · TM<br>"
        f"SEASONS &nbsp;&nbsp; {' · '.join(season_filter)}<br>"
        "MIN MIN &nbsp;&nbsp;&nbsp; 1,800<br>"
        "MODEL &nbsp;&nbsp;&nbsp;&nbsp; 5-Pillar Scout Score<br>"
        "FORMULA &nbsp;&nbsp; Score / log₁₀(Value)<br>"
        "GK MODEL &nbsp; Shot Stopping · Distribution"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Main header ────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='cyber-header'>"
    "<h1 style='margin:0;font-size:1.5rem;'>MONEYBALL // INTELLIGENCE SYSTEM</h1>"
    "<div style='color:#4a8a4a;font-size:0.72rem;letter-spacing:0.1em;margin-top:4px;'>"
    "ENGLISH PREMIER LEAGUE · VULNERABILITY ANALYSIS · TARGET IDENTIFICATION"
    "</div></div>",
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='status-bar'>"
    "<span><span class='status-dot'></span>"
    " <span style='color:#3a7a3a;font-size:0.68rem;letter-spacing:0.1em;'>SYSTEM ONLINE</span></span>"
    "<span style='color:#3a7a3a;font-size:0.68rem;'>|</span>"
    "<span style='color:#3a7a3a;font-size:0.68rem;letter-spacing:0.08em;'>CACHE: 7-DAY TTL</span>"
    "<span style='color:#3a7a3a;font-size:0.68rem;'>|</span>"
    "<span style='color:#3a7a3a;font-size:0.68rem;letter-spacing:0.08em;'>MODEL: 5-PILLAR SCOUT SCORE</span>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Load data ──────────────────────────────────────────────────────────────────
with st.spinner("// SCANNING... initialising data pipeline"):
    try:
        full_df = load_data(tuple(sorted(season_filter)))
    except Exception as e:
        st.error(f"// PIPELINE ERROR: {e}")
        st.stop()

# Apply filters
df = full_df.copy()
if pos_filter:
    df = df[df["Pos"].isin(pos_filter)]
df = df[df["market_value_eur"] <= max_mv * 1_000_000]
df = df.reset_index(drop=True)

if df.empty:
    st.warning("// NO TARGETS MATCH CURRENT FILTERS. Adjust parameters.")
    st.stop()

top5 = df.head(5)

# ── KPI strip ──────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("TARGETS IDENTIFIED", f"{len(full_df):,}")
k2.metric("AFTER FILTERS", f"{len(df):,}")
k3.metric("AVG EXPLOIT INDEX", f"{df['scout_score'].mean():.1f}")
k4.metric("AVG ASSET VALUE", fmt_value(df["market_value_eur"].mean()))
st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "⚡  HIGH-VALUE TARGETS",
    "📡  THREAT MATRIX",
    "📋  FULL SCAN RESULTS",
    "🔬  CAPABILITY ANALYSIS",
])

# ── Tab 1: Top 5 ───────────────────────────────────────────────────────────────
with tab1:
    col_cards, col_radar = st.columns([1, 1.3])

    with col_cards:
        st.markdown("<span class='section-label'>// TOP 5 IDENTIFIED TARGETS</span>", unsafe_allow_html=True)
        for rank, (_, row) in enumerate(top5.iterrows(), 1):
            gap_label = fmt_gap(row.get("value_gap_eur", float("nan")))
            is_gk = row.get("Pos") == "GK"
            gk_badge = "<span class='gk-badge'>GK</span>" if is_gk else ""
            exploit_label = "SHOT STOP / 90" if is_gk else "xG / 90"
            exploit_val = f"{row.get('Save%', 0):.1f}%" if is_gk else f"{row.get('xG_p90', row.get('xG', 0)/max(row.get('Min',1),1)*90):.2f}"
            st.markdown(f"""
            <div class='player-card'>
                <div class='player-rank'>// TARGET #{rank:02d}</div>
                <div class='player-name'>{row['Player']}{gk_badge}</div>
                <div class='player-meta'>{row.get('Squad','—')} &nbsp;·&nbsp; {row.get('Pos','—')} &nbsp;·&nbsp; {int(row['Min']) if pd.notna(row.get('Min')) else '—'} MIN</div>
                <div>
                    <div class='stat-block'>
                        <span class='stat-label'>EXPLOIT INDEX</span>
                        <span class='stat-value'>{row['scout_score']:.1f}</span>
                    </div>
                    <div class='stat-block'>
                        <span class='stat-label'>ASSET VALUE</span>
                        <span class='stat-value cyan'>{fmt_value(row['market_value_eur'])}</span>
                    </div>
                    <div class='stat-block'>
                        <span class='stat-label'>VULN SCORE</span>
                        <span class='stat-value'>{row['uv_score']:.1f}</span>
                    </div>
                </div>
                <span class='target-badge'>▲ {gap_label}</span>
            </div>
            """, unsafe_allow_html=True)

    with col_radar:
        st.plotly_chart(radar_chart(top5), use_container_width=True)

# ── Tab 2: Scatter ─────────────────────────────────────────────────────────────
with tab2:
    st.plotly_chart(scatter_chart(df), use_container_width=True)
    st.markdown(
        "<div style='color:#3a7a3a;font-size:0.72rem;letter-spacing:0.04em;'>"
        "// TARGETS <span style='color:#00ff41;'>ABOVE</span> the dotted line are outperforming their asset value — "
        "high exploit index relative to market price. "
        "Targets <span style='color:#ff4444;'>BELOW</span> are overpriced relative to output."
        "</div>",
        unsafe_allow_html=True,
    )

# ── Tab 3: Leaderboard ─────────────────────────────────────────────────────────
with tab3:
    display_cols = ["Player","Squad","Pos","scout_score","market_value_eur","uv_score","uv_score_age_weighted","value_gap_eur"]
    available_cols = [c for c in display_cols if c in df.columns]
    board = df[available_cols].head(100).copy()
    board["market_value_eur"] = board["market_value_eur"].apply(fmt_value)
    board["value_gap_eur"]    = board["value_gap_eur"].apply(fmt_gap)
    board["scout_score"]      = board["scout_score"].round(1)
    board["uv_score"]         = board["uv_score"].round(1)
    board.columns = [c.replace("_", " ").upper() for c in board.columns]
    board.columns = ["PLAYER","CLUB","POS","EXPLOIT INDEX","ASSET VALUE","VULN SCORE","AGE-ADJ UV","VECTOR DIFF"][:len(board.columns)]
    st.dataframe(board, use_container_width=True, hide_index=True, height=540)

# ── Tab 4: Pillar breakdown ────────────────────────────────────────────────────
with tab4:
    top_n = st.slider("Targets to display", 5, 30, 20)
    st.plotly_chart(pillar_bar_chart(df, top_n), use_container_width=True)
    st.markdown(
        "<div style='color:#3a7a3a;font-size:0.72rem;letter-spacing:0.04em;'>"
        "// Stacked bars show each target's contribution across capability pillars. "
        "Balanced profiles indicate well-rounded players; skewed profiles indicate specialists. "
        "GK pillars: Shot Stopping · Distribution · Aerial Command · Sweeping · Composure."
        "</div>",
        unsafe_allow_html=True,
    )
