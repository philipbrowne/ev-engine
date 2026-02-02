import streamlit as st
import pandas as pd
from datetime import datetime
from src import db, odds_api
from src.config import SPORTS_MAP, logger
from src.type_safety import safe_currency_to_float, safe_get_column, validate_stake
from auth import check_password, add_logout_button

# 🔐 AUTHENTICATION: Check password before showing dashboard
if not check_password():
    st.stop()  # Stop execution if not authenticated


def style_row_by_ev(row):
    """Return background and text color for entire row based on EV percentage.

    Applies color coding to dashboard rows for visual identification of
    high-value betting opportunities.

    Args:
        row: DataFrame row with '_EV_Numeric' column

    Returns:
        List of CSS style strings, one per column in the row

    Color Scheme:
        - Gold (#FFD700): EV >= 5.0% (premium opportunities)
        - Light green (#90EE90): 0% < EV < 5% (positive EV)
        - Light red (#FFCCCB): EV <= 0% (negative EV, avoid)

    Examples:
        >>> row = pd.Series({'_EV_Numeric': 6.5, 'Player': 'LeBron'})
        >>> styles = style_row_by_ev(row)
        >>> print(styles[0])  # Gold background
        'background-color: #FFD700; color: black'
    """
    ev = row.get("_EV_Numeric", 0)
    if ev >= 5.0:
        return ["background-color: #FFD700; color: black"] * len(row)
    elif ev > 0.0:
        return ["background-color: #90EE90; color: black"] * len(row)
    else:
        return ["background-color: #FFCCCB; color: black"] * len(row)


def get_recommendation(ev):
    """Return betting recommendation based on EV percentage.

    Categorizes betting opportunities into three action levels for quick
    decision-making in the dashboard.

    Args:
        ev: Expected value percentage (e.g., 5.2 for +5.2% EV)

    Returns:
        String recommendation: 'SMASH', 'FLEX', or 'AVOID'

    Recommendation Logic:
        - 'SMASH': EV > 5.0% - High-value opportunity, strong bet
        - 'FLEX': 0% < EV <= 5.0% - Positive EV, suitable for flex picks
        - 'AVOID': EV <= 0% - Negative EV, do not bet

    Examples:
        >>> get_recommendation(7.5)
        'SMASH'
        >>> get_recommendation(2.3)
        'FLEX'
        >>> get_recommendation(-1.5)
        'AVOID'
    """
    if ev > 5.0:
        return "SMASH"
    elif ev > 0.0:
        return "FLEX"
    else:
        return "AVOID"


def get_risk_level(win_prob):
    """Return risk level categorization based on fair win probability.

    Classifies bets by their win probability to help users balance their
    pick selections and understand variance.

    Args:
        win_prob: Fair win probability as decimal (0 to 1, e.g., 0.58 for 58%)

    Returns:
        String risk level: 'Low Risk', 'Medium Risk', 'High Risk', or 'Unknown'

    Risk Thresholds:
        - Low Risk: win_prob > 58% (>58% chance to hit)
        - Medium Risk: 55% <= win_prob <= 58%
        - High Risk: win_prob < 55% (coin flip or worse)
        - Unknown: If win_prob is NaN/missing

    Examples:
        >>> get_risk_level(0.60)  # 60% win probability
        'Low Risk'
        >>> get_risk_level(0.56)  # 56% win probability
        'Medium Risk'
        >>> get_risk_level(0.52)  # 52% win probability
        'High Risk'
        >>> import pandas as pd
        >>> get_risk_level(pd.NA)
        'Unknown'
    """
    if pd.isna(win_prob):
        return "Unknown"
    prob_pct = win_prob * 100
    if prob_pct > 58:
        return "Low Risk"
    elif prob_pct >= 55:
        return "Medium Risk"
    else:
        return "High Risk"


def get_freshness(timestamp_str):
    """Calculate time difference from now to timestamp for freshness display.

    Converts timestamps into human-readable age indicators to show how
    recent the odds data is.

    Args:
        timestamp_str: ISO format timestamp string or datetime object

    Returns:
        String describing age: '5s ago', '12m ago', '2h ago', '3d ago', or 'Unknown'

    Time Formatting:
        - Seconds: < 60s
        - Minutes: < 60m
        - Hours: < 24h
        - Days: >= 24h

    Examples:
        >>> get_freshness('2024-01-15T12:00:00')  # If now is 12:05:00
        '5m ago'
        >>> get_freshness('N/A')
        'Unknown'
        >>> from datetime import datetime
        >>> get_freshness(datetime.now())
        '0s ago'
    """
    if pd.isna(timestamp_str) or timestamp_str == "N/A":
        return "Unknown"
    try:
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            timestamp = timestamp_str

        now = datetime.now()
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)

        diff = now - timestamp
        total_seconds = int(diff.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s ago"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h ago"
        else:
            days = total_seconds // 86400
            return f"{days}d ago"
    except Exception as e:
        logger.warning(f"Failed to parse timestamp: {e}")
        return "Unknown"


def main():
    """Main entry point for the EV Scout Streamlit dashboard.

    Renders a comprehensive sports betting analytics dashboard with three main tabs:
    1. Live Board - Real-time betting opportunities with EV calculations
    2. Track Bets - Slip creation and bet tracking interface
    3. Analytics - Performance metrics and ROI analysis

    Features:
        - Multi-sport odds scanning with API quota management
        - Real-time EV calculations using Pinnacle sharp odds
        - Visual color coding for opportunity quality
        - Historical hit rate tracking per player/market
        - Slip-based bet tracking with automatic P/L calculations
        - Performance analytics with bankroll progression
        - Risk level categorization for pick selection

    Database Operations:
        Initializes all required tables on startup and maintains connection
        pool throughout session.

    Streamlit Configuration:
        - Wide layout for maximum data visibility
        - Custom page title and metrics dashboard
        - Multi-select filters for books, sports, and risk levels
        - Interactive forms for bet tracking

    Examples:
        Run from command line:
        >>> streamlit run dashboard.py
    """
    # Master Key: Ensure all database tables exist before any operations
    db.initialize_db()

    st.set_page_config(page_title="EV Scout", layout="wide")
    st.title("EV Scout")

    # Calculate analytics from slips
    analytics = db.get_slip_analytics()

    # Top Row: Metrics in columns
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        total_invested = analytics["total_staked"]
        st.metric("Total Invested", f"${total_invested:,.2f}")
    with metric_col2:
        st.metric("Active Slips", analytics["pending"])
    with metric_col3:
        st.metric("Total P/L", f"${analytics['total_profit']:+.2f}")
    with metric_col4:
        st.metric("Win Rate", f"{analytics['win_rate']:.1f}%")

    # Sidebar: Sports to Scan selector (above filters)
    st.sidebar.header("Scan Settings")
    available_sports = list(SPORTS_MAP.keys())
    default_sports = ["NBA", "NFL", "NHL"]  # Exclude NCAAB by default
    selected_scan_sports = st.sidebar.multiselect(
        "Sports to Scan",
        options=available_sports,
        default=[s for s in default_sports if s in available_sports],
        help="Select which sports to fetch when refreshing. NCAAB excluded by default to save API calls."
    )

    # Add logout button at bottom of sidebar
    add_logout_button()

    # Tabs for different sections
    tab_live, tab_track, tab_analytics = st.tabs(["Live Board", "Track Bets", "Analytics"])

    # ==================== LIVE BOARD TAB ====================
    with tab_live:
        # Action Button
        if st.button("Refresh Market"):
            # Convert selected sport names to API keys
            sport_keys = [SPORTS_MAP[sport] for sport in selected_scan_sports if sport in SPORTS_MAP]
            with st.spinner(f"Fetching odds for {', '.join(selected_scan_sports)}..."):
                odds_api.fetch_odds(sports_to_fetch=sport_keys if sport_keys else None)
            st.success("Market data refreshed!")

        # Load data from database
        with st.spinner("Loading opportunities..."):
            df = db.get_all_opportunities()

        # Store df in session state for use in Track Bets tab
        if df is not None and not df.empty:
            st.session_state["live_board_df"] = df.copy()

        if df is None or df.empty:
            st.info("No opportunities found. Click 'Refresh Market' to fetch data.")
        else:
            # Store original values for calculations before formatting
            if "Win Prob" in df.columns:
                df["_Win_Prob_Numeric"] = df["Win Prob"]
                df["Win Prob"] = df["Win Prob"].apply(lambda x: f"{x * 100:.1f}%" if pd.notna(x) else "N/A")

            if "EV %" in df.columns:
                df["_EV_Numeric"] = df["EV %"]
                df["EV %"] = df["EV %"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A")

            if "Timestamp" in df.columns:
                df["Freshness"] = df["Timestamp"].apply(get_freshness)

            if "_Win_Prob_Numeric" in df.columns:
                df["Risk Level"] = df["_Win_Prob_Numeric"].apply(get_risk_level)

            if "_EV_Numeric" in df.columns:
                df["Recommendation"] = df["_EV_Numeric"].apply(get_recommendation)

            # Calculate actual historical hit rates from database
            def get_hit_rate_for_row(row):
                """Get historical hit rate for a specific player/market combination."""
                player = row.get("Player", "")
                market = row.get("Market", "")
                if player and market:
                    return db.get_historical_hit_rate(player, market, limit=8)
                return []

            df["Hit Rate"] = df.apply(get_hit_rate_for_row, axis=1)

            # Sidebar Filters
            st.sidebar.header("Filters")

            # Player search - most important filter for finding specific players
            player_search = st.sidebar.text_input(
                "🔍 Search Player",
                placeholder="e.g. LeBron, Curry...",
                help="Filter by player name (case-insensitive)"
            )

            # Market type filter
            if "Market" in df.columns:
                # Extract market types from market column (e.g., "player_points_over" -> "points")
                def extract_market_type(market):
                    market_lower = str(market).lower()
                    if "points" in market_lower:
                        return "Points"
                    elif "assists" in market_lower:
                        return "Assists"
                    elif "rebound" in market_lower:
                        return "Rebounds"
                    elif "threes" in market_lower or "3pt" in market_lower:
                        return "Threes"
                    elif "steals" in market_lower:
                        return "Steals"
                    elif "blocks" in market_lower:
                        return "Blocks"
                    else:
                        return "Other"

                df["_Market_Type"] = df["Market"].apply(extract_market_type)
                market_types = sorted(df["_Market_Type"].unique().tolist())
                selected_markets = st.sidebar.multiselect(
                    "Market Type",
                    options=market_types,
                    default=market_types,
                    help="Filter by prop type"
                )
            else:
                selected_markets = []

            books = df["Book"].unique().tolist() if "Book" in df.columns else []
            selected_books = st.sidebar.multiselect(
                "Sportsbooks",
                options=books,
                default=books
            )

            risk_levels = ["Low Risk", "Medium Risk", "High Risk"]
            selected_risks = st.sidebar.multiselect(
                "Risk Level",
                options=risk_levels,
                default=risk_levels
            )

            # Consolidate view toggle
            consolidate_view = st.sidebar.checkbox(
                "Consolidate by Player/Market",
                value=False,
                help="Group same player/market and show available books"
            )

            # Apply filters
            filtered_df = df.copy()

            # Player search filter (case-insensitive)
            if player_search and "Player" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["Player"].str.lower().str.contains(player_search.lower(), na=False)
                ]

            # Market type filter
            if selected_markets and "_Market_Type" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["_Market_Type"].isin(selected_markets)]

            if selected_books and "Book" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Book"].isin(selected_books)]
            if selected_risks and "Risk Level" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Risk Level"].isin(selected_risks)]

            # Sort by EV% descending (best plays first)
            if "_EV_Numeric" in filtered_df.columns:
                filtered_df = filtered_df.sort_values("_EV_Numeric", ascending=False)

            # Consolidate view - group by player/market and show books as comma-separated
            if consolidate_view and not filtered_df.empty:
                # Group by Player, Market, Line and aggregate books
                agg_dict = {
                    "Book": lambda x: ", ".join(sorted(set(x))),
                    "Win Prob": "first",
                    "EV %": "first",
                    "Risk Level": "first",
                    "Recommendation": "first",
                    "Freshness": "first",
                    "Hit Rate": "first",
                    "_EV_Numeric": "first",
                    "_Win_Prob_Numeric": "first",
                }
                # Only include columns that exist
                agg_dict = {k: v for k, v in agg_dict.items() if k in filtered_df.columns}

                group_cols = [c for c in ["Player", "Market", "Line"] if c in filtered_df.columns]
                if group_cols:
                    filtered_df = filtered_df.groupby(group_cols, as_index=False).agg(agg_dict)
                    # Rename Book column to show it contains multiple
                    if "Book" in filtered_df.columns:
                        filtered_df = filtered_df.rename(columns={"Book": "Books"})

            column_config = {
                "Hit Rate": st.column_config.BarChartColumn(
                    "Hit Rate",
                    help="Recent hit history (1=hit, 0=miss)",
                    y_min=0,
                    y_max=1,
                ),
                "Recommendation": st.column_config.TextColumn(
                    "Action",
                    help="SMASH (>5% EV), FLEX (>0% EV), AVOID (<0% EV)",
                ),
                "Risk Level": st.column_config.TextColumn(
                    "Risk",
                    help="Based on fair win probability",
                ),
                "Freshness": st.column_config.TextColumn(
                    "Fresh",
                    help="Time since last update",
                ),
                "Books": st.column_config.TextColumn(
                    "Books",
                    help="Available sportsbooks with this line",
                    width="medium",
                ),
            }

            priority_columns = ["Recommendation", "Risk Level", "Win Prob", "EV %"]
            # Handle both "Book" (normal view) and "Books" (consolidated view)
            book_col = "Books" if "Books" in filtered_df.columns else "Book"
            other_columns = [book_col, "Player", "Market", "Line", "Freshness", "Hit Rate"]

            display_columns = []
            for col in priority_columns:
                if col in filtered_df.columns:
                    display_columns.append(col)
            for col in other_columns:
                if col in filtered_df.columns:
                    display_columns.append(col)

            if display_columns:
                display_df = filtered_df[display_columns].copy()

                # Show filter results summary
                total_before_filter = len(df)
                total_after_filter = len(display_df)
                if player_search:
                    st.caption(f"Showing {total_after_filter} results for '{player_search}'")
                elif total_after_filter < total_before_filter:
                    st.caption(f"Showing {total_after_filter} of {total_before_filter} opportunities")

                st.dataframe(
                    display_df,
                    column_config=column_config,
                    hide_index=True,
                    use_container_width=True,
                    height=500,  # Fixed height with scroll
                )

                st.markdown("---")
                stat_col1, stat_col2, stat_col3 = st.columns(3)
                with stat_col1:
                    st.metric("Total Opportunities", len(filtered_df))
                with stat_col2:
                    smash_count = len(filtered_df[filtered_df["Recommendation"] == "SMASH"]) if "Recommendation" in filtered_df.columns else 0
                    st.metric("SMASH Plays", smash_count)
                with stat_col3:
                    low_risk_count = len(filtered_df[filtered_df["Risk Level"] == "Low Risk"]) if "Risk Level" in filtered_df.columns else 0
                    st.metric("Low Risk Plays", low_risk_count)
            else:
                st.dataframe(filtered_df, hide_index=True, width="stretch")

    # ==================== TRACK BETS TAB ====================
    with tab_track:
        st.subheader("Track Bets")

        # Get live board data for multi-select
        live_df = st.session_state.get("live_board_df", pd.DataFrame())

        st.markdown("### Create New Slip")

        # Initialize session state for selected picks if not exists
        if "selected_legs" not in st.session_state:
            st.session_state.selected_legs = []

        # Callback to clear selections when book or num_legs changes
        def on_selection_change():
            st.session_state.selected_legs = []

        # Book and Number of Legs selectors OUTSIDE the form for dynamic updates
        selector_row = st.columns([1, 1, 2])

        with selector_row[0]:
            book = st.selectbox(
                "Book",
                ["PrizePicks", "Underdog", "Betr", "DK Pick6"],
                key="book_selector",
                on_change=on_selection_change
            )

        with selector_row[1]:
            num_legs = st.radio(
                "Legs",
                [2, 3, 4, 5],
                horizontal=True,
                key="num_legs_radio",
                on_change=on_selection_change
            )

        with selector_row[2]:
            st.empty()  # Spacer

        # Build selectable options filtered by selected book
        pick_options = []
        filtered_df = pd.DataFrame()

        if not live_df.empty and "Player" in live_df.columns and "Market" in live_df.columns:
            # Filter by selected book
            if "Book" in live_df.columns:
                filtered_df = live_df[live_df["Book"] == book].copy()
            else:
                filtered_df = live_df.copy()

            if not filtered_df.empty:
                # Create display labels for selection (without book name since we're filtering)
                filtered_df["_select_label"] = filtered_df.apply(
                    lambda r: f"{r['Player']} - {r['Market']} @ {r.get('Line', 'N/A')}",
                    axis=1
                )
                pick_options = filtered_df["_select_label"].tolist()

        # Slip creation form
        with st.form("create_slip_form", clear_on_submit=True):
            stake = st.number_input("Stake ($)", min_value=1.0, value=10.0, step=1.0)

            st.markdown(f"**Select {num_legs} Picks from {book}:**")

            if pick_options:
                selected_picks = st.multiselect(
                    "Choose your picks",
                    options=pick_options,
                    max_selections=num_legs,
                    default=[],
                    key="pick_multiselect",
                    help=f"Select exactly {num_legs} picks for your {book} slip"
                )
            else:
                st.warning(f"No picks available for {book}. Refresh the Live Board or select a different book!")
                selected_picks = []

            # Optional note
            note = st.text_input("Note (optional)", placeholder="e.g., Lock of the day")

            submitted = st.form_submit_button("Log Slip", width="stretch", type="primary")

            if submitted:
                if len(selected_picks) != num_legs:
                    st.error(f"Please select exactly {num_legs} picks. You selected {len(selected_picks)}.")
                else:
                    # Validate stake with type-safe validation
                    try:
                        validated_stake = validate_stake(stake)
                    except ValueError as e:
                        st.error(str(e))
                        validated_stake = None

                    if validated_stake:
                        # Build legs from selected picks using filtered_df
                        legs = []
                        for pick_label in selected_picks:
                            # Find the matching row in filtered_df (which has _select_label)
                            if not filtered_df.empty and "_select_label" in filtered_df.columns:
                                match = filtered_df[filtered_df["_select_label"] == pick_label]
                                if not match.empty:
                                    row = match.iloc[0]
                                    legs.append({
                                        "player": row.get("Player", "Unknown"),
                                        "market": row.get("Market", "Unknown"),
                                        "line": row.get("Line", 0.0),
                                    })

                        if legs:
                            slip_id = db.create_slip(
                                book=book,
                                stake=validated_stake,
                                legs=legs,
                                note=note if note else None,
                            )
                            st.session_state.selected_legs = []  # Clear after successful submit
                            st.success(f"Slip #{slip_id} created with {len(legs)} legs!")
                            st.rerun()

        st.markdown("---")

        # Display pending slips
        st.markdown("### Pending Slips")
        slips_df = db.get_all_slips(limit=100)

        if slips_df.empty:
            st.info("No slips tracked yet. Create your first slip above!")
        else:
            pending_slips = slips_df[slips_df["Status"] == "Pending"]

            if pending_slips.empty:
                st.info("No pending slips. All slips have been settled!")
            else:
                for _, row in pending_slips.iterrows():
                    slip_id = row["ID"]
                    # Use type-safe currency conversion
                    stake_val = safe_currency_to_float(row["Stake"])
                    multiplier = {2: 3.0, 3: 5.0, 4: 6.0, 5: 10.0}.get(row["Legs"], 3.0)
                    potential = stake_val * multiplier

                    # Slip info row
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.write(f"**Slip #{slip_id}** - {row['Picks']}")
                        st.caption(f"{row['Book']} | {row['Legs']} legs")
                    with col2:
                        st.write(f"Stake: {row['Stake']}")
                    with col3:
                        st.write(f"Potential: ${potential:.0f}")

                    # Resolve expander
                    with st.expander(f"Resolve Slip #{slip_id}", expanded=False):
                        resolve_cols = st.columns([2, 1, 1])

                        with resolve_cols[0]:
                            payout_amount = st.number_input(
                                "Actual Payout ($)",
                                min_value=0.0,
                                max_value=potential * 2,
                                value=0.0,
                                step=1.0,
                                key=f"payout_{slip_id}",
                                help=f"Enter 0 for Lost, {stake_val:.0f} for Push, {potential:.0f} for full Win"
                            )

                        with resolve_cols[1]:
                            # Preview the status
                            if payout_amount > stake_val:
                                preview_status = "Profit"
                            elif payout_amount == stake_val:
                                preview_status = "Push"
                            elif payout_amount > 0:
                                preview_status = "Partial"
                            else:
                                preview_status = "Lost"
                            st.write(f"Status: **{preview_status}**")
                            st.write(f"P/L: ${payout_amount - stake_val:+.2f}")

                        with resolve_cols[2]:
                            if st.button("Save Result", key=f"save_{slip_id}", type="primary"):
                                db.update_slip_status(slip_id, payout_amount)
                                st.success(f"Slip #{slip_id} resolved as {preview_status}!")
                                st.rerun()

                    st.divider()

            # Show recent settled slips
            st.markdown("---")
            st.markdown("### Recent History")
            settled_slips = slips_df[slips_df["Status"] != "Pending"].head(20)

            if not settled_slips.empty:
                display_cols = ["ID", "Book", "Legs", "Picks", "Stake", "Status", "P/L"]
                st.dataframe(
                    settled_slips[display_cols],
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.caption("No settled slips yet.")

    # ==================== ANALYTICS TAB ====================
    with tab_analytics:
        st.subheader("Performance Analytics")

        metric_row1 = st.columns(4)
        with metric_row1[0]:
            st.metric(
                "Total Profit",
                f"${analytics['total_profit']:+.2f}",
                delta=f"{analytics['roi']:+.1f}% ROI" if analytics['total_staked'] > 0 else None
            )
        with metric_row1[1]:
            st.metric("Actual ROI", f"{analytics['roi']:+.1f}%")
        with metric_row1[2]:
            st.metric("Win Rate", f"{analytics['win_rate']:.1f}%")
        with metric_row1[3]:
            st.metric("Total Slips", f"{analytics['wins'] + analytics['losses']} settled")

        st.markdown("---")

        st.markdown("### Record Breakdown")
        record_cols = st.columns(4)
        with record_cols[0]:
            st.metric("Wins", analytics["wins"])
        with record_cols[1]:
            st.metric("Losses", analytics["losses"])
        with record_cols[2]:
            st.metric("Pending", analytics["pending"])
        with record_cols[3]:
            st.metric("Total Wagered", f"${analytics['total_staked']:.2f}")

        st.markdown("---")

        st.markdown("### Bankroll Growth")
        if len(analytics["bankroll_history"]) > 1:
            chart_data = pd.DataFrame({
                "Slip #": range(len(analytics["bankroll_history"])),
                "Bankroll": analytics["bankroll_history"]
            })
            st.line_chart(chart_data.set_index("Slip #"))
        else:
            st.info("Place and settle some slips to see your bankroll growth chart!")

        st.markdown("---")
        st.markdown("### Performance by Book")
        slips_df = db.get_all_slips(limit=500)

        if not slips_df.empty:
            settled = slips_df[slips_df["Status"].isin(["Won", "Lost"])]
            if not settled.empty:
                book_stats = []
                for book in settled["Book"].unique():
                    book_slips = settled[settled["Book"] == book]
                    book_wins = len(book_slips[book_slips["Status"] == "Won"])
                    book_total = len(book_slips)
                    book_wr = (book_wins / book_total * 100) if book_total > 0 else 0
                    book_stats.append({
                        "Book": book,
                        "Slips": book_total,
                        "Wins": book_wins,
                        "Win Rate": f"{book_wr:.1f}%"
                    })

                if book_stats:
                    st.dataframe(
                        pd.DataFrame(book_stats),
                        hide_index=True,
                        width="stretch"
                    )
            else:
                st.info("No settled slips to analyze yet.")
        else:
            st.info("Track some slips to see performance by book!")


if __name__ == "__main__":
    main()
