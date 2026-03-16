"""
test_scraper.py — Smoke tests for scraper.py cache helpers and function stubs.
These tests verify imports succeed and helper functions return expected values
without making any network requests.
"""
import pytest
from scraper import scrape_tm_season, scrape_fbref_stat, run_tm_scrapers, run_fbref_scrapers
from scraper import _cache_path, _is_fresh, _fbref_cache_path


def test_cache_path_returns_csv():
    path = _cache_path("test_key")
    assert path.endswith("test_key.csv")


def test_fbref_cache_path_epl_standard():
    path = _fbref_cache_path("EPL", "stats_standard", "2024-25")
    assert path.endswith("cache/fbref_EPL_stats_standard_2024-25.csv")


def test_fbref_cache_path_epl_keeper_adv():
    path = _fbref_cache_path("EPL", "stats_keeper_adv", "2023-24")
    assert path.endswith("cache/fbref_EPL_stats_keeper_adv_2023-24.csv")


def test_scrape_fbref_stat_stub_returns_dataframe():
    import pandas as pd
    result = scrape_fbref_stat("stats_standard", "2024-25")
    assert isinstance(result, pd.DataFrame)


def test_run_fbref_scrapers_stub_returns_dict():
    result = run_fbref_scrapers()
    assert isinstance(result, dict)
