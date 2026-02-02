# The Odds API Integration Guide

## Overview

### What is The Odds API

[The Odds API](https://the-odds-api.com/) is a real-time sports betting data provider that aggregates odds from multiple bookmakers worldwide. It delivers sports betting lines, player props, game odds, and other betting markets through a simple RESTful API.

### Why We Use It

EV Engine uses The Odds API to obtain real-time sports betting odds for two critical purposes:

1. **Sharp Market Reference** - Pinnacle odds serve as our "fair market" baseline. Pinnacle is known as one of the sharpest (most efficient) sportsbooks with minimal vig and accurate probability assessments.

2. **DFS Comparison** - We compare Pinnacle's fair odds against DFS platforms (PrizePicks, Underdog, Betr, DK Pick6) to identify +EV (positive expected value) betting opportunities.

### Official Documentation

- API Docs: https://the-odds-api.com/liveapi/guides/v4/
- API Dashboard: https://the-odds-api.com/account/

---

## API Key Setup

### How to Get a Free API Key

1. Visit https://the-odds-api.com/
2. Click "Get API Key" or "Sign Up"
3. Create a free account with your email
4. Verify your email address
5. Access your API key from the dashboard at https://the-odds-api.com/account/

### Quota Limits

**Free Tier:**
- 500 requests per month
- Resets on the 1st of each month
- No rate limiting (but be mindful of quota)

**Paid Tiers:**
- Starting at $25/month for 10,000 requests
- Higher tiers available for professional use

### Setting Up the .env File

Create a `.env` file in the project root:

```bash
ODDS_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with your actual API key from the dashboard.

### Environment Variable Configuration

The application automatically loads environment variables from `.env` using `python-dotenv`:

```python
# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
```

**Security Note:** Never commit your `.env` file to version control. It's already included in `.gitignore`.

---

## Supported Sports

EV Engine supports the following sports, prioritizing those with active DFS markets:

| Sport Display Name | API Key (`sport_key`) | Typical Season | Available Markets |
|-------------------|----------------------|----------------|-------------------|
| NBA | `basketball_nba` | October - June | Player props, H2H, spreads, totals |
| NCAAB (College Basketball) | `basketball_ncaab` | November - April | Player props, H2H, spreads, totals |
| NFL | `americanfootball_nfl` | September - February | Player props, H2H, spreads, totals |
| NCAAF (College Football) | `americanfootball_ncaaf` | August - January | Player props, H2H, spreads, totals |
| MLB | `baseball_mlb` | March - October | Player props, H2H, spreads, totals |
| NHL | `icehockey_nhl` | October - June | Player props, H2H, spreads, totals |

**Configuration:**

```python
# src/config.py
SPORTS_MAP = {
    "NBA": "basketball_nba",
    "NCAAB": "basketball_ncaab",
    "NFL": "americanfootball_nfl",
    "NCAAF": "americanfootball_ncaaf",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
}

SUPPORTED_SPORTS = list(SPORTS_MAP.values())
```

---

## Markets & Odds Types

### Player Props (Primary Focus)

Player proposition bets focus on individual player performance:

| Market Key | Description | Example |
|-----------|-------------|---------|
| `player_points` | Points scored | LeBron James Over 25.5 points |
| `player_rebounds` | Total rebounds | Joel Embiid Over 10.5 rebounds |
| `player_assists` | Total assists | Chris Paul Over 8.5 assists |
| `player_threes` | Three-pointers made | Stephen Curry Over 4.5 threes |
| `player_blocks` | Blocks | Anthony Davis Over 2.5 blocks |
| `player_steals` | Steals | Marcus Smart Over 1.5 steals |
| `player_turnovers` | Turnovers | Russell Westbrook Over 3.5 turnovers |
| `player_points_rebounds_assists` | Combined PRA | Luka Doncic Over 45.5 PRA |

### Other Markets

| Market Type | Market Key | Description |
|------------|-----------|-------------|
| Head-to-Head | `h2h` | Moneyline (straight winner) |
| Spreads | `spreads` | Point spread betting |
| Totals | `totals` | Over/Under total points |

### What Markets EV Engine Uses

**Current Implementation:**

```python
# src/odds_api.py (line 339)
prop_markets = "player_points,player_assists,player_threes"
```

We currently focus on:
- **player_points** - Most liquid market
- **player_assists** - High correlation with game flow
- **player_threes** - Popular DFS market

**Why These Markets?**
1. High liquidity on both Pinnacle and DFS books
2. Available for most games
3. Lower correlation between players (better for parlays)
4. Popular on DFS platforms

---

## Bookmakers

### Tracked Bookmakers

| Bookmaker Key | Display Name | Type | Why We Use It |
|--------------|-------------|------|---------------|
| `pinnacle` | Pinnacle | Sharp/Sportsbook | **Reference odds** - Known as the sharpest book, minimal vig (~2%), fastest to move on new information. We use Pinnacle as our "fair market" baseline. |
| `prizepicks` | PrizePicks | DFS Platform | Largest DFS platform by volume, offers 2-6 leg parlays with fixed payouts |
| `underdog` | Underdog Fantasy | DFS Platform | Second-largest DFS platform, known for competitive lines |
| `betr_us_dfs` | Betr | DFS Platform | Newer DFS platform, sometimes offers softer lines |
| `pick6` | DK Pick6 | DFS Platform | DraftKings' DFS offering, backed by major sportsbook |

### Configuration

```python
# src/config.py
SHARP_BOOKMAKER = "pinnacle"
DFS_BOOKMAKERS = ["prizepicks", "underdog", "betr_us_dfs", "pick6"]

DFS_BOOK_NAMES = {
    "prizepicks": "PrizePicks",
    "underdog": "Underdog",
    "betr_us_dfs": "Betr",
    "pick6": "DK Pick6",
}
```

### Why We Use Each Bookmaker

**Pinnacle (Sharp Reference)**
- Industry-leading accuracy
- Minimal vig (typically 2% vs 5-10% at other books)
- Welcomes sharp bettors (doesn't limit winners)
- Fastest to react to news/injuries
- Used to calculate "fair" probabilities after vig removal

**DFS Platforms**
- Fixed payout structures (3x, 6x, 10x, etc.)
- Often slower to move lines than sportsbooks
- Player prop focus aligns with DFS audience
- Legal in more jurisdictions than traditional sportsbooks

---

## API Endpoints Used

### 1. Get List of Sports

**Endpoint:** `GET /sports`

**Purpose:** Retrieve all available sports and their current status (active/inactive)

**URL Structure:**
```
https://api.the-odds-api.com/v4/sports?apiKey=YOUR_API_KEY
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `apiKey` | Yes | Your API key |

**Example Request:**
```bash
curl "https://api.the-odds-api.com/v4/sports?apiKey=YOUR_API_KEY"
```

**Example Response:**
```json
[
  {
    "key": "basketball_nba",
    "group": "Basketball",
    "title": "NBA",
    "description": "US Basketball",
    "active": true,
    "has_outrights": false
  },
  {
    "key": "americanfootball_nfl",
    "group": "American Football",
    "title": "NFL",
    "description": "US Football",
    "active": true,
    "has_outrights": false
  }
]
```

**Rate Limiting Impact:** 1 request per call

**Usage in Code:**
```python
# src/odds_api.py
def get_sports() -> list[dict]:
    """Fetch all available sports from the API."""
    return _make_request("sports")
```

---

### 2. Get Upcoming Events

**Endpoint:** `GET /sports/{sport}/events`

**Purpose:** Get upcoming games/events for a specific sport

**URL Structure:**
```
https://api.the-odds-api.com/v4/sports/{sport_key}/events?apiKey=YOUR_API_KEY
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `apiKey` | Yes | Your API key |

**Example Request:**
```bash
curl "https://api.the-odds-api.com/v4/sports/basketball_nba/events?apiKey=YOUR_API_KEY"
```

**Example Response:**
```json
[
  {
    "id": "8b3e93c4f5d1e2a9b7c6d0e1f2a3b4c5",
    "sport_key": "basketball_nba",
    "sport_title": "NBA",
    "commence_time": "2026-02-02T01:00:00Z",
    "home_team": "Los Angeles Lakers",
    "away_team": "Golden State Warriors"
  },
  {
    "id": "7a2d82b3c4d5e6f7g8h9i0j1k2l3m4n5",
    "sport_key": "basketball_nba",
    "sport_title": "NBA",
    "commence_time": "2026-02-02T04:30:00Z",
    "home_team": "Boston Celtics",
    "away_team": "Miami Heat"
  }
]
```

**Rate Limiting Impact:** 1 request per call (lightweight, minimal quota impact)

**Usage in Code:**
```python
# src/odds_api.py
def get_events(sport_key: str) -> list[dict]:
    """Fetch upcoming events for a given sport."""
    return _make_request(f"sports/{sport_key}/events")
```

---

### 3. Get Odds for Events

**Endpoint:** `GET /sports/{sport}/events/{event_id}/odds`

**Purpose:** Get player props and odds for a specific event

**URL Structure:**
```
https://api.the-odds-api.com/v4/sports/{sport_key}/events/{event_id}/odds
```

**Parameters:**
| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `apiKey` | Yes | Your API key | - |
| `markets` | Yes | Comma-separated market keys | `player_points,player_assists,player_threes` |
| `oddsFormat` | No | Format for odds | `american` (default: `decimal`) |
| `bookmakers` | No | Filter specific bookmakers | `pinnacle,prizepicks,underdog` |

**Example Request:**
```bash
curl "https://api.the-odds-api.com/v4/sports/basketball_nba/events/8b3e93c4f5d1e2a9b7c6d0e1f2a3b4c5/odds?\
apiKey=YOUR_API_KEY&\
markets=player_points,player_assists&\
oddsFormat=american&\
bookmakers=pinnacle,prizepicks"
```

**Example Response:**
```json
[
  {
    "id": "8b3e93c4f5d1e2a9b7c6d0e1f2a3b4c5",
    "sport_key": "basketball_nba",
    "sport_title": "NBA",
    "commence_time": "2026-02-02T01:00:00Z",
    "home_team": "Los Angeles Lakers",
    "away_team": "Golden State Warriors",
    "bookmakers": [
      {
        "key": "pinnacle",
        "title": "Pinnacle",
        "last_update": "2026-02-01T18:30:00Z",
        "markets": [
          {
            "key": "player_points",
            "outcomes": [
              {
                "name": "Over",
                "description": "LeBron James",
                "price": -115,
                "point": 25.5
              },
              {
                "name": "Under",
                "description": "LeBron James",
                "price": -105,
                "point": 25.5
              }
            ]
          }
        ]
      },
      {
        "key": "prizepicks",
        "title": "PrizePicks",
        "last_update": "2026-02-01T18:28:00Z",
        "markets": [
          {
            "key": "player_points",
            "outcomes": [
              {
                "name": "Over",
                "description": "LeBron James",
                "price": 100,
                "point": 24.5
              },
              {
                "name": "Under",
                "description": "LeBron James",
                "price": -100,
                "point": 24.5
              }
            ]
          }
        ]
      }
    ]
  }
]
```

**Rate Limiting Impact:** 1 request per call (this is the main quota consumer)

**Usage in Code:**
```python
# src/odds_api.py
def get_player_props(
    sport_key: str,
    event_id: str,
    markets: str,
    bookmakers: Optional[str] = None,
) -> list[dict]:
    """Fetch player prop odds for a specific event."""
    params = {
        "markets": markets,
        "oddsFormat": "american",
    }
    if bookmakers:
        params["bookmakers"] = bookmakers

    return _make_request(f"sports/{sport_key}/events/{event_id}/odds", params)
```

---

## Request Flow

EV Engine follows this workflow when fetching and analyzing odds:

```
1. Check In-Season Sports
   ├─> GET /sports
   └─> Filter for active=true sports in SUPPORTED_SPORTS

2. Get Events for Each Sport
   ├─> GET /sports/{sport_key}/events
   └─> Filter events by time window (12 hours)

3. For Each Qualifying Event
   ├─> GET /sports/{sport_key}/events/{event_id}/odds
   │   ├─> markets=player_points,player_assists,player_threes
   │   └─> bookmakers=pinnacle,prizepicks,underdog,betr_us_dfs,pick6
   │
   ├─> Parse Response
   │   ├─> Validate structure (4-tier validation)
   │   ├─> Extract player props
   │   └─> Type-safe conversions
   │
   ├─> Calculate EV
   │   ├─> Get Pinnacle Over/Under odds
   │   ├─> Remove vig (devig_pinnacle_odds)
   │   ├─> Calculate fair probability
   │   └─> Compare vs DFS implied breakeven (54.25%)
   │
   └─> Save to Database
       ├─> insert_odds_batch() - Raw odds
       └─> insert_bet() - +EV opportunities

4. Display Results
   └─> Dashboard shows top 200 opportunities ranked by EV%
```

### Detailed Flow Diagram

```
┌─────────────────────────────────────┐
│  fetch_odds()                       │
│  (src/odds_api.py:296)              │
└──────────────┬──────────────────────┘
               │
               ├──> get_sports()
               │    └─> Filter: active=True & in SUPPORTED_SPORTS
               │
               ├──> For each in-season sport:
               │    │
               │    ├──> get_events(sport_key)
               │    │
               │    └──> For each event:
               │         │
               │         ├──> Parse commence_time
               │         │
               │         ├──> Time Filter Check:
               │         │    ├─> Already started? → Skip
               │         │    └─> >12 hours away? → Skip
               │         │
               │         ├──> get_player_props()
               │         │    ├─> markets: player_points,player_assists,player_threes
               │         │    └─> bookmakers: pinnacle + DFS books
               │         │
               │         ├──> _parse_props_response()
               │         │    ├─> 4-Tier Validation
               │         │    ├─> Type-Safe Extraction
               │         │    └─> Build records list
               │         │
               │         ├──> insert_odds_batch()
               │         │
               │         └──> _find_and_save_ev_opportunities()
               │              ├─> Group by (player, market, line)
               │              ├─> Find Pinnacle reference
               │              ├─> devig_pinnacle_odds()
               │              ├─> calculate_ev_percentage()
               │              └─> insert_bet() for each DFS book
               │
               └──> Return total_odds_count
```

---

## Rate Limiting & Quota Management

### Free Tier Constraints

**500 requests/month** sounds generous, but fills up quickly:

```
Example Usage (Single Sport):
├─ 1 request: GET /sports (check active sports)
├─ 1 request: GET /sports/basketball_nba/events (get games)
└─ 10 requests: GET player props (one per game)
────────────────────────────────────────────────
Total: 12 requests to scan 10 NBA games

Daily scan of 6 sports with 10 games each:
├─ 6 × 12 = 72 requests/day
└─ 72 × 30 = 2,160 requests/month (exceeds quota!)
```

### How EV Engine Manages Quota

**1. Time-Based Filtering (12-Hour Window)**

Only fetch props for games starting within 12 hours:

```python
# src/odds_api.py (line 342-383)
now = datetime.now(timezone.utc)
cutoff_time = now + timedelta(hours=12)

for event in events:
    event_time = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))

    # Skip games already started
    if event_time < now:
        continue

    # Skip games more than 12 hours away
    if event_time > cutoff_time:
        continue

    # Only fetch if within window
    fetch_player_props(event_id)
```

**Why 12 hours?**
- Odds are most stable closer to game time
- Lines tend to be sharper (more accurate)
- Reduces wasted API calls on games days away
- Typical usage: 2-5 games per sport per refresh

**2. In-Season Sport Filtering**

Only query sports that are currently active:

```python
# src/odds_api.py (line 321-325)
all_sports = get_sports()  # 1 request
in_season_sports = [
    sport["key"] for sport in all_sports
    if sport.get("active", False) and sport["key"] in target_sports
]
```

**Impact:**
- Filters out NFL in July, MLB in January, etc.
- Typically 2-4 sports active at once
- Saves ~50% of potential requests

**3. Efficient Batching**

Fetch multiple markets in one request:

```python
# Single request fetches all markets:
markets = "player_points,player_assists,player_threes"
bookmakers = "pinnacle,prizepicks,underdog,betr_us_dfs,pick6"

get_player_props(event_id, markets, bookmakers)
# Returns ALL markets and books in ONE response
```

**vs Inefficient Approach:**
```python
# DON'T DO THIS (uses 3x quota):
get_player_props(event_id, "player_points")
get_player_props(event_id, "player_assists")
get_player_props(event_id, "player_threes")
```

### Monitoring API Usage

Check remaining quota programmatically:

```python
# src/odds_api.py (line 275)
from src.odds_api import get_api_usage

usage = get_api_usage()
print(f"Remaining: {usage['requests_remaining']}")
print(f"Used: {usage['requests_used']}")
```

Or via the dashboard:
```
https://the-odds-api.com/account/
```

### What Happens When Quota is Exhausted

**API Response:**
```json
{
  "status": 429,
  "message": "You have exceeded your request quota"
}
```

**EV Engine Handling:**
```python
# src/odds_api.py (line 60)
if response.status_code == 429:
    raise OddsAPIError("429 Quota Exceeded - API rate limit reached. Wait or upgrade plan.")
```

**Options:**
1. Wait until next month (quota resets on the 1st)
2. Upgrade to paid tier ($25/month = 10,000 requests)
3. Reduce refresh frequency
4. Narrow time window further (e.g., 6 hours instead of 12)

---

## Response Validation

EV Engine implements a **4-tier validation system** to ensure data integrity:

### Tier 1: Odds Response Validation

Validates top-level event structure:

```python
# src/validation.py (line 9)
def validate_odds_response(data: Dict[str, Any]) -> bool:
    """Validate odds API response structure."""
    required_fields = ['id', 'sport_key', 'commence_time', 'bookmakers']

    if not isinstance(data, dict):
        logger.error("Odds response is not a dictionary")
        return False

    for field in required_fields:
        if field not in data:
            logger.error(f"Missing required field: {field}")
            return False

    if not isinstance(data.get('bookmakers'), list):
        logger.error("Bookmakers field is not a list")
        return False

    return True
```

**Checks:**
- Response is a dictionary
- Contains `id`, `sport_key`, `commence_time`, `bookmakers`
- `bookmakers` is a list

---

### Tier 2: Bookmaker Data Validation

Validates each bookmaker's structure:

```python
# src/validation.py (line 38)
def validate_bookmaker_data(bookmaker: Dict[str, Any]) -> bool:
    """Validate individual bookmaker data structure."""
    required_fields = ['key', 'markets']

    if not isinstance(bookmaker, dict):
        return False

    for field in required_fields:
        if field not in bookmaker:
            logger.warning(f"Bookmaker missing field: {field}")
            return False

    if not isinstance(bookmaker.get('markets'), list):
        logger.warning("Bookmaker markets field is not a list")
        return False

    return True
```

**Checks:**
- Bookmaker has `key` (e.g., "pinnacle")
- Bookmaker has `markets` list

---

### Tier 3: Market Data Validation

Validates each market's structure:

```python
# src/validation.py (line 64)
def validate_market_data(market: Dict[str, Any]) -> bool:
    """Validate market data structure."""
    required_fields = ['key', 'outcomes']

    if not isinstance(market, dict):
        return False

    for field in required_fields:
        if field not in market:
            return False

    if not isinstance(market.get('outcomes'), list):
        return False

    return True
```

**Checks:**
- Market has `key` (e.g., "player_points")
- Market has `outcomes` list

---

### Tier 4: Outcome Data Validation

Validates individual outcome (player prop):

```python
# src/validation.py (line 88)
def validate_outcome_data(outcome: Dict[str, Any]) -> bool:
    """Validate outcome data structure."""
    required_fields = ['name', 'price']

    if not isinstance(outcome, dict):
        return False

    for field in required_fields:
        if field not in outcome:
            return False

    # Validate price is numeric
    try:
        float(outcome['price'])
    except (ValueError, TypeError):
        logger.warning(f"Invalid price value: {outcome.get('price')}")
        return False

    return True
```

**Checks:**
- Outcome has `name` (e.g., "Over")
- Outcome has `price`
- Price is numeric

---

### Type-Safe Extraction

After validation, data is extracted with type-safe utilities:

```python
# src/odds_api.py (line 213-241)
from src.type_safety import (
    safe_dict_get,
    safe_int,
    safe_float,
    validate_american_odds,
    validate_line_value,
)

# Extract with validation
player_name = safe_dict_get(outcome, "description", expected_type=str)
selection = safe_dict_get(outcome, "name", expected_type=str)
price_raw = outcome.get("price")
point_raw = outcome.get("point")

if all([player_name, selection, price_raw is not None, point_raw is not None]):
    try:
        price = safe_int(price_raw)
        validate_american_odds(price)  # Ensures valid American odds format

        point = safe_float(point_raw)
        validate_line_value(point)  # Ensures reasonable line value

        # Safe to use now
        records.append({...})
    except ValueError as e:
        logger.warning(f"Invalid data: {e}")
        continue
```

---

### How Invalid Data is Handled

**Validation Failures:**
1. **Log warning** with context (player, market, bookmaker)
2. **Skip the invalid record** (continue to next)
3. **Don't fail the entire request** (graceful degradation)

**Example Logs:**
```
2026-02-01 18:30:00 - ev_engine - WARNING - Skipping invalid bookmaker data for event 8b3e93c4...
2026-02-01 18:30:05 - ev_engine - WARNING - Invalid Pinnacle odds for LeBron James player_points: Expected integer, got 'N/A'
```

**Philosophy:**
- Be strict about data types
- Be lenient about missing data (not all books offer all props)
- Never crash on bad data
- Always log for debugging

---

## Error Handling

### HTTP Error Codes

The Odds API returns standard HTTP status codes:

#### 401 Unauthorized

**Meaning:** Invalid or missing API key

**API Response:**
```json
{
  "message": "Invalid API key"
}
```

**EV Engine Handling:**
```python
# src/odds_api.py (line 58)
if response.status_code == 401:
    raise OddsAPIError("401 Unauthorized - Invalid API key. Check your ODDS_API_KEY in .env")
```

**Solutions:**
- Verify API key in `.env` file
- Check for extra spaces or quotes
- Regenerate key from dashboard

---

#### 403 Forbidden

**Meaning:** API key valid but not authorized for this endpoint

**Rare - usually means:**
- Trying to access premium data on free tier
- Account suspended

**Solution:**
- Contact The Odds API support

---

#### 429 Too Many Requests

**Meaning:** Monthly quota exceeded or rate limit hit

**API Response:**
```json
{
  "message": "You have exceeded your request quota"
}
```

**EV Engine Handling:**
```python
# src/odds_api.py (line 60)
elif response.status_code == 429:
    raise OddsAPIError("429 Quota Exceeded - API rate limit reached. Wait or upgrade plan.")
```

**Solutions:**
- Wait until next month (resets on 1st)
- Upgrade to paid tier
- Reduce polling frequency

---

#### 500 Server Error

**Meaning:** API internal error (rare)

**EV Engine Handling:**
```python
# src/odds_api.py (line 62)
elif response.status_code != 200:
    raise OddsAPIError(f"API request failed with status {response.status_code}: {response.text}")
```

**Solutions:**
- Retry after a few minutes
- Check The Odds API status page
- Contact support if persistent

---

### Network Errors

**Timeout Errors:**

```python
# src/odds_api.py (line 56)
response = requests.get(url, params=default_params, timeout=30)
```

If request takes >30 seconds, raises `requests.exceptions.Timeout`

**Connection Errors:**

- `requests.exceptions.ConnectionError` - Network unavailable
- `requests.exceptions.RequestException` - Generic network error

**Handling:**

```python
try:
    odds_data = get_player_props(sport_key, event_id, markets)
except OddsAPIError as e:
    logger.error(f"API error: {e}", exc_info=True)
    # Continue to next event, don't crash
    continue
```

---

### Error Logging

All errors are logged to both file and console:

```python
# src/config.py (line 8)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ev_engine.log'),
        logging.StreamHandler()
    ]
)
```

**Example Log Output:**
```
2026-02-01 18:30:00 - ev_engine - ERROR - API error for basketball_nba: 429 Quota Exceeded
2026-02-01 18:30:00 - ev_engine - ERROR - Failed to fetch props for Lakers @ Warriors: API request failed with status 500
```

---

### Retry Strategies

**Current Implementation:**

No automatic retries (to preserve quota). Failed requests are logged and skipped.

**For Production:**

Consider implementing exponential backoff for 5xx errors:

```python
import time
from requests.exceptions import RequestException

def _make_request_with_retry(endpoint, params=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            return _make_request(endpoint, params)
        except OddsAPIError as e:
            if "500" in str(e) and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Retry {attempt+1}/{max_retries} after {wait_time}s")
                time.sleep(wait_time)
            else:
                raise
```

**Note:** Don't retry 401, 403, or 429 errors (they won't succeed).

---

## Data Freshness

### How Often to Refresh Odds

Odds change frequently based on:
- Betting volume (sharp money moves lines)
- News (injuries, lineup changes)
- Time to game (lines sharpen closer to start)

**Recommended Refresh Intervals:**

| Time Until Game | Refresh Frequency | Reason |
|----------------|-------------------|---------|
| >24 hours | Every 4-6 hours | Lines still soft, minimal value |
| 12-24 hours | Every 2-4 hours | Lines starting to sharpen |
| 6-12 hours | Every 1-2 hours | Active betting, lines moving |
| 2-6 hours | Every 30-60 min | Prime time for +EV opportunities |
| <2 hours | Every 15-30 min | Lines very sharp, last-minute value |

**Current Implementation:**

Manual refresh via dashboard "Refresh Market" button.

**For Automation:**

```python
import schedule
import time

def job():
    from src.odds_api import fetch_odds
    fetch_odds()
    print(f"Refreshed at {datetime.now()}")

# Refresh every 2 hours
schedule.every(2).hours.do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

### Time Filtering Rationale

**12-Hour Window** balances:

1. **Data Relevance** - Odds 24+ hours out are less accurate
2. **API Quota** - Fewer games = fewer requests
3. **Actionable Opportunities** - Most DFS entries close near game time

**Alternative Windows:**

```python
# Conservative (save quota)
cutoff_time = now + timedelta(hours=6)

# Aggressive (more opportunities, uses more quota)
cutoff_time = now + timedelta(hours=24)
```

**Adjust in code:**
```python
# src/odds_api.py (line 343)
cutoff_time = now + timedelta(hours=12)  # Change this value
```

---

## Example API Calls

### 1. Getting Sports List

**cURL Command:**

```bash
curl -X GET "https://api.the-odds-api.com/v4/sports?apiKey=YOUR_API_KEY"
```

**Python Code:**

```python
import requests

response = requests.get(
    "https://api.the-odds-api.com/v4/sports",
    params={"apiKey": "YOUR_API_KEY"}
)

sports = response.json()
for sport in sports:
    if sport.get("active"):
        print(f"{sport['title']} ({sport['key']}) - Active")
```

**Example Response:**

```json
[
  {
    "key": "basketball_nba",
    "group": "Basketball",
    "title": "NBA",
    "description": "US Basketball",
    "active": true,
    "has_outrights": false
  },
  {
    "key": "baseball_mlb",
    "group": "Baseball",
    "title": "MLB",
    "description": "US Baseball",
    "active": false,
    "has_outrights": false
  }
]
```

---

### 2. Getting Events for NBA

**cURL Command:**

```bash
curl -X GET "https://api.the-odds-api.com/v4/sports/basketball_nba/events?apiKey=YOUR_API_KEY"
```

**Python Code:**

```python
import requests
from datetime import datetime, timezone, timedelta

response = requests.get(
    "https://api.the-odds-api.com/v4/sports/basketball_nba/events",
    params={"apiKey": "YOUR_API_KEY"}
)

events = response.json()
now = datetime.now(timezone.utc)
cutoff = now + timedelta(hours=12)

for event in events:
    commence = datetime.fromisoformat(event['commence_time'].replace("Z", "+00:00"))
    hours_until = (commence - now).total_seconds() / 3600

    if now < commence < cutoff:
        print(f"{event['away_team']} @ {event['home_team']}")
        print(f"  Starts in {hours_until:.1f} hours")
        print(f"  Event ID: {event['id']}\n")
```

**Example Response:**

```json
[
  {
    "id": "8b3e93c4f5d1e2a9b7c6d0e1f2a3b4c5",
    "sport_key": "basketball_nba",
    "sport_title": "NBA",
    "commence_time": "2026-02-02T01:00:00Z",
    "home_team": "Los Angeles Lakers",
    "away_team": "Golden State Warriors"
  },
  {
    "id": "7a2d82b3c4d5e6f7g8h9i0j1k2l3m4n5",
    "sport_key": "basketball_nba",
    "sport_title": "NBA",
    "commence_time": "2026-02-02T04:30:00Z",
    "home_team": "Boston Celtics",
    "away_team": "Miami Heat"
  }
]
```

---

### 3. Getting Player Props

**cURL Command:**

```bash
curl -X GET "https://api.the-odds-api.com/v4/sports/basketball_nba/events/8b3e93c4f5d1e2a9b7c6d0e1f2a3b4c5/odds?\
apiKey=YOUR_API_KEY&\
markets=player_points,player_assists,player_threes&\
oddsFormat=american&\
bookmakers=pinnacle,prizepicks,underdog"
```

**Python Code:**

```python
import requests

event_id = "8b3e93c4f5d1e2a9b7c6d0e1f2a3b4c5"

response = requests.get(
    f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds",
    params={
        "apiKey": "YOUR_API_KEY",
        "markets": "player_points,player_assists,player_threes",
        "oddsFormat": "american",
        "bookmakers": "pinnacle,prizepicks,underdog"
    }
)

data = response.json()

# Parse response
for event in data:
    for bookmaker in event['bookmakers']:
        book_name = bookmaker['key']
        for market in bookmaker['markets']:
            market_key = market['key']
            for outcome in market['outcomes']:
                player = outcome['description']
                side = outcome['name']
                line = outcome['point']
                odds = outcome['price']

                print(f"{book_name}: {player} {market_key} {side} {line} ({odds:+d})")
```

**Example Response (Abbreviated):**

```json
[
  {
    "id": "8b3e93c4f5d1e2a9b7c6d0e1f2a3b4c5",
    "sport_key": "basketball_nba",
    "commence_time": "2026-02-02T01:00:00Z",
    "bookmakers": [
      {
        "key": "pinnacle",
        "markets": [
          {
            "key": "player_points",
            "outcomes": [
              {
                "name": "Over",
                "description": "LeBron James",
                "price": -115,
                "point": 25.5
              },
              {
                "name": "Under",
                "description": "LeBron James",
                "price": -105,
                "point": 25.5
              }
            ]
          },
          {
            "key": "player_assists",
            "outcomes": [
              {
                "name": "Over",
                "description": "LeBron James",
                "price": -110,
                "point": 7.5
              },
              {
                "name": "Under",
                "description": "LeBron James",
                "price": -110,
                "point": 7.5
              }
            ]
          }
        ]
      },
      {
        "key": "prizepicks",
        "markets": [
          {
            "key": "player_points",
            "outcomes": [
              {
                "name": "Over",
                "description": "LeBron James",
                "price": 100,
                "point": 24.5
              }
            ]
          }
        ]
      }
    ]
  }
]
```

**Output:**

```
pinnacle: LeBron James player_points Over 25.5 (-115)
pinnacle: LeBron James player_points Under 25.5 (-105)
pinnacle: LeBron James player_assists Over 7.5 (-110)
pinnacle: LeBron James player_assists Under 7.5 (-110)
prizepicks: LeBron James player_points Over 24.5 (+100)
```

---

## Troubleshooting

### Issue: API Key Not Working

**Symptoms:**
- `401 Unauthorized` errors
- "Invalid API key" message

**Checklist:**

1. **Verify `.env` file exists:**
   ```bash
   ls -la .env
   ```

2. **Check `.env` contents:**
   ```bash
   cat .env
   ```
   Should show:
   ```
   ODDS_API_KEY=your_actual_key_here
   ```

3. **No extra characters:**
   - No quotes: ~~`ODDS_API_KEY="abc123"`~~
   - No spaces: ~~`ODDS_API_KEY = abc123`~~
   - Correct: `ODDS_API_KEY=abc123`

4. **Regenerate key:**
   - Visit https://the-odds-api.com/account/
   - Generate new API key
   - Update `.env`

5. **Restart application:**
   ```bash
   # Environment variables loaded on startup
   streamlit run dashboard.py
   ```

---

### Issue: No Data Returned

**Symptoms:**
- API calls succeed (200 OK)
- But `bookmakers` array is empty
- Or specific bookmaker missing

**Common Causes:**

**1. Sport Not In Season**

```python
# Check if sport is active
from src.odds_api import get_sports

sports = get_sports()
for sport in sports:
    if sport['key'] == 'baseball_mlb':
        print(f"Active: {sport.get('active')}")
```

**Solution:** Only query active sports

---

**2. No Games in Time Window**

```python
# Check upcoming events
from src.odds_api import get_events

events = get_events('basketball_nba')
print(f"Found {len(events)} upcoming NBA games")
for event in events[:3]:
    print(f"  {event['away_team']} @ {event['home_team']} - {event['commence_time']}")
```

**Solution:** Adjust time window or wait for game day

---

**3. Bookmaker Doesn't Offer Market**

Not all bookmakers offer all markets for all games:

- Pinnacle usually has full coverage
- DFS books may skip low-profile games
- Player props unavailable until ~24 hours before game

**Solution:** Check multiple bookmakers, accept sparse data

---

**4. Player Not Available**

Player may not be in bookmaker's system:
- Recent call-up
- Injury/inactive
- Name spelling mismatch

**Solution:** Check official bookmaker website to verify availability

---

### Issue: Quota Exceeded

**Symptoms:**
- `429 Too Many Requests` errors
- "You have exceeded your request quota" message

**Check Current Usage:**

```python
from src.odds_api import get_api_usage

usage = get_api_usage()
print(f"Requests Used: {usage['requests_used']}")
print(f"Requests Remaining: {usage['requests_remaining']}")
```

**Solutions:**

**1. Wait Until Reset**
- Quota resets on 1st of each month at midnight UTC
- Check: https://the-odds-api.com/account/

**2. Reduce Time Window**
```python
# In src/odds_api.py (line 343)
cutoff_time = now + timedelta(hours=6)  # Down from 12
```

**3. Reduce Sports**
```python
# In dashboard.py or config.py
SUPPORTED_SPORTS = ["basketball_nba"]  # Only NBA
```

**4. Upgrade Plan**
- $25/month = 10,000 requests
- https://the-odds-api.com/account/upgrade

---

### Issue: Timeouts

**Symptoms:**
- `requests.exceptions.Timeout` errors
- Requests hang for 30+ seconds

**Causes:**
- Slow internet connection
- API server overload (rare)
- Large response size

**Solutions:**

**1. Increase Timeout**
```python
# In src/odds_api.py (line 56)
response = requests.get(url, params=default_params, timeout=60)  # Up from 30
```

**2. Reduce Request Size**
```python
# Fetch fewer markets per request
markets = "player_points"  # Instead of "player_points,player_assists,player_threes"
```

**3. Check Network**
```bash
ping api.the-odds-api.com
```

---

## Cost Optimization

### Staying Within Free Tier (500 Requests/Month)

**Strategy 1: Focus on Prime Time**

Only refresh during peak betting windows:

```python
from datetime import datetime

def should_refresh():
    hour = datetime.now().hour
    # Only refresh 2pm - 2am ET (busy betting hours)
    return 14 <= hour or hour <= 2

if should_refresh():
    fetch_odds()
```

**Savings:** ~50% (skip overnight/morning hours)

---

**Strategy 2: Single Sport Focus**

Pick the sport you know best:

```python
# In config.py
SUPPORTED_SPORTS = ["basketball_nba"]
```

**Savings:** ~80% (1 sport vs 6)

---

**Strategy 3: Aggressive Time Window**

Only look at games in next 4-6 hours:

```python
# In src/odds_api.py (line 343)
cutoff_time = now + timedelta(hours=4)
```

**Savings:** ~60-70% (fewer games in window)

---

**Strategy 4: Event-Driven Refreshes**

Instead of polling every hour, refresh only when:
- New lineup news
- Significant line movement detected
- 1 hour before game time

**Savings:** 70-80% (smart vs blind polling)

---

**Combined Strategy Example:**

```
Baseline (unoptimized): 2,160 requests/month
├─ Single sport (NBA): -80% → 432 requests/month
├─ 6-hour window: -60% → 173 requests/month
├─ Prime time only: -50% → 86 requests/month
└─ Event-driven: -70% → 26 requests/month

Result: Well within 500/month quota
```

---

### Tracking Your Usage Pattern

**Log Requests:**

```python
import logging

logger = logging.getLogger('api_usage')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('api_usage.log')
logger.addHandler(handler)

def _make_request(endpoint, params):
    logger.info(f"API Call: {endpoint} | Params: {params}")
    # ... existing code
```

**Analyze Logs:**

```bash
# Count requests by day
grep "API Call" api_usage.log | cut -d' ' -f1 | uniq -c

# Count requests by endpoint
grep "API Call" api_usage.log | cut -d':' -f2 | sort | uniq -c
```

---

## API Updates

### How to Handle API Changes

The Odds API maintains backward compatibility, but may:
- Add new fields to responses
- Introduce new markets
- Deprecate old endpoints (with notice)

**Best Practices:**

1. **Use Defensive Parsing**
   ```python
   # Good - handles missing fields
   player_name = outcome.get("description", "Unknown")

   # Bad - crashes if field missing
   player_name = outcome["description"]
   ```

2. **Validate Response Structure**
   ```python
   # Always validate before accessing nested data
   if validate_odds_response(data):
       # Safe to parse
   ```

3. **Subscribe to API Announcements**
   - Join mailing list at https://the-odds-api.com/
   - Check changelog: https://the-odds-api.com/liveapi/guides/v4/#changelog

---

### Version Compatibility

**Current Version:** v4

**API Base URL:**
```python
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
```

**Migration Notes:**

If The Odds API releases v5:
1. v4 will remain available (deprecated but functional)
2. Review migration guide at https://the-odds-api.com/
3. Test v5 endpoints in development
4. Update `ODDS_API_BASE_URL` when ready

**Code Update:**
```python
# src/config.py
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v5"  # When v5 released
```

---

### Where to Check for Updates

**Official Resources:**

1. **API Documentation**
   - https://the-odds-api.com/liveapi/guides/v4/

2. **Changelog**
   - https://the-odds-api.com/liveapi/guides/v4/#changelog

3. **Status Page**
   - Check for outages: https://status.the-odds-api.com/

4. **Support**
   - Email: contact@the-odds-api.com
   - Response time: Usually within 24 hours

**Community:**

- Reddit: r/sportsbetting, r/sportsbook
- Twitter: Follow @the_odds_api
- Discord: Various sports betting communities

---

## Additional Resources

### Quick Reference

**Key Files:**
- `/Users/pbrow2/apps/ev-engine/src/odds_api.py` - API client implementation
- `/Users/pbrow2/apps/ev-engine/src/config.py` - Configuration and constants
- `/Users/pbrow2/apps/ev-engine/src/validation.py` - Response validation
- `/Users/pbrow2/apps/ev-engine/src/analysis.py` - EV calculation math

**Key Functions:**
```python
from src.odds_api import (
    get_sports,           # List available sports
    get_events,           # Get upcoming games
    get_player_props,     # Fetch player prop odds
    fetch_odds,           # Main orchestrator
    get_api_usage,        # Check quota
)

from src.analysis import (
    calculate_implied_probability,  # Convert odds → probability
    devig_pinnacle_odds,            # Remove vig
    calculate_ev_percentage,        # Calculate EV%
)
```

---

### Related Documentation

- **BLUEPRINT.md** - Technical architecture and mathematical approach
- **UI_SPEC.md** - Dashboard features and user interface
- **TESTING.md** - Test suite and validation coverage
- **TYPE_SAFETY_QUICK_REFERENCE.md** - Type-safe utilities

---

### Support & Feedback

**For EV Engine Issues:**
- Check logs: `ev_engine.log`
- Review test suite: `pytest tests/`

**For API Issues:**
- Contact The Odds API: contact@the-odds-api.com
- Include: API key (first 6 chars), timestamp, endpoint, error message

---

## Summary

**The Odds API provides:**
- Real-time sports betting odds
- Player props from multiple bookmakers
- Reliable uptime and data quality

**EV Engine uses it to:**
- Get sharp reference odds (Pinnacle)
- Compare against DFS platforms
- Identify +EV betting opportunities
- Track and analyze performance

**Key Takeaways:**
1. **500 requests/month** on free tier - manage wisely
2. **Time-based filtering** reduces quota consumption
3. **4-tier validation** ensures data integrity
4. **Graceful error handling** prevents crashes
5. **Type-safe extraction** catches bad data early

**Next Steps:**
1. Get your API key: https://the-odds-api.com/
2. Configure `.env` file
3. Run `streamlit run dashboard.py`
4. Click "Refresh Market" to fetch odds
5. Review +EV opportunities

Happy betting!
