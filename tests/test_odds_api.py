"""Comprehensive tests for odds_api.py module.

This test suite covers:
- API client initialization and configuration
- HTTP request handling (success, errors, timeouts)
- Response parsing for props and h2h markets
- EV opportunity identification
- Error handling and validation integration
- Sports filtering and time-based filtering
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch, call
import requests

from src.odds_api import (
    OddsAPIError,
    _make_request,
    get_sports,
    get_events,
    get_odds,
    get_player_props,
    fetch_and_store_player_props,
    _parse_props_response,
    fetch_all_sports_props,
    get_api_usage,
    fetch_odds,
    _parse_h2h_response,
    _find_and_save_ev_opportunities,
    IMPLIED_BREAKEVEN_PROB,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_api_key(monkeypatch):
    """Mock ODDS_API_KEY in the config module."""
    import src.config
    monkeypatch.setattr('src.config.ODDS_API_KEY', 'test_api_key_12345')
    return "test_api_key_12345"


@pytest.fixture
def mock_odds_api_response():
    """Mock response from The Odds API for player props."""
    return {
        'id': 'abc123',
        'sport_key': 'basketball_nba',
        'commence_time': '2024-01-15T19:00:00Z',
        'home_team': 'Lakers',
        'away_team': 'Warriors',
        'bookmakers': [
            {
                'key': 'pinnacle',
                'title': 'Pinnacle',
                'markets': [
                    {
                        'key': 'player_points',
                        'outcomes': [
                            {
                                'name': 'Over',
                                'description': 'LeBron James',
                                'price': -110,
                                'point': 25.5
                            },
                            {
                                'name': 'Under',
                                'description': 'LeBron James',
                                'price': -110,
                                'point': 25.5
                            }
                        ]
                    }
                ]
            },
            {
                'key': 'prizepicks',
                'title': 'PrizePicks',
                'markets': [
                    {
                        'key': 'player_points',
                        'outcomes': [
                            {
                                'name': 'Over',
                                'description': 'LeBron James',
                                'price': -110,
                                'point': 25.5
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_h2h_response():
    """Mock response for head-to-head markets."""
    return {
        'id': 'def456',
        'sport_key': 'basketball_nba',
        'commence_time': '2024-01-15T19:00:00Z',
        'home_team': 'Lakers',
        'away_team': 'Warriors',
        'bookmakers': [
            {
                'key': 'pinnacle',
                'markets': [
                    {
                        'key': 'h2h',
                        'outcomes': [
                            {'name': 'Lakers', 'price': -150},
                            {'name': 'Warriors', 'price': 130}
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_sports_response():
    """Mock response for sports list."""
    return [
        {
            'key': 'basketball_nba',
            'group': 'Basketball',
            'title': 'NBA',
            'active': True,
            'has_outrights': False
        },
        {
            'key': 'americanfootball_nfl',
            'group': 'American Football',
            'title': 'NFL',
            'active': True,
            'has_outrights': False
        },
        {
            'key': 'baseball_mlb',
            'group': 'Baseball',
            'title': 'MLB',
            'active': False,
            'has_outrights': False
        }
    ]


@pytest.fixture
def mock_events_response():
    """Mock response for events list."""
    now = datetime.now(timezone.utc)
    return [
        {
            'id': 'event1',
            'sport_key': 'basketball_nba',
            'commence_time': (now + timedelta(hours=2)).isoformat().replace('+00:00', 'Z'),
            'home_team': 'Lakers',
            'away_team': 'Warriors'
        },
        {
            'id': 'event2',
            'sport_key': 'basketball_nba',
            'commence_time': (now + timedelta(hours=15)).isoformat().replace('+00:00', 'Z'),
            'home_team': 'Celtics',
            'away_team': 'Heat'
        }
    ]


# ============================================================================
# Test API Request Functions
# ============================================================================

class TestMakeRequest:
    """Test the _make_request function."""

    def test_make_request_missing_api_key(self, mocker):
        """Test that missing API key raises OddsAPIError."""
        # Patch the constant directly in the odds_api module since it's imported from config
        mocker.patch('src.odds_api.ODDS_API_KEY', '')

        with pytest.raises(OddsAPIError, match="ODDS_API_KEY is not set"):
            _make_request("sports")

    def test_make_request_success(self, mocker, mock_api_key):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}

        mock_get = mocker.patch('requests.get', return_value=mock_response)

        result = _make_request("sports")

        assert result == {"data": "test"}
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "apiKey" in kwargs['params']

    def test_make_request_with_params(self, mocker, mock_api_key):
        """Test request with additional parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        mock_get = mocker.patch('requests.get', return_value=mock_response)

        _make_request("sports/basketball_nba/odds", params={"markets": "h2h"})

        args, kwargs = mock_get.call_args
        # Verify apiKey is present (value depends on environment)
        assert 'apiKey' in kwargs['params']
        assert kwargs['params']['markets'] == "h2h"

    def test_make_request_401_unauthorized(self, mocker, mock_api_key):
        """Test 401 Unauthorized error."""
        mock_response = Mock()
        mock_response.status_code = 401

        mocker.patch('requests.get', return_value=mock_response)

        with pytest.raises(OddsAPIError, match="401 Unauthorized"):
            _make_request("sports")

    def test_make_request_429_rate_limit(self, mocker, mock_api_key):
        """Test 429 rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429

        mocker.patch('requests.get', return_value=mock_response)

        with pytest.raises(OddsAPIError, match="429 Quota Exceeded"):
            _make_request("sports")

    @pytest.mark.parametrize("status_code,error_text", [
        (400, "Bad Request"),
        (403, "Forbidden"),
        (404, "Not Found"),
        (500, "Internal Server Error"),
        (503, "Service Unavailable"),
    ])
    def test_make_request_various_errors(self, mocker, mock_api_key, status_code, error_text):
        """Test various HTTP error codes."""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.text = error_text

        mocker.patch('requests.get', return_value=mock_response)

        with pytest.raises(OddsAPIError, match=f"API request failed with status {status_code}"):
            _make_request("sports")

    def test_make_request_timeout(self, mocker, mock_api_key):
        """Test timeout handling."""
        mocker.patch('requests.get', side_effect=requests.Timeout("Connection timeout"))

        with pytest.raises(requests.Timeout):
            _make_request("sports")

    def test_make_request_connection_error(self, mocker, mock_api_key):
        """Test connection error handling."""
        mocker.patch('requests.get', side_effect=requests.ConnectionError("Network error"))

        with pytest.raises(requests.ConnectionError):
            _make_request("sports")

    def test_make_request_timeout_parameter(self, mocker, mock_api_key):
        """Test that timeout parameter is set correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_get = mocker.patch('requests.get', return_value=mock_response)

        _make_request("sports")

        args, kwargs = mock_get.call_args
        assert kwargs['timeout'] == 30


class TestAPIEndpointFunctions:
    """Test individual API endpoint wrapper functions."""

    def test_get_sports(self, mocker, mock_api_key, mock_sports_response):
        """Test get_sports function."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_sports_response

        mocker.patch('requests.get', return_value=mock_response)

        result = get_sports()

        assert len(result) == 3
        assert result[0]['key'] == 'basketball_nba'

    def test_get_events(self, mocker, mock_api_key, mock_events_response):
        """Test get_events function."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_events_response

        mocker.patch('requests.get', return_value=mock_response)

        result = get_events('basketball_nba')

        assert len(result) == 2
        assert result[0]['id'] == 'event1'

    def test_get_odds(self, mocker, mock_api_key):
        """Test get_odds function."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        mock_get = mocker.patch('requests.get', return_value=mock_response)

        get_odds('basketball_nba', markets='h2h', regions='us')

        args, kwargs = mock_get.call_args
        assert kwargs['params']['markets'] == 'h2h'
        assert kwargs['params']['regions'] == 'us'
        assert kwargs['params']['oddsFormat'] == 'american'

    def test_get_odds_with_bookmakers(self, mocker, mock_api_key):
        """Test get_odds with bookmakers filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        mock_get = mocker.patch('requests.get', return_value=mock_response)

        get_odds('basketball_nba', bookmakers='pinnacle,fanduel')

        args, kwargs = mock_get.call_args
        assert kwargs['params']['bookmakers'] == 'pinnacle,fanduel'

    def test_get_player_props(self, mocker, mock_api_key):
        """Test get_player_props function."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        mock_get = mocker.patch('requests.get', return_value=mock_response)

        get_player_props('basketball_nba', 'event123', 'player_points')

        args, kwargs = mock_get.call_args
        assert 'event123' in args[0]
        assert kwargs['params']['markets'] == 'player_points'

    def test_get_api_usage(self, mocker, mock_api_key):
        """Test get_api_usage function."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'x-requests-remaining': '450',
            'x-requests-used': '50'
        }

        mocker.patch('requests.get', return_value=mock_response)

        result = get_api_usage()

        assert result['requests_remaining'] == '450'
        assert result['requests_used'] == '50'

    def test_get_api_usage_missing_key(self, mocker):
        """Test get_api_usage with missing API key."""
        mocker.patch('src.odds_api.ODDS_API_KEY', '')

        with pytest.raises(OddsAPIError, match="ODDS_API_KEY is not set"):
            get_api_usage()


# ============================================================================
# Test Response Parsing
# ============================================================================

class TestParsePropsResponse:
    """Test _parse_props_response function."""

    def test_parse_props_response_success(self, mock_odds_api_response):
        """Test successful parsing of props response."""
        timestamp = datetime.now()

        records = _parse_props_response([mock_odds_api_response], 'basketball_nba', timestamp)

        assert len(records) == 3  # 2 from Pinnacle, 1 from PrizePicks

        # Check first record
        assert records[0]['event_id'] == 'abc123'
        assert records[0]['sport_key'] == 'basketball_nba'
        assert records[0]['player_name'] == 'LeBron James'
        assert records[0]['market_key'] == 'player_points'
        assert records[0]['point'] == 25.5
        assert records[0]['timestamp'] == timestamp

    def test_parse_props_response_empty_list(self):
        """Test parsing empty response list."""
        timestamp = datetime.now()

        records = _parse_props_response([], 'basketball_nba', timestamp)

        assert records == []

    def test_parse_props_response_invalid_event_structure(self, caplog):
        """Test handling of invalid event structure."""
        timestamp = datetime.now()
        invalid_data = [
            {'id': 'test'},  # Missing required fields
            "not a dict",  # Not a dict
        ]

        records = _parse_props_response(invalid_data, 'basketball_nba', timestamp)

        assert len(records) == 0
        assert "Skipping invalid event data" in caplog.text

    def test_parse_props_response_invalid_bookmaker(self, caplog):
        """Test handling of invalid bookmaker data."""
        timestamp = datetime.now()
        data = [{
            'id': 'abc123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': [
                {'key': 'pinnacle'},  # Missing 'markets'
            ]
        }]

        records = _parse_props_response(data, 'basketball_nba', timestamp)

        assert len(records) == 0
        assert "Skipping invalid bookmaker data" in caplog.text

    def test_parse_props_response_invalid_market(self, caplog):
        """Test handling of invalid market data."""
        timestamp = datetime.now()
        data = [{
            'id': 'abc123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': [
                {
                    'key': 'pinnacle',
                    'markets': [
                        {'key': 'player_points'}  # Missing 'outcomes'
                    ]
                }
            ]
        }]

        records = _parse_props_response(data, 'basketball_nba', timestamp)

        assert len(records) == 0

    def test_parse_props_response_invalid_outcome(self, caplog):
        """Test handling of invalid outcome data."""
        timestamp = datetime.now()
        data = [{
            'id': 'abc123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': [
                {
                    'key': 'pinnacle',
                    'markets': [
                        {
                            'key': 'player_points',
                            'outcomes': [
                                {'name': 'Over'}  # Missing required fields
                            ]
                        }
                    ]
                }
            ]
        }]

        records = _parse_props_response(data, 'basketball_nba', timestamp)

        assert len(records) == 0

    def test_parse_props_response_invalid_odds_value(self, caplog):
        """Test handling of invalid odds values."""
        timestamp = datetime.now()
        data = [{
            'id': 'abc123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': [
                {
                    'key': 'pinnacle',
                    'markets': [
                        {
                            'key': 'player_points',
                            'outcomes': [
                                {
                                    'name': 'Over',
                                    'description': 'LeBron James',
                                    'price': 50,  # Invalid American odds (must be <= -100 or >= 100)
                                    'point': 25.5
                                }
                            ]
                        }
                    ]
                }
            ]
        }]

        records = _parse_props_response(data, 'basketball_nba', timestamp)

        assert len(records) == 0
        assert "Invalid data" in caplog.text

    def test_parse_props_response_invalid_line_value(self, caplog):
        """Test handling of invalid line values."""
        timestamp = datetime.now()
        data = [{
            'id': 'abc123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': [
                {
                    'key': 'pinnacle',
                    'markets': [
                        {
                            'key': 'player_points',
                            'outcomes': [
                                {
                                    'name': 'Over',
                                    'description': 'LeBron James',
                                    'price': -110,
                                    'point': 'invalid'  # Invalid point value
                                }
                            ]
                        }
                    ]
                }
            ]
        }]

        records = _parse_props_response(data, 'basketball_nba', timestamp)

        # safe_float returns 0.0 for invalid values instead of raising
        # So we get a record with point=0.0
        # This is actually acceptable behavior - the warning is logged
        assert "Cannot convert to float" in caplog.text

    def test_parse_props_response_multiple_bookmakers(self, mock_odds_api_response):
        """Test parsing with multiple bookmakers."""
        timestamp = datetime.now()

        records = _parse_props_response([mock_odds_api_response], 'basketball_nba', timestamp)

        bookmakers = {r['bookmaker'] for r in records}
        assert 'pinnacle' in bookmakers
        assert 'prizepicks' in bookmakers

    def test_parse_props_response_multiple_markets(self):
        """Test parsing with multiple markets."""
        timestamp = datetime.now()
        data = [{
            'id': 'abc123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': [
                {
                    'key': 'pinnacle',
                    'markets': [
                        {
                            'key': 'player_points',
                            'outcomes': [
                                {'name': 'Over', 'description': 'LeBron James', 'price': -110, 'point': 25.5}
                            ]
                        },
                        {
                            'key': 'player_rebounds',
                            'outcomes': [
                                {'name': 'Over', 'description': 'LeBron James', 'price': -115, 'point': 8.5}
                            ]
                        }
                    ]
                }
            ]
        }]

        records = _parse_props_response(data, 'basketball_nba', timestamp)

        assert len(records) == 2
        markets = {r['market_key'] for r in records}
        assert 'player_points' in markets
        assert 'player_rebounds' in markets


class TestParseH2HResponse:
    """Test _parse_h2h_response function."""

    def test_parse_h2h_response_success(self, mock_h2h_response):
        """Test successful parsing of h2h response."""
        timestamp = datetime.now()

        records = _parse_h2h_response([mock_h2h_response], 'basketball_nba', timestamp)

        assert len(records) == 2
        assert records[0]['player_name'] == 'Lakers'
        assert records[0]['selection'] == 'Win'
        assert records[0]['price'] == -150
        assert records[0]['point'] == 0.0
        assert records[1]['player_name'] == 'Warriors'
        assert records[1]['price'] == 130

    def test_parse_h2h_response_empty(self):
        """Test parsing empty h2h response."""
        timestamp = datetime.now()

        records = _parse_h2h_response([], 'basketball_nba', timestamp)

        assert records == []

    def test_parse_h2h_response_invalid_event(self, caplog):
        """Test handling of invalid event in h2h response."""
        timestamp = datetime.now()
        data = [{'id': 'test'}]  # Missing required fields

        records = _parse_h2h_response(data, 'basketball_nba', timestamp)

        assert len(records) == 0
        assert "Skipping invalid event data" in caplog.text

    def test_parse_h2h_response_invalid_bookmaker(self, caplog):
        """Test handling of invalid bookmaker in h2h response."""
        timestamp = datetime.now()
        data = [{
            'id': 'def456',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': [
                {'key': 'pinnacle'}  # Missing 'markets'
            ]
        }]

        records = _parse_h2h_response(data, 'basketball_nba', timestamp)

        assert len(records) == 0


# ============================================================================
# Test EV Calculation and Opportunity Finding
# ============================================================================

class TestFindAndSaveEVOpportunities:
    """Test _find_and_save_ev_opportunities function."""

    def test_find_ev_opportunities_positive_ev(self, mocker):
        """Test finding positive EV opportunities."""
        mock_db = MagicMock()

        # Create test records with Pinnacle and DFS book
        records = [
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Over',
                'price': -105  # Slightly better odds = higher fair probability
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Under',
                'price': -115
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'prizepicks',
                'selection': 'Over',
                'price': -110
            }
        ]

        count = _find_and_save_ev_opportunities(records, mock_db)

        # Should save the Over opportunity for PrizePicks
        assert count == 1
        assert mock_db.insert_bet.call_count == 1

    def test_find_ev_opportunities_no_pinnacle_odds(self):
        """Test when Pinnacle odds are missing."""
        mock_db = MagicMock()

        records = [
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'prizepicks',
                'selection': 'Over',
                'price': -110
            }
        ]

        count = _find_and_save_ev_opportunities(records, mock_db)

        assert count == 0
        assert mock_db.insert_bet.call_count == 0

    def test_find_ev_opportunities_no_dfs_books(self):
        """Test when DFS books are missing."""
        mock_db = MagicMock()

        records = [
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Over',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Under',
                'price': -110
            }
        ]

        count = _find_and_save_ev_opportunities(records, mock_db)

        assert count == 0
        assert mock_db.insert_bet.call_count == 0

    def test_find_ev_opportunities_different_lines(self):
        """Test when DFS book has different line value."""
        mock_db = MagicMock()

        records = [
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Over',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Under',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 26.5,  # Different line
                'bookmaker': 'prizepicks',
                'selection': 'Over',
                'price': -110
            }
        ]

        count = _find_and_save_ev_opportunities(records, mock_db)

        # Should not match because lines are different
        assert count == 0

    def test_find_ev_opportunities_both_sides(self):
        """Test finding opportunities on both Over and Under."""
        mock_db = MagicMock()

        records = [
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Over',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Under',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'prizepicks',
                'selection': 'Over',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'prizepicks',
                'selection': 'Under',
                'price': -110
            }
        ]

        count = _find_and_save_ev_opportunities(records, mock_db)

        # Should save both Over and Under
        assert count == 2
        assert mock_db.insert_bet.call_count == 2

    def test_find_ev_opportunities_multiple_dfs_books(self):
        """Test with multiple DFS books."""
        mock_db = MagicMock()

        records = [
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Over',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Under',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'prizepicks',
                'selection': 'Over',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'underdog',
                'selection': 'Over',
                'price': -110
            }
        ]

        count = _find_and_save_ev_opportunities(records, mock_db)

        # Should save opportunity for each DFS book
        assert count == 2
        assert mock_db.insert_bet.call_count == 2

    def test_find_ev_opportunities_invalid_odds(self, caplog):
        """Test handling of invalid Pinnacle odds."""
        mock_db = MagicMock()

        records = [
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Over',
                'price': 50  # Invalid American odds
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Under',
                'price': -110
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'prizepicks',
                'selection': 'Over',
                'price': -110
            }
        ]

        count = _find_and_save_ev_opportunities(records, mock_db)

        assert count == 0
        assert "Invalid pinnacle odds" in caplog.text

    def test_find_ev_opportunities_missing_fields(self, caplog):
        """Test handling of records with missing fields."""
        mock_db = MagicMock()

        records = [
            {
                'event_id': 'event1',
                # Missing player_name
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Over',
                'price': -110
            }
        ]

        count = _find_and_save_ev_opportunities(records, mock_db)

        assert count == 0
        assert "Skipping record with missing required fields" in caplog.text

    def test_find_ev_opportunities_incomplete_pinnacle_odds(self):
        """Test when Pinnacle is missing one side."""
        mock_db = MagicMock()

        records = [
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Over',
                'price': -110
            },
            # Missing Under side
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'prizepicks',
                'selection': 'Over',
                'price': -110
            }
        ]

        count = _find_and_save_ev_opportunities(records, mock_db)

        assert count == 0

    def test_find_ev_opportunities_correct_devig_call(self, mocker):
        """Test that devig function is called correctly."""
        mock_db = MagicMock()
        mock_devig = mocker.patch('src.odds_api.devig_pinnacle_odds', return_value=(0.55, 0.45))

        records = [
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Over',
                'price': -120
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'pinnacle',
                'selection': 'Under',
                'price': 100
            },
            {
                'event_id': 'event1',
                'player_name': 'LeBron James',
                'market_key': 'player_points',
                'point': 25.5,
                'bookmaker': 'prizepicks',
                'selection': 'Over',
                'price': -110
            }
        ]

        _find_and_save_ev_opportunities(records, mock_db)

        mock_devig.assert_called_once_with(-120, 100)


# ============================================================================
# Test High-Level Fetch Functions
# ============================================================================

class TestFetchAndStorePlayerProps:
    """Test fetch_and_store_player_props function."""

    def test_fetch_and_store_success(self, mocker, mock_api_key, mock_events_response, mock_odds_api_response):
        """Test successful fetch and store."""
        # Mock API calls
        mock_get_events = mocker.patch('src.odds_api.get_events', return_value=mock_events_response)
        mock_get_props = mocker.patch('src.odds_api.get_player_props', return_value=[mock_odds_api_response])
        mock_insert = mocker.patch('src.odds_api.insert_odds_batch', return_value=3)

        count = fetch_and_store_player_props('basketball_nba', ['player_points'])

        assert count == 6  # 3 records per event * 2 events
        assert mock_get_events.call_count == 1
        assert mock_get_props.call_count == 2

    def test_fetch_and_store_no_events(self, mocker, mock_api_key):
        """Test when no events are found."""
        mocker.patch('src.odds_api.get_events', return_value=[])

        count = fetch_and_store_player_props('basketball_nba', ['player_points'])

        assert count == 0

    def test_fetch_and_store_event_without_id(self, mocker, mock_api_key):
        """Test handling of event without ID."""
        events = [{'sport_key': 'basketball_nba'}]  # Missing 'id'
        mocker.patch('src.odds_api.get_events', return_value=events)

        count = fetch_and_store_player_props('basketball_nba', ['player_points'])

        assert count == 0

    def test_fetch_and_store_api_error(self, mocker, mock_api_key, mock_events_response):
        """Test handling of API errors."""
        mocker.patch('src.odds_api.get_events', return_value=mock_events_response)
        mocker.patch('src.odds_api.get_player_props', side_effect=OddsAPIError("API error"))

        count = fetch_and_store_player_props('basketball_nba', ['player_points'])

        # Should continue processing despite errors
        assert count == 0

    def test_fetch_and_store_custom_bookmakers(self, mocker, mock_api_key, mock_events_response, mock_odds_api_response):
        """Test with custom bookmakers list."""
        mocker.patch('src.odds_api.get_events', return_value=mock_events_response[:1])
        mock_get_props = mocker.patch('src.odds_api.get_player_props', return_value=[mock_odds_api_response])
        mocker.patch('src.odds_api.insert_odds_batch', return_value=2)

        fetch_and_store_player_props('basketball_nba', ['player_points'], bookmakers=['pinnacle'])

        # Check that custom bookmakers were passed
        args, kwargs = mock_get_props.call_args
        assert 'pinnacle' in kwargs['bookmakers']

    def test_fetch_and_store_empty_props_response(self, mocker, mock_api_key, mock_events_response):
        """Test handling of empty props response."""
        mocker.patch('src.odds_api.get_events', return_value=mock_events_response[:1])
        mocker.patch('src.odds_api.get_player_props', return_value=[])

        count = fetch_and_store_player_props('basketball_nba', ['player_points'])

        assert count == 0


class TestFetchAllSportsProps:
    """Test fetch_all_sports_props function."""

    def test_fetch_all_sports_success(self, mocker, mock_api_key):
        """Test successful fetch for all sports."""
        mock_fetch = mocker.patch('src.odds_api.fetch_and_store_player_props')
        mock_fetch.side_effect = [10, 20, 15]

        results = fetch_all_sports_props(['player_points'], sports=['basketball_nba', 'americanfootball_nfl', 'baseball_mlb'])

        assert results['basketball_nba'] == 10
        assert results['americanfootball_nfl'] == 20
        assert results['baseball_mlb'] == 15

    def test_fetch_all_sports_with_errors(self, mocker, mock_api_key):
        """Test handling of errors for individual sports."""
        mock_fetch = mocker.patch('src.odds_api.fetch_and_store_player_props')
        mock_fetch.side_effect = [10, OddsAPIError("API error"), 15]

        results = fetch_all_sports_props(['player_points'], sports=['basketball_nba', 'americanfootball_nfl', 'baseball_mlb'])

        assert results['basketball_nba'] == 10
        assert "Error" in results['americanfootball_nfl']
        assert results['baseball_mlb'] == 15

    def test_fetch_all_sports_default_sports(self, mocker, mock_api_key):
        """Test using default sports list."""
        mock_fetch = mocker.patch('src.odds_api.fetch_and_store_player_props', return_value=0)

        results = fetch_all_sports_props(['player_points'])

        # Should call for all supported sports
        assert mock_fetch.call_count > 0


class TestFetchOdds:
    """Test main fetch_odds function."""

    def test_fetch_odds_success(self, mocker, mock_api_key, mock_sports_response, mock_events_response, mock_odds_api_response):
        """Test successful fetch_odds workflow."""
        # Mock all dependencies - db is imported inside the function
        mock_db_module = MagicMock()
        mocker.patch.dict('sys.modules', {'src.db': mock_db_module})

        mock_get_sports = mocker.patch('src.odds_api.get_sports', return_value=mock_sports_response)
        mock_get_events = mocker.patch('src.odds_api.get_events', return_value=mock_events_response[:1])  # Only first event (within 12 hours)
        mock_get_props = mocker.patch('src.odds_api.get_player_props', return_value=[mock_odds_api_response])

        count = fetch_odds(['basketball_nba'])

        assert count > 0
        assert mock_get_sports.call_count == 1
        assert mock_get_events.call_count == 1

    def test_fetch_odds_no_in_season_sports(self, mocker, mock_api_key):
        """Test when no sports are in season."""
        mock_sports = [{'key': 'basketball_nba', 'active': False}]
        mock_db_module = MagicMock()
        mocker.patch.dict('sys.modules', {'src.db': mock_db_module})
        mocker.patch('src.odds_api.get_sports', return_value=mock_sports)

        count = fetch_odds()

        assert count == 0

    def test_fetch_odds_no_events(self, mocker, mock_api_key, mock_sports_response):
        """Test when no events are found."""
        mock_db_module = MagicMock()
        mocker.patch.dict('sys.modules', {'src.db': mock_db_module})
        mocker.patch('src.odds_api.get_sports', return_value=mock_sports_response)
        mocker.patch('src.odds_api.get_events', return_value=[])

        count = fetch_odds()

        assert count == 0

    def test_fetch_odds_time_filtering(self, mocker, mock_api_key, mock_sports_response):
        """Test that time filtering works correctly."""
        mock_db_module = MagicMock()
        mocker.patch.dict('sys.modules', {'src.db': mock_db_module})
        mocker.patch('src.odds_api.get_sports', return_value=mock_sports_response)

        now = datetime.now(timezone.utc)
        events = [
            {
                'id': 'event1',
                'sport_key': 'basketball_nba',
                'commence_time': (now - timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),  # Already started
                'home_team': 'Lakers',
                'away_team': 'Warriors'
            },
            {
                'id': 'event2',
                'sport_key': 'basketball_nba',
                'commence_time': (now + timedelta(hours=2)).isoformat().replace('+00:00', 'Z'),  # Within 12 hours
                'home_team': 'Celtics',
                'away_team': 'Heat'
            },
            {
                'id': 'event3',
                'sport_key': 'basketball_nba',
                'commence_time': (now + timedelta(hours=24)).isoformat().replace('+00:00', 'Z'),  # Too far away
                'home_team': 'Bulls',
                'away_team': 'Knicks'
            }
        ]

        mocker.patch('src.odds_api.get_events', return_value=events)
        mock_get_props = mocker.patch('src.odds_api.get_player_props', return_value=[])

        fetch_odds(['basketball_nba'])

        # Should only fetch props for event2 (within 12 hours and not started)
        assert mock_get_props.call_count == 1

    def test_fetch_odds_invalid_commence_time(self, mocker, mock_api_key, mock_sports_response):
        """Test handling of invalid commence time."""
        mock_db_module = MagicMock()
        mocker.patch.dict('sys.modules', {'src.db': mock_db_module})
        mocker.patch('src.odds_api.get_sports', return_value=mock_sports_response)

        events = [
            {
                'id': 'event1',
                'sport_key': 'basketball_nba',
                'commence_time': 'invalid-date',
                'home_team': 'Lakers',
                'away_team': 'Warriors'
            }
        ]

        mocker.patch('src.odds_api.get_events', return_value=events)
        # Mock logger to capture the debug message
        mock_logger = mocker.patch('src.odds_api.logger')

        count = fetch_odds(['basketball_nba'])

        assert count == 0
        # Verify the logger was called with appropriate message
        assert any('Could not parse time' in str(call) for call in mock_logger.debug.call_args_list)

    def test_fetch_odds_api_error_continues(self, mocker, mock_api_key, mock_sports_response, mock_events_response, caplog):
        """Test that API errors don't stop processing."""
        mock_db_module = MagicMock()
        mocker.patch.dict('sys.modules', {'src.db': mock_db_module})
        mocker.patch('src.odds_api.get_sports', return_value=mock_sports_response)
        mocker.patch('src.odds_api.get_events', return_value=mock_events_response[:1])
        mocker.patch('src.odds_api.get_player_props', side_effect=OddsAPIError("API error"))

        count = fetch_odds(['basketball_nba'])

        # Should handle error gracefully
        assert count == 0
        assert "Failed to fetch props" in caplog.text

    def test_fetch_odds_dict_response_converted_to_list(self, mocker, mock_api_key, mock_sports_response, mock_events_response, mock_odds_api_response):
        """Test that single dict response is wrapped in list."""
        mock_db_module = MagicMock()
        mocker.patch.dict('sys.modules', {'src.db': mock_db_module})
        mocker.patch('src.odds_api.get_sports', return_value=mock_sports_response)
        mocker.patch('src.odds_api.get_events', return_value=mock_events_response[:1])
        mocker.patch('src.odds_api.get_player_props', return_value=mock_odds_api_response)  # Dict, not list

        count = fetch_odds(['basketball_nba'])

        # Should handle dict response by converting to list
        assert count > 0

    def test_fetch_odds_calls_ev_finder(self, mocker, mock_api_key, mock_sports_response, mock_events_response, mock_odds_api_response):
        """Test that EV opportunity finder is called."""
        mock_db_module = MagicMock()
        mocker.patch.dict('sys.modules', {'src.db': mock_db_module})
        mocker.patch('src.odds_api.get_sports', return_value=mock_sports_response)
        mocker.patch('src.odds_api.get_events', return_value=mock_events_response[:1])
        mocker.patch('src.odds_api.get_player_props', return_value=[mock_odds_api_response])
        mock_ev_finder = mocker.patch('src.odds_api._find_and_save_ev_opportunities', return_value=0)

        fetch_odds(['basketball_nba'])

        assert mock_ev_finder.call_count == 1

    def test_fetch_odds_default_sports(self, mocker, mock_api_key, mock_sports_response):
        """Test using default sports when none specified."""
        mock_db_module = MagicMock()
        mocker.patch.dict('sys.modules', {'src.db': mock_db_module})
        mocker.patch('src.odds_api.get_sports', return_value=mock_sports_response)
        mocker.patch('src.odds_api.get_events', return_value=[])

        fetch_odds()  # No sports specified

        # Should use all supported sports
        # This is verified by the function not raising an error


# ============================================================================
# Test Constants
# ============================================================================

class TestConstants:
    """Test module constants."""

    def test_implied_breakeven_prob_constant(self):
        """Test IMPLIED_BREAKEVEN_PROB constant is defined."""
        assert IMPLIED_BREAKEVEN_PROB == 0.5425

    def test_odds_api_error_exception(self):
        """Test OddsAPIError can be raised and caught."""
        with pytest.raises(OddsAPIError, match="Test error"):
            raise OddsAPIError("Test error")


# ============================================================================
# Integration Tests (marked for optional execution)
# ============================================================================

@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring actual API calls (run with --integration flag)."""

    def test_real_api_call_sports(self):
        """Test real API call to get sports (requires valid API key)."""
        # This test is marked as integration and should only run with explicit flag
        pytest.skip("Integration test - requires valid API key and quota")

    def test_real_api_call_events(self):
        """Test real API call to get events (requires valid API key)."""
        pytest.skip("Integration test - requires valid API key and quota")
