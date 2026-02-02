import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ev_engine.log'),
        logging.StreamHandler()
    ]
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
DFS_BOOKMAKERS = ["prizepicks", "underdog", "betr_us_dfs", "pick6"]

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
