# Moneyball — Football Efficiency Analysis

A data-driven scouting tool that surfaces undervalued footballers across Europe's top five leagues by bridging on-pitch performance with market valuation.

**[Live App →](https://moneyball-football.streamlit.app/)**

---

## Overview

Moneyball scores every outfield player and goalkeeper across the Premier League, La Liga, Bundesliga, Serie A, and Ligue 1 using a position-specific scout scoring model, then identifies players whose performance most exceeds their market price through OLS regression.

The result is a ranked shortlist of undervalued players — filterable by league, position, age, and market value — with individual deep profiles, radar charts, peer comparisons, and a scatter chart mapping the entire market.

---

## Features

- **Scout Score** — Pillar-based performance score (0–100) tailored per position (FW / MF / DF / GK), incorporating xG, xA, shots on target, tackles won, interceptions, crosses, and more
- **UV Score** — Undervaluation percentile derived from OLS regression residuals; 100 = most undervalued relative to peers
- **Age-Weighted UV** — UV Score adjusted for age, rewarding younger players with more upside
- **Value Gap** — The €M difference between a player's predicted fair value and their actual market value
- **Player Deep Profile** — Radar chart, full stat table with percentile ranks, and a panel of similar players
- **Comparison Mode** — Select two players to compare their radar profiles side by side
- **Scatter Chart** — Full market view with OLS regression line; pan and zoom to explore the distribution
- **Shortlist Filters** — Filter by league, position, age, market value, and UV score threshold
- **Methodology & How To Use tabs** — Transparent breakdown of every calculation, data source, and limitation

---

## Data Sources

| Source | Data | Method |
|--------|------|--------|
| [FBref](https://fbref.com) | Goals, assists, shots, tackles, interceptions, crosses, fouls, saves, minutes | Scraped via nodriver (Chromium) + BeautifulSoup |
| [Understat](https://understat.com) | xG, xA per player per season | Python `understat` library (async) |
| [Transfermarkt](https://transfermarkt.com) | Market values | Scraped via curl_cffi (Chrome impersonation) |
| [football-data.co.uk](https://football-data.co.uk) | League standings | Plain HTTP CSV download |

Seasons covered: **2023-24** and **2024-25** (minimum 900 minutes per season to qualify).

---

## Scoring Model

Scout scores are computed per position using a weighted pillar system. All pillar weights sum to 1.0.

**Position pillar weights (Attacking / Progression / Creation / Defense / Retention):**

| Position | Attacking | Progression | Creation | Defense | Retention |
|----------|-----------|-------------|----------|---------|-----------|
| FW | 45% | 20% | 20% | 5% | 10% |
| MF | 20% | 30% | 25% | 15% | 10% |
| DF | 10% | 15% | 10% | 45% | 20% |
| GK | Shot Stopping 70% | Workload 20% | — | 5% | 3% + 2% |

**Stats per pillar:**

| Pillar | Stats |
|--------|-------|
| Attacking (FW) | xG_p90 × 0.45 + SoT_p90 × 0.35 + Ast_p90 × 0.20 |
| Attacking (MF) | xG_p90 × 0.40 + Gls_p90 × 0.35 + SoT_p90 × 0.25 |
| Progression | Sh_p90 + Fld_p90 (FW/MF); Crs_p90 (DF) |
| Creation (FW/MF) | xA_p90 × 0.50 + Ast_p90 × 0.30 + Crs_p90 × 0.20 |
| Defense | Int_p90 + TklW_p90 |
| Retention | Fld_p90 |
| GK Shot Stopping | Save% |
| GK Workload | Saves_p90 |

**Undervaluation (UV Score):** Position-aware OLS regression on `log10(market_value) ~ scout_score + position_dummies`. The UV Score is the percentile rank of the negative residual — players who perform above what the market pays for score closer to 100.

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Data scraping | nodriver, curl_cffi, BeautifulSoup, requests, understat |
| Data processing | pandas, numpy, scikit-learn (MinMaxScaler), rapidfuzz, statsmodels |
| UI | Streamlit, Plotly |
| Runtime | Python 3.11+ |

---

## Running Locally

```bash
# 1. Clone and create a virtual environment
git clone https://github.com/ArthurAldea/Moneyball.git
cd Moneyball
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app (uses pre-populated cache — no scraping needed)
streamlit run app.py
```

To refresh the data cache (requires Chromium):

```bash
python scraper.py
```

---

## Project Structure

```
app.py          — Streamlit dashboard
scorer.py       — Scoring pipeline (scout score, UV score, regression)
merger.py       — FBref + Transfermarkt + Understat data merge
scraper.py      — FBref, Transfermarkt, and Understat scrapers
config.py       — Constants, league configs, pillar weight definitions
cache/          — Pre-scraped CSVs (7-day TTL, all 5 leagues × 2 seasons)
```

---

## Limitations

- Market values sourced from Transfermarkt are community-estimated and may lag transfers or form changes
- FBref's 2025 "Lit" migration removed most advanced stats (progressive carries, pressures, pass completion, SCA); the model adapts using available data plus Understat for xG/xA
- Players with fewer than 900 minutes in a season are excluded
- Scores are normalised within each league and position group, so comparisons are relative, not absolute
