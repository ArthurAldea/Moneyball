# CONCERNS.md — Known Issues and Technical Debt

## 1. API-Football Free Tier Exhaustion (GK Data Incomplete)

**Severity: High — affects model correctness for goalkeepers**

The API-Football free tier allows 100 requests per day. A full 3-season refresh requires:
- 3 `/teams` calls (1 per season) = 3 requests
- Up to 20 EPL teams × ~2 pages each × 3 seasons = ~120 requests

Total: ~123 requests — exceeding the 100/day limit. On a cold run (no cache), the scraper will be rate-limited mid-season. The most recently configured season (2025-26) is likely to hit this limit first, leaving its API-Football data absent or truncated.

This directly impacts GK scoring: `Saves` and `GoalsConceded` (required for `SavePct`, which has a weight of 50 in the GK model) come exclusively from API-Football. If the 2025-26 API-Football cache is missing, all GKs in that season will have `SavePct = NaN`, which is treated as 0 by `fillna(0)` in `_score_group`. This makes current-season GKs systematically under-scored and distorts UV rankings.

The current cache directory only contains `apifootball_202324.csv` — the 2024-25 and 2025-26 API-Football data has not been fetched. Any GK analysis is currently running on stale or absent defensive stats.

**No mitigation is currently in place.** The scraper does not detect partial completion, does not resume from a checkpoint, and does not warn when GK-critical columns are missing.

---

## 2. Transfermarkt Scraper Fragility

**Severity: Medium — silent data loss on HTML structure change**

The Transfermarkt scraper (`scraper.py`) relies on specific CSS selectors:
- `table.items td.hauptlink a[href*="/verein/"]` — for the club list
- `table.items tr.odd` / `tr.even` — for squad rows
- `td.hauptlink a` with non-digit text — for player name
- Last `td` cell — for market value

Transfermarkt is a commercial site with no public API. Its HTML structure changes without notice. When it does:
- The club list scrape may return an empty list, causing `run_tm_scrapers()` to return an empty DataFrame
- The player name extraction may silently return `None` for all rows (skipped via `if not player_name: continue`)
- The market value cell (`cells[-1]`) may contain non-value text, causing `_parse_tm_value` to return `NaN`

In all cases the scraper **does not raise an exception** — it prints a warning (or nothing) and returns partial/empty data. The cache will be written with the partial data, so the 7-day TTL will prevent re-scraping for a week even if the result is empty.

The `curl_cffi` Chrome impersonation reduces the risk of bot detection blocks, but Transfermarkt actively varies its HTML. The scraper should be treated as fragile by design.

---

## 3. No Test Coverage

**Severity: Medium — silent regressions possible**

There are zero passing tests. `test_scraper.py` is broken (imports `scrape_fbref_stat` which no longer exists). There is no pytest configuration, no CI, and no test fixtures.

The entire pipeline — from position mapping to MinMaxScaler normalization to regression UV scoring — runs untested. Specific risks:
- A change to a pillar stat name in `config.py` that doesn't match a column name in the merged DataFrame will silently score that stat as 0 (the `[scorer] Missing columns (scored 0)` print is easy to miss in Streamlit's output)
- A change to Understat's response field names would produce a DataFrame full of `NaN` with no exception raised
- A regression in `compute_per90s` (e.g., wrong column name) would produce silent NaN propagation through the entire scoring pipeline

---

## 4. CLAUDE.md Is Outdated

**Severity: Low — misleading to future developers**

`/Users/ArthurAldea/ClaudeProjects/Moneyball/CLAUDE.md` describes a version of the project that no longer exists:

| CLAUDE.md claim | Reality |
|---|---|
| "Data: FBref (scraped via requests + BeautifulSoup)" | FBref is gone; data comes from Understat + API-Football + Transfermarkt |
| "Always scrape 3 seasons: 2022-23, 2023-24, 2024-25" | Current seasons are 2023-24, 2024-25, 2025-26 |
| "Undervaluation = scout_score / log10(market_value_eur)" | Formula replaced with OLS regression residuals |
| "FBref tables are wrapped in HTML comments — always search Comment nodes" | FBref is not used; this instruction is irrelevant |
| "Scout score is pillar-based (Attacking 30pts, Progression 25pts, ...)" | Weights are now position-specific (FW: 45/20/20/5/10, MF: 20/30/25/15/10, etc.) |

The `CLAUDE.md` file will mislead any developer or AI assistant that reads it as authoritative. It should be rewritten to reflect the current Understat + API-Football + Transfermarkt architecture.

---

## 5. MinMaxScaler Normalizes Within Position Group — Small Groups Skew Results

**Severity: Medium — affects ranking reliability**

`_score_group` fits a `MinMaxScaler` on the players in a single position group. The minimum stat value in the group is scaled to 0 and the maximum to 1. This means:

- In a small position group (e.g., if only 3 GKs pass the minutes filter), the spread between scores is artificially inflated — the worst of 3 GKs gets a 0 and the best gets a 1, regardless of how good or bad they are in absolute terms
- A GK with objectively mediocre stats could score 80+ if they are the best in a small cohort
- Adding one more outstanding GK to the group would compress all existing GK scores downward
- Scores are not comparable across seasons or across different filter configurations — changing the season filter changes which players are in the group, which changes the scaler boundaries, which changes all scores

This is a fundamental property of MinMax normalization within groups and cannot be patched without changing the normalization strategy.

---

## 6. Fuzzy Name Matching False Positives

**Severity: Medium — attaches wrong stats to a player**

Both `merge_stat_sources` and `match_market_values` use `rapidfuzz.fuzz.WRatio` with a threshold of 80. WRatio considers substring matches and token ordering. At threshold 80, the following types of false positives are plausible:

- Short names: `"Son"` fuzzy-matching `"Sone Aluko"` or similar
- Common surnames: two players with the same surname but different first names (e.g., `"J. Rodriguez"` and `"J. Rodriguez"` from different clubs)
- Transfermarkt name format differences: Transfermarkt often uses localized or shortened names (`"Diogo Jota"` vs `"Diogo Teixeira"`)
- API-Football name abbreviations: API-Football sometimes returns `"B. Fernandes"` while Understat returns `"Bruno Fernandes"`

When a false positive occurs, the stats of the wrong player are silently attached. There is no cross-validation against club name or position. The pipeline has no mechanism to detect or report mismatches.

---

## 7. No Error Recovery in Pipeline — One Bad Scrape = Blank Dashboard

**Severity: High — user-facing failure**

The pipeline is linear with no checkpointing or partial-result handling beyond what each scraper returns. Failure modes:

**Understat fails entirely:** `aggregate_understat` gets an empty dict, `build_dataset` returns an empty DataFrame, `compute_scout_scores` gets an empty DataFrame, `compute_efficiency` gets an empty DataFrame. The app hits `if df.empty: st.warning(...)` and stops rendering.

**Transfermarkt fails:** All players get `market_value_eur = NaN`. `compute_efficiency` requires `market_value_eur > 0` and drops all rows. The final DataFrame is empty. The dashboard stops rendering.

**API-Football fails:** Merger returns Understat-only data. All Defense and Retention pillar scores are 0 (they depend on `Tkl_p90`, `Int_p90`, etc.). GK `SavePct` is NaN → GK `score_attacking` = 0. UV scores are computed but are meaningless for defensive players and GKs.

In all failure cases, the error is either swallowed with a `[warn]` print (invisible in the dashboard) or surfaced as a bare `st.error(f"// PIPELINE ERROR: {e}")` which shows a Python exception message to the user. There is no retry logic, no fallback to last-known-good cache, and no per-source status indicator in the UI (despite the sidebar text listing data sources).
