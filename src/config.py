import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Logging Configuration
# On Streamlit Cloud, file logging may not be available, so we'll use StreamHandler only if FileHandler fails
handlers = []
try:
    handlers.append(logging.FileHandler('ev_engine.log'))
except (OSError, PermissionError):
    # File logging not available (e.g., Streamlit Cloud), use console only
    pass
handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger('ev_engine')

# The Odds API Configuration
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

# Database Configuration
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ev_engine.db")

# EV Calculation Constants
PAYOUT_MULTIPLIER = 3.0  # Standard 2-Pick Power Play
BREAK_EVEN_WIN_PCT = 1 / PAYOUT_MULTIPLIER  # 33.33%
IMPLIED_LEG_PROB = BREAK_EVEN_WIN_PCT ** 0.5  # ~57.7% per leg break-even

# Bookmaker Keys
SHARP_BOOKMAKER = "pinnacle"
FALLBACK_SHARP_BOOKMAKER = "fanduel"
DFS_BOOKMAKERS = ["prizepicks", "underdog", "betr_us_dfs", "pick6"]

# Sharp bookmaker confidence factors for EV calculations
# Pinnacle is the gold standard (1.0), FanDuel is less sharp so we discount the EV
# This accounts for higher vig (~4-5% vs Pinnacle's ~2%) and less efficient lines
SHARP_CONFIDENCE = {
    "pinnacle": 1.0,       # Gold standard - no discount
    "fanduel": 0.75,       # 25% EV discount - lines are less sharp
}

# Readable names for DFS bookmakers
DFS_BOOK_NAMES = {
    "prizepicks": "PrizePicks",
    "underdog": "Underdog",
    "betr_us_dfs": "Betr",
    "pick6": "DK Pick6",
}

# Supported Sports - Dictionary mapping readable names to API keys
SPORTS_MAP = {
    "NBA": "basketball_nba",
    "NCAAB": "basketball_ncaab",
    "NFL": "americanfootball_nfl",
    "NCAAF": "americanfootball_ncaaf",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
}

# Legacy list for backwards compatibility
SUPPORTED_SPORTS = list(SPORTS_MAP.values())
