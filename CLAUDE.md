# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EV Engine is a sports betting Expected Value calculator that identifies profitable betting opportunities in daily fantasy sports (DFS) player props. It compares de-vigged sharp market odds (Pinnacle) against recreational DFS platforms (PrizePicks, Underdog, Betr, DK Pick6) to find pricing inefficiencies.

## Common Commands

```bash
# Run the Streamlit dashboard
streamlit run dashboard.py

# Run all tests with coverage
pytest

# Run a specific test file
pytest tests/test_analysis.py -v

# Run a specific test class or method
pytest tests/test_db.py::TestSlipOperations -v

# Code formatting
black src tests
isort src tests

# Linting and type checking
flake8 src tests
mypy src

# Initialize the database
python -c "from src.db import initialize_db; initialize_db()"
```

## Architecture

### Core Modules (`src/`)

- **analysis.py**: Pure mathematical functions for EV calculation. Stateless, no external dependencies. Contains:
  - `calculate_implied_probability()`: American odds → probability
  - `devig_pinnacle_odds()`: Removes vig using multiplicative method
  - `calculate_ev_percentage()`: Compares fair prob vs breakeven
  - `calculate_breakeven_probability()`: Per-leg breakeven for parlay structures

- **odds_api.py**: The Odds API client. Fetches player prop odds from Pinnacle (sharp) and DFS books.

- **db.py**: SQLite database operations. Key tables:
  - `odds_snapshot`: Raw odds data from API
  - `bets`: Calculated +EV opportunities
  - `slips`: Parent table for multi-leg bet slips
  - `slip_legs`: Individual picks on each slip

- **config.py**: Configuration constants including:
  - `PAYOUT_MULTIPLIER = 3.0` (2-leg parlay)
  - `IMPLIED_LEG_PROB ≈ 57.7%` (per-leg breakeven)
  - `SPORTS_MAP`: Sport name → API key mapping
  - `DFS_BOOKMAKERS`: List of supported DFS books

- **validation.py**: API response validation
- **type_safety.py**: Safe type conversions (`safe_float`, `safe_dict_get`)

### Dashboard (`dashboard.py`)

Streamlit web interface with:
- Live Board: Real-time +EV opportunities sorted by edge
- Track Bets: Log and track multi-leg parlays
- Analytics: ROI, win rate, bankroll progression

### Data Flow

1. `odds_api.py` fetches odds from The Odds API
2. Data stored in `odds_snapshot` table
3. `analysis.py` calculates fair probabilities and EV
4. Results stored in `bets` table
5. Dashboard displays opportunities from `bets` table

## Key Concepts

### EV Calculation
```
EV% = ((fair_prob / breakeven_prob) - 1) * 100
```

For 2-leg DFS parlays (3x payout):
- Breakeven per leg: √(1/3) ≈ 57.7%
- Any leg with fair prob > 57.7% is +EV

### De-vigging (Multiplicative Method)
```python
fair_prob = implied_prob / (over_implied + under_implied)
```

### Sharp Bookmaker Hierarchy
The engine uses Pinnacle as the primary sharp reference for de-vigging. When Pinnacle odds aren't available (e.g., NBA player props), FanDuel is used as a fallback with a 25% EV discount to account for less precise lines.

```python
SHARP_CONFIDENCE = {
    "pinnacle": 1.0,    # Gold standard
    "fanduel": 0.75,    # 25% EV discount
}
```

## Testing

Tests use pytest with markers:
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests requiring database

The `initialized_db` fixture in `conftest.py` provides a clean test database.

## Environment Variables

Required in `.env`:
```
ODDS_API_KEY=your_api_key_here
```

Optional:
```
DATABASE_PATH=data/ev_engine.db
LOG_LEVEL=INFO
```
