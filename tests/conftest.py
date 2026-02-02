"""
Shared pytest fixtures for EV Engine tests.

This module provides fixtures for:
- Database connections (with automatic cleanup)
- Mock API responses
- Sample test data
- Temporary file management
"""

import os
import sqlite3
import tempfile
from typing import Generator, Dict, List, Any
from unittest.mock import Mock, MagicMock

import pytest


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """
    Create a temporary database file for testing.

    Yields:
        Path to temporary database file

    Cleanup:
        Automatically removes the database file after test completion
    """
    # Create temporary database file
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Store the original DATABASE_PATH to restore later
    import src.config
    original_config_path = src.config.DATABASE_PATH
    src.config.DATABASE_PATH = path

    # Also patch the db module's DATABASE_PATH reference
    import src.db
    src.db.DATABASE_PATH = path

    yield path

    # Cleanup: restore original paths
    src.config.DATABASE_PATH = original_config_path
    src.db.DATABASE_PATH = original_config_path

    # Remove the temporary database
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """
    Create a temporary database file for testing (alias for compatibility).

    Yields:
        Path to temporary database file

    Cleanup:
        Automatically removes the database file after test completion
    """
    # Create temporary database file
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    yield path

    # Cleanup: remove the temporary database
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def db_connection(temp_db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """
    Provide a temporary database connection with proper setup and teardown.

    Args:
        temp_db_path: Path to temporary database file

    Yields:
        SQLite connection object with row_factory configured

    Cleanup:
        Closes connection and commits any pending transactions
    """
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row

    yield conn

    # Cleanup
    conn.commit()
    conn.close()


@pytest.fixture
def initialized_db(temp_db: str) -> Generator[str, None, None]:
    """
    Provide a database path with all tables initialized.

    Args:
        temp_db: Path to temporary database file

    Yields:
        Database path with initialized schema
    """
    from src import db
    db.initialize_db()

    yield temp_db


# ============================================================================
# Mock API Response Fixtures
# ============================================================================

@pytest.fixture
def mock_api_sports_response() -> List[Dict[str, Any]]:
    """
    Mock response for the sports endpoint.

    Returns:
        List of sport dictionaries as returned by The Odds API
    """
    return [
        {
            "key": "basketball_nba",
            "group": "Basketball",
            "title": "NBA",
            "description": "US Basketball",
            "active": True,
            "has_outrights": False
        },
        {
            "key": "americanfootball_nfl",
            "group": "American Football",
            "title": "NFL",
            "description": "US Football",
            "active": True,
            "has_outrights": False
        }
    ]


@pytest.fixture
def mock_api_events_response() -> List[Dict[str, Any]]:
    """
    Mock response for the events endpoint.

    Returns:
        List of event dictionaries
    """
    return [
        {
            "id": "event123",
            "sport_key": "basketball_nba",
            "sport_title": "NBA",
            "commence_time": "2024-01-15T19:00:00Z",
            "home_team": "Los Angeles Lakers",
            "away_team": "Boston Celtics"
        }
    ]


@pytest.fixture
def mock_player_props_response() -> Dict[str, Any]:
    """
    Mock response for player props endpoint with comprehensive data.

    Returns:
        Player props data with Pinnacle and DFS bookmakers
    """
    return {
        "id": "event123",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "commence_time": "2024-01-15T19:00:00Z",
        "home_team": "Los Angeles Lakers",
        "away_team": "Boston Celtics",
        "bookmakers": [
            {
                "key": "pinnacle",
                "title": "Pinnacle",
                "markets": [
                    {
                        "key": "player_points",
                        "outcomes": [
                            {
                                "name": "LeBron James",
                                "description": "Over",
                                "price": -110,
                                "point": 25.5
                            },
                            {
                                "name": "LeBron James",
                                "description": "Under",
                                "price": -110,
                                "point": 25.5
                            }
                        ]
                    },
                    {
                        "key": "player_assists",
                        "outcomes": [
                            {
                                "name": "LeBron James",
                                "description": "Over",
                                "price": -120,
                                "point": 7.5
                            },
                            {
                                "name": "LeBron James",
                                "description": "Under",
                                "price": +100,
                                "point": 7.5
                            }
                        ]
                    }
                ]
            },
            {
                "key": "prizepicks",
                "title": "PrizePicks",
                "markets": [
                    {
                        "key": "player_points",
                        "outcomes": [
                            {
                                "name": "LeBron James",
                                "description": "Over",
                                "price": -105,
                                "point": 24.5
                            },
                            {
                                "name": "LeBron James",
                                "description": "Under",
                                "price": -105,
                                "point": 24.5
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_api_error_response() -> Dict[str, Any]:
    """
    Mock error response from The Odds API.

    Returns:
        Error response dictionary
    """
    return {
        "error": "API key is invalid",
        "status": 401
    }


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_odds_data() -> List[Dict[str, Any]]:
    """
    Sample odds data for testing database insertions.

    Returns:
        List of odds dictionaries ready for database insertion
    """
    from datetime import datetime
    return [
        {
            "event_id": "event123",
            "sport_key": "basketball_nba",
            "bookmaker": "pinnacle",
            "market_key": "player_points",
            "player_name": "LeBron James",
            "selection": "Over",
            "price": -110,
            "point": 25.5,
            "timestamp": datetime.now(),
        },
        {
            "event_id": "event123",
            "sport_key": "basketball_nba",
            "bookmaker": "prizepicks",
            "market_key": "player_points",
            "player_name": "LeBron James",
            "selection": "Over",
            "price": -105,
            "point": 24.5,
            "timestamp": datetime.now(),
        }
    ]


@pytest.fixture
def sample_bet_data() -> Dict[str, Any]:
    """
    Sample bet data for testing bet tracking.

    Returns:
        Bet dictionary with all required fields
    """
    return {
        "event_id": "event123",
        "player_name": "LeBron James",
        "market": "Points",
        "line_value": 24.5,
        "pinnacle_over_price": -110,
        "pinnacle_under_price": -110,
        "fair_win_prob": 0.60,
        "ev_percentage": 5.5,
        "dfs_book": "PrizePicks"
    }


@pytest.fixture
def sample_slip_data() -> Dict[str, Any]:
    """
    Sample bet slip data for testing slip tracking.

    Returns:
        Slip dictionary with legs
    """
    return {
        "book": "PrizePicks",
        "stake": 10.0,
        "legs": [
            {
                "player": "LeBron James",
                "market": "Points",
                "line": 24.5,
                "outcome": "Over"
            },
            {
                "player": "Anthony Davis",
                "market": "Rebounds",
                "line": 11.5,
                "outcome": "Over"
            }
        ]
    }


@pytest.fixture
def sample_slip_legs() -> List[Dict[str, Any]]:
    """
    Sample slip legs data for testing.

    Returns:
        List of leg dictionaries
    """
    return [
        {
            'player': 'LeBron James',
            'market': 'Player Points Over',
            'line': 25.5,
        },
        {
            'player': 'Stephen Curry',
            'market': 'Player Assists Over',
            'line': 6.5,
        },
    ]


# ============================================================================
# Mock Object Fixtures
# ============================================================================

@pytest.fixture
def mock_requests_get() -> Mock:
    """
    Mock requests.get function for API testing.

    Returns:
        Mock object configured for requests.get
    """
    mock = Mock()
    mock.return_value.status_code = 200
    mock.return_value.json.return_value = {}
    return mock


@pytest.fixture
def mock_logger() -> Mock:
    """
    Mock logger for testing logging behavior.

    Returns:
        Mock logger object
    """
    mock = Mock()
    mock.info = Mock()
    mock.warning = Mock()
    mock.error = Mock()
    mock.debug = Mock()
    return mock


# ============================================================================
# Environment Configuration Fixtures
# ============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch) -> None:
    """
    Set up mock environment variables for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    monkeypatch.setenv("ODDS_API_KEY", "test_api_key_12345")
    monkeypatch.setenv("DATABASE_PATH", "/tmp/test_ev_engine.db")


@pytest.fixture
def no_api_key(monkeypatch) -> None:
    """
    Remove API key from environment to test error handling.

    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    monkeypatch.delenv("ODDS_API_KEY", raising=False)


# ============================================================================
# Data Validation Fixtures
# ============================================================================

@pytest.fixture
def valid_american_odds() -> List[int]:
    """Valid American odds values for testing."""
    return [-110, -120, -150, -200, +100, +150, +200, +300]


@pytest.fixture
def invalid_american_odds() -> List[int]:
    """Invalid American odds values for testing."""
    return [-99, 0, 50, -50, 99]


@pytest.fixture
def valid_line_values() -> List[float]:
    """Valid line values for testing."""
    return [0.5, 1.5, 10.5, 25.5, 50.5, 100.5]


@pytest.fixture
def invalid_line_values() -> List[float]:
    """Invalid line values for testing."""
    return [-1.5, 0.0, 1.0, 10.0]  # Should end in .5
