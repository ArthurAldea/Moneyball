# Research Summary

*Synthesized from STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md — 2026-03-16*

---

## Key Findings

### Stack

- **Add** `soccerdata` as the primary FBref abstraction layer — it handles HTML comment-wrapped tables, multi-level header flattening, and per-request pacing automatically across all five leagues.
- **Remove** `understat` and `aiohttp` — both are EPL-only and fully replaced by FBref via `soccerdata`.
- **Retain** `requests` + `lxml` + `beautifulsoup4` as the fallback for any table `soccerdata` does not expose; `curl_cffi` remains available if FBref adds Cloudflare protection.

### Architecture

- **Pipeline design:** Scrape and normalize per-league in isolation (MinMaxScaler fits within each league+position group), then concat all five scored DataFrames into a single master DataFrame before running the OLS UV regression. Pooling before normalization suppresses strong-within-league players.
- **Team strength formula:** Apply a ±10% multiplier to defensive per-90 stats only (not attacking stats) based on league position — bottom-half clubs get an upward adjustment, top-half get a downward adjustment. Source standings from `soccerdata.read_league_table()`. Location: `merger.py`, after `compute_per90s()`.
- **Age-weight formula:** Multiplicative post-UV log-decay (beta=0.30). Age 22 → ×1.16, Age 27 → ×1.05, Age 29+ → ×1.00. Both `uv_score` and `uv_score_age_weighted` are stored as separate columns; dashboard defaults to age-weighted sort.
- **Similar players method:** Cosine similarity on the 5 normalized `score_*` pillar columns, filtered to same position group, drawn from all five leagues. Cosine captures profile shape, not absolute volume — cross-club and cross-league scale differences don't distort matches.

### Table Stakes Features

- **Filters:** Position, league (multi-select), age range, minutes played threshold (≥900 min standard), market value range, club, and season selector.
- **Shortlist table:** Player, club, league, position, age, market value, composite score, and at least one headline stat — sortable by any column, row-click opens profile.
- **Player profile:** Header block (name, age, nationality, club, value, foot, height) + per-90 stats with percentile bars vs. position peers + season trend (3-season view) + radar chart vs. position-peer median.
- **Multi-league comparability:** All stats normalized to per-90; percentile ranks calculated cross-league for transfer relevance; radar comparisons use cross-league position pools.

### Our Differentiators

- **UV Score as a first-class metric:** No standard tool (Wyscout, Opta, StatsBomb) surfaces an undervaluation signal automatically. Our regression-residual UV Score converts the manual scout-vs-Transfermarkt cross-reference into a ranked signal, default-sorted on the shortlist.
- **Age-weighted UV Score:** No existing off-the-shelf platform weights performance by age to produce a prospect premium. A 22-year-old with identical output to a 29-year-old is explicitly scored higher — surfaced as a column, not just a filter.
- **Cross-league single regression line:** The scatter plot (scout score vs. log market value) places players from all five leagues against one shared value curve. Standard tools do not cross-league plot on a unified performance-vs-value plane.

### Watch Out For (Top 5 Critical Pitfalls)

1. **FBref rate limiting / Cloudflare blocks** — Randomize delays (`uniform(3.5, 6.0)s`), serialize all requests, add exponential backoff (30s → 60s → 120s) on 429.
2. **HTML comment-wrapped tables** — Always search `Comment` nodes; `soup.find("table", id=...)` returns `None` for most FBref stat tables.
3. **Multi-level column headers produce silent NaN columns** — Flatten with `df.columns = [col[1] if col[1] else col[0] for col in df.columns]` immediately after `pd.read_html()`.
4. **Multi-club aggregate rows double-count players in MinMaxScaler fitting** — Drop rows where `Squad` matches `r"\d+ Clubs?"` before scoring; retain per-club rows for team strength, aggregate row for scoring.
5. **MinMaxScaler / UV regression must be fit on the full unfiltered pool** — Fitting on a filtered view produces scores that shift as the user adjusts filters; apply UI filters for display only, never for model fitting.

---

## Build Sequence

1. **FBref scraper (EPL only)** — `scraper.py` rewrite: all required tables, HTML comment parsing, CSV cache with new naming convention (`fbref_{league}_{table}_{season}.csv`).
2. **Merger rewrite** — Multi-table join, FBref column mapping, `xGChain` → `sca_p90` / `PrgP_p90` substitution, team strength adjustment.
3. **Scorer update** — Confirm pillar models work with new column names; add age-weighted UV score.
4. **EPL end-to-end test** — Verify full pipeline produces sensible scores before expanding leagues.
5. **Multi-league expansion** — Extend scraper and TM scraper to four remaining leagues; add `League` column to all DataFrames; league-loop in scorer.
6. **Dashboard rebuild** — New filters, shortlist-first landing page, similar players panel, professional dark theme.

---

## Open Questions

1. **Minimum minutes threshold:** CLAUDE.md specifies 3,000 minutes across 3 seasons. FEATURES.md cites 900 minutes per season as industry standard. Which rule governs for the multi-league MVP — cumulative cross-season or per-season floor?

2. **Season scope:** CLAUDE.md mandates scraping 3 seasons (2022-23, 2023-24, 2024-25). ARCHITECTURE.md designs for a single active season per cache file. Is multi-season aggregation still in scope for v1, or is 2024-25 (current season) single-season the target?

3. **Team strength adjustment magnitude:** The formula uses a fixed ±10% range (beta hardcoded to produce 0.90–1.10 multiplier). PITFALLS.md recommends externalizing beta to `config.py` with a suggested range of 0.1–0.3. Confirm final beta value and whether it should be user-tunable in the UI.

4. **League quality adjustment:** Raw per-90 cross-league comparison is flagged as a known limitation (0.8 xG/90 in Ligue 1 ≠ 0.8 xG/90 in EPL). Deferred to post-MVP in PITFALLS.md — confirm this is acceptable for v1 and that the UI will carry a visible disclaimer.

5. **`xGChain` replacement:** The current pillar model uses `xGChain_p90` for MF Progression (30% weight). The proposed FBref replacement blends `sca_p90` + `progressive_passes_p90`. This is a model change, not a column rename — confirm the blending formula and weight split before implementation begins.
