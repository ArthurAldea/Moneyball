# Architecture Research

*Written: 2026-03-16. Based on analysis of existing codebase maps and domain knowledge.*

---

## Pipeline Design

**Recommendation: League-parallel scrape → league-isolated normalization → combined at UV regression**

The pipeline processes each league independently through scraping and pillar scoring, then merges all leagues into a single master DataFrame for UV regression and display.

```
FBref (5 leagues × N tables)
  ↓  scraper.py  [one CSV cache per league/table/season]
  ↓
Transfermarkt (5 leagues)
  ↓  scraper.py
  ↓
merger.py:
  aggregate_fbref(data)          # sum/mean across seasons per player
  apply_team_strength()          # league position normalization
  compute_per90s()               # per-90 derivations
  match_market_values()          # TM fuzzy name matching
  ↓
scorer.py:
  for each league:
    for each position group (GK/FW/MF/DF):
      MinMaxScaler.fit_transform()   # normalize WITHIN league+position
      compute_pillar_scores()
  ↓
  concat all leagues → master DataFrame
  ↓
  UV regression on full pool (~2,500–3,000 players)
  apply_age_weight()
  ↓
app.py: display
```

**Why league-isolated normalization:** MinMaxScaler must run per-position-group per-league, not across the pooled dataset. Pooling before normalization suppresses strong-within-league players if another league happens to have higher absolute numbers. After per-league scoring, concat all 5 scored DataFrames into a master DataFrame, then run the single OLS UV regression on the full pool. The larger sample gives a more stable regression line and enables cross-league UV comparisons.

**Scraper signature change:**
```python
# Old
run_scoring_pipeline(understat_data, api_data, tm_data)

# New
run_scoring_pipeline(fbref_data, tm_data)
# where fbref_data: dict[(league, season), dict[table_type, DataFrame]]
```

---

## Team Strength Adjustment

**Where in pipeline:** After `compute_per90s()`, before `MinMaxScaler` normalization.

**What stats to adjust:** Apply only to defensive stats for outfield players (Tkl_p90, Int_p90, Blocks_p90, DuelsWon_p90, pressures_p90) and all volume-dependent stats for GKs. Do NOT adjust attacking stats (xG, goals) — attacking output is less correlated with team defensive load.

**Formula:**
```python
def apply_team_strength_adjustment(df: pd.DataFrame, standings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adjust defensive per-90 stats for team defensive workload context.
    Bottom-half clubs face more defensive pressure → upward adjustment.
    Top-half clubs face less → downward adjustment.

    adjustment_multiplier range: 0.90 (1st) to 1.10 (20th)
    """
    n_teams = standings_df["position"].max()
    standings_df = standings_df.copy()
    standings_df["league_position_factor"] = (standings_df["position"] - 1) / (n_teams - 1)
    # 0.0 = champions, 1.0 = relegated
    standings_df["adjustment_multiplier"] = 1 + 0.20 * (standings_df["league_position_factor"] - 0.5)
    # Champions → ×0.90,  midtable → ×0.99–1.01,  relegated → ×1.10

    df = df.merge(standings_df[["Squad", "adjustment_multiplier"]], on="Squad", how="left")
    df["adjustment_multiplier"] = df["adjustment_multiplier"].fillna(1.0)

    defensive_stats = ["Tkl_p90", "Int_p90", "Blocks_p90", "DuelsWon_p90", "pressures_p90",
                       "Saves_p90", "SavePct"]  # GK stats also adjusted
    for stat in defensive_stats:
        if stat in df.columns:
            df[stat] = df[stat] * df["adjustment_multiplier"]

    df.drop(columns=["adjustment_multiplier"], inplace=True)
    return df
```

**New function location:** `merger.py`, called after `compute_per90s()`.

**Standings data source:** FBref league table via `soccerdata`'s `read_league_table()`. Cache as `cache/fbref_{league}_standings_{season}.csv`.

---

## Age-Weighted UV Formula

**Approach:** Multiplicative post-UV with log-age decay.

```python
def apply_age_weight(df: pd.DataFrame, beta: float = 0.30) -> pd.DataFrame:
    """
    Age-weighted UV score: younger players performing at the same level score higher.

    At beta=0.30:
    - Age 18: ×1.28 multiplier
    - Age 22: ×1.16 multiplier
    - Age 27: ×1.05 multiplier
    - Age 29+: ×1.00 multiplier (no change)

    Both uv_score and uv_score_age_weighted are stored as separate columns.
    """
    import numpy as np
    peak_age = 29
    min_age = 17

    log_peak = np.log(peak_age)
    log_min = np.log(min_age)

    age = pd.to_numeric(df["Age"], errors="coerce").fillna(peak_age)
    age_clipped = age.clip(upper=peak_age)

    age_weight = (np.log(peak_age) - np.log(age_clipped)) / (log_peak - log_min)
    age_weight = age_weight.clip(lower=0.0)

    df["uv_score_age_weighted"] = df["uv_score"] * (1 + beta * age_weight)
    return df
```

**Dashboard default sort:** `uv_score_age_weighted`. Standard UV Score retained as separate column and displayable.

**New function location:** `scorer.py`, called after `compute_efficiency()`.

---

## Cache Architecture

**Naming convention:**
```
cache/fbref_{league}_{table}_{season}.csv
cache/tm_values_{league}_{season}.csv
cache/fbref_{league}_standings_{season}.csv
```

**Examples:**
```
cache/fbref_epl_standard_202526.csv
cache/fbref_laliga_defense_202526.csv
cache/fbref_epl_keepers_adv_202526.csv
cache/tm_values_bundesliga_202526.csv
cache/fbref_bundesliga_standings_202526.csv
```

**Rationale for granular per-table files:** Isolates scrape failures — a network error on `keepers_adv` does not invalidate a good `standard` cache. Each table type is a separate fetch that can fail/succeed independently.

**TTL:** Retain existing 7-day mtime check. Only naming convention changes.

**Season key format:** `{year1}{year2}` → `202526` (4+2 digits, no separator). Consistent, no hyphen ambiguity.

**League key:** lowercase slug — `epl`, `laliga`, `bundesliga`, `seriea`, `ligue1`.

---

## Similar Players Algorithm

**Method:** Cosine similarity on the 5 normalized pillar score columns.

```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def find_similar_players(df: pd.DataFrame, player_name: str, n: int = 5) -> pd.DataFrame:
    """
    Find N most similar players by pillar score profile (cosine similarity).
    Only compares within the same position group.
    Includes all leagues — cross-league discovery is the primary value.
    """
    player_row = df[df["Player"] == player_name]
    if player_row.empty:
        return pd.DataFrame()

    pos = player_row["Pos"].iloc[0]
    pos_df = df[df["Pos"] == pos].copy().reset_index(drop=True)

    pillar_cols = [c for c in pos_df.columns if c.startswith("score_")]
    if not pillar_cols:
        return pd.DataFrame()

    feature_matrix = pos_df[pillar_cols].fillna(0).values
    target_idx = pos_df[pos_df["Player"] == player_name].index[0]
    target_vector = feature_matrix[target_idx].reshape(1, -1)

    similarities = cosine_similarity(target_vector, feature_matrix)[0]
    pos_df["similarity_score"] = similarities

    similar = (pos_df
               .drop(index=target_idx)
               .sort_values("similarity_score", ascending=False)
               .head(n))

    return similar[["Player", "Squad", "League", "Pos", "Age",
                     "market_value_eur", "uv_score_age_weighted", "similarity_score"]]
```

**Why cosine over Euclidean:** Captures profile *shape* (relative distribution across pillars), not absolute magnitude. Cross-club and cross-league volume differences don't distort the similarity.

**Feature vector:** Use `score_*` pillar columns (already normalized and weighted). Do NOT include `scout_score` — it's a weighted sum of pillars, adding it introduces circularity.

---

## FBref Table Reference

| League | Comp ID | URL Pattern |
|--------|---------|-------------|
| EPL | 9 | `fbref.com/en/comps/9/{season}/stats/...` |
| La Liga | 12 | `fbref.com/en/comps/12/{season}/stats/...` |
| Bundesliga | 20 | `fbref.com/en/comps/20/{season}/stats/...` |
| Serie A | 11 | `fbref.com/en/comps/11/{season}/stats/...` |
| Ligue 1 | 13 | `fbref.com/en/comps/13/{season}/stats/...` |

Season format in URL: `2025-2026`. All stat tables wrapped in HTML comments.

**Key table IDs:**
- `stats_standard` — goals, assists, npxG, xAG, progressive passes/carries, minutes, age
- `stats_shooting` — shots, SoT, G-xG
- `stats_passing` — xAG, KP, progressive passes, pass completion %
- `stats_gca` — SCA, GCA (shot/goal creating actions)
- `stats_defense` — tackles, interceptions, blocks, pressures
- `stats_possession` — progressive carries, dribbles completed, touches in final third
- `stats_misc` — aerial duels won/lost, fouls
- `stats_keeper` — save%, PSxG, clean sheets
- `stats_keeper_adv` — PSxG-GA, launched passes, sweeper actions, crosses stopped

**Critical migration note:** FBref does not publish `xGChain` (Understat-specific). The existing MF Progression pillar uses `xGChain_p90`. Best FBref substitute: `sca_p90` (shot-creating actions per 90 from `stats_gca`) blended with `progressive_passes_p90` from `stats_standard`.

---

## Build Order

1. **FBref scraper (EPL only)** — `scraper.py` rewrite: all required tables, HTML comment parsing, CSV cache with new naming convention
2. **Merger rewrite** — multi-table join, FBref column mapping, xGChain → sca substitution, team strength adjustment
3. **Scorer update** — confirm pillar models work with new column names, add age-weighted UV
4. **EPL end-to-end test** — verify the full pipeline produces sensible scores before expanding
5. **Multi-league expansion** — extend scraper + TM scraper to 4 remaining leagues, add `League` column to all DataFrames, league-loop in scorer
6. **Dashboard rebuild** — new filters, shortlist landing page, similar players panel, professional dark theme

---

*Last updated: 2026-03-16*
