# Antigravity EV Engine

Expected Value calculator for sports betting, comparing sharp odds (Pinnacle) against DFS platforms (PrizePicks, Underdog, etc.).

## Quick Start

Run the initialization script:

**Mac/Linux:**
```bash
./init.sh
```

**Windows (or alternative):**
```bash
python3 init.py
```

This will:
- ✓ Check Python installation
- ✓ Create virtual environment
- ✓ Install dependencies
- ✓ Configure API keys
- ✓ Initialize database

Then start the dashboard:

```bash
source venv/bin/activate
streamlit run dashboard.py
```

## What You Need

1. **Python 3.8+** - [Download here](https://www.python.org/)
2. **The Odds API Key** - [Get free key](https://the-odds-api.com/)

## How It Works

1. **Fetch Odds** - Click "Refresh Market" to pull odds from Pinnacle (sharp) and DFS books
2. **Calculate EV** - Compares de-vigged Pinnacle probabilities vs DFS lines
3. **Find Edges** - Identifies +EV opportunities for 2-5 leg parlays
4. **Track Performance** - Log slips and analyze results

## Features

- **Live Board** - Real-time +EV opportunities with risk ratings
- **Track Bets** - Log and manage your slips
- **Analytics** - Win rate, ROI, and bankroll tracking

## Documentation

- `BLUEPRINT.md` - Technical architecture and math
- `UI_SPEC.md` - Dashboard features and layout

## Support

Questions? Check the documentation or review the source code in `src/`.
