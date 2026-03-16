"""
config.py — Central configuration for Moneyball Efficiency Analysis.
"""

# ── Seasons ───────────────────────────────────────────────────────────────────
SEASONS = {
    "2023-24": 2023,
    "2024-25": 2024,
    "2025-26": 2025,
}

MIN_MINUTES = 3000          # minimum across all seasons combined (3-season default)
MIN_MINUTES_PER_SEASON = 900  # scales down when fewer seasons are selected

# ── FBref scraper constants ────────────────────────────────────────────────────
FBREF_LEAGUES = {
    "EPL": {"comp_id": 9, "slug": "Premier-League"},
}

FBREF_TABLES = [
    "stats_standard",
    "stats_shooting",
    "stats_passing",
    "stats_defense",
    "stats_possession",
    "stats_misc",
    "stats_keeper",
    "stats_keeper_adv",
    "stats_gca",
]

# Seasons to scrape in Phase 1 — 2023-24 and 2024-25 only (2025-26 is mid-season, incomplete)
FBREF_SEASONS = ["2023-24", "2024-25"]

# Rate limiting (DATA-06)
FBREF_RATE_MIN = 3.5   # seconds — minimum delay between requests
FBREF_RATE_MAX = 6.0   # seconds — maximum delay between requests

# Exponential backoff sequence on 429 (DATA-06)
FBREF_BACKOFF_SEQUENCE = [30, 60, 120]  # seconds

# FBref URL segments per table type (table_type -> URL path segment)
FBREF_TABLE_URL_SEGMENTS = {
    "stats_standard":   "stats",
    "stats_shooting":   "shooting",
    "stats_passing":    "passing",
    "stats_defense":    "defense",
    "stats_possession": "possession",
    "stats_misc":       "misc",
    "stats_keeper":     "keepers",
    "stats_keeper_adv": "keepersadv",
    "stats_gca":        "gca",
}

# Minimum minutes per season filter (DATA-07)
FBREF_MIN_MINUTES = 900

# FBref request headers — mimics Chrome browser to avoid 403
FBREF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def build_fbref_url(league: str, table_type: str, season_label: str) -> str:
    """
    Construct the FBref stats URL for a given league, table type, and season.

    Args:
        league: League key from FBREF_LEAGUES, e.g. "EPL"
        table_type: Table key from FBREF_TABLES, e.g. "stats_standard"
        season_label: Short season label, e.g. "2024-25"

    Returns:
        Full FBref URL, e.g.:
        "https://fbref.com/en/comps/9/2024-2025/stats/2024-2025-Premier-League-Stats"
    """
    league_cfg = FBREF_LEAGUES[league]
    comp_id    = league_cfg["comp_id"]
    slug       = league_cfg["slug"]
    url_seg    = FBREF_TABLE_URL_SEGMENTS[table_type]

    # Convert "2024-25" -> "2024-2025"
    parts = season_label.split("-")
    start_year = int(parts[0])
    end_year   = start_year + 1
    season_long = f"{start_year}-{end_year}"

    return (
        f"https://fbref.com/en/comps/{comp_id}"
        f"/{season_long}/{url_seg}"
        f"/{season_long}-{slug}-Stats"
    )


# ── API-Football (api-sports.io) ───────────────────────────────────────────────
API_FOOTBALL_BASE   = "https://v3.football.api-sports.io"
API_FOOTBALL_LEAGUE = 39
API_FOOTBALL_RATE_S = 1.5

# ── Transfermarkt ─────────────────────────────────────────────────────────────
TM_BASE = (
    "https://www.transfermarkt.com/premier-league/marktwerte/"
    "wettbewerb/GB1/plus/1/galerie/0"
)
TM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.transfermarkt.com/",
}
TM_RATE_LIMIT_S = 5

FUZZY_THRESHOLD = 80

# ── Outfield Scout Score Pillars (position-specific) ──────────────────────────
# Weights reflect each position's primary responsibilities.
# Creation pillar: Ast_p90 removed (was double-counted from Attacking pillar).
# Progression for FW/DF: uses xGBuildup_p90 (excludes own shots/chances) instead
# of xGChain_p90 to avoid double-counting forward output.

_CREATION = {
    "weight": 20,
    "label": "Creation",
    "color": "#00cfff",
    "stats": {"xA_p90": 0.55, "KP_p90": 0.45},
}
_DEFENSE = {
    "weight": 15,
    "label": "Defense",
    "color": "#f5a623",
    "stats": {"Tkl_p90": 0.35, "Int_p90": 0.30, "Blocks_p90": 0.20, "DuelsWon_p90": 0.15},
}
_RETENTION = {
    "weight": 10,
    "label": "Retention",
    "color": "#c084fc",
    "stats": {"Cmp%": 0.60, "DuelsWon%": 0.40},
}

PILLARS_FW = {
    "attacking": {
        "weight": 45,
        "label": "Attacking",
        "color": "#ff3131",
        "stats": {"xG_p90": 0.40, "Gls_p90": 0.35, "Ast_p90": 0.15, "SoT_p90": 0.10},
    },
    "progression": {
        "weight": 20,
        "label": "Progression",
        "color": "#00ff41",
        "stats": {"xGBuildup_p90": 0.45, "DrbAttempts_p90": 0.30, "DrbSucc_p90": 0.25},
    },
    "creation": {**_CREATION, "weight": 20},
    "defense":   {**_DEFENSE,   "weight":  5},
    "retention": {**_RETENTION, "weight": 10},
}

PILLARS_MF = {
    "attacking": {
        "weight": 20,
        "label": "Attacking",
        "color": "#ff3131",
        "stats": {"xG_p90": 0.40, "Gls_p90": 0.30, "Ast_p90": 0.20, "SoT_p90": 0.10},
    },
    "progression": {
        "weight": 30,
        "label": "Progression",
        "color": "#00ff41",
        "stats": {"xGChain_p90": 0.40, "DrbAttempts_p90": 0.35, "DrbSucc_p90": 0.25},
    },
    "creation": {**_CREATION, "weight": 25},
    "defense":   {**_DEFENSE,   "weight": 15},
    "retention": {**_RETENTION, "weight": 10},
}

PILLARS_DF = {
    "attacking": {
        "weight": 10,
        "label": "Attacking",
        "color": "#ff3131",
        "stats": {"xG_p90": 0.40, "Gls_p90": 0.30, "Ast_p90": 0.20, "SoT_p90": 0.10},
    },
    "progression": {
        "weight": 15,
        "label": "Progression",
        "color": "#00ff41",
        "stats": {"xGBuildup_p90": 0.50, "DrbAttempts_p90": 0.30, "DrbSucc_p90": 0.20},
    },
    "creation": {**_CREATION, "weight": 10},
    "defense":   {**_DEFENSE,   "weight": 45},
    "retention": {**_RETENTION, "weight": 20},
}

# Legacy alias — kept so any external code referencing PILLARS still works
PILLARS = PILLARS_MF

# ── GK Scout Score Pillars ────────────────────────────────────────────────────
# Mapped to same 5 slots so the UI (radar, stacked bar) works without changes.
GK_PILLARS = {
    "attacking": {          # → Shot Stopping
        "weight": 50,
        "label": "Shot Stopping",
        "color": "#ff3131",
        # SavePct = saves / (saves + goals_conceded) — rewards quality, not volume.
        # Higher saves/90 at a weak team is penalised; good GKs at strong teams rewarded.
        "stats": {"SavePct": 1.0},
    },
    "progression": {        # → Distribution
        "weight": 20,
        "label": "Distribution",
        "color": "#00ff41",
        "stats": {"Cmp%": 0.65, "DuelsWon%": 0.35},
    },
    "creation": {           # → Aerial Command
        "weight": 15,
        "label": "Aerial Command",
        "color": "#00cfff",
        "stats": {"DuelsWon_p90": 0.65, "DuelsWon%": 0.35},
    },
    "defense": {            # → Sweeping / Blocking
        "weight": 10,
        "label": "Sweeping",
        "color": "#f5a623",
        "stats": {"Blocks_p90": 0.55, "Int_p90": 0.45},
    },
    "retention": {          # → Composure
        "weight": 5,
        "label": "Composure",
        "color": "#c084fc",
        "stats": {"Cmp%": 1.0},
    },
}

# ── Aggregation rules ─────────────────────────────────────────────────────────
UNDERSTAT_SUM    = ["Min", "Gls", "Ast", "xG", "xA", "npxG", "xGChain", "xGBuildup", "Sh", "KP"]
API_FOOTBALL_SUM = ["Saves", "GoalsConceded", "SoT", "Tkl", "Blocks", "Int",
                    "DuelsTotal", "DuelsWon", "DrbAttempts", "DrbSucc", "Fld"]
SUM_STATS  = UNDERSTAT_SUM + API_FOOTBALL_SUM
MEAN_STATS = ["Cmp%"]
PER90_STATS = [
    "Gls", "Ast", "xG", "xA", "npxG", "xGChain", "xGBuildup", "Sh", "KP",
    "Saves", "SoT", "Tkl", "Blocks", "Int", "DuelsWon",
    "DrbAttempts", "DrbSucc", "Fld",
]
