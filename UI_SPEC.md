# UI Specification: EV Engine Dashboard

## 1. Goal
Create a Streamlit-based dashboard (`app.py`) that acts as the command center for the EV Engine. It allows the user to view calculated +EV betting opportunities compared against Pinnacle's sharp lines and filter them to find the best plays.

## 2. Layout & Components

### 2.1 Top Row: Metrics
Display high-level status using `st.metric` columns.
*   **Bankroll**: Hardcoded to `$100.00` for MVP.
*   **Active Bets**: Placeholder integer `0` for MVP.

### 2.2 Sidebar: Filters
Controls to refine the main data view.
*   **Sport Selection**: `st.sidebar.multiselect`
    *   Label: "Select Sports"
    *   Options: Derived from unique sports in the database (e.g., 'NBA', 'NFL').
    *   Default: All.
*   **Minimum EV Threshold**: `st.sidebar.slider`
    *   Label: "Minimum EV %"
    *   Range: `0` to `20`
    *   Default: `0`
    *   Step: `1`

### 2.3 Main Area
*   **Title**: `st.title("EV Engine Dashboard")`
*   **Action Button**: `st.button("Refresh Market")` placed prominently at the top.
*   **Opportunities Table**: A sortable, interactive dataframe displaying potential bets.

## 3. Interaction Logic

### 3.1 Refresh Workflow
When "Refresh Market" is clicked:
1.  Show a spinner: `with st.spinner('Fetching fresh odds...'):`
2.  Call `src.odds_api.fetch_odds()` to get new data from The Odds API.
3.  Trigger a data reload from the database.
4.  Display a success toast or message upon completion.

### 3.2 Styling & Data Presentation
*   **DataFrame**: Use `st.dataframe` for interactivity (sorting).
*   **Columns to Display**: `Player`, `Market`, `Line`, `Odds (Pinnacle)`, `Win Prob`, `EV %`.
*   **Color Coding**:
    *   Apply a style highlight to the *EV %* column.
    *   **Logic**: If `EV % > 10.0`, background color = **Green**.

## 4. Technical Integration

### 4.1 Imports
The dashboard must integrate with the backend modules defined in `BLUEPRINT.md`:
```python
import streamlit as st
import pandas as pd
from src import db
from src import odds_api
from src import analysis  # If calculation logic is needed on the fly
```

### 4.2 Data Integration
*   **Fetching Data**: 
    *   Use `src.db.get_all_opportunities()` (to be implemented) which executes a SQL query against the `bets` table.
    *   The query should return results as a Pandas DataFrame or a list of dictionaries convertible to a DataFrame.
*   **Filtering**:
    *   Apply the `Sport` multiselect filter to the DataFrame.
    *   Apply the `Minimum EV %` slider filter to the DataFrame (`df[df['ev'] >= min_ev]`).

## 5. Requirements Checklist
*   [ ] Streamlit is installed.
*   [ ] `src.db` and `src.odds_api` are importable.
*   [ ] Database is initialized before running the app.
