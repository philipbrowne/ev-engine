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
    DFS_BOOKMAKERS,
    DFS_BOOK_NAMES,
)
from .db import insert_odds_batch


class OddsAPIError(Exception):
    """Custom exception for Odds API errors."""
    pass


def _make_request(endpoint: str, params: Optional[dict] = None) -> dict:
    """Make a request to The Odds API."""
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
    """Fetch all available sports from the API."""
    return _make_request("sports")


def get_events(sport_key: str) -> list[dict]:
    """Fetch upcoming events for a given sport."""
    return _make_request(f"sports/{sport_key}/events")


def get_odds(
    sport_key: str,
    markets: str = "h2h",
    regions: str = "us",
    bookmakers: Optional[str] = None,
) -> list[dict]:
    """Fetch odds for a given sport."""
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
    """Fetch player prop odds for a specific event."""
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
    """
    Fetch player props for all events of a sport and store them in the database.

    Args:
        sport_key: Sport identifier (e.g., 'basketball_nba')
        markets: List of market keys (e.g., ['player_points', 'player_rebounds'])
        bookmakers: List of bookmaker keys to filter (default: Pinnacle + DFS books)

    Returns:
        Number of records inserted
    """
    if bookmakers is None:
        bookmakers = [SHARP_BOOKMAKER] + DFS_BOOKMAKERS

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
    """Parse the API response and convert to database records."""
    records = []

    for event_data in response:
        if not isinstance(event_data, dict):
            continue
        event_id = event_data.get("id")
        bookmakers_data = event_data.get("bookmakers", [])

        for bookmaker in bookmakers_data:
            bookmaker_key = bookmaker.get("key")
            markets_data = bookmaker.get("markets", [])

            for market in markets_data:
                market_key = market.get("key")
                outcomes = market.get("outcomes", [])

                for outcome in outcomes:
                    player_name = outcome.get("description")
                    selection = outcome.get("name")  # "Over" or "Under"
                    price = outcome.get("price")
                    point = outcome.get("point")

                    if all([player_name, selection, price is not None, point is not None]):
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

    return records


def fetch_all_sports_props(
    markets: list[str],
    sports: Optional[list[str]] = None,
) -> dict[str, int]:
    """
    Fetch player props for multiple sports.

    Args:
        markets: List of market keys to fetch
        sports: List of sport keys (default: all supported sports)

    Returns:
        Dictionary mapping sport_key to number of records inserted
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
    """
    Check API usage by making a minimal request.
    Returns remaining requests and used requests from response headers.
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
    """
    Fetch odds for specified sports including player props and h2h markets.
    Filters for +EV opportunities and saves them to the database.

    Only fetches props for games starting within 12 hours to conserve API quota.

    Args:
        sports_to_fetch: List of sport API keys to fetch. If None, uses all SUPPORTED_SPORTS.

    Returns:
        Total number of odds records fetched
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

    print(f"DEBUG: Found {len(in_season_sports)} in-season sports: {in_season_sports}")

    if not in_season_sports:
        print("Fetched 0 odds")
        return 0

    total_odds_count = 0
    timestamp = datetime.now()
    bookmakers = [SHARP_BOOKMAKER] + DFS_BOOKMAKERS
    bookmakers_str = ",".join(bookmakers)

    # Markets to fetch for player props
    prop_markets = "player_points,player_assists,player_threes"

    # Time filter: only fetch games starting within 12 hours
    now = datetime.now(timezone.utc)
    cutoff_time = now + timedelta(hours=12)

    for sport_key in in_season_sports:
        print(f"DEBUG: Processing {sport_key}")
        try:
            # Get events list (cheap call - doesn't count against quota heavily)
            events = get_events(sport_key)

            if not events:
                print(f"DEBUG: No events found for {sport_key}")
                continue

            print(f"DEBUG: Found {len(events)} total events for {sport_key}")

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
                    print(f"DEBUG: Could not parse time for {event_name}")
                    continue

                # Calculate hours until game
                hours_until = (event_time - now).total_seconds() / 3600

                # Skip games that have already started
                if event_time < now:
                    print(f"Skipping {event_name} (Already started)")
                    continue

                # Skip games more than 12 hours away
                if event_time > cutoff_time:
                    print(f"Skipping {event_name} (Starts in {hours_until:.1f} hours)")
                    continue

                # Game passes filter - fetch props
                print(f"Fetching props for {event_name} (Starts in {hours_until:.1f} hours)")

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
                    print(f"ERROR: Failed to fetch props for {event_name}: {e}")
                    continue

        except OddsAPIError as e:
            print(f"ERROR: API error for {sport_key}: {e}")

    print(f"Fetched {total_odds_count} odds")
    return total_odds_count


def _parse_h2h_response(
    response: list[dict],
    sport_key: str,
    timestamp: datetime,
) -> list[dict]:
    """Parse h2h API response and convert to database records."""
    records = []

    for event_data in response:
        event_id = event_data.get("id")
        bookmakers_data = event_data.get("bookmakers", [])

        for bookmaker in bookmakers_data:
            bookmaker_key = bookmaker.get("key")
            markets_data = bookmaker.get("markets", [])

            for market in markets_data:
                market_key = market.get("key")
                outcomes = market.get("outcomes", [])

                for outcome in outcomes:
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
    """
    Find Pick-Em opportunities by comparing DFS book lines to sharp (Pinnacle) fair probabilities.
    Saves opportunities where Pinnacle's fair win probability exceeds the implied breakeven
    probability for a 3x payout.

    Returns:
        Number of Pick-Em opportunities saved
    """
    # Group records by player/market/point to ensure lines match
    grouped = {}
    for record in records:
        key = (record["player_name"], record["market_key"], record["point"])
        if key not in grouped:
            grouped[key] = {}
        book = record["bookmaker"]
        if book not in grouped[key]:
            grouped[key][book] = {}
        grouped[key][book][record["selection"]] = record["price"]

    ev_count = 0
    all_evs = []  # Track all EVs to show top 3

    for (player_name, market_key, point), books in grouped.items():
        # Need Pinnacle odds as the sharp reference
        if SHARP_BOOKMAKER not in books:
            continue

        pinnacle = books[SHARP_BOOKMAKER]
        pinnacle_over = pinnacle.get("Over")
        pinnacle_under = pinnacle.get("Under")

        if pinnacle_over is None or pinnacle_under is None:
            continue

        # Calculate fair probability from Pinnacle odds (removing vig)
        over_implied = _american_to_prob(pinnacle_over)
        under_implied = _american_to_prob(pinnacle_under)
        total_implied = over_implied + under_implied

        fair_over_prob = over_implied / total_implied
        fair_under_prob = under_implied / total_implied

        # Track all EVs (even those below threshold) for top 3 display
        over_ev_pct = ((fair_over_prob / IMPLIED_BREAKEVEN_PROB) - 1) * 100
        under_ev_pct = ((fair_under_prob / IMPLIED_BREAKEVEN_PROB) - 1) * 100
        all_evs.append((player_name, market_key, point, "Over", fair_over_prob, over_ev_pct))
        all_evs.append((player_name, market_key, point, "Under", fair_under_prob, under_ev_pct))

        # Check DFS books for Pick-Em opportunities (must have same line)
        for dfs_book in DFS_BOOKMAKERS:
            if dfs_book not in books:
                continue

            dfs_odds = books[dfs_book]
            book_name = DFS_BOOK_NAMES.get(dfs_book, dfs_book)

            # Check Over - save if DFS book has this line
            if "Over" in dfs_odds:
                ev_pct = ((fair_over_prob / IMPLIED_BREAKEVEN_PROB) - 1) * 100

                db.insert_bet(
                    event_id=records[0]["event_id"],
                    player_name=player_name,
                    market=f"{market_key}_over",
                    line_value=point,
                    pinnacle_over_price=pinnacle_over,
                    pinnacle_under_price=pinnacle_under,
                    fair_win_prob=fair_over_prob,
                    ev_percentage=ev_pct,
                    dfs_book=book_name,
                )
                ev_count += 1

            # Check Under - save if DFS book has this line
            if "Under" in dfs_odds:
                ev_pct = ((fair_under_prob / IMPLIED_BREAKEVEN_PROB) - 1) * 100

                db.insert_bet(
                    event_id=records[0]["event_id"],
                    player_name=player_name,
                    market=f"{market_key}_under",
                    line_value=point,
                    pinnacle_over_price=pinnacle_over,
                    pinnacle_under_price=pinnacle_under,
                    fair_win_prob=fair_under_prob,
                    ev_percentage=ev_pct,
                    dfs_book=book_name,
                )
                ev_count += 1

    # Print Top 3 highest EV found (regardless of threshold)
    if all_evs:
        top_3 = sorted(all_evs, key=lambda x: x[5], reverse=True)[:3]
        print("Top 3 EV (all lines):")
        for player, market, line, selection, prob, ev in top_3:
            print(f"  {player} {market} {selection} {line}: {prob:.1%} prob, {ev:+.1f}% EV")

    print(f"Saved {ev_count} total opportunities (Top 200 will be displayed)")
    return ev_count


def _american_to_prob(american_odds: int) -> float:
    """Convert American odds to implied probability."""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)
