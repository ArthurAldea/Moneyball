# Roadmap — Moneyball v2

## Phases

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| 1 | FBref Scraper (EPL) | Replace Understat + API-Football with a complete FBref scraper covering all required stat tables for EPL only | DATA-01 (EPL), DATA-02, DATA-05, DATA-06, DATA-07 | ✅ Complete |
| 2 | Merger & Scorer Rewrite (EPL End-to-End) | Rebuild merger and scorer to ingest FBref columns, confirm all pillar models produce sensible scores for EPL, and add age-weighted UV | DATA-03, SCORE-01, SCORE-02, SCORE-03, SCORE-06, SCORE-07 | ✅ Complete |
| 3 | Multi-League Expansion | Complete    | 2026-03-17 | ✅ Complete |
| 4 | Advanced Scoring | Apply team strength adjustment and league quality multiplier across the full five-league pool; add cosine similar-player computation | SCORE-04, SCORE-05, SCORE-08 | Not Started |
| 5 | Dashboard Rebuild — Shortlist & Filters | Replace current tab layout with shortlist-first landing page, all six filters, professional dark theme, and UV scatter plot | FILTER-01, FILTER-02, FILTER-03, FILTER-04, FILTER-05, FILTER-06, DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07 | Not Started |
| 6 | Player Deep Profile | Add drill-down player profile with radar chart, full per-90 stat table with percentile bars, scatter highlight, and similar players panel | PROFILE-01, PROFILE-02, PROFILE-03, PROFILE-04, PROFILE-05 | Not Started |

---

## Phase Details

### Phase 1: FBref Scraper (EPL)

**Status:** ✅ Complete

| Plan | Title | Status |
|------|-------|--------|
| 01-01 | Config & Cache Infrastructure | ✅ Done |
| 01-02 | FBref Fetch Functions | ✅ Done |
| 01-03 | Multi-Table Orchestrator & Integration | ✅ Done |

**Goal:** Rewrite `scraper.py` to pull all eight required FBref stat tables for EPL from both seasons, write league-keyed CSV cache files, and retire the Understat and API-Football scrapers entirely.

**Requirements:** DATA-01 (EPL), DATA-02, DATA-05, DATA-06, DATA-07

**Success Criteria:**
1. Running `python scraper.py` with EPL selected populates `cache/fbref_EPL_stats_standard_2024-25.csv` (and equivalents for all eight tables and both seasons) without hitting the network on a second run within 7 days.
2. Every required stat column from all eight tables (`stats_standard`, `stats_shooting`, `stats_passing`, `stats_defense`, `stats_possession`, `stats_misc`, `stats_keeper`, `stats_keeper_adv`) is present and non-empty in the cached output.
3. Players with fewer than 900 minutes in a given season are absent from the cached DataFrame.
4. Running the scraper a second time within 7 days produces no network requests and returns in under two seconds.
5. A 429 response triggers exponential backoff (30s → 60s → 120s) rather than a crash.

---

### Phase 2: Merger & Scorer Rewrite (EPL End-to-End)

**Status:** ✅ Complete

| Plan | Title | Status |
|------|-------|--------|
| 02-01 | Config & Test Infrastructure | ✅ Done |
| 02-02 | Merger Rewrite | ✅ Done |
| 02-03 | Scorer Rewrite + Age-Weight | ✅ Done |
| 02-04 | app.py Rewire & Integration | ✅ Done |

**Goal:** Rebuild `merger.py` and `scorer.py` to join the eight FBref tables into one DataFrame, substitute FBref column names for the old Understat/API-Football equivalents in all pillar models, scrape EPL league standings for team-strength input, and produce `uv_score` and `uv_score_age_weighted` columns — with the full EPL pipeline verified end-to-end before multi-league work begins.

**Requirements:** DATA-03, SCORE-01, SCORE-02, SCORE-03, SCORE-06, SCORE-07

**Success Criteria:**
1. Running `python scorer.py` (or equivalent) on EPL cache data produces a DataFrame with `scout_score`, `uv_score`, and `uv_score_age_weighted` columns for all qualifying EPL players.
2. GK players have non-zero `score_attacking` (Shot Stopping) values — confirming the FBref migration fixes the API-Football daily-limit gap that previously zeroed GK data.
3. MF Progression pillar draws from `PrgP_p90` and `SCA_p90` (not `xGChain_p90`); FW and DF Progression pillars draw from `PrgC_p90` — verifiable by inspecting the scorer config.
4. `uv_score_age_weighted` is strictly greater than `uv_score` for players aged 21 and under, and equals `uv_score` for players aged 29 and over.
5. The UV regression is fit on the full unfiltered player pool — confirmed by verifying `uv_score` values do not change when a position filter is applied before scoring.

---

### Phase 3: Multi-League Expansion

**Status:** ✅ Complete

| Plan | Title | Status |
|------|-------|--------|
| 03-01 | Multi-League Scraper Foundation | ✅ Done |
| 03-02 | Multi-League Merger | ✅ Done |
| 03-03 | Multi-League Scorer & Pipeline | ✅ Done |

**Goal:** Extend the scraper to all five leagues and the Transfermarkt scraper to all five league club lists; add a `League` column to every DataFrame; loop the full pipeline over all five leagues so the master output contains players from EPL, La Liga, Bundesliga, Serie A, and Ligue 1.

**Requirements:** DATA-01 (all leagues), DATA-04, DATA-05 (league-keyed cache)

**Success Criteria:**
1. Running `python scraper.py` populates cache files for all five leagues (40 FBref table files per season + five Transfermarkt files per season).
2. The scored master DataFrame contains players from all five leagues, with a non-null `League` column on every row.
3. Cache files follow the naming convention `cache/fbref_{league}_{table}_{season}.csv` and `cache/tm_values_{league}_{season}.csv`; re-running within 7 days serves all five leagues from cache with no network requests.
4. MinMaxScaler normalization is fitted independently per league+position group — confirmed by verifying that the top-scored forward in La Liga and the top-scored forward in the EPL both receive `scout_score` values near 100.

---

### Phase 4: Advanced Scoring

**Goal:** Apply the ±10% team strength adjustment to defensive per-90 stats based on league position, apply the UEFA-coefficient league quality multiplier before cross-league comparison, and compute cosine-similarity similar players (top 5 per player) across the full five-league pool.

**Requirements:** SCORE-04, SCORE-05, SCORE-08

**Plans:** 3 plans

Plans:
- [ ] 04-01-PLAN.md — Config + Merger fixes + team strength adjustment (SCORE-04)
- [ ] 04-02-PLAN.md — League quality multiplier (SCORE-05)
- [ ] 04-03-PLAN.md — Similar players via cosine similarity (SCORE-08)

**Success Criteria:**
1. A defender from a bottom-half club receives a higher adjusted defensive pillar score than the identical raw stats would yield for a defender at a top-half club — difference traceable to the team strength multiplier column.
2. The five similar players returned for any given player are all from the same position group, drawn from across multiple leagues where applicable, and ranked by cosine similarity on the five `score_*` pillar columns.
3. Attacking per-90 stats are unaffected by the team strength adjustment — confirmed by checking that `score_attacking` values for forwards are identical before and after the adjustment step.
4. Each player row carries a `league_quality_multiplier` value consistent with the UEFA club coefficient ranking (EPL highest, Ligue 1 lowest among the five).

---

### Phase 5: Dashboard Rebuild — Shortlist & Filters

**Goal:** Replace the current four-tab dashboard with a shortlist-first landing page sorted by `uv_score_age_weighted`, six sidebar filters (league, position, age, club, market value, season), professional navy/charcoal dark theme, and a UV scatter plot with cross-league disclaimer.

**Requirements:** FILTER-01, FILTER-02, FILTER-03, FILTER-04, FILTER-05, FILTER-06, DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07

**Success Criteria:**
1. The landing page displays a ranked shortlist table with all required columns (Player, Club, League, Position, Age, Scout Score, UV Score, Age-Weighted UV Score, Market Value, Value Gap) sorted by Age-Weighted UV Score descending by default.
2. Selecting "La Liga" in the league filter removes all non-La Liga players from the shortlist within one Streamlit re-run.
3. The club dropdown options update dynamically to reflect only the clubs present in the currently selected leagues.
4. The scatter plot renders all selected players with the OLS regression line; each point is colored by position group; when more than one league is selected a visible disclaimer about the league quality multiplier appears on the chart.
5. The dashboard background, typography, and accent colors match the specified professional dark theme (navy/dark charcoal, electric blue or amber accents, off-white text, all-caps column headers) — visually distinct from the current green-on-black terminal aesthetic.

---

### Phase 6: Player Deep Profile

**Goal:** Implement the drill-down player profile view triggered by clicking a shortlist row, displaying the full header block, radar chart vs. position-peer median, per-90 stat table with percentile bars, scatter chart highlight, and similar players panel.

**Requirements:** PROFILE-01, PROFILE-02, PROFILE-03, PROFILE-04, PROFILE-05

**Success Criteria:**
1. Clicking any row in the shortlist opens the player profile view showing the header block with all required fields (name, age, nationality, club, league, position, market value).
2. The radar chart renders all five pillar scores as a filled polygon overlaid on the cross-league position-peer median polygon — both are visually distinct.
3. The per-90 stat table groups stats by pillar and displays a colored percentile bar (red → amber → green) for each stat relative to cross-league position peers.
4. The player's data point on the UV scatter chart is highlighted with a distinct marker; the rest of the selected player pool is visible as context.
5. The Similar Players panel lists exactly five players with Player, Club, League, Age, Market Value, and Age-Weighted UV Score — each drawn from the cosine similarity computation in Phase 4.
