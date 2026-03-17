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
            "similar_players": "[]",
            "_season": "2023-24" if i % 2 == 0 else "2024-25",
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
    """scatter_chart returns a go.Figure with scout_score on x, predicted_log_mv on y, and FAIR VALUE LINE trace."""
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

    # y-values for player traces should be log-scale (predicted_log_mv: all < 10 since log10(30e6) ~ 7.5)
    sub_traces = [t for t in fig.data if t.name != "FAIR VALUE LINE"]
    for t in sub_traces:
        if t.y is not None and len(t.y) > 0:
            y_vals = [float(v) for v in t.y if v is not None]
            assert all(v < 10 for v in y_vals), (
                f"Trace '{t.name}' y-values should be log-scale (< 10), got max: {max(y_vals):.2f}"
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
