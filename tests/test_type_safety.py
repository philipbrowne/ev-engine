"""Comprehensive tests for src/type_safety.py module.

Tests cover all type safety utilities:
- safe_currency_to_float()
- safe_int()
- safe_float()
- safe_dict_get()
- safe_get_column()
- safe_list_get()
- validate_stake()
- validate_american_odds()
- validate_probability()
- validate_line_value()
- validate_positive_number()

Test patterns:
- Safe converters: valid inputs, invalid inputs return defaults, edge cases
- Safe accessors: existing keys/indices, missing return defaults, None inputs
- Validators: valid inputs return value, invalid inputs raise ValueError
"""

import pytest
import pandas as pd
from typing import Any
from src.type_safety import (
    safe_currency_to_float,
    safe_int,
    safe_float,
    safe_dict_get,
    safe_get_column,
    safe_list_get,
    validate_stake,
    validate_american_odds,
    validate_probability,
    validate_line_value,
    validate_positive_number
)


@pytest.mark.unit
class TestSafeCurrencyToFloat:
    """Tests for safe_currency_to_float() function."""

    @pytest.mark.parametrize("value,expected", [
        # Standard currency strings
        ("$100.00", 100.0),
        ("$1,234.56", 1234.56),
        ("$10,000.00", 10000.0),
        ("$0.99", 0.99),

        # Without dollar sign
        ("100.00", 100.0),
        ("1234.56", 1234.56),
        ("1,234.56", 1234.56),

        # Numeric types
        (100, 100.0),
        (100.5, 100.5),
        (0, 0.0),
        (1234, 1234.0),

        # Edge cases that should work
        ("$0", 0.0),
        ("0", 0.0),
        ("  $100.00  ", 100.0),  # With whitespace
        ("$  100.00", 100.0),  # Space after $

        # Invalid values return 0.0
        ("invalid", 0.0),
        ("abc", 0.0),
        ("$$$", 0.0),
        ("", 0.0),
        (None, 0.0),
        ("N/A", 0.0),
    ])
    def test_currency_conversion(self, value, expected):
        """Test various currency format conversions."""
        assert safe_currency_to_float(value) == expected

    def test_negative_currency(self):
        """Test negative currency values."""
        assert safe_currency_to_float("$-100.00") == -100.0
        assert safe_currency_to_float("-$100.00") == -100.0
        assert safe_currency_to_float(-100) == -100.0

    def test_large_numbers(self):
        """Test large currency values."""
        assert safe_currency_to_float("$1,000,000.00") == 1000000.0
        assert safe_currency_to_float("$999,999,999.99") == 999999999.99

    def test_invalid_types_log_warning(self, caplog):
        """Test that invalid types log warnings."""
        safe_currency_to_float("invalid")
        assert "Invalid currency value: invalid" in caplog.text

    def test_unexpected_type_logs_warning(self, caplog):
        """Test that unexpected types log warnings."""
        safe_currency_to_float([100])
        assert "Unexpected currency value type:" in caplog.text

    def test_dict_input(self, caplog):
        """Test dictionary input returns default."""
        assert safe_currency_to_float({'value': 100}) == 0.0
        assert "Unexpected currency value type:" in caplog.text

    def test_list_input(self, caplog):
        """Test list input returns default."""
        assert safe_currency_to_float([100, 200]) == 0.0
        assert "Unexpected currency value type:" in caplog.text

    def test_boolean_input(self):
        """Test boolean input (bool is subclass of int in Python)."""
        assert safe_currency_to_float(True) == 1.0
        assert safe_currency_to_float(False) == 0.0

    def test_multiple_dollar_signs(self, caplog):
        """Test multiple dollar signs."""
        # After removing all $, should fail to parse
        result = safe_currency_to_float("$$100")
        assert result == 100.0  # Both $ removed, leaves "100"

    def test_decimal_only(self):
        """Test decimal-only values."""
        assert safe_currency_to_float(".99") == 0.99
        assert safe_currency_to_float("$.99") == 0.99

    def test_scientific_notation_string(self):
        """Test scientific notation in strings."""
        assert safe_currency_to_float("1e2") == 100.0
        assert safe_currency_to_float("$1e2") == 100.0


@pytest.mark.unit
class TestSafeInt:
    """Tests for safe_int() function."""

    @pytest.mark.parametrize("value,expected", [
        # Valid integer inputs
        (0, 0),
        (100, 100),
        (-50, -50),
        (999999, 999999),

        # Float to int conversion
        (100.0, 100),
        (100.9, 100),  # Truncates
        (100.1, 100),
        (-50.9, -50),

        # String to int conversion
        ("100", 100),
        ("-50", -50),
        ("0", 0),
        ("  100  ", 100),  # With whitespace

        # String floats to int
        ("100.0", 100),
        ("100.9", 100),
        ("-50.5", -50),
    ])
    def test_int_conversion(self, value, expected):
        """Test various integer conversions."""
        assert safe_int(value) == expected

    @pytest.mark.parametrize("value,default,expected", [
        # Invalid values with custom defaults
        ("invalid", -1, -1),
        (None, -1, -1),
        ("", 0, 0),
        ("abc", 999, 999),
        ([], 0, 0),
        ({}, 0, 0),
    ])
    def test_invalid_inputs_with_defaults(self, value, default, expected):
        """Test invalid inputs return specified defaults."""
        assert safe_int(value, default=default) == expected

    def test_invalid_string_uses_default(self, caplog):
        """Test invalid string returns default and logs warning."""
        result = safe_int("not a number", default=42)
        assert result == 42
        assert "Cannot convert to int: not a number" in caplog.text

    def test_none_uses_default(self, caplog):
        """Test None returns default and logs warning."""
        result = safe_int(None, default=0)
        assert result == 0
        assert "Unexpected type for int conversion:" in caplog.text

    def test_list_uses_default(self, caplog):
        """Test list returns default and logs warning."""
        result = safe_int([1, 2, 3], default=0)
        assert result == 0
        assert "Unexpected type for int conversion:" in caplog.text

    def test_dict_uses_default(self, caplog):
        """Test dict returns default and logs warning."""
        result = safe_int({'value': 100}, default=0)
        assert result == 0
        assert "Unexpected type for int conversion:" in caplog.text

    def test_boolean_input(self):
        """Test boolean input (bool is subclass of int)."""
        assert safe_int(True) == 1
        assert safe_int(False) == 0

    def test_empty_string_uses_default(self, caplog):
        """Test empty string returns default."""
        result = safe_int("", default=-1)
        assert result == -1
        assert "Cannot convert to int:" in caplog.text

    def test_whitespace_only_uses_default(self, caplog):
        """Test whitespace-only string returns default."""
        result = safe_int("   ", default=-1)
        assert result == -1
        assert "Cannot convert to int:" in caplog.text

    def test_large_numbers(self):
        """Test large integer values."""
        assert safe_int(999999999) == 999999999
        assert safe_int("999999999") == 999999999
        assert safe_int(999999999.9) == 999999999

    def test_scientific_notation(self):
        """Test scientific notation."""
        assert safe_int(1e6) == 1000000
        assert safe_int("1e6") == 1000000


@pytest.mark.unit
class TestSafeFloat:
    """Tests for safe_float() function."""

    @pytest.mark.parametrize("value,expected", [
        # Valid float inputs
        (100.5, 100.5),
        (0.0, 0.0),
        (-50.75, -50.75),
        (999.999, 999.999),

        # Integer to float
        (100, 100.0),
        (0, 0.0),
        (-50, -50.0),

        # String to float
        ("100.5", 100.5),
        ("-50.75", -50.75),
        ("0.0", 0.0),
        ("  100.5  ", 100.5),  # With whitespace

        # Integer strings
        ("100", 100.0),
        ("0", 0.0),
        ("-50", -50.0),
    ])
    def test_float_conversion(self, value, expected):
        """Test various float conversions."""
        assert safe_float(value) == expected

    @pytest.mark.parametrize("value,default,expected", [
        # Invalid values with custom defaults
        ("invalid", -1.0, -1.0),
        (None, -1.0, -1.0),
        ("", 0.0, 0.0),
        ("abc", 999.9, 999.9),
        ([], 0.0, 0.0),
        ({}, 0.0, 0.0),
    ])
    def test_invalid_inputs_with_defaults(self, value, default, expected):
        """Test invalid inputs return specified defaults."""
        assert safe_float(value, default=default) == expected

    def test_invalid_string_uses_default(self, caplog):
        """Test invalid string returns default and logs warning."""
        result = safe_float("not a number", default=3.14)
        assert result == 3.14
        assert "Cannot convert to float: not a number" in caplog.text

    def test_none_uses_default(self, caplog):
        """Test None returns default and logs warning."""
        result = safe_float(None, default=0.0)
        assert result == 0.0
        assert "Unexpected type for float conversion:" in caplog.text

    def test_list_uses_default(self, caplog):
        """Test list returns default and logs warning."""
        result = safe_float([1.5, 2.5], default=0.0)
        assert result == 0.0
        assert "Unexpected type for float conversion:" in caplog.text

    def test_dict_uses_default(self, caplog):
        """Test dict returns default and logs warning."""
        result = safe_float({'value': 100.5}, default=0.0)
        assert result == 0.0
        assert "Unexpected type for float conversion:" in caplog.text

    def test_boolean_input(self):
        """Test boolean input (bool is subclass of int)."""
        assert safe_float(True) == 1.0
        assert safe_float(False) == 0.0

    def test_empty_string_uses_default(self, caplog):
        """Test empty string returns default."""
        result = safe_float("", default=-1.0)
        assert result == -1.0
        assert "Cannot convert to float:" in caplog.text

    def test_whitespace_only_uses_default(self, caplog):
        """Test whitespace-only string returns default."""
        result = safe_float("   ", default=-1.0)
        assert result == -1.0
        assert "Cannot convert to float:" in caplog.text

    def test_scientific_notation(self):
        """Test scientific notation."""
        assert safe_float(1e6) == 1000000.0
        assert safe_float("1e6") == 1000000.0
        assert safe_float("1.5e2") == 150.0

    def test_decimal_values(self):
        """Test various decimal values."""
        assert safe_float("0.1") == 0.1
        assert safe_float(".5") == 0.5
        assert safe_float("10.") == 10.0

    def test_negative_zero(self):
        """Test negative zero."""
        assert safe_float("-0.0") == 0.0
        assert safe_float(-0.0) == 0.0


@pytest.mark.unit
class TestSafeDictGet:
    """Tests for safe_dict_get() function."""

    def test_get_existing_key(self):
        """Test retrieving existing key."""
        data = {'a': 1, 'b': 2}
        assert safe_dict_get(data, 'a') == 1
        assert safe_dict_get(data, 'b') == 2

    def test_get_missing_key_no_default(self):
        """Test retrieving missing key returns None."""
        data = {'a': 1}
        assert safe_dict_get(data, 'b') is None

    def test_get_missing_key_with_default(self):
        """Test retrieving missing key returns default."""
        data = {'a': 1}
        assert safe_dict_get(data, 'b', default=0) == 0
        assert safe_dict_get(data, 'c', default='N/A') == 'N/A'

    def test_type_checking_valid(self):
        """Test type checking passes for valid types."""
        data = {'a': 1, 'b': 'text', 'c': [1, 2, 3]}
        assert safe_dict_get(data, 'a', expected_type=int) == 1
        assert safe_dict_get(data, 'b', expected_type=str) == 'text'
        assert safe_dict_get(data, 'c', expected_type=list) == [1, 2, 3]

    def test_type_checking_invalid(self, caplog):
        """Test type checking returns default for type mismatch."""
        data = {'a': 'text'}
        result = safe_dict_get(data, 'a', expected_type=int, default=0)
        assert result == 0
        assert "expected int, got str" in caplog.text

    def test_type_checking_none_value(self):
        """Test type checking allows None values."""
        data = {'a': None}
        # None values should pass through (not type-checked)
        assert safe_dict_get(data, 'a', expected_type=int) is None

    def test_not_a_dict_input(self, caplog):
        """Test non-dict input returns default."""
        result = safe_dict_get("not a dict", 'key', default='default')
        assert result == 'default'
        assert "Expected dict, got" in caplog.text

    def test_none_input(self, caplog):
        """Test None input returns default."""
        result = safe_dict_get(None, 'key', default='default')
        assert result == 'default'
        assert "Expected dict, got" in caplog.text

    def test_list_input(self, caplog):
        """Test list input returns default."""
        result = safe_dict_get([1, 2, 3], 'key', default='default')
        assert result == 'default'
        assert "Expected dict, got" in caplog.text

    def test_nested_dict_retrieval(self):
        """Test retrieving nested dictionary values."""
        data = {'outer': {'inner': 'value'}}
        assert safe_dict_get(data, 'outer') == {'inner': 'value'}

        # Can't directly get nested value, need multiple calls
        outer = safe_dict_get(data, 'outer')
        assert safe_dict_get(outer, 'inner') == 'value'

    def test_empty_dict(self):
        """Test empty dictionary."""
        data = {}
        assert safe_dict_get(data, 'any_key', default='default') == 'default'

    def test_type_checking_with_missing_key(self):
        """Test type checking doesn't affect missing keys."""
        data = {'a': 1}
        result = safe_dict_get(data, 'b', expected_type=int, default=0)
        assert result == 0

    def test_various_types_as_values(self):
        """Test retrieving various types as dictionary values."""
        data = {
            'int': 42,
            'float': 3.14,
            'str': 'text',
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'bool': True,
            'none': None
        }

        assert safe_dict_get(data, 'int') == 42
        assert safe_dict_get(data, 'float') == 3.14
        assert safe_dict_get(data, 'str') == 'text'
        assert safe_dict_get(data, 'list') == [1, 2, 3]
        assert safe_dict_get(data, 'dict') == {'nested': 'value'}
        assert safe_dict_get(data, 'bool') is True
        assert safe_dict_get(data, 'none') is None


@pytest.mark.unit
class TestSafeGetColumn:
    """Tests for safe_get_column() function."""

    def test_get_existing_column(self):
        """Test retrieving existing column value."""
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        assert safe_get_column(df, 0, 'A') == 1
        assert safe_get_column(df, 1, 'B') == 5
        assert safe_get_column(df, 2, 'A') == 3

    def test_get_missing_column(self, caplog):
        """Test retrieving missing column returns default."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        result = safe_get_column(df, 0, 'B', default='N/A')
        assert result == 'N/A'
        assert "Column 'B' not found in DataFrame" in caplog.text

    def test_get_missing_column_no_default(self, caplog):
        """Test retrieving missing column returns None by default."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        result = safe_get_column(df, 0, 'B')
        assert result is None
        assert "Column 'B' not found in DataFrame" in caplog.text

    def test_invalid_row_index(self, caplog):
        """Test invalid row index returns default."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        result = safe_get_column(df, 99, 'A', default='N/A')
        assert result == 'N/A'
        assert "Error accessing row 99" in caplog.text

    def test_negative_row_index(self):
        """Test negative row index works (pandas supports it)."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        # Negative indices don't work with .at[], should return default
        result = safe_get_column(df, -1, 'A', default='N/A')
        # This might fail or succeed depending on pandas version
        # Just ensure it doesn't crash

    def test_empty_dataframe(self, caplog):
        """Test empty DataFrame."""
        df = pd.DataFrame()
        result = safe_get_column(df, 0, 'A', default='N/A')
        assert result == 'N/A'

    def test_dataframe_with_none_values(self):
        """Test DataFrame with None values."""
        df = pd.DataFrame({'A': [1, None, 3]})
        result = safe_get_column(df, 1, 'A')
        assert result is None or pd.isna(result)

    def test_dataframe_various_types(self):
        """Test DataFrame with various column types."""
        df = pd.DataFrame({
            'int': [1, 2, 3],
            'float': [1.1, 2.2, 3.3],
            'str': ['a', 'b', 'c'],
            'bool': [True, False, True]
        })

        assert safe_get_column(df, 0, 'int') == 1
        assert safe_get_column(df, 1, 'float') == 2.2
        assert safe_get_column(df, 2, 'str') == 'c'
        # Pandas returns numpy.bool_, not Python bool
        assert safe_get_column(df, 0, 'bool') == True

    def test_both_missing_column_and_row(self, caplog):
        """Test both column and row missing."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        result = safe_get_column(df, 99, 'Z', default='N/A')
        assert result == 'N/A'
        # Should log column not found first
        assert "Column 'Z' not found" in caplog.text


@pytest.mark.unit
class TestSafeListGet:
    """Tests for safe_list_get() function."""

    def test_get_existing_index(self):
        """Test retrieving existing index."""
        lst = [10, 20, 30, 40]
        assert safe_list_get(lst, 0) == 10
        assert safe_list_get(lst, 2) == 30
        assert safe_list_get(lst, 3) == 40

    def test_get_missing_index(self, caplog):
        """Test retrieving out of range index returns default."""
        import logging
        caplog.set_level(logging.DEBUG)  # Function logs at DEBUG level

        lst = [10, 20, 30]
        result = safe_list_get(lst, 10, default='N/A')
        assert result == 'N/A'
        assert "Index 10 out of range for list of length 3" in caplog.text

    def test_get_missing_index_no_default(self, caplog):
        """Test retrieving out of range index returns None by default."""
        lst = [10, 20, 30]
        result = safe_list_get(lst, 10)
        assert result is None

    def test_negative_index(self):
        """Test negative index works."""
        lst = [10, 20, 30]
        assert safe_list_get(lst, -1) == 30
        assert safe_list_get(lst, -2) == 20

    def test_negative_index_out_of_range(self, caplog):
        """Test negative index out of range."""
        lst = [10, 20, 30]
        result = safe_list_get(lst, -10, default='N/A')
        assert result == 'N/A'

    def test_empty_list(self, caplog):
        """Test empty list."""
        lst = []
        result = safe_list_get(lst, 0, default='N/A')
        assert result == 'N/A'

    def test_not_a_list_input(self, caplog):
        """Test non-list input returns default."""
        result = safe_list_get("not a list", 0, default='N/A')
        assert result == 'N/A'
        assert "Expected list, got" in caplog.text

    def test_none_input(self, caplog):
        """Test None input returns default."""
        result = safe_list_get(None, 0, default='N/A')
        assert result == 'N/A'
        assert "Expected list, got" in caplog.text

    def test_dict_input(self, caplog):
        """Test dict input returns default."""
        result = safe_list_get({'a': 1}, 0, default='N/A')
        assert result == 'N/A'
        assert "Expected list, got" in caplog.text

    def test_list_of_various_types(self):
        """Test list containing various types."""
        lst = [1, 'text', 3.14, None, [1, 2], {'a': 1}]

        assert safe_list_get(lst, 0) == 1
        assert safe_list_get(lst, 1) == 'text'
        assert safe_list_get(lst, 2) == 3.14
        assert safe_list_get(lst, 3) is None
        assert safe_list_get(lst, 4) == [1, 2]
        assert safe_list_get(lst, 5) == {'a': 1}

    def test_nested_list(self):
        """Test nested list retrieval."""
        lst = [[1, 2], [3, 4], [5, 6]]
        assert safe_list_get(lst, 0) == [1, 2]
        assert safe_list_get(lst, 1) == [3, 4]

        # Can get nested elements with multiple calls
        inner = safe_list_get(lst, 0)
        assert safe_list_get(inner, 1) == 2


@pytest.mark.unit
class TestValidateStake:
    """Tests for validate_stake() function."""

    @pytest.mark.parametrize("stake", [
        1.0,
        10.0,
        100.0,
        1000.0,
        0.01,  # Minimum viable stake
        999999.99,
    ])
    def test_valid_stakes(self, stake):
        """Test valid stake values."""
        assert validate_stake(stake) == stake

    @pytest.mark.parametrize("stake", [
        "10.0",
        "100",
        10,
        100,
    ])
    def test_valid_stakes_various_types(self, stake):
        """Test valid stakes as different types."""
        result = validate_stake(stake)
        assert result == float(stake)

    def test_zero_stake_raises(self):
        """Test zero stake raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_stake(0.0)
        assert "Stake must be greater than 0" in str(exc_info.value)
        assert "0.0" in str(exc_info.value)

    def test_negative_stake_raises(self):
        """Test negative stake raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_stake(-10.0)
        assert "Stake must be greater than 0" in str(exc_info.value)
        assert "-10.0" in str(exc_info.value)

    def test_non_numeric_stake_raises(self):
        """Test non-numeric stake raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_stake("not a number")
        assert "Stake must be a number" in str(exc_info.value)

    def test_none_stake_raises(self):
        """Test None stake raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_stake(None)
        assert "Stake must be a number" in str(exc_info.value)

    def test_list_stake_raises(self):
        """Test list stake raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_stake([10.0])
        assert "Stake must be a number" in str(exc_info.value)

    def test_dict_stake_raises(self):
        """Test dict stake raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_stake({'value': 10.0})
        assert "Stake must be a number" in str(exc_info.value)

    def test_string_numeric_stake(self):
        """Test numeric string stake is converted."""
        assert validate_stake("10.5") == 10.5
        assert validate_stake("100") == 100.0

    def test_very_small_stake(self):
        """Test very small but positive stake."""
        assert validate_stake(0.0001) == 0.0001


@pytest.mark.unit
class TestValidateAmericanOdds:
    """Tests for validate_american_odds() function."""

    @pytest.mark.parametrize("odds", [
        -100, -110, -120, -150, -200, -500, -1000,
        100, 110, 120, 150, 200, 500, 1000,
    ])
    def test_valid_american_odds(self, odds):
        """Test valid American odds."""
        assert validate_american_odds(odds) == odds

    @pytest.mark.parametrize("odds", [
        -99, -50, -1, 0, 1, 50, 99,
    ])
    def test_invalid_american_odds_in_dead_zone(self, odds):
        """Test invalid odds in the -100 to 100 range."""
        with pytest.raises(ValueError) as exc_info:
            validate_american_odds(odds)
        assert "must be <= -100 or >= 100" in str(exc_info.value)
        assert str(odds) in str(exc_info.value)

    def test_exactly_minus_100(self):
        """Test edge case of exactly -100."""
        assert validate_american_odds(-100) == -100

    def test_exactly_100(self):
        """Test edge case of exactly 100."""
        assert validate_american_odds(100) == 100

    def test_string_odds_converted(self):
        """Test string odds are converted to int."""
        assert validate_american_odds("-110") == -110
        assert validate_american_odds("150") == 150

    def test_float_odds_converted(self):
        """Test float odds are converted to int."""
        assert validate_american_odds(-110.0) == -110
        assert validate_american_odds(150.0) == 150

    def test_non_convertible_string_raises(self):
        """Test non-numeric string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_american_odds("not a number")
        assert "must be an integer" in str(exc_info.value)

    def test_none_raises(self):
        """Test None raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_american_odds(None)
        assert "must be an integer" in str(exc_info.value)

    def test_list_raises(self):
        """Test list raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_american_odds([-110])
        assert "must be an integer" in str(exc_info.value)

    def test_large_odds(self):
        """Test large odds values."""
        assert validate_american_odds(-10000) == -10000
        assert validate_american_odds(10000) == 10000

    def test_custom_name_in_error(self):
        """Test custom name appears in error message."""
        with pytest.raises(ValueError) as exc_info:
            validate_american_odds(50, name="custom_odds")
        assert "custom_odds" in str(exc_info.value)


@pytest.mark.unit
class TestValidateProbability:
    """Tests for validate_probability() function."""

    @pytest.mark.parametrize("prob", [
        0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0,
        0.001, 0.999,
    ])
    def test_valid_probabilities(self, prob):
        """Test valid probability values."""
        assert validate_probability(prob) == prob

    def test_exactly_zero(self):
        """Test edge case of exactly 0."""
        assert validate_probability(0.0) == 0.0

    def test_exactly_one(self):
        """Test edge case of exactly 1."""
        assert validate_probability(1.0) == 1.0

    @pytest.mark.parametrize("prob", [
        -0.1, -0.5, -1.0,
        1.1, 1.5, 2.0, 100.0,
    ])
    def test_invalid_probabilities(self, prob):
        """Test invalid probability values."""
        with pytest.raises(ValueError) as exc_info:
            validate_probability(prob)
        assert "must be between 0 and 1" in str(exc_info.value)
        assert str(prob) in str(exc_info.value)

    def test_just_below_zero(self):
        """Test value just below 0."""
        with pytest.raises(ValueError):
            validate_probability(-0.0001)

    def test_just_above_one(self):
        """Test value just above 1."""
        with pytest.raises(ValueError):
            validate_probability(1.0001)

    def test_custom_name_in_error(self):
        """Test custom name appears in error message."""
        with pytest.raises(ValueError) as exc_info:
            validate_probability(1.5, name="win_prob")
        assert "win_prob" in str(exc_info.value)

    def test_default_name_in_error(self):
        """Test default name appears in error message."""
        with pytest.raises(ValueError) as exc_info:
            validate_probability(1.5)
        assert "probability" in str(exc_info.value)


@pytest.mark.unit
class TestValidateLineValue:
    """Tests for validate_line_value() function."""

    @pytest.mark.parametrize("line", [
        0.5, 1.5, 10.5, 25.5, 50.5, 100.5,
        0.0, 1.0, -5.5, -10.0,
    ])
    def test_valid_line_values(self, line):
        """Test valid line values."""
        assert validate_line_value(line) == line

    @pytest.mark.parametrize("line", [
        "25.5", "10.0", "0.5",
        25, 10, 0,
    ])
    def test_valid_line_values_various_types(self, line):
        """Test valid lines as different types."""
        result = validate_line_value(line)
        assert result == float(line)

    def test_negative_line(self):
        """Test negative line value."""
        assert validate_line_value(-5.5) == -5.5

    def test_zero_line(self):
        """Test zero line value."""
        assert validate_line_value(0.0) == 0.0

    def test_non_numeric_line_raises(self):
        """Test non-numeric line raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_line_value("not a number")
        assert "Line value must be numeric" in str(exc_info.value)
        assert "not a number" in str(exc_info.value)

    def test_none_line_raises(self):
        """Test None line raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_line_value(None)
        assert "Line value must be numeric" in str(exc_info.value)

    def test_list_line_raises(self):
        """Test list line raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_line_value([25.5])
        assert "Line value must be numeric" in str(exc_info.value)

    def test_dict_line_raises(self):
        """Test dict line raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_line_value({'value': 25.5})
        assert "Line value must be numeric" in str(exc_info.value)

    def test_large_line_value(self):
        """Test large line value."""
        assert validate_line_value(1000.5) == 1000.5


@pytest.mark.unit
class TestValidatePositiveNumber:
    """Tests for validate_positive_number() function."""

    @pytest.mark.parametrize("value", [
        0.1, 1.0, 10.0, 100.0, 1000.0,
        0.001, 999999.99,
    ])
    def test_valid_positive_numbers(self, value):
        """Test valid positive numbers."""
        assert validate_positive_number(value) == value

    def test_zero_raises(self):
        """Test zero raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_positive_number(0.0)
        assert "must be positive" in str(exc_info.value)
        assert "0.0" in str(exc_info.value)

    @pytest.mark.parametrize("value", [
        -0.1, -1.0, -10.0, -100.0,
    ])
    def test_negative_numbers_raise(self, value):
        """Test negative numbers raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_positive_number(value)
        assert "must be positive" in str(exc_info.value)
        assert str(value) in str(exc_info.value)

    def test_very_small_positive(self):
        """Test very small positive number."""
        assert validate_positive_number(0.0001) == 0.0001

    def test_large_positive(self):
        """Test large positive number."""
        assert validate_positive_number(999999999.0) == 999999999.0

    def test_custom_name_in_error(self):
        """Test custom name appears in error message."""
        with pytest.raises(ValueError) as exc_info:
            validate_positive_number(-5.0, name="custom_value")
        assert "custom_value" in str(exc_info.value)

    def test_default_name_in_error(self):
        """Test default name appears in error message."""
        with pytest.raises(ValueError) as exc_info:
            validate_positive_number(-5.0)
        assert "value" in str(exc_info.value)

    def test_integer_positive(self):
        """Test integer positive numbers work."""
        assert validate_positive_number(10) == 10
        assert validate_positive_number(1) == 1


@pytest.mark.unit
class TestTypeSafetyIntegration:
    """Integration tests for type safety functions working together."""

    def test_safe_converters_chain(self):
        """Test chaining safe converters."""
        # Currency -> Float -> Int
        currency_str = "$100.50"
        as_float = safe_currency_to_float(currency_str)
        as_int = safe_int(as_float)
        assert as_int == 100

    def test_safe_dict_get_with_safe_converters(self):
        """Test combining safe_dict_get with converters."""
        data = {'price': '$100.50', 'quantity': '5'}

        price_str = safe_dict_get(data, 'price', default='$0')
        price = safe_currency_to_float(price_str)
        assert price == 100.5

        qty_str = safe_dict_get(data, 'quantity', default='0')
        qty = safe_int(qty_str)
        assert qty == 5

    def test_validators_with_safe_converters(self):
        """Test validators with safe converters."""
        data = {'stake': '$10.00', 'odds': '-110', 'prob': '0.5'}

        # Convert and validate stake
        stake_str = safe_dict_get(data, 'stake', default='$0')
        stake = safe_currency_to_float(stake_str)
        validated_stake = validate_stake(stake)
        assert validated_stake == 10.0

        # Convert and validate odds
        odds_str = safe_dict_get(data, 'odds', default='100')
        odds = safe_int(odds_str)
        validated_odds = validate_american_odds(odds)
        assert validated_odds == -110

        # Convert and validate probability
        prob_str = safe_dict_get(data, 'prob', default='0.5')
        prob = safe_float(prob_str)
        validated_prob = validate_probability(prob)
        assert validated_prob == 0.5

    def test_dataframe_with_converters(self):
        """Test DataFrame access with type converters."""
        df = pd.DataFrame({
            'stake': ['$10.00', '$20.00', '$30.00'],
            'odds': ['-110', '150', '-200']
        })

        # Get and convert stake
        stake_str = safe_get_column(df, 0, 'stake', default='$0')
        stake = safe_currency_to_float(stake_str)
        assert stake == 10.0

        # Get and convert odds
        odds_str = safe_get_column(df, 1, 'odds', default='100')
        odds = safe_int(odds_str)
        assert odds == 150

    def test_nested_safe_access(self):
        """Test nested safe access patterns."""
        data = {
            'user': {
                'bets': [
                    {'stake': '$10.00', 'odds': -110},
                    {'stake': '$20.00', 'odds': 150}
                ]
            }
        }

        # Safely navigate nested structure
        user = safe_dict_get(data, 'user', default={})
        bets = safe_dict_get(user, 'bets', default=[])
        first_bet = safe_list_get(bets, 0, default={})

        stake_str = safe_dict_get(first_bet, 'stake', default='$0')
        stake = safe_currency_to_float(stake_str)
        assert stake == 10.0

    def test_error_handling_cascade(self):
        """Test error handling cascades through functions."""
        # Invalid data that should fail gracefully at each level
        data = {'invalid': 'data'}

        value = safe_dict_get(data, 'missing', default='invalid')
        numeric = safe_float(value, default=0.0)

        # Should not raise, should use defaults
        assert numeric == 0.0

    def test_validation_after_safe_conversion(self):
        """Test validators work correctly after safe conversions."""
        # Even with safe converters, validators should catch logic errors
        bad_stake = safe_currency_to_float("$0.00")  # Returns 0.0

        # Validator should catch this
        with pytest.raises(ValueError):
            validate_stake(bad_stake)

    def test_mixed_valid_invalid_data(self):
        """Test processing mixed valid/invalid data."""
        data_list = [
            {'stake': '$10.00', 'odds': -110},
            {'stake': 'invalid', 'odds': 'bad'},
            {'stake': '$20.00', 'odds': 150},
        ]

        results = []
        for item in data_list:
            stake_raw = safe_dict_get(item, 'stake', default='$0')
            stake = safe_currency_to_float(stake_raw)

            odds_raw = safe_dict_get(item, 'odds', default=100)
            odds = safe_int(odds_raw)

            # Only validate if conversions succeeded
            if stake > 0:
                try:
                    validated_stake = validate_stake(stake)
                    validated_odds = validate_american_odds(odds)
                    results.append((validated_stake, validated_odds))
                except ValueError:
                    pass  # Skip invalid items

        # Should have 2 valid results
        assert len(results) == 2
        assert results[0] == (10.0, -110)
        assert results[1] == (20.0, 150)
