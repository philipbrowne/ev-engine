"""Comprehensive tests for src/validation.py module.

Tests cover:
- validate_odds_response()
- validate_bookmaker_data()
- validate_market_data()
- validate_outcome_data()

Each function is tested for:
- Valid inputs (should return True)
- Invalid inputs (should return False and log errors)
- Edge cases (empty dicts, None, missing fields, wrong types)
- Logging behavior verification
"""

import pytest
from typing import Dict, Any
from src.validation import (
    validate_odds_response,
    validate_bookmaker_data,
    validate_market_data,
    validate_outcome_data
)


@pytest.mark.unit
class TestValidateOddsResponse:
    """Tests for validate_odds_response() function."""

    def test_valid_odds_response(self):
        """Test validation passes with all required fields."""
        data = {
            'id': 'event123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': []
        }
        assert validate_odds_response(data) is True

    def test_valid_odds_response_with_bookmakers(self):
        """Test validation passes with populated bookmakers list."""
        data = {
            'id': 'event456',
            'sport_key': 'americanfootball_nfl',
            'commence_time': '2024-02-01T18:30:00Z',
            'bookmakers': [
                {'key': 'pinnacle', 'markets': []},
                {'key': 'draftkings', 'markets': []}
            ]
        }
        assert validate_odds_response(data) is True

    def test_valid_odds_response_with_extra_fields(self):
        """Test validation passes with extra fields beyond required ones."""
        data = {
            'id': 'event789',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-20T20:00:00Z',
            'bookmakers': [],
            'home_team': 'Lakers',
            'away_team': 'Celtics',
            'extra_field': 'should be ignored'
        }
        assert validate_odds_response(data) is True

    def test_invalid_not_dict(self, caplog):
        """Test validation fails when input is not a dictionary."""
        assert validate_odds_response("not a dict") is False
        assert "Odds response is not a dictionary" in caplog.text

    def test_invalid_not_dict_list(self, caplog):
        """Test validation fails when input is a list."""
        assert validate_odds_response([1, 2, 3]) is False
        assert "Odds response is not a dictionary" in caplog.text

    def test_invalid_none(self, caplog):
        """Test validation fails when input is None."""
        assert validate_odds_response(None) is False
        assert "Odds response is not a dictionary" in caplog.text

    def test_missing_id_field(self, caplog):
        """Test validation fails when 'id' field is missing."""
        data = {
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': []
        }
        assert validate_odds_response(data) is False
        assert "Missing required field: id" in caplog.text

    def test_missing_sport_key_field(self, caplog):
        """Test validation fails when 'sport_key' field is missing."""
        data = {
            'id': 'event123',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': []
        }
        assert validate_odds_response(data) is False
        assert "Missing required field: sport_key" in caplog.text

    def test_missing_commence_time_field(self, caplog):
        """Test validation fails when 'commence_time' field is missing."""
        data = {
            'id': 'event123',
            'sport_key': 'basketball_nba',
            'bookmakers': []
        }
        assert validate_odds_response(data) is False
        assert "Missing required field: commence_time" in caplog.text

    def test_missing_bookmakers_field(self, caplog):
        """Test validation fails when 'bookmakers' field is missing."""
        data = {
            'id': 'event123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z'
        }
        assert validate_odds_response(data) is False
        assert "Missing required field: bookmakers" in caplog.text

    def test_missing_multiple_fields(self, caplog):
        """Test validation fails and logs first missing field."""
        data = {
            'id': 'event123'
        }
        assert validate_odds_response(data) is False
        # Should log error for first missing field encountered
        assert "Missing required field:" in caplog.text

    def test_empty_dict(self, caplog):
        """Test validation fails with empty dictionary."""
        assert validate_odds_response({}) is False
        assert "Missing required field:" in caplog.text

    def test_bookmakers_not_list(self, caplog):
        """Test validation fails when bookmakers is not a list."""
        data = {
            'id': 'event123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': "not a list"
        }
        assert validate_odds_response(data) is False
        assert "Bookmakers field is not a list" in caplog.text

    def test_bookmakers_is_dict(self, caplog):
        """Test validation fails when bookmakers is a dictionary."""
        data = {
            'id': 'event123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': {'key': 'value'}
        }
        assert validate_odds_response(data) is False
        assert "Bookmakers field is not a list" in caplog.text

    def test_bookmakers_is_none(self, caplog):
        """Test validation fails when bookmakers is None."""
        data = {
            'id': 'event123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': None
        }
        assert validate_odds_response(data) is False
        assert "Bookmakers field is not a list" in caplog.text

    def test_fields_with_none_values(self, caplog):
        """Test validation passes even if field values are None (field exists)."""
        data = {
            'id': None,
            'sport_key': None,
            'commence_time': None,
            'bookmakers': []
        }
        # Fields exist, just have None values
        assert validate_odds_response(data) is True

    def test_fields_with_empty_strings(self):
        """Test validation passes with empty string values."""
        data = {
            'id': '',
            'sport_key': '',
            'commence_time': '',
            'bookmakers': []
        }
        assert validate_odds_response(data) is True


@pytest.mark.unit
class TestValidateBookmakerData:
    """Tests for validate_bookmaker_data() function."""

    def test_valid_bookmaker_data(self):
        """Test validation passes with valid bookmaker data."""
        bookmaker = {
            'key': 'pinnacle',
            'markets': []
        }
        assert validate_bookmaker_data(bookmaker) is True

    def test_valid_bookmaker_data_with_markets(self):
        """Test validation passes with populated markets."""
        bookmaker = {
            'key': 'draftkings',
            'markets': [
                {'key': 'player_points', 'outcomes': []},
                {'key': 'player_assists', 'outcomes': []}
            ]
        }
        assert validate_bookmaker_data(bookmaker) is True

    def test_valid_bookmaker_with_extra_fields(self):
        """Test validation passes with extra fields."""
        bookmaker = {
            'key': 'fanduel',
            'title': 'FanDuel',
            'markets': [],
            'extra_field': 'ignored'
        }
        assert validate_bookmaker_data(bookmaker) is True

    def test_invalid_not_dict(self):
        """Test validation fails when input is not a dictionary."""
        assert validate_bookmaker_data("not a dict") is False

    def test_invalid_none(self):
        """Test validation fails when input is None."""
        assert validate_bookmaker_data(None) is False

    def test_invalid_list(self):
        """Test validation fails when input is a list."""
        assert validate_bookmaker_data([1, 2, 3]) is False

    def test_missing_key_field(self, caplog):
        """Test validation fails when 'key' field is missing."""
        bookmaker = {'markets': []}
        assert validate_bookmaker_data(bookmaker) is False
        assert "Bookmaker missing field: key" in caplog.text

    def test_missing_markets_field(self, caplog):
        """Test validation fails when 'markets' field is missing."""
        bookmaker = {'key': 'pinnacle'}
        assert validate_bookmaker_data(bookmaker) is False
        assert "Bookmaker missing field: markets" in caplog.text

    def test_empty_dict(self, caplog):
        """Test validation fails with empty dictionary."""
        assert validate_bookmaker_data({}) is False
        assert "Bookmaker missing field:" in caplog.text

    def test_markets_not_list(self, caplog):
        """Test validation fails when markets is not a list."""
        bookmaker = {
            'key': 'pinnacle',
            'markets': "not a list"
        }
        assert validate_bookmaker_data(bookmaker) is False
        assert "Bookmaker markets field is not a list" in caplog.text

    def test_markets_is_dict(self, caplog):
        """Test validation fails when markets is a dictionary."""
        bookmaker = {
            'key': 'pinnacle',
            'markets': {'key': 'value'}
        }
        assert validate_bookmaker_data(bookmaker) is False
        assert "Bookmaker markets field is not a list" in caplog.text

    def test_markets_is_none(self, caplog):
        """Test validation fails when markets is None."""
        bookmaker = {
            'key': 'pinnacle',
            'markets': None
        }
        assert validate_bookmaker_data(bookmaker) is False
        assert "Bookmaker markets field is not a list" in caplog.text

    def test_fields_with_none_values(self):
        """Test validation passes even if key is None (field exists)."""
        bookmaker = {
            'key': None,
            'markets': []
        }
        assert validate_bookmaker_data(bookmaker) is True

    def test_fields_with_empty_strings(self):
        """Test validation passes with empty string values."""
        bookmaker = {
            'key': '',
            'markets': []
        }
        assert validate_bookmaker_data(bookmaker) is True

    def test_logging_uses_warning_level(self, caplog):
        """Test that validation logs at WARNING level, not ERROR."""
        import logging
        caplog.set_level(logging.WARNING)

        bookmaker = {'key': 'test'}  # Missing markets
        validate_bookmaker_data(bookmaker)

        # Check that warning was logged
        assert any(record.levelname == 'WARNING' for record in caplog.records)


@pytest.mark.unit
class TestValidateMarketData:
    """Tests for validate_market_data() function."""

    def test_valid_market_data(self):
        """Test validation passes with valid market data."""
        market = {
            'key': 'player_points',
            'outcomes': []
        }
        assert validate_market_data(market) is True

    def test_valid_market_with_outcomes(self):
        """Test validation passes with populated outcomes."""
        market = {
            'key': 'player_assists',
            'outcomes': [
                {'name': 'LeBron James', 'price': -110},
                {'name': 'LeBron James', 'price': -110}
            ]
        }
        assert validate_market_data(market) is True

    def test_valid_market_with_extra_fields(self):
        """Test validation passes with extra fields."""
        market = {
            'key': 'player_rebounds',
            'last_update': '2024-01-15T19:00:00Z',
            'outcomes': [],
            'extra_field': 'ignored'
        }
        assert validate_market_data(market) is True

    def test_invalid_not_dict(self):
        """Test validation fails when input is not a dictionary."""
        assert validate_market_data("not a dict") is False

    def test_invalid_none(self):
        """Test validation fails when input is None."""
        assert validate_market_data(None) is False

    def test_invalid_list(self):
        """Test validation fails when input is a list."""
        assert validate_market_data([1, 2, 3]) is False

    def test_missing_key_field(self):
        """Test validation fails when 'key' field is missing."""
        market = {'outcomes': []}
        assert validate_market_data(market) is False

    def test_missing_outcomes_field(self):
        """Test validation fails when 'outcomes' field is missing."""
        market = {'key': 'player_points'}
        assert validate_market_data(market) is False

    def test_empty_dict(self):
        """Test validation fails with empty dictionary."""
        assert validate_market_data({}) is False

    def test_outcomes_not_list(self):
        """Test validation fails when outcomes is not a list."""
        market = {
            'key': 'player_points',
            'outcomes': "not a list"
        }
        assert validate_market_data(market) is False

    def test_outcomes_is_dict(self):
        """Test validation fails when outcomes is a dictionary."""
        market = {
            'key': 'player_points',
            'outcomes': {'name': 'value'}
        }
        assert validate_market_data(market) is False

    def test_outcomes_is_none(self):
        """Test validation fails when outcomes is None."""
        market = {
            'key': 'player_points',
            'outcomes': None
        }
        assert validate_market_data(market) is False

    def test_fields_with_none_values(self):
        """Test validation passes even if key is None (field exists)."""
        market = {
            'key': None,
            'outcomes': []
        }
        assert validate_market_data(market) is True

    def test_fields_with_empty_strings(self):
        """Test validation passes with empty string values."""
        market = {
            'key': '',
            'outcomes': []
        }
        assert validate_market_data(market) is True

    def test_no_logging_on_failure(self, caplog):
        """Test that market validation doesn't log errors (silent failure)."""
        market = {'key': 'test'}  # Missing outcomes
        validate_market_data(market)

        # Should not log anything (unlike bookmaker validation)
        assert len(caplog.records) == 0


@pytest.mark.unit
class TestValidateOutcomeData:
    """Tests for validate_outcome_data() function."""

    def test_valid_outcome_data_int_price(self):
        """Test validation passes with integer price."""
        outcome = {
            'name': 'LeBron James',
            'price': -110
        }
        assert validate_outcome_data(outcome) is True

    def test_valid_outcome_data_float_price(self):
        """Test validation passes with float price."""
        outcome = {
            'name': 'Anthony Davis',
            'price': -110.5
        }
        assert validate_outcome_data(outcome) is True

    def test_valid_outcome_data_string_price(self):
        """Test validation passes with numeric string price."""
        outcome = {
            'name': 'Stephen Curry',
            'price': "150"
        }
        assert validate_outcome_data(outcome) is True

    def test_valid_outcome_with_extra_fields(self):
        """Test validation passes with extra fields."""
        outcome = {
            'name': 'Kevin Durant',
            'price': 200,
            'point': 25.5,
            'description': 'Over',
            'extra_field': 'ignored'
        }
        assert validate_outcome_data(outcome) is True

    def test_valid_outcome_positive_price(self):
        """Test validation passes with positive price."""
        outcome = {
            'name': 'Giannis Antetokounmpo',
            'price': 150
        }
        assert validate_outcome_data(outcome) is True

    def test_valid_outcome_negative_price(self):
        """Test validation passes with negative price."""
        outcome = {
            'name': 'Damian Lillard',
            'price': -200
        }
        assert validate_outcome_data(outcome) is True

    def test_valid_outcome_zero_price(self):
        """Test validation passes with zero price (edge case)."""
        outcome = {
            'name': 'Jrue Holiday',
            'price': 0
        }
        assert validate_outcome_data(outcome) is True

    def test_invalid_not_dict(self):
        """Test validation fails when input is not a dictionary."""
        assert validate_outcome_data("not a dict") is False

    def test_invalid_none(self):
        """Test validation fails when input is None."""
        assert validate_outcome_data(None) is False

    def test_invalid_list(self):
        """Test validation fails when input is a list."""
        assert validate_outcome_data([1, 2, 3]) is False

    def test_missing_name_field(self):
        """Test validation fails when 'name' field is missing."""
        outcome = {'price': -110}
        assert validate_outcome_data(outcome) is False

    def test_missing_price_field(self):
        """Test validation fails when 'price' field is missing."""
        outcome = {'name': 'LeBron James'}
        assert validate_outcome_data(outcome) is False

    def test_empty_dict(self):
        """Test validation fails with empty dictionary."""
        assert validate_outcome_data({}) is False

    def test_invalid_price_string(self, caplog):
        """Test validation fails with non-numeric string price."""
        outcome = {
            'name': 'LeBron James',
            'price': 'not a number'
        }
        assert validate_outcome_data(outcome) is False
        assert "Invalid price value: not a number" in caplog.text

    def test_invalid_price_none(self, caplog):
        """Test validation fails when price is None."""
        outcome = {
            'name': 'LeBron James',
            'price': None
        }
        assert validate_outcome_data(outcome) is False
        assert "Invalid price value: None" in caplog.text

    def test_invalid_price_dict(self, caplog):
        """Test validation fails when price is a dictionary."""
        outcome = {
            'name': 'LeBron James',
            'price': {'value': 110}
        }
        assert validate_outcome_data(outcome) is False
        assert "Invalid price value:" in caplog.text

    def test_invalid_price_list(self, caplog):
        """Test validation fails when price is a list."""
        outcome = {
            'name': 'LeBron James',
            'price': [110]
        }
        assert validate_outcome_data(outcome) is False
        assert "Invalid price value:" in caplog.text

    def test_invalid_price_empty_string(self, caplog):
        """Test validation fails with empty string price."""
        outcome = {
            'name': 'LeBron James',
            'price': ''
        }
        assert validate_outcome_data(outcome) is False
        assert "Invalid price value:" in caplog.text

    def test_fields_with_none_name(self):
        """Test validation passes even if name is None (field exists)."""
        outcome = {
            'name': None,
            'price': -110
        }
        assert validate_outcome_data(outcome) is True

    def test_fields_with_empty_string_name(self):
        """Test validation passes with empty string name."""
        outcome = {
            'name': '',
            'price': -110
        }
        assert validate_outcome_data(outcome) is True

    def test_logging_uses_warning_level(self, caplog):
        """Test that price validation logs at WARNING level."""
        import logging
        caplog.set_level(logging.WARNING)

        outcome = {
            'name': 'Player',
            'price': 'invalid'
        }
        validate_outcome_data(outcome)

        # Check that warning was logged
        assert any(record.levelname == 'WARNING' for record in caplog.records)

    def test_numeric_string_with_decimal(self):
        """Test validation passes with decimal string price."""
        outcome = {
            'name': 'Player',
            'price': "110.5"
        }
        assert validate_outcome_data(outcome) is True

    def test_numeric_string_with_negative(self):
        """Test validation passes with negative string price."""
        outcome = {
            'name': 'Player',
            'price': "-110"
        }
        assert validate_outcome_data(outcome) is True

    def test_scientific_notation_price(self):
        """Test validation passes with scientific notation price."""
        outcome = {
            'name': 'Player',
            'price': 1e2  # 100.0
        }
        assert validate_outcome_data(outcome) is True

    def test_scientific_notation_string_price(self):
        """Test validation passes with scientific notation string price."""
        outcome = {
            'name': 'Player',
            'price': "1e2"
        }
        assert validate_outcome_data(outcome) is True


@pytest.mark.unit
class TestValidationIntegration:
    """Integration tests for multiple validation functions working together."""

    def test_full_valid_response_chain(self, mock_player_props_response):
        """Test validation chain on full valid response."""
        # Validate top-level response
        assert validate_odds_response(mock_player_props_response) is True

        # Validate each bookmaker
        for bookmaker in mock_player_props_response['bookmakers']:
            assert validate_bookmaker_data(bookmaker) is True

            # Validate each market
            for market in bookmaker['markets']:
                assert validate_market_data(market) is True

                # Validate each outcome
                for outcome in market['outcomes']:
                    assert validate_outcome_data(outcome) is True

    def test_partial_invalid_response(self):
        """Test that one invalid bookmaker doesn't affect others."""
        response = {
            'id': 'event123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': [
                {'key': 'pinnacle', 'markets': []},  # Valid
                {'key': 'invalid'},  # Invalid - missing markets
                {'key': 'draftkings', 'markets': []}  # Valid
            ]
        }

        # Top-level should be valid
        assert validate_odds_response(response) is True

        # Individual bookmakers validated separately
        assert validate_bookmaker_data(response['bookmakers'][0]) is True
        assert validate_bookmaker_data(response['bookmakers'][1]) is False
        assert validate_bookmaker_data(response['bookmakers'][2]) is True

    def test_nested_invalid_data(self):
        """Test validation at different nesting levels."""
        response = {
            'id': 'event123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': [
                {
                    'key': 'pinnacle',
                    'markets': [
                        {
                            'key': 'player_points',
                            'outcomes': [
                                {'name': 'Player', 'price': -110},  # Valid
                                {'name': 'Player', 'price': 'invalid'}  # Invalid
                            ]
                        }
                    ]
                }
            ]
        }

        # Each level validated independently
        assert validate_odds_response(response) is True
        assert validate_bookmaker_data(response['bookmakers'][0]) is True
        assert validate_market_data(response['bookmakers'][0]['markets'][0]) is True
        assert validate_outcome_data(
            response['bookmakers'][0]['markets'][0]['outcomes'][0]
        ) is True
        assert validate_outcome_data(
            response['bookmakers'][0]['markets'][0]['outcomes'][1]
        ) is False

    def test_empty_nested_structures(self):
        """Test validation with empty but valid nested structures."""
        response = {
            'id': 'event123',
            'sport_key': 'basketball_nba',
            'commence_time': '2024-01-15T19:00:00Z',
            'bookmakers': []
        }

        assert validate_odds_response(response) is True

        # Add bookmaker with empty markets
        response['bookmakers'].append({
            'key': 'pinnacle',
            'markets': []
        })

        assert validate_bookmaker_data(response['bookmakers'][0]) is True

        # Add market with empty outcomes
        response['bookmakers'][0]['markets'].append({
            'key': 'player_points',
            'outcomes': []
        })

        assert validate_market_data(response['bookmakers'][0]['markets'][0]) is True
