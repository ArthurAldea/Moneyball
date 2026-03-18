# STACK.md — Technology Stack

## Language and Runtime

- **Language:** Python 3.11.14
- **Runtime:** CPython via Anaconda (`/opt/anaconda3/bin/python3.11`)
- **Virtual environment:** `venv/` at project root (created with `python3 -m venv`)

## Application Framework

- **Streamlit** — web dashboard server. Launched with `streamlit run app.py`.
- **Plotly** — interactive charts (plotly.graph_objects and plotly.express). Installed version: 6.6.0.

## Data Sources and Scraping

- **understat** — Python library wrapping the Understat API. Uses async/await internally.
- **aiohttp** — async HTTP client required by the `understat` library at runtime.
- **requests** — synchronous HTTP client used for all API-Football REST calls.
- **curl_cffi** — Chrome TLS fingerprint impersonation library used for Transfermarkt scraping. Configured with `impersonate="chrome120"`.
- **beautifulsoup4** — HTML parser used to extract player rows and market values from Transfermarkt pages.
- **lxml** — fast XML/HTML parser backend passed to BeautifulSoup (`"lxml"` parser string).

## Data Processing

- **pandas** — primary data structure throughout the pipeline. All inter-module data is passed as DataFrames.
- **numpy** — used in merger.py (log10, nan handling, polyfit in app.py) and scorer.py.
- **scikit-learn** — `MinMaxScaler` (per-position group normalization in scorer.py), `LinearRegression` (UV score regression in scorer.py). Installed version: inferred from venv.
- **rapidfuzz** — fuzzy name matching. Uses `process.extractOne` with `fuzz.WRatio` scorer. Installed version: 3.14.3.
- **statsmodels** — listed in requirements.txt but not imported in any current source file (likely a leftover dependency).
- **python-dotenv** — loads `API_FOOTBALL_KEY` from a `.env` file at the project root via `load_dotenv()` in scraper.py.

## Full requirements.txt

```
understat
aiohttp
requests
curl_cffi
beautifulsoup4
lxml
pandas
numpy
scikit-learn
rapidfuzz
python-dotenv
streamlit
plotly
statsmodels
```

No version pins are specified. All packages install at latest compatible versions.

## Configuration Approach

### config.py (constants file)
All application-level constants live in `/Users/ArthurAldea/ClaudeProjects/Moneyball/config.py`. There is no argparse, no YAML, no TOML. Key constants:

| Constant | Value | Purpose |
|---|---|---|
| `SEASONS` | `{"2023-24": 2023, "2024-25": 2024, "2025-26": 2025}` | Season labels mapped to year integers |
| `MIN_MINUTES` | `3000` | Legacy constant (total across all seasons) |
| `MIN_MINUTES_PER_SEASON` | `900` | Per-season threshold; total = this × number of seasons |
| `API_FOOTBALL_BASE` | `"https://v3.football.api-sports.io"` | REST API base URL |
| `API_FOOTBALL_LEAGUE` | `39` | EPL league ID on api-sports.io |
| `API_FOOTBALL_RATE_S` | `1.5` | Seconds to sleep between API-Football requests |
| `TM_BASE` | Transfermarkt league market value page URL | Unused now (squad pages used instead) |
| `TM_RATE_LIMIT_S` | `5` | Seconds to sleep between Transfermarkt requests |
| `FUZZY_THRESHOLD` | `80` | Minimum WRatio score for fuzzy name matches |

### .env file (secrets)
A `.env` file at the project root must contain:
```
API_FOOTBALL_KEY=<your_api_sports_key>
```
This is loaded by `python-dotenv` in scraper.py. The key is read via `os.environ.get("API_FOOTBALL_KEY", "")`. If absent, API-Football scraping is skipped with a warning.

## Development Environment Setup

```bash
# 1. Clone / navigate to project
cd /Users/ArthurAldea/ClaudeProjects/Moneyball

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env with API key
echo "API_FOOTBALL_KEY=your_key_here" > .env

# 5. Pre-populate cache (avoids live scrape on first dashboard load; ~4-5 min)
python scraper.py

# 6. Launch dashboard
streamlit run app.py
```

The `cache/` directory is created automatically by scraper.py when first needed (`os.makedirs(CACHE_DIR, exist_ok=True)`).
