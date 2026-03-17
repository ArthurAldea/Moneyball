"""
conftest.py — pytest configuration for Moneyball test suite.

Patches Streamlit module-level execution so that `import app` can be done
quickly during test collection without triggering live FBref/TM network scrapes.

This is required because app.py (pre-Phase-5-refactor) runs Streamlit code at
module level including a data-loading pipeline. Plan 05-02 will refactor app.py
into a pure-Python module; this patch bridges the gap during Phase 5 Plan 01.
"""

import sys
import types
import pandas as pd


class _NoopCtx:
    """A context manager that accepts any attribute access and calls, all returning None."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __getattr__(self, name):
        # Return a callable that returns another _NoopCtx for chaining
        def _noop(*args, **kwargs):
            return _NoopCtx()
        return _noop

    def __iter__(self):
        # Support: col1, col2 = st.columns(2)
        return iter([])

    def __bool__(self):
        return False


def _noop(*args, **kwargs):
    return _NoopCtx()


def _make_streamlit_stub():
    """Create a minimal Streamlit stub that makes module-level st.* calls no-ops."""
    st = types.ModuleType("streamlit")

    st.set_page_config = _noop
    st.markdown = _noop
    st.spinner = lambda *a, **kw: _NoopCtx()
    class _StopExecution(SystemExit):
        """Raised by st.stop() to halt module-level Streamlit execution in test context."""
        pass

    def _stop_stub():
        raise _StopExecution(0)

    st.stop = _stop_stub
    st.error = _noop
    st.warning = _noop
    st.info = _noop
    st.success = _noop
    st.rerun = _noop
    st.experimental_rerun = _noop

    # Columns returns a list of NoopCtx objects supporting attribute calls
    def _columns(n, **kw):
        count = n if isinstance(n, int) else len(n)
        return [_NoopCtx() for _ in range(count)]
    st.columns = _columns

    # Tabs likewise
    st.tabs = lambda labels: [_NoopCtx() for _ in labels]

    # Sidebar supports attribute access (with statement, etc.)
    st.sidebar = _NoopCtx()

    st.button = lambda *a, **kw: False
    # multiselect returns empty list so conditional filters (if pos_filter:) are skipped
    st.multiselect = lambda *a, **kw: []
    st.slider = lambda *a, **kw: kw.get("value", kw.get("min_value", 0))
    st.metric = _noop
    st.dataframe = _noop
    st.plotly_chart = _noop
    st.write = _noop

    # st.cache_data: wrap decorated functions to return a schema-correct empty DataFrame.
    # This prevents load_data() from calling run_fbref_scrapers() (network call).
    # The empty DataFrame has all required columns so downstream filters don't KeyError.
    _EMPTY_PIPELINE_DF = pd.DataFrame(columns=[
        "Player", "Squad", "Pos", "Age", "League",
        "market_value_eur", "scout_score", "uv_score", "uv_score_age_weighted",
        "value_gap_eur", "league_quality_multiplier", "predicted_log_mv",
        "similar_players", "_season", "Min",
        "score_attacking", "score_progression", "score_creation",
        "score_defense", "score_retention",
        "uv_score", "xG_p90", "Save%",
    ])

    class _CacheData:
        def __call__(self, func=None, ttl=None, show_spinner=True, **kwargs):
            def _make_stub(f):
                def _fast_stub(*a, **kw):
                    return _EMPTY_PIPELINE_DF.copy()
                _fast_stub.__name__ = getattr(f, "__name__", "cached_fn")
                _fast_stub.__doc__ = getattr(f, "__doc__", "")
                return _fast_stub
            if func is not None:
                return _make_stub(func)
            return _make_stub

        def clear(self):
            pass

    st.cache_data = _CacheData()

    # session_state stub
    st.session_state = {}

    return st


# Install the Streamlit stub before any test file imports app.py.
# Must be done at conftest load time so module-level Streamlit calls become no-ops.
sys.modules["streamlit"] = _make_streamlit_stub()
