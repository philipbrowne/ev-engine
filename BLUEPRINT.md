# EV Engine Blueprint

## 1. Project Structure

```text
ev-engine/
├── data/
│   └── ev_engine.db          # SQLite Database
├── src/
│   ├── __init__.py
│   ├── config.py             # API keys and constants
│   ├── db.py                 # Database connection and queries
│   ├── odds_api.py           # The Odds API client
│   ├── analysis.py           # Math logic and EV calculation
│   └── main.py               # Streamlit application entry point
├── requirements.txt          # Python dependencies
└── BLUEPRINT.md              # This file
```

## 2. Database Schema

### Table: `odds_snapshot`
Stores raw odds data fetched from The Odds API.

| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-incrementing ID |
| event_id | TEXT | Unique event ID from API |
| sport_key | TEXT | e.g., 'basketball_nba' |
| bookmaker | TEXT | e.g., 'pinnacle', 'prizepicks' |
| market_key | TEXT | e.g., 'player_points' |
| player_name | TEXT | Name of the player |
| selection | TEXT | 'Over' or 'Under' |
| price | REAL | American odds or line value |
| point | REAL | The handicap/line (e.g., 22.5) |
| timestamp | DATETIME | When the data was fetched |

### Table: `bets`
Stores calculated opportunities where Sharp odds disagree with DFS lines.

| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-incrementing ID |
| event_id | TEXT | FK to odds_snapshot |
| player_name | TEXT | |
| market | TEXT | |
| line_value | REAL | The PrizePicks line (e.g., 22.5) |
| pinnacle_over_price | INTEGER | Pinnacle Over odds |
| pinnacle_under_price | INTEGER | Pinnacle Under odds |
| fair_win_prob | REAL | No-vig probability of winning the bet |
| ev_percentage | REAL | Calculated Expected Value |
| timestamp | DATETIME | Time of calculation |

## 3. The Math Logic

**Objective:** identifying if a 2-pick parlay (3x Payout) has positive expected value based on Pinnacle's efficient market pricing.

**Constants:**
- `PAYOUT_MULTIPLIER = 3.0` (Standard 2-Pick Power Play)
- `BREAK_EVEN_WIN_PCT = 1 / 3.0 = 33.33%` (For the entire parlay)
- `IMPLIED_LEG_PROB = sqrt(0.3333) ≈ 57.7%` (Per leg break-even probability)

**Pseudocode:**

```python
def calculate_parlay_ev(leg1_odds_over, leg1_odds_under, leg2_odds_over, leg2_odds_under):
    """
    Inputs are American Odds from Pinnacle (e.g., -130, +110)
    """
    
    # 1. Helper to convert American Odds to Decimal
    def to_decimal(american):
        if american > 0:
            return 1 + (american / 100)
        else:
            return 1 + (100 / abs(american))

    # 2. De-Vig Pinnacle Odds to get Fair Win Probability (Multiplicative/Proportional Method)
    def get_fair_prob(odds_main, odds_counter):
        dec_main = to_decimal(odds_main)
        dec_counter = to_decimal(odds_counter)
        
        implied_main = 1 / dec_main
        implied_counter = 1 / dec_counter
        
        market_vig = implied_main + implied_counter
        
        # Fair probability removes the vigorish
        fair_prob = implied_main / market_vig
        return fair_prob

    # Calculate fair probabilities for each chosen leg (assuming we pick the favored side)
    # in a real scenario, we check both sides to find the one with > 57.7% win prob
    leg1_prob = get_fair_prob(leg1_odds_over, leg1_odds_under)
    leg2_prob = get_fair_prob(leg2_odds_over, leg2_odds_under)

    # 3. Calculate Parlay Win Probability
    # Assuming independent events
    parlay_win_prob = leg1_prob * leg2_prob

    # 4. Calculate Expected Value (EV) against the 3x Payout
    # EV = (Probability of Win * Profit) - (Probability of Loss * Stake)
    # Profit on 1 unit is 2 units (3x payout - 1 stake). 
    # Or simply: (Win Prob * Payout) - 1
    
    ev = (parlay_win_prob * 3.0) - 1
    
    return {
        "parlay_win_prob": parlay_win_prob,
        "ev": ev,
        "is_profitable": ev > 0
    }
```

## 4. Implementation Steps

1.  **Project & Database Setup**: Initialize the folder structure, create the virtual environment, install requirements, and set up the SQLite database with the schema defined above.
2.  **API Integration**: Build the `odds_api.py` module to fetch player prop odds from The Odds API for both 'Pinnacle' (Sharp) and 'PrizePicks/Underdog' (DFS).
3.  **Data Processing & De-vig**: Implement the math logic in `analysis.py`. Match Pinnacle lines to PrizePicks lines (ensure strict name and line matching, e.g., LeBron James Points 24.5 vs 24.5). De-vig the Pinnacle odds to find the "fair" probability.
4.  **EV Engine Core**: Run the comparison loop. Identify individual legs where Pinnacle's fair win probability is significantly higher than the break-even threshold (~57.7%). Store these potential plays in the `bets` table.
5.  **Streamlit Visualization**: Create a simple dashboard (`main.py`) that queries the `bets` table and displays the best +EV plays, allowing filter by sport or start time.
