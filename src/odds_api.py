"""The Odds API client for fetching sports betting data."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from .config import (
    ODDS_API_KEY,
    ODDS_API_BASE_URL,
    SUPPORTED_SPORTS,
    SPORTS_MAP,
    SHARP_BOOKMAKER,
    FALLBACK_SHARP_BOOKMAKER,
    DFS_BOOKMAKERS,
    DFS_BOOK_NAMES,
    SHARP_CONFIDENCE,
    logger,
)
from .db import insert_odds_batch
from .analysis import (
    calculate_implied_probability,
    devig_pinnacle_odds,
    calculate_ev_percentage,
)
from .validation import (
    validate_odds_response,
    validate_bookmaker_data,
    validate_market_data,
    validate_outcome_data,
)
from .type_safety import (
    safe_dict_get,
    safe_int,
    safe_float,
    safe_list_get,
    validate_american_odds,
    validate_line_value,
)


class OddsAPIError(Exception):
    """Custom exception for Odds API errors."""
    pass


def _make_request(endpoint: str, params: Optional[dict] = None) -> dict:
    """Make a request to The Odds API with error handling.

    Internal helper function that handles API authentication, request construction,
    and error handling for all Odds API calls.

    Args:
        endpoint: API endpoint path (e.g., 'sports', 'sports/basketball_nba/odds')
        params: Optional query parameters (API key is added automatically)

    Returns:
        JSON response as dictionary

    Raises:
        OddsAPIError: If API key missing, unauthorized (401), quota exceeded (429),
            or other HTTP errors occur

    Rate Limiting:
        The Odds API has usage limits. Monitor with get_api_usage().
        - 401: Invalid API key
        - 429: Quota exceeded

    Examples:
        >>> data = _make_request('sports')
        >>> print(f"Found {len(data)} sports")

        >>> odds = _make_request('sports/basketball_nba/odds', {
        ...     'markets': 'h2h',
        ...     'regions': 'us'
        ... })
    """
    if not ODDS_API_KEY:
        raise OddsAPIError("ODDS_API_KEY is not set. Please set it in your .env file.")

    url = f"{ODDS_API_BASE_URL}/{endpoint}"
    default_params = {"apiKey": ODDS_API_KEY}

    if params:
        default_params.update(params)

    response = requests.get(url, params=default_params, timeout=30)

    if response.status_code == 401:
        raise OddsAPIError("401 Unauthorized - Invalid API key. Check your ODDS_API_KEY in .env")
    elif response.status_code == 429:
        raise OddsAPIError("429 Quota Exceeded - API rate limit reached. Wait or upgrade plan.")
    elif response.status_code != 200:
        raise OddsAPIError(f"API request failed with status {response.status_code}: {response.text}")

    return response.json()


def get_sports() -> list[dict]:
    """Fetch all available sports from The Odds API.

    Retrieves the list of all sports currently available through the API,
    including their active status and other metadata.

    Returns:
        List of sport dictionaries with keys: key, active, group, title, etc.

    API Endpoint:
        GET /v4/sports

    Rate Limiting:
        Low cost operation, safe to call frequently

    Raises:
        OddsAPIError: If API request fails

    Examples:
        >>> sports = get_sports()
        >>> active_sports = [s for s in sports if s.get('active', False)]
        >>> print(f"Found {len(active_sports)} active sports")
        >>> for sport in active_sports:
        ...     print(f"{sport['key']}: {sport['title']}")
    """
    return _make_request("sports")


def get_events(sport_key: str) -> list[dict]:
    """Fetch upcoming events for a given sport.

    Retrieves the list of upcoming games/matches for a specific sport,
    including event IDs, team names, and start times.

    Args:
        sport_key: Sport identifier (e.g., 'basketball_nba', 'icehockey_nhl')

    Returns:
        List of event dictionaries with keys: id, sport_key, commence_time,
        home_team, away_team

    API Endpoint:
        GET /v4/sports/{sport_key}/events

    Rate Limiting:
        Low cost operation, relatively safe to call

    Raises:
        OddsAPIError: If API request fails

    Examples:
        >>> events = get_events('basketball_nba')
        >>> print(f"Found {len(events)} NBA games")
        >>> for event in events:
        ...     print(f"{event['away_team']} @ {event['home_team']}")
        ...     print(f"  Start: {event['commence_time']}")
    """
    return _make_request(f"sports/{sport_key}/events")


def get_odds(
    sport_key: str,
    markets: str = "h2h",
    regions: str = "us",
    bookmakers: Optional[str] = None,
) -> list[dict]:
    """Fetch odds for a given sport with configurable markets and bookmakers.

    Retrieves betting odds for all upcoming events in a sport. Can filter by
    market type and bookmakers.

    Args:
        sport_key: Sport identifier (e.g., 'basketball_nba')
        markets: Comma-separated market keys (default: 'h2h' for moneyline)
        regions: Comma-separated regions (default: 'us')
        bookmakers: Optional comma-separated bookmaker keys to filter

    Returns:
        List of event dictionaries with odds data including bookmakers, markets,
        and outcomes

    API Endpoint:
        GET /v4/sports/{sport_key}/odds

    Rate Limiting:
        HIGHER cost operation - counts against quota more heavily

    Raises:
        OddsAPIError: If API request fails

    Examples:
        >>> # Get moneyline odds for NBA
        >>> odds = get_odds('basketball_nba', markets='h2h')

        >>> # Get spreads and totals from specific books
        >>> odds = get_odds(
        ...     'basketball_nba',
        ...     markets='spreads,totals',
        ...     bookmakers='pinnacle,fanduel'
        ... )
    """
    params = {
        "markets": markets,
        "regions": regions,
        "oddsFormat": "american",
    }

    if bookmakers:
        params["bookmakers"] = bookmakers

    return _make_request(f"sports/{sport_key}/odds", params)


def get_player_props(
    sport_key: str,
    event_id: str,
    markets: str,
    bookmakers: Optional[str] = None,
) -> list[dict]:
    """Fetch player prop odds for a specific event.

    Retrieves player prop betting markets (points, assists, etc.) for a single
    game. This is the core data source for EV calculations.

    Args:
        sport_key: Sport identifier (e.g., 'basketball_nba')
        event_id: Unique event identifier from get_events()
        markets: Comma-separated player prop markets (e.g., 'player_points,player_assists')
        bookmakers: Optional comma-separated bookmaker keys to filter

    Returns:
        List with single event dictionary containing bookmakers, markets with
        player prop outcomes (each outcome has: description, name, price, point)

    API Endpoint:
        GET /v4/sports/{sport_key}/events/{event_id}/odds

    Rate Limiting:
        HIGH cost operation - main quota consumer. Use sparingly and filter
        by time windows to minimize calls.

    Raises:
        OddsAPIError: If API request fails

    Examples:
        >>> props = get_player_props(
        ...     sport_key='basketball_nba',
        ...     event_id='abc123',
        ...     markets='player_points,player_assists,player_threes',
        ...     bookmakers='pinnacle,prizepicks'
        ... )
        >>> for book in props[0]['bookmakers']:
        ...     for market in book['markets']:
        ...         for outcome in market['outcomes']:
        ...             print(f"{outcome['description']}: {outcome['name']} {outcome['point']}")
    """
    params = {
        "markets": markets,
        "oddsFormat": "american",
    }

    if bookmakers:
        params["bookmakers"] = bookmakers

    return _make_request(f"sports/{sport_key}/events/{event_id}/odds", params)


def fetch_and_store_player_props(
    sport_key: str,
    markets: list[str],
    bookmakers: Optional[list[str]] = None,
) -> int:
    """Fetch player props for all events of a sport and store in database.

    Retrieves player prop odds for all upcoming events in a sport and saves
    them to the odds_snapshot table. Useful for batch data collection.

    Args:
        sport_key: Sport identifier (e.g., 'basketball_nba')
        markets: List of market keys (e.g., ['player_points', 'player_rebounds'])
        bookmakers: List of bookmaker keys to filter (default: Pinnacle + DFS books)

    Returns:
        Total number of odds records inserted into database

    API Calls:
        - 1 call to get_events() for event list
        - N calls to get_player_props() where N = number of events

    Rate Limiting:
        VERY HIGH cost operation - fetches props for ALL events in a sport.
        Can quickly consume API quota. Prefer fetch_odds() which filters by time.

    Raises:
        OddsAPIError: If critical API requests fail (continues on individual errors)

    Examples:
        >>> # Fetch NBA player points and assists props
        >>> count = fetch_and_store_player_props(
        ...     sport_key='basketball_nba',
        ...     markets=['player_points', 'player_assists']
        ... )
        >>> print(f"Stored {count} odds records")
    """
    if bookmakers is None:
        bookmakers = [SHARP_BOOKMAKER, FALLBACK_SHARP_BOOKMAKER] + DFS_BOOKMAKERS

    # Get all upcoming events for the sport
    events = get_events(sport_key)

    if not events:
        return 0

    total_records = 0
    timestamp = datetime.now()
    markets_str = ",".join(markets)
    bookmakers_str = ",".join(bookmakers)

    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue

        try:
            props_data = get_player_props(
                sport_key=sport_key,
                event_id=event_id,
                markets=markets_str,
                bookmakers=bookmakers_str,
            )
        except OddsAPIError:
            continue

        records = _parse_props_response(props_data, sport_key, timestamp)

        if records:
            inserted = insert_odds_batch(records)
            total_records += inserted

    return total_records


def _parse_props_response(
    response: list[dict],
    sport_key: str,
    timestamp: datetime,
) -> list[dict]:
    """Parse the API response and convert to database records.

    Internal function that validates and transforms player prop API responses
    into the standardized database record format. Performs type-safe conversions
    and validation using validation and type_safety modules.

    Args:
        response: List of event dictionaries from API
        sport_key: Sport identifier to include in records
        timestamp: Timestamp to assign to all records

    Returns:
        List of database-ready record dictionaries with keys: event_id, sport_key,
        bookmaker, market_key, player_name, selection, price, point, timestamp

    Validation:
        - Validates odds response structure
        - Validates bookmaker data
        - Validates market data
        - Validates outcome data
        - Validates American odds format
        - Validates line values
        - Skips invalid records with warnings

    Examples:
        >>> from datetime import datetime
        >>> response = [{"id": "abc", "bookmakers": [...]}]
        >>> records = _parse_props_response(response, "basketball_nba", datetime.now())
        >>> print(f"Parsed {len(records)} valid records")
    """
    records = []

    for event_data in response:
        if not isinstance(event_data, dict):
            continue

        # Validate odds response structure
        if not validate_odds_response(event_data):
            logger.warning(f"Skipping invalid event data: {event_data.get('id')}")
            continue

        event_id = event_data.get("id")
        bookmakers_data = event_data.get("bookmakers", [])

        for bookmaker in bookmakers_data:
            # Validate bookmaker data
            if not validate_bookmaker_data(bookmaker):
                logger.warning(f"Skipping invalid bookmaker data for event {event_id}")
                continue

            bookmaker_key = bookmaker.get("key")
            markets_data = bookmaker.get("markets", [])

            for market in markets_data:
                # Validate market data
                if not validate_market_data(market):
                    logger.warning(f"Skipping invalid market data for bookmaker {bookmaker_key}")
                    continue

                market_key = market.get("key")
                outcomes = market.get("outcomes", [])

                for outcome in outcomes:
                    # Validate outcome data
                    if not validate_outcome_data(outcome):
                        logger.warning(f"Skipping invalid outcome data for market {market_key}")
                        continue

                    player_name = safe_dict_get(outcome, "description", expected_type=str)
                    selection = safe_dict_get(outcome, "name", expected_type=str)  # "Over" or "Under"
                    price_raw = outcome.get("price")
                    point_raw = outcome.get("point")

                    if all([player_name, selection, price_raw is not None, point_raw is not None]):
                        # Type-safe conversions with validation
                        try:
                            price = safe_int(price_raw)
                            validate_american_odds(price)
                            point = safe_float(point_raw)
                            validate_line_value(point)

                            records.append({
                                "event_id": event_id,
                                "sport_key": sport_key,
                                "bookmaker": bookmaker_key,
                                "market_key": market_key,
                                "player_name": player_name,
                                "selection": selection,
                                "price": price,
                                "point": point,
                                "timestamp": timestamp,
                            })
                        except ValueError as e:
                            logger.warning(
                                f"Invalid data for {player_name} {selection} in market {market_key}: {e}"
                            )
                            continue

    return records


def fetch_all_sports_props(
    markets: list[str],
    sports: Optional[list[str]] = None,
) -> dict[str, int]:
    """Fetch player props for multiple sports in one operation.

    Convenience function that calls fetch_and_store_player_props() for each
    sport in the list. Returns results summary for all sports.

    Args:
        markets: List of market keys to fetch (e.g., ['player_points', 'player_assists'])
        sports: List of sport keys (default: all supported sports from config)

    Returns:
        Dictionary mapping sport_key to number of records inserted (or error message)
        Example: {'basketball_nba': 1234, 'icehockey_nhl': 567}

    API Calls:
        Very high - calls fetch_and_store_player_props() for each sport

    Rate Limiting:
        EXTREME cost - fetches ALL events for ALL sports. Use with caution!
        Prefer fetch_odds() for production use.

    Examples:
        >>> results = fetch_all_sports_props(
        ...     markets=['player_points'],
        ...     sports=['basketball_nba', 'icehockey_nhl']
        ... )
        >>> for sport, count in results.items():
        ...     print(f"{sport}: {count} records")
    """
    if sports is None:
        sports = SUPPORTED_SPORTS

    results = {}

    for sport_key in sports:
        try:
            count = fetch_and_store_player_props(sport_key, markets)
            results[sport_key] = count
        except OddsAPIError as e:
            results[sport_key] = f"Error: {str(e)}"

    return results


def get_api_usage() -> dict:
    """Check API usage by making a minimal request.

    Makes a low-cost API call to retrieve usage statistics from response headers.
    Useful for monitoring quota consumption and avoiding rate limit errors.

    Returns:
        Dictionary with keys:
        - requests_remaining: Number of requests left in current quota period
        - requests_used: Number of requests used in current quota period

    API Endpoint:
        GET /v4/sports (minimal cost call)

    Raises:
        OddsAPIError: If API key is not set

    Examples:
        >>> usage = get_api_usage()
        >>> print(f"Remaining: {usage['requests_remaining']}")
        >>> print(f"Used: {usage['requests_used']}")
        >>> if int(usage['requests_remaining']) < 100:
        ...     print("Warning: Low on API quota!")
    """
    if not ODDS_API_KEY:
        raise OddsAPIError("ODDS_API_KEY is not set")

    url = f"{ODDS_API_BASE_URL}/sports"
    response = requests.get(
        url,
        params={"apiKey": ODDS_API_KEY},
        timeout=30,
    )

    return {
        "requests_remaining": response.headers.get("x-requests-remaining"),
        "requests_used": response.headers.get("x-requests-used"),
    }


def fetch_odds(sports_to_fetch: Optional[list[str]] = None) -> int:
    """Fetch odds for specified sports and identify +EV opportunities.

    Main entry point for refreshing market data. Fetches player props from
    sharp (Pinnacle) and DFS bookmakers, calculates fair probabilities and
    EV percentages, then saves opportunities to the database.

    Time Filter:
        Only fetches games starting within 12 hours to conserve API quota.
        Games outside this window are skipped with INFO log messages.

    Args:
        sports_to_fetch: List of sport API keys to fetch (e.g., ['basketball_nba']).
            If None, uses all SUPPORTED_SPORTS from config.

    Returns:
        Total number of odds records fetched and stored

    Process Flow:
        1. Initialize database schema
        2. Clear old bet opportunities
        3. Get in-season sports from API
        4. For each sport, get upcoming events
        5. Filter events by 12-hour time window
        6. Fetch player props for filtered events
        7. Parse and store odds in database
        8. Calculate and save +EV opportunities

    API Calls:
        - 1 call to get_sports()
        - N calls to get_events() where N = number of sports
        - M calls to get_player_props() where M = number of games in 12hr window

    Rate Limiting:
        Optimized for quota conservation via time window filtering. Logs skipped
        games with hours-until-start information.

    Examples:
        >>> # Fetch only NBA
        >>> count = fetch_odds(sports_to_fetch=['basketball_nba'])
        >>> print(f"Fetched {count} odds records")

        >>> # Fetch all supported sports
        >>> count = fetch_odds()
    """
    from . import db

    # Ensure bets table exists before any operations
    db.initialize_db()

    # Clear old bets before fetching fresh data
    db.clear_bets()

    # Determine which sports to scan
    target_sports = sports_to_fetch if sports_to_fetch else SUPPORTED_SPORTS

    # Get all sports and filter for in-season ones that match our target
    all_sports = get_sports()
    in_season_sports = [
        sport["key"] for sport in all_sports
        if sport.get("active", False) and sport["key"] in target_sports
    ]

    logger.debug(f"Found {len(in_season_sports)} in-season sports: {in_season_sports}")

    if not in_season_sports:
        logger.info("Fetched 0 odds")
        return 0

    total_odds_count = 0
    timestamp = datetime.now()
    bookmakers = [SHARP_BOOKMAKER, FALLBACK_SHARP_BOOKMAKER] + DFS_BOOKMAKERS
    bookmakers_str = ",".join(bookmakers)

    # Markets to fetch for player props
    prop_markets = "player_points,player_assists,player_threes"

    # Time filter: only fetch games starting within 12 hours
    now = datetime.now(timezone.utc)
    cutoff_time = now + timedelta(hours=12)

    for sport_key in in_season_sports:
        logger.debug(f"Processing {sport_key}")
        try:
            # Get events list (cheap call - doesn't count against quota heavily)
            events = get_events(sport_key)

            if not events:
                logger.debug(f"No events found for {sport_key}")
                continue

            logger.debug(f"Found {len(events)} total events for {sport_key}")

            for event in events:
                event_id = event.get("id")
                event_name = f"{event.get('away_team', '?')} @ {event.get('home_team', '?')}"
                commence_time_str = event.get("commence_time")

                if not event_id or not commence_time_str:
                    continue

                # Parse commence_time (ISO format)
                try:
                    event_time = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
                except ValueError:
                    logger.debug(f"Could not parse time for {event_name}")
                    continue

                # Calculate hours until game
                hours_until = (event_time - now).total_seconds() / 3600

                # Skip games that have already started
                if event_time < now:
                    logger.info(f"Skipping {event_name} (Already started)")
                    continue

                # Skip games more than 12 hours away
                if event_time > cutoff_time:
                    logger.info(f"Skipping {event_name} (Starts in {hours_until:.1f} hours)")
                    continue

                # Game passes filter - fetch props
                logger.info(f"Fetching props for {event_name} (Starts in {hours_until:.1f} hours)")

                try:
                    props_data = get_player_props(
                        sport_key=sport_key,
                        event_id=event_id,
                        markets=prop_markets,
                        bookmakers=bookmakers_str,
                    )

                    if not props_data:
                        continue

                    # Wrap in list if single dict returned
                    if isinstance(props_data, dict):
                        props_data = [props_data]

                    prop_records = _parse_props_response(props_data, sport_key, timestamp)

                    if prop_records:
                        db.insert_odds_batch(prop_records)
                        total_odds_count += len(prop_records)

                        # Check for +EV opportunities and save them
                        _find_and_save_ev_opportunities(prop_records, db)

                except OddsAPIError as e:
                    logger.error(f"Failed to fetch props for {event_name}: {e}", exc_info=True)
                    continue

        except OddsAPIError as e:
            logger.error(f"API error for {sport_key}: {e}", exc_info=True)

    logger.info(f"Fetched {total_odds_count} odds")
    return total_odds_count


def _parse_h2h_response(
    response: list[dict],
    sport_key: str,
    timestamp: datetime,
) -> list[dict]:
    """Parse head-to-head (moneyline) API response into database records.

    Internal function that validates and transforms moneyline odds API responses
    into the standardized database record format.

    Args:
        response: List of event dictionaries from API
        sport_key: Sport identifier to include in records
        timestamp: Timestamp to assign to all records

    Returns:
        List of database-ready record dictionaries with standardized schema

    Validation:
        - Validates odds response structure
        - Validates bookmaker data
        - Validates market data
        - Validates outcome data
        - Skips invalid records with warnings

    Examples:
        >>> from datetime import datetime
        >>> response = [{"id": "abc", "bookmakers": [...]}]
        >>> records = _parse_h2h_response(response, "basketball_nba", datetime.now())
    """
    records = []

    for event_data in response:
        # Validate odds response structure
        if not validate_odds_response(event_data):
            logger.warning(f"Skipping invalid event data: {event_data.get('id')}")
            continue

        event_id = event_data.get("id")
        bookmakers_data = event_data.get("bookmakers", [])

        for bookmaker in bookmakers_data:
            # Validate bookmaker data
            if not validate_bookmaker_data(bookmaker):
                logger.warning(f"Skipping invalid bookmaker data for event {event_id}")
                continue

            bookmaker_key = bookmaker.get("key")
            markets_data = bookmaker.get("markets", [])

            for market in markets_data:
                # Validate market data
                if not validate_market_data(market):
                    logger.warning(f"Skipping invalid market data for bookmaker {bookmaker_key}")
                    continue

                market_key = market.get("key")
                outcomes = market.get("outcomes", [])

                for outcome in outcomes:
                    # Validate outcome data
                    if not validate_outcome_data(outcome):
                        logger.warning(f"Skipping invalid outcome data for market {market_key}")
                        continue

                    team_name = outcome.get("name")
                    price = outcome.get("price")

                    if team_name and price is not None:
                        records.append({
                            "event_id": event_id,
                            "sport_key": sport_key,
                            "bookmaker": bookmaker_key,
                            "market_key": market_key,
                            "player_name": team_name,
                            "selection": "Win",
                            "price": price,
                            "point": 0.0,
                            "timestamp": timestamp,
                        })

    return records


# Implied breakeven probability for 5-Pick Flex
IMPLIED_BREAKEVEN_PROB = 0.5425


def _find_and_save_ev_opportunities(records: list[dict], db) -> int:
    """Find and save Pick-Em opportunities by comparing sharp odds to DFS lines.

    Internal function that analyzes fetched odds to identify positive EV plays.
    Compares sharp bookmaker (Pinnacle preferred, FanDuel fallback) fair probabilities
    against DFS book availability at the same line values.

    Process:
        1. Group records by (player, market, point) to ensure line matching
        2. For each group, check if Pinnacle odds exist; if not, use FanDuel as fallback
        3. Calculate fair probabilities using devig_pinnacle_odds()
        4. Apply confidence discount based on sharp source (FanDuel EVs discounted 25%)
        5. Calculate EV percentage vs IMPLIED_BREAKEVEN_PROB (54.25% for 5-pick 10x)
        6. Save opportunities where DFS books have matching lines
        7. Log top 3 highest EV plays found

    Args:
        records: List of parsed odds records from API
        db: Database module reference (for insert_bet function)

    Returns:
        Number of Pick-Em opportunities saved to database

    Algorithm:
        - Uses multiplicative vig removal on sharp odds
        - Applies confidence discount for non-Pinnacle sources (FanDuel: 0.75x EV)
        - Compares fair probability to 54.25% breakeven threshold
        - Saves ALL opportunities (not just +EV) for user filtering
        - Logs top 3 EV plays regardless of threshold

    Examples:
        >>> records = [...]  # Parsed odds data
        >>> import src.db as db
        >>> count = _find_and_save_ev_opportunities(records, db)
        >>> print(f"Saved {count} opportunities")
        # Logs: "Top 3 EV (all lines): ..."
    """
    # Group records by player/market/point to ensure lines match
    grouped = {}
    for record in records:
        # Type-safe extraction with validation
        player_name = safe_dict_get(record, "player_name", default="", expected_type=str)
        market_key = safe_dict_get(record, "market_key", default="", expected_type=str)
        point = safe_dict_get(record, "point", default=0.0)
        bookmaker = safe_dict_get(record, "bookmaker", default="", expected_type=str)
        selection = safe_dict_get(record, "selection", default="", expected_type=str)
        price = record.get("price")

        if not all([player_name, market_key, bookmaker, selection, price is not None]):
            logger.warning(f"Skipping record with missing required fields: {record}")
            continue

        key = (player_name, market_key, point)
        if key not in grouped:
            grouped[key] = {}
        if bookmaker not in grouped[key]:
            grouped[key][bookmaker] = {}
        grouped[key][bookmaker][selection] = price

    ev_count = 0
    all_evs = []  # Track all EVs to show top 3
    sharp_source_counts = {"pinnacle": 0, "fanduel": 0}

    for (player_name, market_key, point), books in grouped.items():
        # Determine which sharp bookmaker to use (Pinnacle preferred, FanDuel fallback)
        sharp_source = None
        if SHARP_BOOKMAKER in books:
            sharp_source = SHARP_BOOKMAKER
        elif FALLBACK_SHARP_BOOKMAKER in books:
            sharp_source = FALLBACK_SHARP_BOOKMAKER
        else:
            # No sharp reference available, skip this player/market
            continue

        sharp_odds = books[sharp_source]
        sharp_over_raw = sharp_odds.get("Over")
        sharp_under_raw = sharp_odds.get("Under")

        if sharp_over_raw is None or sharp_under_raw is None:
            continue

        # Type-safe conversion and validation of sharp odds
        try:
            sharp_over = safe_int(sharp_over_raw)
            sharp_under = safe_int(sharp_under_raw)
            validate_american_odds(sharp_over, name=f"{sharp_source}_over")
            validate_american_odds(sharp_under, name=f"{sharp_source}_under")
        except ValueError as e:
            logger.warning(
                f"Invalid {sharp_source} odds for {player_name} {market_key}: {e}"
            )
            continue

        # Get confidence factor for this sharp source
        confidence = SHARP_CONFIDENCE.get(sharp_source, 0.75)

        # Calculate fair probability from sharp odds (removing vig)
        fair_over_prob, fair_under_prob = devig_pinnacle_odds(sharp_over, sharp_under)

        # Calculate raw EV percentages
        raw_over_ev = calculate_ev_percentage(fair_over_prob, IMPLIED_BREAKEVEN_PROB)
        raw_under_ev = calculate_ev_percentage(fair_under_prob, IMPLIED_BREAKEVEN_PROB)

        # Apply confidence discount to EV (only discount positive EV, don't make negative EV worse)
        over_ev_pct = raw_over_ev * confidence if raw_over_ev > 0 else raw_over_ev
        under_ev_pct = raw_under_ev * confidence if raw_under_ev > 0 else raw_under_ev

        # Track all EVs (even those below threshold) for top 3 display
        all_evs.append((player_name, market_key, point, "Over", fair_over_prob, over_ev_pct, sharp_source))
        all_evs.append((player_name, market_key, point, "Under", fair_under_prob, under_ev_pct, sharp_source))

        # Check DFS books for Pick-Em opportunities (must have same line)
        for dfs_book in DFS_BOOKMAKERS:
            if dfs_book not in books:
                continue

            dfs_odds = books[dfs_book]
            book_name = DFS_BOOK_NAMES.get(dfs_book, dfs_book)

            # Check Over - save if DFS book has this line
            if "Over" in dfs_odds:
                db.insert_bet(
                    event_id=records[0]["event_id"],
                    player_name=player_name,
                    market=f"{market_key}_over",
                    line_value=point,
                    pinnacle_over_price=sharp_over,
                    pinnacle_under_price=sharp_under,
                    fair_win_prob=fair_over_prob,
                    ev_percentage=over_ev_pct,
                    dfs_book=book_name,
                )
                ev_count += 1
                sharp_source_counts[sharp_source] = sharp_source_counts.get(sharp_source, 0) + 1

            # Check Under - save if DFS book has this line
            if "Under" in dfs_odds:
                db.insert_bet(
                    event_id=records[0]["event_id"],
                    player_name=player_name,
                    market=f"{market_key}_under",
                    line_value=point,
                    pinnacle_over_price=sharp_over,
                    pinnacle_under_price=sharp_under,
                    fair_win_prob=fair_under_prob,
                    ev_percentage=under_ev_pct,
                    dfs_book=book_name,
                )
                ev_count += 1
                sharp_source_counts[sharp_source] = sharp_source_counts.get(sharp_source, 0) + 1

    # Log sharp source usage
    if sharp_source_counts["fanduel"] > 0:
        logger.info(f"Sharp sources used: Pinnacle={sharp_source_counts['pinnacle']}, FanDuel={sharp_source_counts['fanduel']} (FanDuel EVs discounted 25%)")

    # Print Top 3 highest EV found (regardless of threshold)
    if all_evs:
        top_3 = sorted(all_evs, key=lambda x: x[5], reverse=True)[:3]
        logger.info("Top 3 EV (all lines):")
        for player, market, line, selection, prob, ev, source in top_3:
            source_note = "" if source == "pinnacle" else f" [{source}]"
            logger.info(f"  {player} {market} {selection} {line}: {prob:.1%} prob, {ev:+.1f}% EV{source_note}")

    logger.info(f"Saved {ev_count} total opportunities (Top 200 will be displayed)")
    return ev_count
