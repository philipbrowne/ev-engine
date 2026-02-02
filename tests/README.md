# EV Engine Test Suite

Comprehensive test suite for the EV Engine project.

## Structure

```
tests/
├── __init__.py           # Test package initialization
├── conftest.py           # Shared pytest fixtures
├── test_analysis.py      # Analysis module tests
├── test_db.py            # Database layer tests
├── test_odds_api.py      # API client tests
├── test_validation.py    # Validation module tests
├── test_type_safety.py   # Type safety tests
└── test_dashboard.py     # Dashboard tests
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_analysis.py
```

### Run specific test class
```bash
pytest tests/test_analysis.py::TestImpliedProbability
```

### Run specific test
```bash
pytest tests/test_analysis.py::TestImpliedProbability::test_favorite_odds
```

### Run tests with markers
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Test Markers

- `unit`: Fast, isolated unit tests
- `integration`: Tests that interact with external systems or database
- `slow`: Tests that take longer to execute

## Coverage Reports

After running tests with coverage, view the HTML report:
```bash
open htmlcov/index.html
```

## Writing New Tests

### Test Structure
```python
import pytest

class TestYourFeature:
    """Tests for your feature."""

    @pytest.mark.unit
    def test_something(self, fixture_name):
        """Test description."""
        # Arrange
        input_data = "test"

        # Act
        result = your_function(input_data)

        # Assert
        assert result == expected_value
```

### Using Fixtures

Fixtures are defined in `conftest.py` and can be used by adding them as test parameters:

```python
def test_with_database(initialized_db):
    """Test using initialized database."""
    # initialized_db is automatically created and cleaned up
    pass
```

### Available Fixtures

- `temp_db_path`: Temporary database file path
- `db_connection`: SQLite connection with row factory
- `initialized_db`: Database with all tables created
- `mock_api_sports_response`: Mock sports API response
- `mock_player_props_response`: Mock player props response
- `sample_odds_data`: Sample odds for testing
- `sample_bet_data`: Sample bet data
- `sample_slip_data`: Sample bet slip data
- `mock_env_vars`: Mock environment variables
- `valid_american_odds`: Valid American odds values
- `invalid_american_odds`: Invalid American odds values

## Code Quality

### Run linting
```bash
flake8 src tests
```

### Run type checking
```bash
mypy src
```

### Format code
```bash
black src tests
isort src tests
```

## Continuous Integration

Tests should pass before merging:
1. All unit tests pass
2. Coverage > 80%
3. No linting errors
4. Type checking passes
