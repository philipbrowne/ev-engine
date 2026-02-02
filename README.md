# EV Engine

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](./TEST_SUMMARY.md)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> A sports betting Expected Value (EV) calculator and tracker for identifying profitable betting opportunities in daily fantasy sports player props.

Find +EV plays by comparing sharp market odds (Pinnacle) against recreational DFS platforms (PrizePicks, Underdog, Betr, DK Pick6). Track your bets, analyze performance, and manage your bankroll with data-driven insights.

---

## Overview

**EV Engine** helps sports bettors identify positive expected value opportunities by leveraging the efficient market hypothesis. Pinnacle is widely regarded as the sharpest sportsbook in the world - their lines reflect true probabilities. By comparing de-vigged Pinnacle odds against DFS platform lines, you can find pricing inefficiencies and exploit profitable edges.

**Who it's for:**
- Sports bettors seeking data-driven edge
- DFS players looking to maximize ROI on player props
- Anyone interested in sports betting analytics

**Key Value Proposition:**
The difference between profitable and losing bettors isn't luck - it's math. EV Engine brings institutional-grade sports betting analysis to your desktop, helping you find and track +EV opportunities across multiple sports and bookmakers.

---

## Features

### Core Functionality
- **Real-time Odds Aggregation** - Fetches live odds from The Odds API for both sharp and recreational books
- **De-vigged Pinnacle Odds** - Removes bookmaker vig to calculate true fair probabilities
- **EV Calculation** - Compares fair probabilities against DFS payout structures (3x, 6x, 10x multipliers)
- **Multi-Sport Support** - NBA, NFL, NHL, MLB, NCAAB, NCAAF
- **Multi-Book Coverage** - PrizePicks, Underdog, Betr, DK Pick6

### Bet Management
- **Slip Tracking** - Log multi-leg parlays with automatic EV calculation
- **Bankroll Management** - Track total invested, profit/loss, and ROI
- **Performance Analytics** - Win rate, historical hit rates, and time-series P/L charts
- **Historical Analysis** - Review past performance by player, market, and line direction

### User Experience
- **Streamlit Dashboard** - Clean, intuitive web interface
- **Live Board** - Real-time +EV opportunities sorted by edge
- **Risk Ratings** - Color-coded recommendations (SMASH, FLEX, AVOID)
- **Freshness Indicators** - See how recent odds data is

---

## Quick Start

### Automated Setup (Recommended)

**Mac/Linux:**
```bash
./init.sh
```

**Windows:**
```bash
python init.py
```

This will:
- Check Python 3.9+ installation
- Create virtual environment
- Install dependencies
- Set up API keys via interactive prompt
- Initialize SQLite database

### Manual Setup

If you prefer manual setup:

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env and add your ODDS_API_KEY

# 4. Initialize database
python -c "from src.db import initialize_db; initialize_db()"
```

### Start the Dashboard

```bash
source venv/bin/activate  # Activate virtual environment
streamlit run dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

---

## Prerequisites

### Required
- **Python 3.9 or higher** - [Download here](https://www.python.org/downloads/)
- **The Odds API Key** - [Get free tier (500 requests/month)](https://the-odds-api.com/)

### System Requirements
- 500 MB disk space (for database and dependencies)
- 2 GB RAM (recommended)
- Internet connection for API calls

---

## Installation

### Step 1: Clone or Download

```bash
git clone https://github.com/yourusername/ev-engine.git
cd ev-engine
```

### Step 2: Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure API Key

Create a `.env` file in the project root:

```bash
ODDS_API_KEY=your_api_key_here
```

**Getting Your API Key:**
1. Visit [The Odds API](https://the-odds-api.com/)
2. Sign up for a free account
3. Navigate to your dashboard
4. Copy your API key
5. Paste it into the `.env` file

### Step 5: Initialize Database

```bash
python -c "from src.db import initialize_db; initialize_db()"
```

This creates `data/ev_engine.db` with the required schema.

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
ODDS_API_KEY=your_api_key_from_the_odds_api

# Optional (defaults shown)
DATABASE_PATH=data/ev_engine.db
LOG_LEVEL=INFO
```

### Configuration Options

Edit `src/config.py` to customize:

```python
# EV Calculation Constants
PAYOUT_MULTIPLIER = 3.0  # Standard 2-leg parlay payout
BREAK_EVEN_WIN_PCT = 1 / 3.0  # 33.33%
IMPLIED_LEG_PROB = 0.577  # ~57.7% per leg break-even

# Supported Sports
SPORTS_MAP = {
    "NBA": "basketball_nba",
    "NCAAB": "basketball_ncaab",
    "NFL": "americanfootball_nfl",
    "NCAAF": "americanfootball_ncaaf",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
}

# DFS Bookmakers
DFS_BOOKMAKERS = ["prizepicks", "underdog", "betr_us_dfs", "pick6"]
```

---

## Usage

### Starting the Dashboard

```bash
streamlit run dashboard.py
```

### Live Board Tab

The Live Board displays real-time +EV opportunities:

1. **Select Sports** - Use the sidebar to choose which sports to scan (NBA, NFL, etc.)
2. **Set Parlay Type** - Choose 2-leg (3x), 3-leg (6x), or 5-leg (10x) payouts
3. **Adjust Filters**:
   - Minimum EV % threshold
   - Minimum fair win probability
4. **Refresh Market** - Click to fetch latest odds from The Odds API
5. **Review Opportunities** - Sort by EV%, win probability, or freshness

**Interpreting Results:**
- **EV %**: Expected return per dollar wagered (higher is better)
- **Win Prob**: De-vigged fair probability of hitting this leg
- **Risk**: Low (<58%), Medium (55-58%), High (<55%)
- **Rec**: SMASH (>5% EV), FLEX (0-5% EV), AVOID (<0% EV)
- **Freshness**: How recently the odds were fetched

### Track Bets Tab

Log your placed bets and track performance:

1. **Create New Slip**:
   - Enter stake amount
   - Select picks from the Live Board
   - Review parlay details
   - Submit to database

2. **Active Slips**:
   - View pending bets
   - Update outcomes (Won/Lost/Push)
   - Enter payout amounts

3. **Bet History**:
   - Review past slips
   - Filter by date range
   - Export to CSV

### Analytics Tab

Review your betting performance:

- **Bankroll Chart** - Cumulative P/L over time
- **Win Rate** - Percentage of winning slips
- **ROI** - Return on investment
- **Hit Rate by Player** - Historical performance for specific players
- **Hit Rate by Market** - Performance by market type (points, assists, etc.)

---

## How It Works

### The EV Calculation Methodology

#### Step 1: Fetch Sharp Odds
We use Pinnacle as our "true probability" baseline. Pinnacle has the lowest margins in the industry and is used by professional bettors worldwide.

#### Step 2: Remove the Vig (De-vig)
Bookmakers add "vigorish" (vig) to ensure profit. For a fair coin flip, odds should be +100/+100 (50%/50%), but books might offer -110/-110 (52.4%/52.4% = 104.8% total).

We use the multiplicative method to remove vig:
```python
fair_prob = implied_prob / (over_implied + under_implied)
```

Example:
```
Pinnacle Over: -130 (implied: 56.5%)
Pinnacle Under: +110 (implied: 47.6%)
Total: 104.1% (vig is 4.1%)

Fair Over Probability: 56.5% / 104.1% = 54.3%
Fair Under Probability: 47.6% / 104.1% = 45.7%
```

#### Step 3: Compare to DFS Payout Structure
DFS platforms use fixed payout multipliers:
- 2-leg parlay: 3x payout (requires 57.7% per leg to break even)
- 3-leg parlay: 6x payout (requires 55.0% per leg to break even)
- 5-leg parlay: 10x payout (requires 63.1% per leg to break even)

#### Step 4: Calculate Expected Value
```python
EV% = ((fair_prob / breakeven_prob) - 1) * 100
```

Example:
```
Fair Win Probability: 60%
Breakeven Probability: 57.7% (for 2-leg parlay)
EV% = ((0.60 / 0.577) - 1) * 100 = +3.98%
```

This means for every $100 wagered on this parlay, you expect to profit $3.98 over the long run.

### Sharp vs Recreational Odds

**Sharp Books (Pinnacle):**
- Low margins (1-2%)
- Accept large bets from professionals
- Odds move quickly based on market information
- Considered the most "efficient" pricing

**Recreational Books (PrizePicks, Underdog):**
- Higher margins (5-15%)
- Fixed payout structures
- Limited bet sizing
- Slower to adjust to market movements

The difference between these two creates +EV opportunities.

### Parlay Payout Structures

DFS platforms offer fixed multipliers based on number of legs:

| Legs | Payout | Breakeven/Leg | True Fair Odds |
|------|--------|---------------|----------------|
| 2    | 3x     | 57.7%         | +73.3          |
| 3    | 6x     | 55.0%         | +81.8          |
| 5    | 10x    | 63.1%         | +58.4          |

If you can consistently find legs with fair probabilities above these thresholds, you have a mathematical edge.

---

## Project Structure

```
ev-engine/
├── src/                    # Core application modules
│   ├── __init__.py
│   ├── analysis.py         # EV calculation and probability math
│   ├── config.py           # Configuration and constants
│   ├── db.py               # Database operations and queries
│   ├── odds_api.py         # The Odds API client
│   ├── type_safety.py      # Input validation utilities
│   └── validation.py       # API response validation
├── tests/                  # Comprehensive test suite (99% coverage)
│   ├── conftest.py         # Pytest fixtures
│   ├── test_analysis.py    # Math logic tests
│   ├── test_db.py          # Database tests
│   ├── test_odds_api.py    # API client tests
│   ├── test_validation.py  # Validation tests
│   └── test_type_safety.py # Type safety tests
├── data/                   # SQLite database directory
│   └── ev_engine.db        # Main database (created on init)
├── docs/                   # Documentation files
│   ├── BLUEPRINT.md        # Technical architecture
│   ├── UI_SPEC.md          # Dashboard specifications
│   └── IMPROVEMENT_PLAN.md # Development roadmap
├── dashboard.py            # Streamlit web interface
├── init.py                 # Automated setup script (Python)
├── init.sh                 # Automated setup script (Bash)
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── pytest.ini              # Pytest configuration
├── .env                    # Environment variables (create this)
└── README.md               # This file
```

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_analysis.py

# Run specific test class
pytest tests/test_db.py::TestSlipOperations -v

# View coverage report
open htmlcov/index.html
```

**Current Test Coverage:** 99% (374/378 lines covered)

### Code Quality Tools

The project uses professional code quality tools:

```bash
# Format code
black src tests

# Sort imports
isort src tests

# Lint code
flake8 src tests

# Type checking
mypy src
```

Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Development Dependencies

```
pytest>=7.4.0           # Testing framework
pytest-cov>=4.1.0       # Coverage reporting
pytest-mock>=3.11.0     # Mocking utilities
black>=23.0.0           # Code formatting
flake8>=6.0.0           # Linting
mypy>=1.5.0             # Type checking
isort>=5.12.0           # Import sorting
```

---

## Database

### Schema Overview

EV Engine uses SQLite for data persistence with 5 main tables:

**odds_snapshot** - Raw odds data from The Odds API
```sql
CREATE TABLE odds_snapshot (
    id INTEGER PRIMARY KEY,
    event_id TEXT,
    sport_key TEXT,
    bookmaker TEXT,
    market_key TEXT,
    player_name TEXT,
    selection TEXT,           -- 'Over' or 'Under'
    price REAL,              -- American odds
    point REAL,              -- Line value (e.g., 24.5)
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**bets** - Calculated +EV opportunities
```sql
CREATE TABLE bets (
    id INTEGER PRIMARY KEY,
    event_id TEXT,
    player_name TEXT,
    market TEXT,
    line_value REAL,
    pinnacle_over_price INTEGER,
    pinnacle_under_price INTEGER,
    fair_win_prob REAL,      -- De-vigged probability
    ev_percentage REAL,      -- Expected value %
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**slips** - Multi-leg parlay tracking
```sql
CREATE TABLE slips (
    id INTEGER PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    stake REAL,
    status TEXT,             -- 'Pending', 'Won', 'Lost', 'Push'
    payout REAL,
    num_legs INTEGER
);
```

**slip_legs** - Individual picks within a slip
```sql
CREATE TABLE slip_legs (
    id INTEGER PRIMARY KEY,
    slip_id INTEGER REFERENCES slips(id),
    player_name TEXT,
    market TEXT,
    line_value REAL,
    selection TEXT,
    outcome TEXT             -- 'Hit', 'Miss', 'Push', 'Pending'
);
```

**placed_bets** - Legacy single-bet tracking (deprecated)

### Database Operations

Common database operations are available in `src/db.py`:

```python
from src import db

# Initialize database
db.initialize_db()

# Insert odds snapshot
db.insert_odds_snapshot([odds_data])

# Get best opportunities
opportunities = db.get_best_bets(min_ev=2.0, limit=50)

# Create a bet slip
slip_id = db.create_slip(stake=10.0, legs=[leg1, leg2])

# Update slip outcome
db.update_slip_status(slip_id, status='Won', payout=30.0)

# Get analytics
analytics = db.get_slip_analytics()
```

### Data Retention

- **odds_snapshot**: Retains all historical odds (can be pruned manually)
- **bets**: Retains all calculated opportunities
- **slips**: Retains all bet slips indefinitely
- **slip_legs**: Retains all leg details indefinitely

To clear old odds data:
```python
from datetime import datetime, timedelta
from src.db import clear_odds_snapshots_before

cutoff = datetime.now() - timedelta(days=30)
clear_odds_snapshots_before(cutoff)
```

---

## API Integration

### The Odds API

EV Engine uses [The Odds API](https://the-odds-api.com/) for real-time sports odds data.

**Free Tier:**
- 500 requests per month
- Access to all sports
- Real-time odds updates
- No credit card required

**Rate Limits:**
Each "Refresh Market" operation consumes requests based on sports selected:
- 1 request per sport for available events
- 1 request per sport per bookmaker for player props

Example: Scanning NBA with Pinnacle + 4 DFS books = 6 requests total

**Quota Management:**
Monitor your usage at: https://the-odds-api.com/account/

Tips to conserve quota:
- Refresh only during active betting windows
- Select specific sports instead of scanning all
- Use cached data when possible (freshness indicator)

### Supported Sports and Markets

| Sport | API Key | Markets Supported |
|-------|---------|-------------------|
| NBA | `basketball_nba` | Points, Assists, Rebounds, Threes, Blocks, Steals |
| NCAAB | `basketball_ncaab` | Points, Assists, Rebounds, Threes |
| NFL | `americanfootball_nfl` | Passing Yards, Rushing Yards, Receiving Yards, TDs |
| NCAAF | `americanfootball_ncaaf` | Passing Yards, Rushing Yards, Receiving Yards |
| MLB | `baseball_mlb` | Hits, Runs, RBIs, Strikeouts, Home Runs |
| NHL | `icehockey_nhl` | Points, Goals, Assists, Shots |

### Bookmaker Coverage

**Sharp Bookmaker:**
- Pinnacle (`pinnacle`)

**DFS Platforms:**
- PrizePicks (`prizepicks`)
- Underdog Fantasy (`underdog`)
- Betr (`betr_us_dfs`)
- DraftKings Pick6 (`pick6`)

---

## Testing

### Test Suite Overview

EV Engine has comprehensive test coverage across all modules:

**Test Statistics:**
- Total Tests: 86
- Coverage: 99% (374/378 lines)
- Pass Rate: 100%

### Running Tests

```bash
# All tests with coverage
pytest --cov=src --cov-report=term-missing

# Specific module
pytest tests/test_analysis.py -v

# Integration tests only
pytest -m integration

# Unit tests only
pytest -m unit

# Generate HTML coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Test Organization

**test_analysis.py** - Math and probability calculations
- Implied probability conversions
- De-vig calculations
- EV percentage calculations
- Breakeven probability calculations
- Edge cases and invalid inputs

**test_db.py** - Database operations
- Schema initialization
- CRUD operations for all tables
- Query filtering and sorting
- Transaction management
- Analytics calculations

**test_odds_api.py** - API client functionality
- API response parsing
- Error handling (timeouts, rate limits)
- Data transformation pipeline
- Bookmaker matching logic

**test_validation.py** - Input validation
- API response schema validation
- Type checking and coercion
- Error message clarity

**test_type_safety.py** - Type safety utilities
- Currency parsing
- DataFrame column access
- Stake validation

### Writing New Tests

```python
import pytest

class TestYourFeature:
    """Tests for your new feature."""

    @pytest.mark.unit
    def test_expected_behavior(self):
        """Test description of expected behavior."""
        # Arrange
        input_data = "test"

        # Act
        result = your_function(input_data)

        # Assert
        assert result == expected_value

    @pytest.mark.integration
    def test_database_interaction(self, initialized_db):
        """Test that requires database."""
        # Use initialized_db fixture
        pass
```

---

## Logging

### Log Configuration

Logs are written to both file and console with configurable levels:

```python
# src/config.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ev_engine.log'),
        logging.StreamHandler()
    ]
)
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages for unexpected events
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical issues requiring immediate attention

### Log File Location

Logs are written to `ev_engine.log` in the project root directory.

**Viewing Logs:**
```bash
# View all logs
cat ev_engine.log

# Tail logs in real-time
tail -f ev_engine.log

# View only errors
grep ERROR ev_engine.log

# View last 50 lines
tail -n 50 ev_engine.log
```

### Monitoring Application Health

Check logs for:
- API request failures: `grep "API request failed" ev_engine.log`
- Database errors: `grep "Database operation failed" ev_engine.log`
- Validation failures: `grep "Validation failed" ev_engine.log`

---

## Roadmap

### Completed Phases

**Phase 1: Critical Fixes** ✅
- Fixed hardcoded hit rate data
- Removed duplicate database functions
- Created dedicated analysis module
- Added .env.example template

**Phase 2: Code Quality** ✅
- Implemented logging module
- Fixed silent exception handling
- Added input validation
- Improved type safety

**Phase 3: Testing & Validation** ✅
- Built comprehensive test suite
- Achieved 99% test coverage
- Added pytest fixtures and markers
- Integrated coverage reporting

### Future Enhancements

**Phase 4: Performance Optimization**
- API rate limiting protection with quota warnings
- Response caching (5-10 minute TTL)
- Database query optimization
- Connection pooling

**Phase 5: Feature Expansion**
- Configurable bankroll management
- Expanded market coverage (player_turnovers, player_steals, etc.)
- Start time filtering for live board
- CSV/Excel export functionality
- Email/SMS alerts for high EV opportunities

**Phase 6: Advanced Features**
- Automated bet result fetching via sports data API
- Machine learning models for line movement prediction
- Correlation analysis between player props
- Hedge calculator for in-game betting
- Multi-book arbitrage detection

---

## Troubleshooting

### Common Issues

**Issue: "Module not found" errors**
```bash
# Solution: Ensure virtual environment is activated
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

**Issue: "Database is locked" error**
```bash
# Solution: Close all other connections to the database
# Check for other running instances of dashboard.py
ps aux | grep dashboard.py
kill <process_id>
```

**Issue: "Invalid API key" error**
```bash
# Solution: Verify .env file exists and contains valid key
cat .env
# Should show: ODDS_API_KEY=your_actual_key_here

# Test API key directly
curl "https://api.the-odds-api.com/v4/sports?apiKey=YOUR_KEY"
```

**Issue: No odds data returned**
```bash
# Solution: Check if sport is in season
# Some sports have off-seasons with limited player props
# Try a different sport (NBA is active Oct-June)
```

**Issue: High API quota usage**
```bash
# Solution: Reduce refresh frequency
# Each refresh uses requests = num_sports * (num_bookmakers + 1)
# Be strategic about when you refresh
```

**Issue: Streamlit not opening in browser**
```bash
# Solution: Manually navigate to the URL shown in terminal
# Usually: http://localhost:8501
# Or specify port: streamlit run dashboard.py --server.port 8502
```

### FAQ

**Q: How often should I refresh market data?**
A: Player prop lines typically update every 15-30 minutes. Refreshing more frequently wastes API quota. Aim for 2-3 refreshes per betting session.

**Q: What's a "good" EV percentage?**
A: Generally:
- 0-2%: Marginal edge, proceed with caution
- 2-5%: Solid edge, recommended
- 5%+: Strong edge, high priority
- 10%+: Exceptional edge, verify data is fresh

**Q: Why do some players show both Over and Under +EV?**
A: This can happen temporarily due to line movements or data staleness. Always verify with fresh data before betting. True +EV should be on one side only.

**Q: How is this different from betting odds comparison sites?**
A: Most comparison sites show raw odds. EV Engine de-vigs sharp odds to calculate true probabilities, then compares against DFS payout structures to find mathematical edges.

**Q: Can I use this for traditional sportsbooks?**
A: The math works for any bet type, but it's optimized for DFS pick-em parlays with fixed multipliers. Traditional sportsbook parlays have different payout structures.

**Q: Is positive EV guaranteed profit?**
A: No. EV is a long-term expectation. Short-term variance means you can lose even with +EV bets. Proper bankroll management is essential.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses

- **The Odds API**: Subject to their [Terms of Service](https://the-odds-api.com/terms)
- **Streamlit**: Apache License 2.0
- **Pandas**: BSD 3-Clause License
- **Requests**: Apache License 2.0

---

## Acknowledgments

### Data Sources
- [The Odds API](https://the-odds-api.com/) - Real-time sports odds data

### Libraries and Frameworks
- [Streamlit](https://streamlit.io/) - Web framework for data applications
- [Pandas](https://pandas.pydata.org/) - Data manipulation and analysis
- [Requests](https://requests.readthedocs.io/) - HTTP library for API calls
- [Pytest](https://pytest.org/) - Testing framework

### Inspiration
- The sports betting analytics community
- Professional sports bettors who share their methodologies
- The efficient market hypothesis in sports betting

---

## Disclaimer

**Important Legal and Financial Notice**

This software is provided for **educational and informational purposes only**.

### Gambling Risks
- Sports betting involves financial risk
- Past performance does not guarantee future results
- "Positive EV" does not guarantee profit in any individual bet or session
- Variance can lead to significant losses even with mathematically sound strategies
- Only bet with money you can afford to lose

### Legal Compliance
- Sports betting laws vary by jurisdiction
- It is your responsibility to ensure compliance with local laws
- Some jurisdictions prohibit or restrict sports betting
- Daily fantasy sports may have different legal status than traditional sports betting
- Consult with legal counsel if uncertain about legality in your area

### No Financial Advice
- This tool does not constitute financial, legal, or gambling advice
- Do not rely solely on this software for betting decisions
- Always perform your own due diligence
- Consider consulting with licensed professionals

### Accuracy and Reliability
- Odds data is sourced from third-party APIs and may contain errors
- Database calculations are provided "as-is" without warranty
- The developers are not responsible for losses resulting from use of this software
- Always verify data against official sportsbook sources before placing bets

### Responsible Gambling
If you or someone you know has a gambling problem:
- **National Problem Gambling Helpline**: 1-800-522-4700
- **Online Resources**: [ncpgambling.org](https://www.ncpgambling.org/)

**USE AT YOUR OWN RISK**

By using this software, you acknowledge that you have read and understood this disclaimer.

---

## Support

### Documentation
- [BLUEPRINT.md](./BLUEPRINT.md) - Technical architecture and math methodology
- [UI_SPEC.md](./UI_SPEC.md) - Dashboard features and specifications
- [IMPROVEMENT_PLAN.md](./IMPROVEMENT_PLAN.md) - Development roadmap and future plans
- [TESTING.md](./TESTING.md) - Testing guide and best practices

### Community
- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Ask questions and share ideas in GitHub Discussions
- **Contributing**: See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines

### Getting Help
1. Check this README and documentation files
2. Search existing GitHub Issues
3. Review the test files for usage examples
4. Check application logs in `ev_engine.log`
5. Open a new GitHub Issue with detailed description

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Write tests** for new functionality
4. **Ensure tests pass** (`pytest`)
5. **Format code** (`black src tests && isort src tests`)
6. **Commit changes** (`git commit -m 'Add amazing feature'`)
7. **Push to branch** (`git push origin feature/amazing-feature`)
8. **Open a Pull Request**

### Code Standards
- Follow PEP 8 style guidelines
- Add docstrings to all public functions
- Maintain test coverage above 90%
- Update documentation for new features

---

**Built with data, powered by math, driven by edge.**

*Find your edge. Track your progress. Beat the books.*
