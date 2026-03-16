# Moneyball — Multi-League Professional Scout Dashboard

## What This Is

A football player analysis tool for professional scouts that identifies undervalued players across the top 5 European leagues by comparing position-adjusted performance scores against market valuations. The tool accounts for team strength context (a defender at a relegated side faces a harder job than one at Man City) and adjusts the undervaluation score for player age, so a 20-year-old performing at the same level as a 30-year-old registers as more undervalued. Results are presented in a shortlist-focused Streamlit dashboard with drill-down player profiles.

## Core Value

Surface the players whose performance output most exceeds what the market currently prices them at — in the right positional and team context.

## Requirements

### Validated

<!-- Existing working features inferred from codebase -->

- ✓ EPL player data pipeline (Understat xG/xA + API-Football defensive stats + Transfermarkt market values) — existing (being replaced by FBref in Phase 1)
- ✓ Position-specific pillar scoring: FW (Attack 45 / Prog 20 / Creation 20 / Def 5 / Retention 10), MF (20/30/25/15/10), DF (10/15/10/45/20), GK Shot-Stopping 50 / Distribution 20 / Aerial 15 / Sweeping 10 / Composure 5 — existing
- ✓ UV Score via regression residuals: fit log10(market_value) ~ scout_score + position_dummies — existing
- ✓ MinMaxScaler normalization per position group (GK, FW, MF, DF scored independently) — existing
- ✓ Season filter with dynamic min-minutes scaling (MIN_MINUTES_PER_SEASON × n_seasons) — existing
- ✓ Current-season filter (only retains players active in most recent season) — existing
- ✓ 7-day CSV cache layer — existing
- ✓ Radar chart, scatter plot, full player scan tab — existing
- ✓ Dark theme Streamlit dashboard — existing
- ✓ rapidfuzz WRatio fuzzy name matching across data sources — existing
- ✓ FBref EPL scraper — 9 stat tables (stats_standard, shooting, passing, defense, possession, misc, keeper, keeper_adv, gca), 2 seasons (2023-24 / 2024-25), 7-day cache, 429 backoff, 900-min filter, comment-node HTML extraction — Phase 1
- ✓ DATA-05: League-keyed cache naming `cache/fbref_{league}_{table}_{season}.csv` — Phase 1
- ✓ DATA-06: Rate-limited fetch (3.5–6.0s delay) + exponential backoff 30s→60s→120s on 429 — Phase 1
- ✓ DATA-07: 900-minute-per-season minimum filter applied at scrape time — Phase 1

### Active

<!-- New scope for this project -->

**Data Layer**
- ✓ Migrate EPL data source from Understat + API-Football to FBref (consistent across all leagues) — Phase 1 (scraper complete; merger/scorer rewrite in Phase 2)
- [ ] Add FBref scrapers for La Liga, Bundesliga, Serie A, Ligue 1
- [ ] Keep Transfermarkt market value scraper (extend to top 5 league clubs)
- [ ] Maintain 7-day CSV cache — extend cache key to include league

**Scoring Model**
- [ ] Team strength adjustment: normalize per-90 stats against league position context (bottom-half clubs face higher workloads in defensive positions)
- [ ] Age-weighted UV score: apply age multiplier to undervaluation — younger players performing at the same level score higher UV
- [ ] Preserve position-specific pillar model structure (GK/FW/MF/DF)

**Dashboard — Design**
- [ ] Redesign to professional dark theme (Opta / Wyscout aesthetic) — navy/dark grey base, clean data typography, professional accent colors
- [ ] Replace cybersecurity green-on-black terminal aesthetic

**Dashboard — Filters**
- [ ] League filter (EPL, La Liga, Bundesliga, Serie A, Ligue 1, All)
- [ ] Position filter (All, GK, DF, MF, FW)
- [ ] Age filter with range slider (min/max age)
- [ ] Team filter (multi-select dropdown)
- [ ] Market value filter (min/max range)
- [ ] Season filter (existing, preserve)

**Dashboard — Shortlist View (landing page)**
- [ ] Ranked shortlist table as primary view: Player, Club, League, Position, Age, Scout Score, UV Score, Market Value, Value Gap
- [ ] Sortable columns
- [ ] Clicking a row opens player deep profile

**Dashboard — Player Deep Profile**
- [ ] Radar chart: pillar breakdown vs position-peer median
- [ ] Full stat table with per-90 values and percentile ranks vs position peers
- [ ] Position on value-vs-performance scatter chart
- [ ] Similar players panel: top 5 comparable players by scout profile

### Out of Scope

- Real-time or live data — cache-based pipeline only; data refreshes on-demand
- Video or tactical analysis integration — stats only
- Player contract data (wages, expiry) — not in scope for v1
- Transfer fee prediction or negotiation tools — UV score is the output, not a price recommendation
- Leagues outside top 5 — architecture supports extension, not in scope now
- User accounts or saved shortlists — single-user local tool for now

## Context

- Existing codebase in `/Users/ArthurAldea/ClaudeProjects/Moneyball` has a working EPL pipeline with Understat + API-Football + Transfermarkt. The core scoring logic (position-specific pillars, regression residual UV) is solid and should be preserved.
- API-Football free tier (100 req/day) is a known blocker — migration to FBref eliminates this constraint entirely.
- FBref has xG, xA, progressive passes/carries, defensive stats, and aerial stats for all top 5 leagues — sufficient to populate all pillar models for all positions.
- The GK scoring is currently impacted by incomplete API-Football data (daily limit hit mid-scrape). FBref migration will fix this by providing complete defensive stats without rate limits.
- CLAUDE.md updated in Phase 1 to reflect FBref architecture, cache naming, rate limits, and backoff sequence.
- Phase 2 blocker: `merger.py` still uses old Understat/API-Football column names (`xGChain`, `GoalsConceded`, etc.) — must be remapped to FBref columns (`PrgP`, `GA`, `Save%`, etc.) before scoring can run. `app.py` currently shows 0 players as a result (expected).
- Target user: a professional scout or analyst at a top-5 EPL club who wants to identify transfer targets efficiently.

## Constraints

- **Tech Stack**: Python + Streamlit + Plotly — existing stack, no framework changes
- **Data**: FBref scraping (HTML, no official API) — fragile to site structure changes; mitigated by 7-day cache reducing scrape frequency
- **Rate Limiting**: Transfermarkt requires curl_cffi Chrome impersonation + polite delays — existing approach retained
- **No Backend**: Local tool only — no database, no server, all data in CSV cache files
- **Budget**: Free data sources only (FBref + Transfermarkt scraping)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Migrate from Understat + API-Football to FBref | Single consistent source for all 5 leagues; eliminates 100 req/day API limit blocking GK data | ✓ Phase 1 scraper complete; Phase 2 wires merger/scorer |
| stats_gca added as 9th FBref table | SCA (shot-creating actions) needed by SCORE-02 MF Progression — captured now to avoid Phase 2 re-scrape | ✓ Phase 1 |
| pd.read_html(header=1) for FBref table parsing | Cleaner than manual MultiIndex flattening; handles FBref's group-label row without fragile index manipulation | ✓ Phase 1 |
| xAG→xA rename at scrape time | Phase 2 merger agnostic of FBref's 2022-23 column rename; consistent column name regardless of season | ✓ Phase 1 |
| League position for team strength adjustment | Simple, available, intuitive — no extra data source required | — Pending (Phase 4) |
| Age-weighted UV score | Primary use case is prospect scouting; younger high-performers are structurally undervalued by market | — Pending (Phase 2) |
| Enhance existing codebase (not full rebuild) | Core scoring logic (pillars, regression residual UV) is sound; rewriting risks regressions | — Pending |
| Shortlist-focused dashboard layout | Scout workflow is shortlist → drill-down, not comparison-first | — Pending (Phase 5) |

---
*Last updated: 2026-03-16 after Phase 1*
