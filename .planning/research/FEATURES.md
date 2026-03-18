# Features Research

*Research basis: training knowledge of Wyscout, StatsBomb IQ, InStat Scout, Transfermarkt Scout, Opta Perform, and related tools as of August 2025.*

---

## Table Stakes (Must Have)

These features appear in every credible scouting platform. Absence makes the tool feel incomplete to a professional user.

### Player Discovery & Filtering

- **Position filter** — GK / DF / MF / FW minimum
- **League / Competition filter** — single or multi-select; top 5 leagues are the floor expectation
- **Age range** — slider (min/max). Most scouts set upper bound of 28–30 for prospect searches
- **Minutes played threshold** — ~900 min (10 full 90s) per season standard
- **Market value range** — min/max ceiling relative to club budget
- **Club / team filter** — to scout within a rival's squad
- **Season selector** — current, prior, or multi-season aggregation

### Shortlist / Results Table

- Player name, current club, league, primary position, age, market value
- At least one composite score/rating
- Key headline stat (goals, xG, duels won %, etc.)
- Sortable by any column. Row-click opens player profile.

### Player Profile Page

**Header block:** Full name, age, nationality, current club, market value, preferred foot, height

**Statistical summary:**
- Per-90 stats for the current season, segmented by position role
- Percentile ranks vs. position peers (bar fills or color-coded numbers) — universal in modern tools; raw stats without peer context are considered outdated
- Season-over-season trend for key metrics (3-season view is common)

**Standard visualizations:**
- Radar/spider chart comparing the player's percentile profile vs. position-peer median — the single most universal scouting visualization
- Scatter chart placing the player in a value-vs-performance space

**Similar players panel:** Top 5–10 comparable players with stat similarity rationale

### Multi-League Comparability

- Per-90 normalization as baseline (raw totals never used for cross-league comparison)
- Position-peer percentile ranks calculated cross-league for transfer scouting
- Opta and StatsBomb use cross-league position pools for radar comparisons

### Standard Visualizations (in order of universality)

1. **Radar / spider chart** — every tool has this
2. **Scatter plot** — two-metric comparison across a player set
3. **Percentile bar rows** — horizontal bars showing position vs. peers per metric
4. **Season trend line** — sparkline of key metric across seasons
5. **Pitch heatmap / action map** — NOT relevant (requires event-level spatial data; FBref aggregates don't include this)

---

## Differentiators (Our Angle)

### UV Score — Explicit Undervaluation Ranking

No standard scouting tool surfaces an "undervalued player" signal as a first-class metric. Wyscout, Opta, and StatsBomb show performance data; scouts manually cross-reference Transfermarkt values. Our regression-residual UV Score converts that manual workflow into an automatic ranking signal.

**Implementation note:** UV Score should be the primary sort on the shortlist by default, not scout score. This is what makes our shortlist meaningfully different from "sort by xG."

### Age-Weighted UV Score

Standard tools show age as a filter. None weight performance scores by age to produce a prospect premium. A 22-year-old with the same output as a 29-year-old is structurally more undervalued (longer peak window, greater development upside). Surfacing this as a scored signal — not just a filter — is a differentiator.

### Team Strength Context Adjustment

Most tools show raw or per-90 stats without team-context normalization. A center-back at a bottom-half club faces more defensive duels and higher xG-against than one at a top-6 club. This adjustment is present in academic work and some elite club internal tools but not in any off-the-shelf accessible platform.

### Cross-League UV Comparison on One Screen

Our scatter (scout score vs. log market value, all leagues on a shared regression line) is differentiating. Standard tools don't plot players from multiple leagues against a single value-vs-performance curve.

### Shortlist-First Layout

Most professional tools are database-first (search → filter → result). Ours is shortlist-first: the landing page IS the ranked undervaluation shortlist. Matches the scout workflow for weekly target scanning.

---

## Anti-Features (Deliberately Skip)

- **Video integration** — requires licensing arrangements; FBref aggregates are stats-only
- **Event-level / spatial data** — pitch heatmaps require action coordinates; FBref doesn't provide them
- **Contract expiry / wage data** — not reliably available from free sources
- **Side-by-side player comparison** — "similar players" panel partially covers this; full comparison view deferred
- **Team / tactical views** — unit of analysis is individual player
- **User accounts / saved shortlists** — single-user local tool
- **Live / real-time data** — incompatible with cache-based pipeline
- **Transfer fee prediction** — UV Score is an undervaluation signal, not a price recommendation

---

## Professional Dashboard Design Patterns

Based on Wyscout, Opta Perform / Stats Perform, StatsBomb IQ:

### Color Palette

- **Background**: Deep navy (#0D1B2A range) or dark charcoal (#1A1A2E). NOT pure black — navy reads as "sports analytics professional," black reads as consumer/gaming
- **Card / panel surfaces**: 8–12% lighter than background (#162032 on #0D1B2A)
- **Primary accent**: Single bright accent — electric blue (#00A8FF, #1E90FF), amber (#F0A500), or bright teal (#00D4AA). Wyscout uses blue. Opta uses amber-orange.
- **Text**: Off-white primary (#E8EDF2), medium grey secondary (#8A9BB0) — never pure white on dark
- **Positive/Negative**: Green (#2ECC71) above-average / undervalued; Red (#E74C3C) below-average / overvalued
- **Percentile color scale**: Red → Amber → Green gradient (low → median → elite) — universal

### Typography

- **Data typography**: Tabular-figures or semi-condensed sans-serif for numbers (ensures column alignment). Common: Inter, Roboto, IBM Plex Sans
- **Labels**: ALL-CAPS small tracking for section headers and column labels ("SCOUT SCORE", "UV SCORE") — consistent in analytics UIs to distinguish labels from data values
- **No decorative fonts**: Everything sans-serif

### Layout Patterns

- **Top nav bar**: League/season context selectors live here, not in sidebar
- **Sidebar**: Record-level filters (position, age, value range)
- **Shortlist table**: Full content width, 8–12 columns, sticky header, subtle alternating row tint
- **Player profile**: Two-column layout. Left ~35%: header block (name, club, age, value, headline stats as large numbers). Right ~65%: visualizations (radar top, stat table below, scatter inset)
- **Radar chart**: 350–450px square. Larger becomes hard to read. Short axis labels
- **Stat table in profile**: Grouped by pillar (Attack / Progression / Creation / Defense / Retention), not alphabetical. Each row: metric name | raw value | per-90 | percentile bar + number

### Interaction Patterns

- Click row → player profile (full-page or right-panel slide-out)
- Hover on radar axis → tooltip with exact stat and percentile
- Scatter chart: hover on dot → player name tooltip; click dot → player profile
- Filter changes update table in real-time (no "Apply" button)

---

## Similar Players Logic

### Recommended Implementation: Cosine Similarity on Pillar Scores

1. Take the normalized pillar score vector for the target player (5 pillar scores)
2. Filter candidates to the same position group (MF vs MF only)
3. Calculate cosine similarity between target's pillar vector and all other qualifying players
4. Return top 5, excluding the player themselves

**Cosine over Euclidean**: Captures profile *shape* (relative distribution across pillars) rather than absolute magnitude. A high-volume and lower-volume forward with the same pillar weight distribution are "stylistically similar" even if one plays at a stronger club.

**Cross-league**: Include all 5 leagues in the comparison pool — cross-league similar players are more transfer-relevant than same-league peers.

### What to Display in Similar Players Panel

- Player name + club + league + age + market value
- **UV Score** (our differentiator — "this similar player is also undervalued")
- The 1–2 pillars where scores are closest (why they are similar)
- Optional: small inline radar overlay on target's profile

**Key value-add vs. standard tools:** Surface which similar players are ALSO undervalued. Standard tools show statistical peers; we show "here are 5 players who play like your target and are also underpriced."

---

*Last updated: 2026-03-16*
