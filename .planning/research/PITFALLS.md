# Pitfalls Research

*Milestone: FBref migration — multi-league expansion*
*Context: Migrating from Understat + API-Football to FBref as sole stats source for all top 5 leagues*

---

## FBref Scraping Risks

### Rate Limiting and Anti-Scraping

**Severity: High — the most common cause of FBref scrapers breaking in production**

- **429 Too Many Requests** triggers at ~20–25 requests within 60 seconds.
- **HTTP 403** (Cloudflare bot challenge) occurs when requests lack plausible browser headers or when intervals are too uniform (fingerprinting).
- Cloudflare blocks can persist for hours even after requests stop.

**Prevention strategies:**
- Randomize delay: `time.sleep(random.uniform(3.5, 6.0))` — uniform intervals are a bot fingerprint
- Use a realistic `User-Agent` string (existing TM headers pattern is correct)
- Do not parallelize FBref requests — serial polite scraping only
- Cold run: 5 leagues × ~8 tables = ~40 requests at 5s = ~4 minutes minimum for FBref alone
- Add exponential backoff on 429: retry after 30s, then 60s, then 120s before giving up

---

### Table Structure Quirks

**Severity: High — will produce silent NaN columns if not handled correctly**

**Multi-level column headers (most common FBref scraping bug):**

FBref stat tables use a two-row header (group row + stat name row). After `pd.read_html()`:
- Columns are a `MultiIndex`: `("Performance", "Gls")`, `("Expected", "xG")`, etc.
- `df["xG"]` will raise `KeyError`
- **Safe pattern:** `df.columns = [col[1] if col[1] else col[0] for col in df.columns]`
- Never reference top-level group names — they have been renamed without notice

**HTML comment wrapping:**

Many FBref tables are embedded in HTML comments. `soup.find("table", id="stats_standard_9")` returns `None`.

**Correct approach:**
```python
from bs4 import Comment
for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
    if "stats_standard" in comment:
        comment_soup = BeautifulSoup(str(comment), "lxml")
        table = comment_soup.find("table", id=target_id)
        if table: ...
```

**Table IDs — stable patterns:**

| League | FBref league ID | Example table ID |
|--------|---------|-------------|
| EPL | 9 | `stats_standard_9` |
| La Liga | 12 | `stats_standard_12` |
| Bundesliga | 20 | `stats_standard_20` |
| Serie A | 11 | `stats_standard_11` |
| Ligue 1 | 13 | `stats_standard_13` |

Never select by positional index (`tables[2]`) — FBref adds/removes sections and offsets shift.

**Duplicate header rows:** FBref repeats column headers every ~20 rows. Filter: `df = df[df["Rk"] != "Rk"]`

---

### FBref Column Name Stability

**Severity: Medium — silent failures when FBref renames stats**

- `xA` was renamed to `xAG` in 2022-23 without notice
- `npxG` appears as `npxG` in some tables, `npxG+xAG` in combined tables
- `Prog` appears in multiple tables under the same leaf name — verify which table a column originates from

**Prevention:** Assert required columns immediately after scraping. If missing, log a warning with available columns — do not silently fill with 0.

---

### What FBref Provides vs. What the Current Pillar Model Needs

**`xGChain` and `xGBuildup` are Understat-proprietary. FBref does not provide them.**

| Position | Affected pillar | Current stat | FBref replacement |
|----------|----------------|-------------|-------------------|
| MF | Progression (30%) | `xGChain_p90` | `PrgP_p90` (progressive passes) |
| FW, DF | Progression | `xGBuildup_p90` | `PrgC_p90` (progressive carries) |

This is a model change, not just a column rename — it must be intentional and documented.

**FBref tables required per league (~6–8 HTTP requests):**

| FBref table | Stats needed |
|-------------|-------------|
| `stats_standard` | xG, xAG, Gls, Ast, Min, Pos, Squad, PrgP, PrgC |
| `stats_shooting` | SoT |
| `stats_passing` | Cmp%, KP |
| `stats_defense` | Tkl, Int, Blocks |
| `stats_possession` | DrbAttempts, DrbSucc, PrgC |
| `stats_misc` | aerial duel wins/losses |
| `stats_keeper` | Saves, GA, SoTA |
| `stats_keeper_adv` | PSxG, sweeper stats |

---

## Data Quality Risks

### Player Name Normalization: FBref vs. Transfermarkt

**Severity: Medium-High — same problem as current cross-source matching, at 5× scale**

**Predictable mismatch patterns:**
- **Mononym/nickname players:** `"Vinicius Junior"` (FBref) vs. `"Vinicius Jr."` (TM) — WRatio ~88, passes threshold of 80
- **Spanish mononyms:** `"Gavi"` (FBref) vs. `"Pablo Martín Páez Gavira"` (TM legal name) — WRatio very low. Ensure TM scraper targets shirt-name field
- The existing `normalize_name()` (NFD + ASCII encode) is correct — do not replace with a manual dict

**Multi-team players (mid-season transfers):**

FBref records a player for each club plus a `"2 Clubs"` aggregate row. **Only the per-club rows should be kept for team-strength adjustment; only aggregate row for scoring.** If both are retained, the player is double-counted in MinMaxScaler fitting.

Filter: `df = df[~df["Squad"].str.contains(r"\d+ Clubs?", na=False)]` to drop aggregate rows.

**Club-name cross-validation guard:**

At 500+ players across 5 leagues, false positive name matches increase. Add: if `normalize_name(club_fbref)` and `normalize_name(club_tm)` differ significantly for a matched pair, flag as suspect.

---

### Cross-League Stat Normalization

**Severity: Medium — affects UV score validity in "All Leagues" view**

- EPL/La Liga forwards will set the xG/90 ceiling, compressing all other leagues — this is correct behavior for a raw output comparison tool but must be documented
- 0.8 xG/90 in Ligue 1 ≠ 0.8 xG/90 in EPL (weaker opposition)
- Defensive stats (Tkl/90, Int/90) are noisier cross-league than xG due to team pressing styles

**Recommendation for MVP:** Use raw per-90 stats without league quality adjustment. Label "All Leagues" view as raw output comparison. League quality adjustment is a post-MVP roadmap item.

---

## Scoring Model Risks

### Team Strength Adjustment — Edge Cases

**Severity: Medium**

- **Newly promoted clubs mid-season:** No historical context. Use current standing; accept noisier scores early in season
- **Games in hand:** Use **points-per-game (PPG) rank** rather than raw points rank
- **Multi-club players:** Use minutes-weighted average of club positions for team strength adjustment
- **Live season volatility:** For live season, use rolling 10-game PPG; for completed seasons, use final standing
- **Adjustment magnitude:** Define beta parameter in `config.py` (suggested range 0.1–0.3), not hardcoded

---

### MinMaxScaler with Small Position Groups

**Severity: Medium — aggravated by multi-league + filter combinations**

- "Single team filter + GK" = 1–2 GKs → scores meaningless (one player scores 0, one scores 1)
- Minimum group size guard: enforce `n >= 10` before fitting; display warning in UI below this

**Recommended fix:** Fit MinMaxScaler on the **full unfiltered position group** (all leagues, all ages), then apply UI filters for display only. A player's score should not change when filters are adjusted.

---

### UV Score Regression Stability

**Severity: Low-Medium**

OLS regression fitted on a small filtered view is unstable (collinear position dummies if only one position visible).

**Recommendation:** Fit regression on the **full unfiltered dataset** (all leagues, all positions). Apply resulting residuals to all players. Apply UI filters for display only.

---

### Age-Weighted UV Score Design Risk

**Severity: Low**

A monotonic age multiplier without bounds inflates UV scores for any young player regardless of quality.

**Recommendation:** Apply multiplier post-hoc on UV score, not on scout score. Cap at 1.5× for under-21. Define multiplier function in `config.py` as tunable parameter.

---

## Transfermarkt Reliability

| League | Coverage Quality | Notes |
|--------|----------------|-------|
| Bundesliga | Excellent | Transfermarkt's home market |
| La Liga | Excellent | Use shirt name, not legal name (e.g., "Gavi") |
| Serie A | Good | Minor dual-nationality name variant risk |
| Ligue 1 | Good | Values may lag ~2 weeks for mid-table clubs |

**Scraper extension — league URL slugs:**

| League | TM URL path | Competition code |
|--------|-------------|------------------|
| La Liga | `/primera-division/startseite/wettbewerb/ES1/` | ES1 |
| Bundesliga | `/1-bundesliga/startseite/wettbewerb/L1/` | L1 |
| Serie A | `/serie-a/startseite/wettbewerb/IT1/` | IT1 |
| Ligue 1 | `/ligue-1/startseite/wettbewerb/FR1/` | FR1 |

The `table.items` CSS structure and kader page format are uniform across leagues.

**Volume:** 5 leagues × ~19 clubs = ~95 clubs at `TM_RATE_LIMIT_S = 5` = ~9 minutes cold run.

**Post-scrape validation (critical):** Assert row count > 0 and `market_value_eur` non-null for >50% of rows per league. A silent CSS-selector failure will produce all-NaN market values for an entire league.

---

## FBref 2025-26 Data Availability

FBref publishes live data during the season, updated within 24–48 hours of each matchday. All stats (xG, GK PSxG, per-90s) are live during 2025-26.

**Season URL structure:**
- Completed: `fbref.com/en/comps/9/2023-2024/stats/2023-2024-Premier-League-Stats`
- Current: `fbref.com/en/comps/9/stats/Premier-League-Stats` (redirects to current)
- Prefer explicit year URL once confirmed — redirect can change during season

---

## Phase Mapping

| Pitfall | Phase |
|---------|-------|
| FBref rate limiting — randomized delays, exponential backoff | Phase 1: FBref scraper |
| HTML comment-wrapped tables | Phase 1: FBref scraper |
| Multi-level column headers — flatten MultiIndex | Phase 1: FBref scraper |
| Duplicate header rows — filter `Rk == "Rk"` | Phase 1: FBref scraper |
| Table IDs — never use positional index | Phase 1: FBref scraper |
| Column rename guard — assert required columns post-scrape | Phase 1: FBref scraper |
| Multi-club aggregate rows — deduplicate correctly | Phase 1: FBref scraper |
| `xGChain`/`xGBuildup` unavailable — replace with `PrgP_p90`/`PrgC_p90` | Phase 1: Pillar model mapping |
| Invalidate old Understat CSV cache before migration | Phase 1: Migration housekeeping |
| Cross-league name normalization — club cross-validation guard | Phase 2: Multi-league merger |
| TM scraper — parameterize league URL slug | Phase 2: Multi-league TM scraper |
| TM post-scrape row count validation per league | Phase 2: Multi-league TM scraper |
| MinMaxScaler small group guard — fit on full unfiltered pool | Phase 3: Scoring model |
| UV regression — fit on full unfiltered dataset | Phase 3: Scoring model |
| Team strength adjustment — PPG rank, rolling 10-game for live season | Phase 3: Team strength |
| Age-weighted UV — post-hoc, cap at 1.5×, config.py | Phase 3: Age weighting |
| Cross-league raw comparison — documented in UI as known limitation | Phase 3: Dashboard |
| League quality adjustment | Post-MVP |

---

*Research compiled: 2026-03-16*
