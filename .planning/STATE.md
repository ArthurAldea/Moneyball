---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 06.1
status: completed
stopped_at: Completed 06.1-03-PLAN.md
last_updated: "2026-03-18T09:50:32.956Z"
progress:
  total_phases: 8
  completed_phases: 8
  total_plans: 23
  completed_plans: 23
---

# Project State

**Current Phase:** 06.1
**Status:** Milestone complete
**Last Updated:** 2026-03-18

## Project Reference
See: .planning/PROJECT.md
**Core value:** Surface players whose performance most exceeds their market price — in the right positional and team context.
**Current focus:** Phase 6 — Player Deep Profile

## Phase Progress

| # | Phase | Status |
|---|-------|--------|
| 1 | FBref Scraper (EPL) | ✅ Complete |
| 2 | Merger & Scorer Rewrite (EPL End-to-End) | ✅ Complete |
| 3 | Multi-League Expansion | ✅ Complete |
| 4 | Advanced Scoring | ✅ Complete |
| 5 | Dashboard Rebuild — Shortlist & Filters | ✅ Complete |
| 5.1 | Fix FBref Scraping — Playwright Cloudflare bypass | ✅ Complete |
| 6 | Player Deep Profile | ✅ Complete |
| 6.1 | Understat Integration | ✅ Complete |

## Current Position

**Next:** Phase 06.1 complete. All 3 plans executed. xG/xA Understat integration fully live.

## Accumulated Decisions

- **[06-01] compute_percentile uses rank(method='min'):** Avoids boundary inflation when test value equals series minimum; correct boundary: val=min of series → percentile ≤ 1/n*100.
- **[06-01] build_radar_figure strips margin from NAVY_LAYOUT:** NAVY_LAYOUT.margin conflicts with explicit radar margin override; fix strips key before spreading dict.
- **[FBref Lit 2025] Pillar model rebuilt from scratch:** xG, xA, PrgC, PrgP, KP, SCA, Blocks, Pres, aerial duels, pass completion all gone from FBref public pages. Pillars now use: Gls_p90, Ast_p90, SoT_p90, Sh_p90, Int_p90, TklW_p90, Fld_p90, Crs_p90, Save%, Saves_p90.
- **[FBref Lit 2025] Standings via football-data.co.uk:** Plain HTTP CSV downloads, no Cloudflare — all 5 leagues × 2 seasons pre-cached.
- **[06-02] scatter_chart switched to linear y-axis (€M):** Regression stays in log10(€M) space but back-converted to €M for plotting. Sidebar x/y range sliders drive axis ranges. Eliminates log-scale tick cramping.
- **[FBref Lit 2025] Scatter chart (historical):** Originally used raw market_value_eur + Plotly log axis. Superseded by 06-02 linear scale fix.
- **[04-03] compute_similar_players scoped per position group across all leagues**
- **[04-03] similar_players wired as final pipeline step**
- **[03-03] compute_scout_scores outer per-league loop:** MinMaxScaler fitted per league+position group independently
- **[03-02] Pass 3 requires club cross-check**
- **[02-01] MEAN_STATS=[] in aggregation:** All rate stats re-derived from summed raw counts
- [Phase 06-03]: render_comparison_profile() uses first player's Pos as peer median reference group for radar; stat table pillars follow first player position config but percentile computed per-player against own position peer pool
- [Phase 06-03]: scatter_chart x_range param removed — Plotly native rangeslider handles x-axis zoom embedded below chart
- [Phase 06-03]: Y-axis range split into two sliders (mv_plot_max, mv_plot_min) in 4% column beside scatter chart; sidebar axis sliders removed
- **[06.1-01] scrape_understat_league cache key**: `understat_{league}_{season_label}` (e.g. understat_EPL_2024-25.csv) — distinct from legacy EPL-only `understat_{season_label.replace('-','')}` format; both coexist
- **[06.1-01] run_understat_scrapers return structure**: `{league: {season_label: DataFrame}}` — matches attach_understat_xg signature in Plan 02
- **[06.1-02] attach_understat_xg Pass 2 adds token_sort_ratio >= 60 gate**: WRatio alone scores "Unknown Player" vs "Known Player" at 92 due to shared suffix — token_sort_ratio=46 for that pair correctly rejects it while real abbreviation mismatches pass.
- **[06.1-02] League column set before attach_understat_xg in build_dataset loop**: function requires League column to scope understat lookup to correct league data.
- **[06.1-02] run_understat_scrapers called inside run_scoring_pipeline**: keeps public API unchanged while adding understat data to the pipeline.
- [Phase 06.1]: FW/MF creation pillars use explicit inline dicts (not _CREATION spread) to allow xA_p90 stats while DF creation stays unchanged on Ast_p90+Crs_p90

## Session Continuity
Last session: 2026-03-18T09:11:20.952Z
Stopped at: Completed 06.1-03-PLAN.md
Resume file: None

## Roadmap Evolution

- Phase 06.1 inserted after Phase 6: Understat integration — resurrect xG/xA scraper, merge into FBref pipeline, update Attacking and Creation pillar weights in scorer (URGENT)

## Blockers/Concerns
- Some Transfermarkt market values appear stale/incorrect (e.g. Álex Grimaldo at €100K) — TM scraping issue, not scoring
