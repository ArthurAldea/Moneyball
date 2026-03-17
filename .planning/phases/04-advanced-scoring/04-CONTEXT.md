# Phase 4: Advanced Scoring - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Apply two context adjustments to the scoring model (team strength, league quality) and compute cosine-similarity similar-player vectors. No scraper URL changes, no dashboard work. All changes live in scorer.py, config.py, and merger.py (pressures column retention).

</domain>

<decisions>
## Implementation Decisions

### Team Strength Adjustment (SCORE-04)
- Magnitude: **±10%** (not ±20% — REQUIREMENTS.md SCORE-04 has a typo; ROADMAP success criteria are authoritative)
- Applies to: **DF and GK only** — positions most affected by team quality context
- Stats adjusted: `Tkl_p90`, `Int_p90`, `Blocks_p90`, `DuelsWon_p90`, pressures, and GK `Save%`/`PSxG/SoT`
- Direction: bottom-half club (league_position > half of clubs) → +10% on defensive stats; top-half → −10%
- Attacking per-90 stats are **never adjusted** — FW/MF attacking pillars untouched
- `league_position` column is already attached in merger.py (Phase 2) — data is available
- Pressures: **include** — the `Pres` column exists in the stats_defense table that is already fetched but currently dropped in merger. Retain it and add to config SUM_STATS

### League Quality Multiplier (SCORE-05)
- Function: **applied to `uv_score_age_weighted`** after UV regression — multiply the final age-weighted UV score by the league coefficient
- This means a Ligue 1 player with the same raw performance as an EPL player will end up with a lower final UV score, reflecting the lower competitive baseline
- Coefficients (stored as `league_quality_multiplier` column on every player row):
  - EPL: 1.10
  - LaLiga: 1.08
  - Bundesliga: 1.05
  - SerieA: 1.03
  - Ligue1: 1.00
- The `uv_score_age_weighted` column is updated in-place (multiplied by the coefficient) — Phase 5/6 consumers see the adjusted value automatically
- `league_quality_multiplier` column also stored separately for dashboard display (Phase 5 disclaimer)

### Similar Players (SCORE-08)
- Basis: **style-based matching** — cosine similarity on the 5 per-league-normalized `score_*` pillar columns (`score_attacking`, `score_progression`, `score_creation`, `score_defense`, `score_retention`)
- Scope: within the same position group (GK/FW/MF/DF), across all 5 leagues
- Output: top 5 per player, stored as **`similar_players` JSON column** in the main scored DataFrame — list of dicts: `[{player, club, league, uv_score_age_weighted}, ...]`
- A player is excluded from their own similar-players list

### Claude's Discretion
- Exact formula for bottom-half vs. top-half threshold (e.g., whether to use the midpoint of total clubs in the league or a fixed cutoff)
- How to handle NaN league_position (already soft-fails to NaN in merger — skip adjustment for those players)
- How to handle ties in cosine similarity

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements for this phase
- `.planning/REQUIREMENTS.md` §SCORE-04 — team strength adjustment (note: magnitude says ±20% but decision is ±10%; correct the doc)
- `.planning/REQUIREMENTS.md` §SCORE-05 — league quality multiplier spec
- `.planning/REQUIREMENTS.md` §SCORE-08 — similar players spec

### Existing scoring model
- `scorer.py` — `compute_scout_scores()`, `compute_efficiency()`, `compute_age_weighted_uv()`, `run_scoring_pipeline()` — all functions that Phase 4 modifies or extends
- `config.py` — `PILLARS_FW`, `PILLARS_MF`, `PILLARS_DF`, `GK_PILLARS`, `SUM_STATS` — pillar definitions and stat lists that need pressures added

### Existing merger integration point
- `merger.py` — `attach_league_position()` (line ~281) — already adds `league_position` column; Phase 4 adjustment reads this
- `merger.py` — `_join_table("stats_defense", drop_cols=...)` (line ~140) — currently drops pressures columns; Phase 4 needs to retain `Pres`

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scorer.py:compute_scout_scores()` — outer league+position loop is the natural insertion point for team strength adjustment; apply multiplier to defensive stats *before* `_score_group()` is called
- `scorer.py:compute_age_weighted_uv()` — league quality multiplier should be applied as a final step after this function, analogous to how age weighting wraps UV score
- `config.py:SUM_STATS` — list to extend with `Pres` (pressures raw count from stats_defense)

### Established Patterns
- Per-league MinMaxScaler normalization (Phase 3): normalization is fitted after all adjustments are applied to stats — team strength adjustment must happen before `_score_group()` call, not after
- `league_position` is already a column on the merged DataFrame; no additional scraping needed for team strength
- Soft-fail pattern: Phase 2 set `league_position` to NaN when standings unavailable — Phase 4 should skip adjustment for NaN rows (consistent with existing pattern)
- JSON column pattern: not established yet — this is new for similar_players

### Integration Points
- `run_scoring_pipeline()` in scorer.py is the top-level function — new steps (team adjustment, league multiplier, similar players) should be added here in pipeline order
- `merger.py` drop_cols list for stats_defense needs `Pres` removed from the drop list (or explicitly retained)

</code_context>

<specifics>
## Specific Ideas

- REQUIREMENTS.md SCORE-04 should be corrected from ±20% to ±10% as part of this phase
- League quality multiplier adjusts `uv_score_age_weighted` in-place so Phase 5/6 always see the adjusted final value — no separate "adjusted" column needed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-advanced-scoring*
*Context gathered: 2026-03-17*
