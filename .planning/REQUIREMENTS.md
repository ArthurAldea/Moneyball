# Requirements — Moneyball v2

*Defined: 2026-03-16*

---

## v1 Requirements

### Data Pipeline

- [x] **DATA-01**: User can load player stats from FBref for all top 5 European leagues (EPL, La Liga, Bundesliga, Serie A, Ligue 1) for 2024-25 and 2025-26 seasons via `python scraper.py`
- [ ] **DATA-02**: System scrapes all required FBref stat tables per league: `stats_standard`, `stats_shooting`, `stats_passing`, `stats_defense`, `stats_possession`, `stats_misc`, `stats_keeper`, `stats_keeper_adv`
- [ ] **DATA-03**: System scrapes FBref league standings table per league for team strength adjustment
- [x] **DATA-04**: System scrapes Transfermarkt market values for all clubs across all 5 leagues
- [x] **DATA-05**: System caches all scraped data as CSV files with 7-day TTL using naming convention `cache/fbref_{league}_{table}_{season}.csv` and `cache/tm_values_{league}_{season}.csv`
- [ ] **DATA-06**: System applies polite scraping: randomized 3.5–6.0s delays between FBref requests, exponential backoff (30s → 60s → 120s) on 429 responses
- [ ] **DATA-07**: System filters out players with fewer than 900 minutes in a given season before aggregation

### Scoring Model

- [ ] **SCORE-01**: System computes position-specific pillar scores (GK / FW / MF / DF) using existing weight structure, normalized via MinMaxScaler fitted per league+position group independently
- [ ] **SCORE-02**: MF Progression pillar uses `0.6 × PrgP_p90 + 0.4 × SCA_p90` (replaces `xGChain_p90` from Understat)
- [ ] **SCORE-03**: FW and DF Progression pillar uses `PrgC_p90` (progressive carries per 90, replaces `xGBuildup_p90` from Understat)
- [x] **SCORE-04**: System applies team strength adjustment: ±10% multiplier on defensive per-90 stats (Tkl, Int, Blocks, DuelsWon, Pres, GK Save%/PSxG/SoT) for DF and GK only, based on league position — bottom-half clubs upward, top-half downward
- [x] **SCORE-05**: System applies a league quality multiplier to stats before cross-league comparison, based on UEFA club coefficient rankings (EPL highest weight, Ligue 1 lowest among top 5)
- [ ] **SCORE-06**: UV Score regression (`log10(market_value) ~ scout_score + position_dummies`) is fitted on the full unfiltered player pool — never on a filtered view
- [ ] **SCORE-07**: Age-weighted UV Score is computed: `uv_score_age_weighted = uv_score × (1 + 0.30 × age_weight)` where `age_weight` uses log-decay from age 17 to 29, capped at 1.5× for players under 21. Both `uv_score` and `uv_score_age_weighted` are stored as separate columns.
- [x] **SCORE-08**: System identifies top 5 similar players per player using cosine similarity on the 5 normalized pillar score columns, within the same position group, across all 5 leagues

### Dashboard — Filters

- [x] **FILTER-01**: User can filter by league (multi-select: EPL, La Liga, Bundesliga, Serie A, Ligue 1; default: All)
- [x] **FILTER-02**: User can filter by position (GK, DF, MF, FW; default: All)
- [x] **FILTER-03**: User can filter by age range via a slider (min/max; default: 17–38)
- [x] **FILTER-04**: User can filter by club via a multi-select dropdown (list updates based on selected leagues)
- [x] **FILTER-05**: User can filter by market value range (min/max in €M; default: no restriction)
- [x] **FILTER-06**: User can select seasons to include (2024-25, 2025-26, or both; default: both)

### Dashboard — Shortlist View

- [x] **DASH-01**: Landing page displays a ranked shortlist table sorted by `uv_score_age_weighted` (descending) by default
- [x] **DASH-02**: Shortlist table shows: Player, Club, League, Position, Age, Scout Score, UV Score, Age-Weighted UV Score, Market Value (€M), Value Gap (€M)
- [ ] **DASH-03**: User can click any column header to sort the shortlist by that column
- [x] **DASH-04**: User can click any row to open the player deep profile

### Dashboard — Design

- [x] **DASH-05**: Dashboard uses professional dark theme: navy/dark charcoal background (#0D1B2A range), single primary accent color (electric blue or amber), off-white primary text (#E8EDF2), all-caps labels for column headers and section titles
- [x] **DASH-06**: Dashboard includes a UV scatter plot: scout score (x-axis) vs. log10 market value (y-axis), all selected players plotted, regression line shown, each point colored by position group
- [x] **DASH-07**: When multiple leagues are selected in the scatter view, a visible disclaimer notes that cross-league comparison uses a league quality multiplier (not raw per-90 equivalence)

### Player Deep Profile

- [ ] **PROFILE-01**: Player profile displays a header block: full name, age, nationality, current club, league, primary position, market value
- [ ] **PROFILE-02**: Player profile displays a radar chart of the 5 pillar scores (Attack / Progression / Creation / Defense / Retention) vs. cross-league position-peer median, rendered as a filled polygon
- [ ] **PROFILE-03**: Player profile displays a full stat table grouped by pillar, showing: stat name | raw value | per-90 value | percentile rank vs. cross-league position peers (visualized as a colored bar: red→amber→green)
- [ ] **PROFILE-04**: Player profile shows the player's location on the UV scatter chart (highlighted with a distinct marker)
- [ ] **PROFILE-05**: Player profile displays a "Similar Players" panel showing top 5 players by cosine profile similarity: Player, Club, League, Age, Market Value, Age-Weighted UV Score

---

## v2 Requirements (Deferred)

- Advanced league quality adjustment with rolling club-coefficient update (v1 uses static UEFA coefficients)
- Season-over-season trend lines for key metrics (3-season view)
- Export player shortlist to CSV / PDF
- Club filter for "by target squad" scouting (show only players from one club)
- Player comparison side-by-side view
- Contract expiry data integration (when a free data source is identified)
- Team / positional depth chart view
- Rolling form scoring (last 10 games vs. season average)

---

## Out of Scope

- Video or event-level spatial data — no event coordinates in FBref aggregates
- Real-time / live match data — cache-based pipeline only
- User accounts, saved shortlists, or notes — single-user local tool
- Transfer fee negotiation or price recommendation — UV Score is a signal, not a valuation
- Leagues outside top 5 European — architecture supports extension, not in scope for v1
- Wage / contract data — not reliably available from free sources

---

## Traceability

| REQ-ID | Phase |
|--------|-------|
| DATA-01 | Phase 1 (EPL scraper), Phase 3 (multi-league expansion) |
| DATA-02 | Phase 1 |
| DATA-03 | Phase 2 |
| DATA-04 | Phase 3 |
| DATA-05 | Phase 1 (EPL cache), Phase 3 (league-keyed cache) |
| DATA-06 | Phase 1 |
| DATA-07 | Phase 1 |
| SCORE-01 | Phase 2 |
| SCORE-02 | Phase 2 |
| SCORE-03 | Phase 2 |
| SCORE-04 | Phase 4 |
| SCORE-05 | Phase 4 |
| SCORE-06 | Phase 2 |
| SCORE-07 | Phase 2 |
| SCORE-08 | Phase 4 |
| FILTER-01 | Phase 5 |
| FILTER-02 | Phase 5 |
| FILTER-03 | Phase 5 |
| FILTER-04 | Phase 5 |
| FILTER-05 | Phase 5 |
| FILTER-06 | Phase 5 |
| DASH-01 | Phase 5 |
| DASH-02 | Phase 5 |
| DASH-03 | Phase 5 |
| DASH-04 | Phase 5 |
| DASH-05 | Phase 5 |
| DASH-06 | Phase 5 |
| DASH-07 | Phase 5 |
| PROFILE-01 | Phase 6 |
| PROFILE-02 | Phase 6 |
| PROFILE-03 | Phase 6 |
| PROFILE-04 | Phase 6 |
| PROFILE-05 | Phase 6 |

---

*Last updated: 2026-03-16 after requirements definition*
