"""
config.py — Central configuration for Moneyball Efficiency Analysis.
"""

# ── Seasons ───────────────────────────────────────────────────────────────────
SEASONS = {
    "2023-24": 2023,
    "2024-25": 2024,
    "2025-26": 2025,
}

MIN_MINUTES = 1800          # minimum across all seasons combined (2-season threshold: 900 × 2)
MIN_MINUTES_PER_SEASON = 900  # scales down when fewer seasons are selected

# ── FBref scraper constants ────────────────────────────────────────────────────
FBREF_LEAGUES = {
    "EPL":        {"comp_id": 9,  "slug": "Premier-League"},
    "LaLiga":     {"comp_id": 12, "slug": "La-Liga"},
    "Bundesliga": {"comp_id": 20, "slug": "Bundesliga"},
    "SerieA":     {"comp_id": 11, "slug": "Serie-A"},
    "Ligue1":     {"comp_id": 13, "slug": "Ligue-1"},
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

# ── Understat league name mapping (Phase 06.1) ────────────────────────────────
# Maps project league keys to Understat internal slug names used by get_league_players().
# Source: understat library utils.py to_league_name() + URL pattern inspection.
UNDERSTAT_LEAGUE_NAMES = {
    "EPL":        "EPL",
    "LaLiga":     "La_liga",
    "Bundesliga": "Bundesliga",
    "SerieA":     "Serie_A",
    "Ligue1":     "Ligue_1",
}

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
TM_LEAGUE_URLS = {
    "EPL":        "https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1",
    "LaLiga":     "https://www.transfermarkt.com/laliga/startseite/wettbewerb/ES1",
    "Bundesliga": "https://www.transfermarkt.com/bundesliga/startseite/wettbewerb/L1",
    "SerieA":     "https://www.transfermarkt.com/serie-a/startseite/wettbewerb/IT1",
    "Ligue1":     "https://www.transfermarkt.com/ligue-1/startseite/wettbewerb/FR1",
}
# ── League quality multipliers (SCORE-05) ─────────────────────────────────────
# Applied to uv_score_age_weighted after age-weighting step.
# Coefficients reflect UEFA club competition coefficient ranking.
LEAGUE_QUALITY_MULTIPLIERS = {
    "EPL":        1.10,
    "LaLiga":     1.08,
    "Bundesliga": 1.05,
    "SerieA":     1.03,
    "Ligue1":     1.00,
}

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
FUZZY_THRESHOLD_PASS3 = 70

# ── Outfield Scout Score Pillars (position-specific) ──────────────────────────
# Post-FBref Lit migration (2025): only basic stats remain in public FBref tables.
# Available outfield stats: Gls, Ast, SoT, Sh (shooting); Int, TklW (defense);
#   Fls, Fld, Crs (misc). All advanced stats (xG, xA, KP, SCA, PrgC/P, Blocks,
#   Pres, aerial duels, pass completion) are no longer served by FBref.
#
# Pillar mapping with available stats:
#   Attacking:   FW: xG_p90 + SoT_p90 + Ast_p90; MF: xG_p90 + Gls_p90 + SoT_p90; DF: Gls_p90 + Ast_p90 + SoT_p90
#   Progression: Sh_p90  + Fld_p90               (shot volume + fouls drawn)
#   Creation:    FW/MF: xA_p90 + Ast_p90 + Crs_p90; DF: Ast_p90 + Crs_p90
#   Defense:     Int_p90 + TklW_p90              (interceptions + tackles won)
#   Retention:   Fld_p90                         (winning free-kicks = composure proxy)
#
# Weights sum to 1.0 per pillar so max scout score ≈ 100 for the best player.

_CREATION = {
    "weight": 20,
    "label": "Creation",
    "color": "#00cfff",
    "stats": {"Ast_p90": 0.60, "Crs_p90": 0.40},
}
_DEFENSE = {
    "weight": 15,
    "label": "Defense",
    "color": "#f5a623",
    "stats": {"Int_p90": 0.55, "TklW_p90": 0.45},
}
_RETENTION = {
    "weight": 10,
    "label": "Retention",
    "color": "#c084fc",
    "stats": {"Fld_p90": 1.00},
}

PILLARS_FW = {
    "attacking": {
        "weight": 45,
        "label": "Attacking",
        "color": "#ff3131",
        "stats": {"xG_p90": 0.45, "SoT_p90": 0.35, "Ast_p90": 0.20},
    },
    "progression": {
        "weight": 20,
        "label": "Progression",
        "color": "#00ff41",
        "stats": {"Sh_p90": 0.65, "Fld_p90": 0.35},
    },
    "creation": {
        "weight": 20,
        "label": "Creation",
        "color": "#00cfff",
        "stats": {"xA_p90": 0.50, "Ast_p90": 0.30, "Crs_p90": 0.20},
    },
    "defense":    {**_DEFENSE,  "weight":  5},
    "retention":  {**_RETENTION, "weight": 10},
}

PILLARS_MF = {
    "attacking": {
        "weight": 20,
        "label": "Attacking",
        "color": "#ff3131",
        "stats": {"xG_p90": 0.40, "Gls_p90": 0.35, "SoT_p90": 0.25},
    },
    "progression": {
        "weight": 30,
        "label": "Progression",
        "color": "#00ff41",
        "stats": {"Crs_p90": 0.55, "Fld_p90": 0.45},
    },
    "creation": {
        "weight": 25,
        "label": "Creation",
        "color": "#00cfff",
        "stats": {"xA_p90": 0.50, "Ast_p90": 0.30, "Crs_p90": 0.20},
    },
    "defense":    {**_DEFENSE,  "weight": 15},
    "retention":  {**_RETENTION, "weight": 10},
}

PILLARS_DF = {
    "attacking": {
        "weight": 10,
        "label": "Attacking",
        "color": "#ff3131",
        "stats": {"Gls_p90": 0.40, "Ast_p90": 0.35, "SoT_p90": 0.25},
    },
    "progression": {
        "weight": 15,
        "label": "Progression",
        "color": "#00ff41",
        "stats": {"Crs_p90": 1.00},
    },
    "creation":   {**_CREATION, "weight": 10},
    "defense": {
        "weight": 45,
        "label": "Defense",
        "color": "#f5a623",
        "stats": {"Int_p90": 0.55, "TklW_p90": 0.45},
    },
    "retention":  {**_RETENTION, "weight": 20},
}

# Legacy alias — kept so any external code referencing PILLARS still works
PILLARS = PILLARS_MF

# ── GK Scout Score Pillars ────────────────────────────────────────────────────
# Post-Lit migration: keeper tables retain Save%, Saves, SoTA, CS%.
# PSxG/SoT, Cmp%, aerial, and sweeping stats are gone.
# GK scoring uses Save% (quality) + CS% (outcomes) + Saves_p90 (volume).
GK_PILLARS = {
    # Post-Lit migration: only Save% and Saves raw count survive in keeper table.
    # PSxG/SoT, Cmp%, CS%, aerial, and sweeping stats are gone.
    "attacking": {          # → Shot Stopping (quality)
        "weight": 70,
        "label": "Shot Stopping",
        "color": "#ff3131",
        "stats": {"Save%": 1.00},
    },
    "progression": {        # → Workload (volume of saves)
        "weight": 20,
        "label": "Workload",
        "color": "#00ff41",
        "stats": {"Saves_p90": 1.00},
    },
    "creation": {           # → Aerial / Command (proxied by Int_p90)
        "weight": 5,
        "label": "Aerial Command",
        "color": "#00cfff",
        "stats": {"Int_p90": 1.00},
    },
    "defense": {            # → Sweeping / Contribution
        "weight": 3,
        "label": "Sweeping",
        "color": "#f5a623",
        "stats": {"TklW_p90": 1.00},
    },
    "retention": {          # → Composure
        "weight": 2,
        "label": "Composure",
        "color": "#c084fc",
        "stats": {"Fld_p90": 1.00},
    },
}

# ── Aggregation rules ─────────────────────────────────────────────────────────
# Raw-count columns present in FBref tables after the Lit migration.
# Only columns with actual data are listed; empty columns are omitted.
SUM_STATS = [
    "Min", "Gls", "Ast",
    "Sh", "SoT",               # shooting counts (stats_shooting)
    "Int", "TklW",             # defensive counts (stats_defense / stats_misc)
    "Fls", "Fld", "Crs",       # misc: fouls committed, fouls drawn, crosses
    "Saves", "GA", "SoTA",     # GK stats_keeper (GA and SoTA for Save% re-derivation)
    "xG", "xA",                # Understat totals — summed across seasons in _aggregate_fbref_seasons
]
MEAN_STATS = []  # all rate stats re-derived from sums, not averaged
PER90_STATS = [
    "Gls", "Ast",
    "Sh", "SoT",               # → Sh_p90, SoT_p90
    "Int", "TklW",             # → Int_p90, TklW_p90
    "Fls", "Fld", "Crs",       # → Fls_p90, Fld_p90, Crs_p90
    "Saves",                   # GK → Saves_p90
    "xG", "xA",                # → xG_p90, xA_p90 via compute_per90s()
]
