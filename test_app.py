"""Tests for app.py Phase 5 dashboard — filter logic, chart functions, CSS constants."""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Attempt to import pure-Python functions from app.py directly — no Streamlit server running.
# Plan 05-02 will refactor app.py to extract these as module-level functions.
# Until then, this block raises ImportError (functions not yet defined in app.py).
# RED state: all 12 tests fail. GREEN state after Plan 05-02.
_APP_IMPORT_ERROR = None
try:
    from app import (  # noqa: E402  (guarded by try/except)
        apply_filters,
        get_available_clubs,
        prepare_display_df,
        scatter_chart,
        should_show_disclaimer,
        NAVY_CSS,
        filter_by_name,
        cap_selection,
        get_profile_header,
        build_radar_figure,
        compute_percentile,
        parse_similar_players,
    )
except BaseException as _e:
    # Catches ImportError (functions not yet defined), SystemExit from st.stop(),
    # and any other exception that app.py may raise during module-level execution.
    _APP_IMPORT_ERROR = _e
    # Provide sentinel stubs so the module parses; tests will raise via _require_app()
    apply_filters = None
    get_available_clubs = None
    prepare_display_df = None
    scatter_chart = None
    should_show_disclaimer = None
    NAVY_CSS = None
    filter_by_name = None
    cap_selection = None
    get_profile_header = None
    build_radar_figure = None
    compute_percentile = None
    parse_similar_players = None


def _require_app():
    """Raise ImportError inside any test that runs before Plan 05-02 is complete."""
    if _APP_IMPORT_ERROR is not None:
        raise ImportError(
            f"app.py does not yet export the required Phase 5 functions. "
            f"Original error: {_APP_IMPORT_ERROR}"
        )


# ── Fixture factory ───────────────────────────────────────────────────────────

def make_pipeline_df(n: int = 20) -> pd.DataFrame:
    """
    Deterministic synthetic DataFrame matching run_scoring_pipeline output schema.
    Columns: Player, Squad, Pos, Age, League, market_value_eur, scout_score,
             uv_score, uv_score_age_weighted, value_gap_eur,
             league_quality_multiplier, predicted_log_mv, similar_players, _season
    """
    positions = ["FW", "MF", "DF", "GK"]
    leagues = ["EPL", "LaLiga", "Bundesliga", "SerieA", "Ligue1"]
    ages = ["22-150", "24-201", "26-100", "28-050", "30-200"]
    mv_values = [5e6, 10e6, 15e6, 20e6, 25e6, 30e6]

    players = []
    scout_scores = np.linspace(40.0, 90.0, n)

    for i in range(n):
        mv = mv_values[i % len(mv_values)]
        predicted_log_mv = np.log10(mv)
        scout = float(scout_scores[i])
        uv = scout / predicted_log_mv
        uv_age_w = uv * 1.1 if i < n // 2 else uv
        league = leagues[i % len(leagues)]

        players.append({
            "Player": f"Player{i}",
            "Squad": f"Club{i % 10}",
            "Pos": positions[i % len(positions)],
            "Age": ages[i % len(ages)],
            "League": league,
            "market_value_eur": mv,
            "scout_score": scout,
            "uv_score": uv,
            "uv_score_age_weighted": uv_age_w,
            "value_gap_eur": mv * 0.1,
            "league_quality_multiplier": 1.10 if league == "EPL" else 1.00,
            "predicted_log_mv": predicted_log_mv,
            "similar_players": (
                '[{"player":"Player5","club":"Club5","league":"EPL","uv_score_age_weighted":8.5}]'
                if i == 0 else "[]"
            ),
            "_season": "2023-24" if i % 2 == 0 else "2024-25",
            "Nation": ["ENG", "ESP", "BRA", "FRA", "DEU"][i % 5],
            "score_attacking":   round(float(scout_scores[i]) * 0.45, 2),
            "score_progression": round(float(scout_scores[i]) * 0.20, 2),
            "score_creation":    round(float(scout_scores[i]) * 0.20, 2),
            "score_defense":     round(float(scout_scores[i]) * 0.05, 2),
            "score_retention":   round(float(scout_scores[i]) * 0.10, 2),
            "Gls_p90":  round(0.3 + (i % 5) * 0.1, 2),
            "Ast_p90":  round(0.2 + (i % 4) * 0.1, 2),
            "SoT_p90":  round(1.2 + (i % 3) * 0.2, 2),
            "Sh_p90":   round(2.5 + (i % 5) * 0.3, 2),
            "Int_p90":  round(1.0 + (i % 4) * 0.2, 2),
            "TklW_p90": round(0.8 + (i % 3) * 0.2, 2),
            "Fld_p90":  round(1.5 + (i % 5) * 0.1, 2),
            "Crs_p90":  round(0.5 + (i % 4) * 0.1, 2),
            "Saves_p90": round(3.0 + (i % 3) * 0.5, 2) if positions[i % len(positions)] == "GK" else 0.0,
            "Save%":     round(70 + (i % 5) * 3.0, 2) if positions[i % len(positions)] == "GK" else 0.0,
        })

    return pd.DataFrame(players)


@pytest.fixture
def full_df() -> pd.DataFrame:
    """Pytest fixture that delegates to make_pipeline_df(20)."""
    return make_pipeline_df(20)


# ── Tests ────────────────────────────────────────────────────────────────────


def test_filter_league(full_df):
    """apply_filters with leagues=["EPL"] returns only EPL players."""
    _require_app()
    result = apply_filters(full_df, leagues=["EPL"])
    assert not result.empty, "Expected EPL rows to be present"
    assert (result["League"] == "EPL").all(), (
        f"Expected all rows to be EPL, got: {result['League'].unique().tolist()}"
    )
    # Should have excluded LaLiga players
    assert "LaLiga" not in result["League"].values, "LaLiga players should be excluded"


def test_filter_position(full_df):
    """apply_filters with positions=["FW"] returns only FW players."""
    _require_app()
    result = apply_filters(full_df, positions=["FW"])
    assert not result.empty, "Expected FW rows to be present"
    assert (result["Pos"] == "FW").all(), (
        f"Expected all rows to be FW, got: {result['Pos'].unique().tolist()}"
    )


def test_filter_age(full_df):
    """apply_filters with age_range=(20, 25) excludes players outside 20–25 float age range."""
    _require_app()
    # "24-201" → age 24 → passes; "26-100" → age 26 → excluded
    result = apply_filters(full_df, age_range=(20, 25))

    # Verify "24-201" (age 24) players are included
    ages_present = result["Age"].tolist()
    # Verify "26-100" (age 26) players are excluded
    assert "26-100" not in ages_present, (
        "'26-100' (age 26) should be excluded when age_range=(20, 25)"
    )
    # Verify "24-201" (age 24) players are included
    assert "24-201" in ages_present, (
        "'24-201' (age 24) should be included when age_range=(20, 25)"
    )


def test_club_options_derived_from_leagues(full_df):
    """get_available_clubs(full_df, leagues=["EPL"]) returns only clubs present in EPL rows."""
    _require_app()
    epl_clubs = set(full_df.loc[full_df["League"] == "EPL", "Squad"].unique())
    non_epl_clubs = set(full_df.loc[full_df["League"] != "EPL", "Squad"].unique())

    result = get_available_clubs(full_df, leagues=["EPL"])
    result_set = set(result)

    # All returned clubs must be from EPL
    assert result_set.issubset(epl_clubs), (
        f"Non-EPL clubs returned: {result_set - epl_clubs}"
    )
    # No club that appears ONLY in non-EPL rows should be included
    # (clubs appearing in both EPL and non-EPL are valid to include)
    epl_only_clubs = epl_clubs - non_epl_clubs
    if epl_only_clubs:
        assert epl_only_clubs.issubset(result_set), (
            f"EPL-only clubs missing from result: {epl_only_clubs - result_set}"
        )


def test_filter_market_value(full_df):
    """apply_filters with mv_range=(0, 20) excludes players with market_value_eur > 20_000_000."""
    _require_app()
    # mv_range values are in €M — apply_filters multiplies by 1e6 internally
    result = apply_filters(full_df, mv_range=(0, 20))

    # All players should have market_value_eur <= 20_000_000
    assert (result["market_value_eur"] <= 20_000_000).all(), (
        f"Players with market_value_eur > 20M should be excluded. "
        f"Max found: {result['market_value_eur'].max()}"
    )
    # Players with market_value_eur > 20_000_000 should NOT appear
    assert not (result["market_value_eur"] > 20_000_000).any(), (
        "Players with market_value > €20M must be excluded (slider uses €M * 1e6 internally)"
    )


def test_filter_season(full_df):
    """apply_filters with seasons=["2023-24"] returns only 2023-24 rows; absent _season returns df unchanged."""
    _require_app()
    result = apply_filters(full_df, seasons=["2023-24"])
    assert not result.empty, "Expected 2023-24 rows"
    assert (result["_season"] == "2023-24").all(), (
        f"Expected all rows to be 2023-24, got: {result['_season'].unique().tolist()}"
    )
    assert "2024-25" not in result["_season"].values, "2024-25 rows should be excluded"

    # Defensive skip: if _season column absent, return df unchanged
    df_no_season = full_df.drop(columns=["_season"])
    result_no_season = apply_filters(df_no_season, seasons=["2023-24"])
    assert len(result_no_season) == len(df_no_season), (
        "When _season column is absent, apply_filters should return df unchanged"
    )


def test_default_sort_order(full_df):
    """prepare_display_df returns DataFrame sorted by uv_score_age_weighted descending."""
    _require_app()
    result = prepare_display_df(full_df)

    # First row should have the highest uv_score_age_weighted
    max_uv_aw = full_df["uv_score_age_weighted"].max()
    assert result.iloc[0]["uv_score_age_weighted"] == pytest.approx(max_uv_aw, rel=1e-6), (
        f"First row uv_score_age_weighted {result.iloc[0]['uv_score_age_weighted']:.4f} "
        f"!= max {max_uv_aw:.4f}"
    )

    # Verify descending order throughout
    uv_vals = result["uv_score_age_weighted"].tolist()
    assert uv_vals == sorted(uv_vals, reverse=True), (
        "Rows are not sorted by uv_score_age_weighted descending"
    )


def test_display_columns(full_df):
    """prepare_display_df returns DataFrame with exactly the expected columns; market_value_eur in €M."""
    _require_app()
    expected_cols = {
        "Player", "Squad", "League", "Pos", "Age",
        "scout_score", "uv_score", "uv_score_age_weighted",
        "market_value_eur", "value_gap_eur",
    }
    result = prepare_display_df(full_df)

    result_cols = set(result.columns)
    assert result_cols == expected_cols, (
        f"Column mismatch.\nExpected: {sorted(expected_cols)}\nGot: {sorted(result_cols)}"
    )

    # market_value_eur must be in €M (divided by 1e6)
    original_max_mv = full_df["market_value_eur"].max()
    result_max_mv = result["market_value_eur"].max()
    assert result_max_mv == pytest.approx(original_max_mv / 1e6, rel=1e-6), (
        f"market_value_eur should be in €M. "
        f"Original max: {original_max_mv}, result max: {result_max_mv}"
    )


def test_row_selection_index(full_df):
    """Row index 0 of prepare_display_df output is the player with max uv_score_age_weighted."""
    _require_app()
    result = prepare_display_df(full_df).reset_index(drop=True)

    top_player_name = full_df.loc[
        full_df["uv_score_age_weighted"].idxmax(), "Player"
    ]
    assert result.iloc[0]["Player"] == top_player_name, (
        f"display_df.iloc[0]['Player'] = {result.iloc[0]['Player']!r}, "
        f"expected player with max uv_score_age_weighted = {top_player_name!r}"
    )


def test_css_contains_navy_theme():
    """NAVY_CSS string contains #0D1B2A (background), #00A8FF (accent), and Inter (font)."""
    _require_app()
    assert "#0D1B2A" in NAVY_CSS, (
        f"NAVY_CSS missing background color #0D1B2A"
    )
    assert "#00A8FF" in NAVY_CSS, (
        f"NAVY_CSS missing accent color #00A8FF"
    )
    assert "Inter" in NAVY_CSS, (
        f"NAVY_CSS missing Inter font family"
    )


def test_scatter_axes():
    """scatter_chart returns a go.Figure with scout_score on x, raw market_value_eur on y (log axis), and FAIR VALUE LINE trace."""
    _require_app()
    df = make_pipeline_df(10)
    fig = scatter_chart(df)

    assert isinstance(fig, go.Figure), (
        f"scatter_chart should return go.Figure, got {type(fig)}"
    )

    # Figure must have at least one trace
    assert len(fig.data) > 0, "scatter_chart figure has no traces"

    # Must have a trace named "FAIR VALUE LINE"
    trace_names = [t.name for t in fig.data]
    assert "FAIR VALUE LINE" in trace_names, (
        f"No 'FAIR VALUE LINE' trace found. Trace names: {trace_names}"
    )

    # Non-fair-value traces should use scout_score on x
    player_traces = [t for t in fig.data if t.name != "FAIR VALUE LINE"]
    assert len(player_traces) > 0, "No player scatter traces found"

    scout_scores_in_df = set(df["scout_score"].tolist())
    trace_x_values = set()
    for t in player_traces:
        if t.x is not None and len(t.x) > 0:
            trace_x_values.update(float(v) for v in t.x)

    assert trace_x_values.issubset(scout_scores_in_df | {float("nan")}), (
        "Scatter trace x-values should be scout_score values"
    )

    # y-values for player traces are raw market_value_eur (Plotly renders log via yaxis.type="log")
    sub_traces = [t for t in fig.data if t.name != "FAIR VALUE LINE"]
    for t in sub_traces:
        if t.y is not None and len(t.y) > 0:
            y_vals = [float(v) for v in t.y if v is not None]
            assert all(v >= 1 for v in y_vals), (
                f"Trace '{t.name}' y-values should be positive market values (EUR), got min: {min(y_vals):.2f}"
            )
    # y-axis must be configured as log-scale
    assert fig.layout.yaxis.type == "log", (
        f"scatter_chart yaxis.type should be 'log', got '{fig.layout.yaxis.type}'"
    )


def test_cross_league_disclaimer_condition():
    """should_show_disclaimer returns True only when 2+ leagues selected."""
    _require_app()
    assert should_show_disclaimer(selected_leagues=["EPL"]) is False, (
        "should_show_disclaimer(['EPL']) should return False (single league)"
    )
    assert should_show_disclaimer(selected_leagues=["EPL", "LaLiga"]) is True, (
        "should_show_disclaimer(['EPL', 'LaLiga']) should return True (multi-league)"
    )
    assert should_show_disclaimer(selected_leagues=[]) is False, (
        "should_show_disclaimer([]) should return False (no leagues selected)"
    )


# ── Phase 6 tests ─────────────────────────────────────────────────────────────

def test_filter_by_name(full_df):
    """filter_by_name(df, 'player0') returns only rows where Player contains 'player0' (case-insensitive)."""
    _require_app()
    result = filter_by_name(full_df, "player0")
    assert not result.empty, "Expected matching rows"
    assert result["Player"].str.contains("player0", case=False).all()


def test_filter_by_name_empty(full_df):
    """filter_by_name(df, '') returns the full DataFrame unchanged."""
    _require_app()
    result = filter_by_name(full_df, "")
    assert len(result) == len(full_df), f"Expected {len(full_df)} rows, got {len(result)}"


def test_filter_by_name_case_insensitive(full_df):
    """filter_by_name is case-insensitive: 'PLAYER' matches 'Player0'."""
    _require_app()
    result = filter_by_name(full_df, "PLAYER")
    assert len(result) == len(full_df), "All players should match 'PLAYER' (case-insensitive)"


def test_selection_cap():
    """cap_selection([0,1,2,3], max_n=3) returns [0,1,2]."""
    _require_app()
    result = cap_selection([0, 1, 2, 3], max_n=3)
    assert result == [0, 1, 2], f"Expected [0,1,2], got {result}"
    assert cap_selection([0, 1], max_n=3) == [0, 1], "Lists <= max_n must be returned unchanged"
    assert cap_selection([], max_n=3) == [], "Empty list must return empty list"


def test_profile_header_data(full_df):
    """get_profile_header(row) returns dict with required keys."""
    _require_app()
    row = full_df.iloc[0]
    result = get_profile_header(row)
    required_keys = {"name", "age", "club", "league", "position", "nation", "market_value_m"}
    assert required_keys.issubset(set(result.keys())), (
        f"Missing keys: {required_keys - set(result.keys())}"
    )
    assert isinstance(result["age"], (int, float)), "age must be numeric"
    assert result["market_value_m"] == pytest.approx(row["market_value_eur"] / 1e6, rel=1e-3)


def test_radar_figure():
    """build_radar_figure returns go.Figure with >= 2 Scatterpolar traces (player + median)."""
    import plotly.graph_objects as go
    _require_app()
    players_data = [{"name": "TestPlayer", "scores": [50.0, 60.0, 40.0, 55.0, 45.0], "color": "#00A8FF"}]
    peer_median = [45.0, 50.0, 35.0, 50.0, 40.0]
    fig = build_radar_figure(players_data, peer_median)
    assert isinstance(fig, go.Figure), f"Expected go.Figure, got {type(fig)}"
    assert len(fig.data) >= 2, f"Expected >= 2 traces (player + median), got {len(fig.data)}"
    trace_types = [type(t).__name__ for t in fig.data]
    assert all(t == "Scatterpolar" for t in trace_types), (
        f"All traces must be Scatterpolar, got: {trace_types}"
    )


def test_radar_median_source():
    """build_radar_figure includes a trace named 'PEER MEDIAN'."""
    _require_app()
    players_data = [{"name": "X", "scores": [50.0, 60.0, 40.0, 55.0, 45.0], "color": "#FF5757"}]
    peer_median = [45.0, 50.0, 35.0, 50.0, 40.0]
    fig = build_radar_figure(players_data, peer_median)
    trace_names = [t.name for t in fig.data]
    assert "PEER MEDIAN" in trace_names, (
        f"No 'PEER MEDIAN' trace found. Trace names: {trace_names}"
    )


def test_compute_percentile():
    """compute_percentile returns float in [0, 100]."""
    _require_app()
    series = pd.Series([0, 25, 50, 75, 100])
    result = compute_percentile(75.0, series)
    assert isinstance(result, float), f"Expected float, got {type(result)}"
    assert 0.0 <= result <= 100.0, f"Percentile {result} is out of [0, 100] range"
    # Value at or above all others → percentile near 100
    top = compute_percentile(100.0, series)
    assert top >= 80.0, f"Value at max should have high percentile, got {top}"
    # Value at or below all others → percentile near 0
    bot = compute_percentile(0.0, series)
    assert bot <= 20.0, f"Value at min should have low percentile, got {bot}"


def test_scatter_highlight():
    """scatter_chart(df, highlighted_players=['Player0']) adds a named trace with marker.size > 7."""
    import plotly.graph_objects as go
    _require_app()
    df = make_pipeline_df(10)
    fig = scatter_chart(df, highlighted_players=["Player0"])
    assert isinstance(fig, go.Figure)
    highlighted = [t for t in fig.data if t.name == "Player0"]
    assert len(highlighted) == 1, (
        f"Expected 1 trace named 'Player0', got {len(highlighted)}. "
        f"All trace names: {[t.name for t in fig.data]}"
    )
    assert highlighted[0].marker.size > 7, (
        f"Highlighted trace marker.size should be > 7, got {highlighted[0].marker.size}"
    )


def test_parse_similar_players(full_df):
    """parse_similar_players returns enriched list with age and market_value_m."""
    _require_app()
    # Row 0 has similar_players JSON with Player5/Club5
    row = full_df.iloc[0]
    result = parse_similar_players(row, full_df)
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    if result:  # non-empty: check structure
        item = result[0]
        required_keys = {"player", "club", "league", "uv_score_age_weighted", "age", "market_value_m"}
        assert required_keys.issubset(set(item.keys())), (
            f"Missing keys: {required_keys - set(item.keys())}"
        )


def test_parse_similar_players_malformed(full_df):
    """parse_similar_players with malformed JSON returns empty list (no crash)."""
    _require_app()
    bad_row = full_df.iloc[0].copy()
    bad_row["similar_players"] = "not valid json {{{{"
    result = parse_similar_players(bad_row, full_df)
    assert result == [], f"Expected empty list for malformed JSON, got {result}"
