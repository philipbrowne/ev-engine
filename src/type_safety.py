"""Type safety utilities for robust data handling.

This module provides type-safe conversion functions and validators to handle
potentially unsafe data from external sources (APIs, user input, databases).
"""

from typing import Any, Optional, Dict, TypeVar
import logging
import pandas as pd

logger = logging.getLogger('ev_engine')

T = TypeVar('T')


def safe_currency_to_float(value: Any) -> float:
    """Safely convert currency string to float.

    Handles various currency formats:
    - String with $ symbol: "$123.45" -> 123.45
    - String with commas: "1,234.56" -> 1234.56
    - Already numeric: 123 -> 123.0
    - Invalid values: returns 0.0 with warning

    Args:
        value: Currency value (string with $ or numeric)

    Returns:
        Float value, 0.0 if invalid

    Examples:
        >>> safe_currency_to_float("$123.45")
        123.45
        >>> safe_currency_to_float("1,234.56")
        1234.56
        >>> safe_currency_to_float(100)
        100.0
        >>> safe_currency_to_float("invalid")
        0.0
    """
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # Remove currency symbols, commas, and whitespace
        clean_value = value.replace("$", "").replace(",", "").strip()
        try:
            return float(clean_value)
        except ValueError:
            logger.warning(f"Invalid currency value: {value}")
            return 0.0

    logger.warning(f"Unexpected currency value type: {type(value)}: {value}")
    return 0.0


def safe_get_column(
    df: pd.DataFrame,
    row_idx: int,
    column: str,
    default: Any = None
) -> Any:
    """Safely get DataFrame column value with default.

    Args:
        df: DataFrame
        row_idx: Row index
        column: Column name
        default: Default value if column missing

    Returns:
        Column value or default

    Examples:
        >>> df = pd.DataFrame({"A": [1, 2, 3]})
        >>> safe_get_column(df, 0, "A")
        1
        >>> safe_get_column(df, 0, "B", default="N/A")
        'N/A'
    """
    if column not in df.columns:
        logger.warning(f"Column '{column}' not found in DataFrame")
        return default

    try:
        return df.at[row_idx, column]
    except (KeyError, IndexError) as e:
        logger.warning(f"Error accessing row {row_idx}, column '{column}': {e}")
        return default


def safe_dict_get(
    data: Dict[str, Any],
    key: str,
    default: Any = None,
    expected_type: Optional[type] = None
) -> Any:
    """Safely get dictionary value with type checking.

    Args:
        data: Source dictionary
        key: Key to retrieve
        default: Default value if key missing or type mismatch
        expected_type: Optional type to validate against

    Returns:
        Value from dictionary or default

    Examples:
        >>> safe_dict_get({"a": 1}, "a")
        1
        >>> safe_dict_get({"a": 1}, "b", default=0)
        0
        >>> safe_dict_get({"a": "text"}, "a", expected_type=int, default=0)
        0
    """
    if not isinstance(data, dict):
        logger.warning(f"Expected dict, got {type(data)}")
        return default

    value = data.get(key, default)

    if expected_type is not None and value is not None:
        if not isinstance(value, expected_type):
            logger.warning(
                f"Key '{key}': expected {expected_type.__name__}, "
                f"got {type(value).__name__}. Using default."
            )
            return default

    return value


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer.

    Args:
        value: Value to convert
        default: Default if conversion fails

    Returns:
        Integer value or default

    Examples:
        >>> safe_int("123")
        123
        >>> safe_int("invalid", default=-1)
        -1
        >>> safe_int(123.7)
        123
    """
    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        try:
            return int(float(value))  # Handle "123.0" strings
        except ValueError:
            logger.warning(f"Cannot convert to int: {value}")
            return default

    logger.warning(f"Unexpected type for int conversion: {type(value)}: {value}")
    return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float.

    Args:
        value: Value to convert
        default: Default if conversion fails

    Returns:
        Float value or default

    Examples:
        >>> safe_float("123.45")
        123.45
        >>> safe_float("invalid", default=-1.0)
        -1.0
        >>> safe_float(123)
        123.0
    """
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        clean_value = value.strip()
        try:
            return float(clean_value)
        except ValueError:
            logger.warning(f"Cannot convert to float: {value}")
            return default

    logger.warning(f"Unexpected type for float conversion: {type(value)}: {value}")
    return default


def validate_positive_number(value: float, name: str = "value") -> float:
    """Validate that a number is positive.

    Args:
        value: Number to validate
        name: Name for error messages

    Returns:
        The value if valid

    Raises:
        ValueError: If value is not positive

    Examples:
        >>> validate_positive_number(10.0)
        10.0
        >>> validate_positive_number(-5.0)
        Traceback (most recent call last):
        ...
        ValueError: value must be positive, got -5.0
    """
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value


def validate_probability(value: float, name: str = "probability") -> float:
    """Validate that a value is a valid probability (0 to 1).

    Args:
        value: Probability to validate
        name: Name for error messages

    Returns:
        The value if valid

    Raises:
        ValueError: If value is not between 0 and 1

    Examples:
        >>> validate_probability(0.5)
        0.5
        >>> validate_probability(1.5)
        Traceback (most recent call last):
        ...
        ValueError: probability must be between 0 and 1, got 1.5
    """
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1, got {value}")
    return value


def validate_american_odds(value: int, name: str = "odds") -> int:
    """Validate American odds format.

    American odds must be:
    - An integer
    - Either positive (100 or greater) or negative (-100 or less)
    - Not between -100 and 100 (exclusive)

    Args:
        value: Odds value to validate
        name: Name for error messages

    Returns:
        The value if valid

    Raises:
        ValueError: If odds are invalid

    Examples:
        >>> validate_american_odds(-110)
        -110
        >>> validate_american_odds(150)
        150
        >>> validate_american_odds(50)
        Traceback (most recent call last):
        ...
        ValueError: odds must be <= -100 or >= 100, got 50
    """
    if not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"{name} must be an integer, got {value}")

    # American odds must be <= -100 or >= 100
    if -100 < value < 100:
        raise ValueError(f"{name} must be <= -100 or >= 100, got {value}")

    return value


def safe_list_get(lst: list, index: int, default: Any = None) -> Any:
    """Safely get list element by index.

    Args:
        lst: Source list
        index: Index to retrieve
        default: Default value if index out of range

    Returns:
        List element or default

    Examples:
        >>> safe_list_get([1, 2, 3], 0)
        1
        >>> safe_list_get([1, 2, 3], 10, default="N/A")
        'N/A'
    """
    if not isinstance(lst, list):
        logger.warning(f"Expected list, got {type(lst)}")
        return default

    try:
        return lst[index]
    except IndexError:
        logger.debug(f"Index {index} out of range for list of length {len(lst)}")
        return default


def validate_stake(stake: float) -> float:
    """Validate bet stake amount.

    Args:
        stake: Stake amount to validate

    Returns:
        The stake if valid

    Raises:
        ValueError: If stake is invalid

    Examples:
        >>> validate_stake(10.0)
        10.0
        >>> validate_stake(0.0)
        Traceback (most recent call last):
        ...
        ValueError: Stake must be greater than 0, got 0.0
        >>> validate_stake(-5.0)
        Traceback (most recent call last):
        ...
        ValueError: Stake must be greater than 0, got -5.0
    """
    try:
        stake_value = float(stake)
    except (ValueError, TypeError):
        raise ValueError(f"Stake must be a number, got {stake}")

    if stake_value <= 0:
        raise ValueError(f"Stake must be greater than 0, got {stake_value}")

    return stake_value


def validate_line_value(line: Any) -> float:
    """Validate prop bet line value.

    Args:
        line: Line value to validate

    Returns:
        The line value as float

    Raises:
        ValueError: If line is invalid

    Examples:
        >>> validate_line_value(25.5)
        25.5
        >>> validate_line_value("25.5")
        25.5
        >>> validate_line_value("invalid")
        Traceback (most recent call last):
        ...
        ValueError: Line value must be numeric, got invalid
    """
    try:
        line_value = float(line)
    except (ValueError, TypeError):
        raise ValueError(f"Line value must be numeric, got {line}")

    return line_value
