"""Input validation for API responses and data."""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger('ev_engine')


def validate_odds_response(data: Dict[str, Any]) -> bool:
    """Validate odds API response structure for required fields.

    Ensures the API response contains all required top-level fields and that
    critical fields have the correct data types. Logs specific errors for debugging.

    Args:
        data: API response dictionary from The Odds API

    Returns:
        True if response structure is valid, False otherwise

    Validation Rules:
        - Must be a dictionary (not list, string, etc.)
        - Must contain: id, sport_key, commence_time, bookmakers
        - bookmakers field must be a list

    Invalid Input Examples:
        - None or non-dict types
        - Missing required fields
        - bookmakers as dict instead of list

    Valid Input Example:
        >>> valid_data = {
        ...     'id': 'abc123',
        ...     'sport_key': 'basketball_nba',
        ...     'commence_time': '2024-01-15T19:00:00Z',
        ...     'bookmakers': [...]
        ... }
        >>> validate_odds_response(valid_data)
        True

    Examples:
        >>> invalid_data = {'id': 'abc123'}  # Missing fields
        >>> validate_odds_response(invalid_data)
        False
    """
    # Check required top-level fields
    required_fields = ['id', 'sport_key', 'commence_time', 'bookmakers']

    if not isinstance(data, dict):
        logger.error("Odds response is not a dictionary")
        return False

    for field in required_fields:
        if field not in data:
            logger.error(f"Missing required field: {field}")
            return False

    # Validate bookmakers is a list
    if not isinstance(data.get('bookmakers'), list):
        logger.error("Bookmakers field is not a list")
        return False

    return True


def validate_bookmaker_data(bookmaker: Dict[str, Any]) -> bool:
    """Validate individual bookmaker data structure within odds response.

    Checks that bookmaker data contains required fields and correct types.
    Used when parsing API responses to filter out malformed data.

    Args:
        bookmaker: Bookmaker data dictionary from API response

    Returns:
        True if bookmaker structure is valid, False otherwise

    Validation Rules:
        - Must be a dictionary
        - Must contain: key (bookmaker identifier), markets (list of markets)
        - markets field must be a list

    Invalid Input Examples:
        - Non-dict types (None, string, list)
        - Missing 'key' or 'markets' fields
        - markets as dict instead of list

    Valid Input Example:
        >>> valid_bookmaker = {
        ...     'key': 'pinnacle',
        ...     'title': 'Pinnacle',
        ...     'markets': [...]
        ... }
        >>> validate_bookmaker_data(valid_bookmaker)
        True

    Examples:
        >>> invalid_bookmaker = {'key': 'pinnacle'}  # Missing markets
        >>> validate_bookmaker_data(invalid_bookmaker)
        False
    """
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


def validate_market_data(market: Dict[str, Any]) -> bool:
    """Validate market data structure within bookmaker response.

    Checks that market data (e.g., player_points, h2h) contains required
    fields and correct types. Silent validation for performance.

    Args:
        market: Market data dictionary from API response

    Returns:
        True if market structure is valid, False otherwise

    Validation Rules:
        - Must be a dictionary
        - Must contain: key (market identifier), outcomes (list of bets)
        - outcomes field must be a list

    Invalid Input Examples:
        - Non-dict types
        - Missing 'key' or 'outcomes' fields
        - outcomes as dict instead of list

    Valid Input Example:
        >>> valid_market = {
        ...     'key': 'player_points',
        ...     'outcomes': [
        ...         {'name': 'Over', 'price': -110, 'point': 25.5, 'description': 'LeBron James'},
        ...         {'name': 'Under', 'price': -110, 'point': 25.5, 'description': 'LeBron James'}
        ...     ]
        ... }
        >>> validate_market_data(valid_market)
        True

    Examples:
        >>> invalid_market = {'key': 'player_points'}  # Missing outcomes
        >>> validate_market_data(invalid_market)
        False
    """
    required_fields = ['key', 'outcomes']

    if not isinstance(market, dict):
        return False

    for field in required_fields:
        if field not in market:
            return False

    if not isinstance(market.get('outcomes'), list):
        return False

    return True


def validate_outcome_data(outcome: Dict[str, Any]) -> bool:
    """Validate individual outcome (bet option) data structure.

    Checks that outcome data contains required fields and that price is numeric.
    An outcome represents a single bettable option like "Over 25.5" or "Team A Win".

    Args:
        outcome: Outcome data dictionary from API response

    Returns:
        True if outcome structure is valid, False otherwise

    Validation Rules:
        - Must be a dictionary
        - Must contain: name (e.g., 'Over', 'Under'), price (odds)
        - price must be numeric (convertible to float)

    Invalid Input Examples:
        - Non-dict types
        - Missing 'name' or 'price' fields
        - Non-numeric price (e.g., 'N/A', None)

    Valid Input Example:
        >>> valid_outcome = {
        ...     'name': 'Over',
        ...     'price': -110,
        ...     'point': 25.5,
        ...     'description': 'LeBron James'
        ... }
        >>> validate_outcome_data(valid_outcome)
        True

    Examples:
        >>> invalid_outcome = {'name': 'Over', 'price': 'N/A'}  # Invalid price
        >>> validate_outcome_data(invalid_outcome)
        False

        >>> missing_field = {'name': 'Over'}  # Missing price
        >>> validate_outcome_data(missing_field)
        False
    """
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
