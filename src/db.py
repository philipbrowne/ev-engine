"""Database connection and query management for EV Engine."""

import sqlite3
from datetime import datetime
from typing import Optional

import pandas as pd

from .config import DATABASE_PATH, logger
from .type_safety import safe_float, safe_dict_get


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection with row factory enabled.

    Establishes a connection to the SQLite database and configures it to return
    rows as dictionaries (using sqlite3.Row) for convenient column access by name.

    Returns:
        SQLite connection object with row_factory configured

    Examples:
        >>> conn = get_connection()
        >>> cursor = conn.cursor()
        >>> cursor.execute("SELECT * FROM bets LIMIT 1")
        >>> row = cursor.fetchone()
        >>> print(row["player_name"])  # Access by column name
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    """Initialize the database schema with all required tables and indexes.

    Creates the following tables if they don't exist:
    - odds_snapshot: Stores historical odds data from bookmakers
    - bets: Stores calculated EV opportunities
    - placed_bets: Legacy table for tracking placed bets
    - slips: Parent table for multi-leg bet slips
    - slip_legs: Child table for individual picks on each slip

    Also creates indexes on commonly queried columns for performance optimization.
    This function is idempotent and safe to call multiple times.

    SQL Operations:
        - CREATE TABLE IF NOT EXISTS (5 tables)
        - CREATE INDEX IF NOT EXISTS (5 indexes)
        - Transaction is committed before closing connection

    Examples:
        >>> initialize_db()  # Safe to call on first run
        >>> initialize_db()  # Safe to call again, no-op if tables exist
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create odds_snapshot table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odds_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            sport_key TEXT NOT NULL,
            bookmaker TEXT NOT NULL,
            market_key TEXT NOT NULL,
            player_name TEXT NOT NULL,
            selection TEXT NOT NULL,
            price REAL NOT NULL,
            point REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create bets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            market TEXT NOT NULL,
            line_value REAL NOT NULL,
            pinnacle_over_price INTEGER,
            pinnacle_under_price INTEGER,
            fair_win_prob REAL NOT NULL,
            ev_percentage REAL NOT NULL,
            dfs_book TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create placed_bets table for tracking actual bets (legacy)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS placed_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            book TEXT NOT NULL,
            player_market TEXT,
            stake REAL NOT NULL,
            payout REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Pending',
            expected_ev REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create slips table (parent - the bet slip)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS slips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book TEXT NOT NULL,
            stake REAL NOT NULL,
            payout REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Pending',
            note TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create slip_legs table (children - individual picks on the slip)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS slip_legs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slip_id INTEGER NOT NULL,
            player TEXT NOT NULL,
            market TEXT NOT NULL,
            line REAL,
            outcome TEXT,
            FOREIGN KEY (slip_id) REFERENCES slips(id) ON DELETE CASCADE
        )
    """)

    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_odds_snapshot_event
        ON odds_snapshot(event_id, player_name, market_key)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bets_ev
        ON bets(ev_percentage DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_placed_bets_date
        ON placed_bets(date DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_slips_status
        ON slips(status, timestamp DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_slip_legs_slip
        ON slip_legs(slip_id)
    """)

    conn.commit()
    conn.close()


def insert_odds_snapshot(
    event_id: str,
    sport_key: str,
    bookmaker: str,
    market_key: str,
    player_name: str,
    selection: str,
    price: float,
    point: float,
    timestamp: Optional[datetime] = None,
) -> int:
    """Insert a single odds snapshot record into the database.

    Captures a point-in-time snapshot of betting odds from a specific bookmaker
    for a player prop market. Used for tracking odds movements over time.

    Args:
        event_id: Unique identifier for the sporting event
        sport_key: Sport identifier (e.g., 'basketball_nba', 'icehockey_nhl')
        bookmaker: Bookmaker key (e.g., 'pinnacle', 'prizepicks')
        market_key: Market type (e.g., 'player_points', 'player_assists')
        player_name: Full name of the player
        selection: Bet selection ('Over' or 'Under')
        price: American odds (e.g., -110, +150)
        point: Line value (e.g., 25.5 points)
        timestamp: Time of odds snapshot (default: current time)

    Returns:
        Database row ID of the inserted record

    SQL Operations:
        - INSERT INTO odds_snapshot
        - Table affected: odds_snapshot
        - Transaction is committed before closing connection

    Examples:
        >>> row_id = insert_odds_snapshot(
        ...     event_id="abc123",
        ...     sport_key="basketball_nba",
        ...     bookmaker="pinnacle",
        ...     market_key="player_points",
        ...     player_name="LeBron James",
        ...     selection="Over",
        ...     price=-110,
        ...     point=25.5
        ... )
    """
    conn = get_connection()
    cursor = conn.cursor()

    if timestamp is None:
        timestamp = datetime.now()

    cursor.execute(
        """
        INSERT INTO odds_snapshot
        (event_id, sport_key, bookmaker, market_key, player_name, selection, price, point, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (event_id, sport_key, bookmaker, market_key, player_name, selection, price, point, timestamp),
    )

    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def insert_odds_batch(records: list[dict]) -> int:
    """Insert multiple odds snapshot records in a single transaction.

    Efficiently inserts a batch of odds data using executemany() for better
    performance. Automatically initializes database schema if needed.

    Args:
        records: List of dictionaries with keys: event_id, sport_key, bookmaker,
            market_key, player_name, selection, price, point, timestamp

    Returns:
        Number of records successfully inserted

    SQL Operations:
        - INSERT INTO odds_snapshot (batch operation)
        - Table affected: odds_snapshot
        - Single transaction for all records

    Examples:
        >>> records = [
        ...     {
        ...         "event_id": "abc123",
        ...         "sport_key": "basketball_nba",
        ...         "bookmaker": "pinnacle",
        ...         "market_key": "player_points",
        ...         "player_name": "LeBron James",
        ...         "selection": "Over",
        ...         "price": -110,
        ...         "point": 25.5,
        ...         "timestamp": datetime.now()
        ...     },
        ...     # ... more records
        ... ]
        >>> count = insert_odds_batch(records)
        >>> print(f"Inserted {count} records")
    """
    if not records:
        return 0

    # Ensure tables exist before inserting
    initialize_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.executemany(
        """
        INSERT INTO odds_snapshot
        (event_id, sport_key, bookmaker, market_key, player_name, selection, price, point, timestamp)
        VALUES (:event_id, :sport_key, :bookmaker, :market_key, :player_name, :selection, :price, :point, :timestamp)
        """,
        records,
    )

    rows_inserted = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_inserted


def insert_bet(
    event_id: str,
    player_name: str,
    market: str,
    line_value: float,
    pinnacle_over_price: Optional[int],
    pinnacle_under_price: Optional[int],
    fair_win_prob: float,
    ev_percentage: float,
    dfs_book: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> int:
    """Insert a calculated betting opportunity with EV metrics.

    Stores an analyzed betting opportunity that compares sharp bookmaker (Pinnacle)
    odds against DFS book lines to identify positive expected value plays.

    Args:
        event_id: Unique identifier for the sporting event
        player_name: Full name of the player
        market: Market type with direction (e.g., 'player_points_over')
        line_value: Prop line value (e.g., 25.5)
        pinnacle_over_price: Pinnacle's Over odds (American format, e.g., -110)
        pinnacle_under_price: Pinnacle's Under odds (American format, e.g., -110)
        fair_win_prob: Fair win probability after devigging (0 to 1)
        ev_percentage: Expected value as percentage (e.g., 5.2 for +5.2% EV)
        dfs_book: DFS bookmaker name (e.g., 'PrizePicks', 'Underdog')
        timestamp: Time of calculation (default: current time)

    Returns:
        Database row ID of the inserted bet opportunity

    SQL Operations:
        - INSERT INTO bets
        - Table affected: bets
        - Transaction is committed before closing connection

    Examples:
        >>> bet_id = insert_bet(
        ...     event_id="abc123",
        ...     player_name="LeBron James",
        ...     market="player_points_over",
        ...     line_value=25.5,
        ...     pinnacle_over_price=-105,
        ...     pinnacle_under_price=-115,
        ...     fair_win_prob=0.548,
        ...     ev_percentage=1.0,
        ...     dfs_book="PrizePicks"
        ... )
    """
    conn = get_connection()
    cursor = conn.cursor()

    if timestamp is None:
        timestamp = datetime.now()

    cursor.execute(
        """
        INSERT INTO bets
        (event_id, player_name, market, line_value, pinnacle_over_price, pinnacle_under_price, fair_win_prob, ev_percentage, dfs_book, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (event_id, player_name, market, line_value, pinnacle_over_price, pinnacle_under_price, fair_win_prob, ev_percentage, dfs_book, timestamp),
    )

    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_latest_odds(
    sport_key: Optional[str] = None,
    bookmaker: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Retrieve the latest odds snapshots with optional filtering.

    Queries the odds_snapshot table for recent odds data, optionally filtered
    by sport and/or bookmaker. Results are ordered by timestamp descending.

    Args:
        sport_key: Filter by sport (e.g., 'basketball_nba'). None returns all sports.
        bookmaker: Filter by bookmaker (e.g., 'pinnacle'). None returns all bookmakers.
        limit: Maximum number of records to return (default: 100)

    Returns:
        List of dictionaries containing odds snapshot data with keys:
        id, event_id, sport_key, bookmaker, market_key, player_name,
        selection, price, point, timestamp

    SQL Operations:
        - SELECT * FROM odds_snapshot with optional WHERE filters
        - Ordered by timestamp DESC
        - Table queried: odds_snapshot

    Examples:
        >>> # Get latest 100 NBA odds from Pinnacle
        >>> odds = get_latest_odds(sport_key="basketball_nba", bookmaker="pinnacle")
        >>> print(f"Found {len(odds)} odds records")

        >>> # Get latest 50 odds from all sports and bookmakers
        >>> all_odds = get_latest_odds(limit=50)
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM odds_snapshot WHERE 1=1"
    params = []

    if sport_key:
        query += " AND sport_key = ?"
        params.append(sport_key)

    if bookmaker:
        query += " AND bookmaker = ?"
        params.append(bookmaker)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_best_bets(min_ev: float = 0.0, limit: int = 50) -> list[dict]:
    """Retrieve betting opportunities with EV above the specified threshold.

    Queries the bets table for positive expected value opportunities, sorted
    by EV percentage in descending order (highest EV first).

    Args:
        min_ev: Minimum EV percentage threshold (default: 0.0 for all +EV bets)
        limit: Maximum number of bets to return (default: 50)

    Returns:
        List of dictionaries containing bet data with keys: id, event_id,
        player_name, market, line_value, pinnacle_over_price,
        pinnacle_under_price, fair_win_prob, ev_percentage, dfs_book, timestamp

    SQL Operations:
        - SELECT * FROM bets WHERE ev_percentage >= ?
        - Ordered by ev_percentage DESC
        - Table queried: bets

    Examples:
        >>> # Get top 50 positive EV bets
        >>> bets = get_best_bets(min_ev=0.0)

        >>> # Get only high-value bets (>5% EV)
        >>> premium_bets = get_best_bets(min_ev=5.0, limit=10)
        >>> for bet in premium_bets:
        ...     print(f"{bet['player_name']}: {bet['ev_percentage']:.1f}% EV")
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM bets
        WHERE ev_percentage >= ?
        ORDER BY ev_percentage DESC
        LIMIT ?
        """,
        (min_ev, limit),
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_pinnacle_odds_for_player(
    player_name: str,
    market_key: str,
    point: float,
) -> Optional[dict]:
    """Get the latest Pinnacle over/under odds for a specific player and line.

    Retrieves the most recent Pinnacle odds for both Over and Under selections
    on a specific player prop market at a given line value. Used as the sharp
    reference point for calculating fair probabilities.

    Args:
        player_name: Full name of the player
        market_key: Market type (e.g., 'player_points', 'player_assists')
        point: Line value to match (e.g., 25.5)

    Returns:
        Dictionary with keys: player_name, market_key, point, over_price, under_price
        Returns None if no Pinnacle odds found for the specified player/market/line

    SQL Operations:
        - SELECT with subquery to get most recent timestamp
        - Table queried: odds_snapshot
        - Filters: bookmaker='pinnacle', exact match on player/market/point

    Examples:
        >>> odds = get_pinnacle_odds_for_player(
        ...     player_name="LeBron James",
        ...     market_key="player_points",
        ...     point=25.5
        ... )
        >>> if odds:
        ...     print(f"Over: {odds['over_price']}, Under: {odds['under_price']}")
        ... else:
        ...     print("No Pinnacle odds available")
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT selection, price FROM odds_snapshot
        WHERE player_name = ?
        AND market_key = ?
        AND point = ?
        AND bookmaker = 'pinnacle'
        AND timestamp = (
            SELECT MAX(timestamp) FROM odds_snapshot
            WHERE player_name = ? AND market_key = ? AND point = ? AND bookmaker = 'pinnacle'
        )
        """,
        (player_name, market_key, point, player_name, market_key, point),
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    result = {"player_name": player_name, "market_key": market_key, "point": point}
    for row in rows:
        if row["selection"] == "Over":
            result["over_price"] = row["price"]
        elif row["selection"] == "Under":
            result["under_price"] = row["price"]

    return result


def clear_old_snapshots(days: int = 7) -> int:
    """Remove odds snapshots older than the specified number of days.

    Deletes historical odds data to prevent database bloat. Useful for
    maintaining only recent odds relevant to active betting opportunities.

    Args:
        days: Delete snapshots older than this many days (default: 7)

    Returns:
        Number of records deleted

    SQL Operations:
        - DELETE FROM odds_snapshot WHERE timestamp < datetime('now', '-N days')
        - Table affected: odds_snapshot
        - Transaction is committed before closing connection

    Examples:
        >>> # Remove odds data older than 7 days
        >>> deleted = clear_old_snapshots(days=7)
        >>> print(f"Deleted {deleted} old odds records")

        >>> # Keep only last 24 hours of data
        >>> deleted = clear_old_snapshots(days=1)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM odds_snapshot
        WHERE timestamp < datetime('now', ?)
        """,
        (f"-{days} days",),
    )

    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_deleted


def clear_bets() -> int:
    """Clear all records from the bets table.

    Removes all calculated betting opportunities from the database. Typically
    called before refreshing market data to ensure stale opportunities are removed.

    Returns:
        Number of records deleted (0 if table doesn't exist)

    SQL Operations:
        - DELETE FROM bets (all records)
        - Table affected: bets
        - Transaction is committed before closing connection
        - Handles OperationalError gracefully if table doesn't exist

    Examples:
        >>> # Clear old opportunities before fetching fresh data
        >>> deleted = clear_bets()
        >>> print(f"Cleared {deleted} stale betting opportunities")
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM bets")
        rows_deleted = cursor.rowcount
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.error(f"Database operation failed in clear_bets: {e}", exc_info=True)
        # Table doesn't exist yet, nothing to clear
        rows_deleted = 0
    finally:
        conn.close()

    return rows_deleted


def get_all_opportunities() -> pd.DataFrame:
    """Retrieve betting opportunities from the bets table as a formatted DataFrame.

    Queries the bets table and formats the data for display in the dashboard.
    Groups by player/market/line/book to deduplicate, keeping the highest EV
    and most recent timestamp for each unique opportunity.

    Returns:
        DataFrame with columns: Book, Player, Market, Line, Odds (Pinnacle),
        Win Prob, EV %, Timestamp. Returns empty DataFrame if no opportunities
        exist or table doesn't exist yet.

    SQL Operations:
        - SELECT with GROUP BY player_name, market, line_value, dfs_book
        - Ordered by ev_percentage DESC
        - Table queried: bets
        - Handles OperationalError if table doesn't exist

    Examples:
        >>> df = get_all_opportunities()
        >>> if not df.empty:
        ...     print(f"Found {len(df)} opportunities")
        ...     top_ev = df.iloc[0]
        ...     print(f"Best: {top_ev['Player']} - {top_ev['EV %']}")
        ... else:
        ...     print("No opportunities available")
    """
    columns = [
        "Book",
        "Player",
        "Market",
        "Line",
        "Odds (Pinnacle)",
        "Win Prob",
        "EV %",
        "Timestamp",
    ]

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                player_name,
                market,
                line_value,
                pinnacle_over_price,
                pinnacle_under_price,
                fair_win_prob,
                MAX(ev_percentage) as ev_percentage,
                dfs_book,
                MAX(timestamp) as timestamp
            FROM bets
            GROUP BY player_name, market, line_value, dfs_book
            ORDER BY ev_percentage DESC
            """
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        logger.error(f"Database operation failed in get_all_opportunities: {e}", exc_info=True)
        # Table doesn't exist yet, return empty DataFrame
        conn.close()
        return pd.DataFrame(columns=columns)

    conn.close()

    if not rows:
        return pd.DataFrame(columns=columns)

    data = []
    for row in rows:
        over_price = row["pinnacle_over_price"]
        under_price = row["pinnacle_under_price"]
        if over_price and under_price:
            odds_str = f"{over_price}/{under_price}"
        elif over_price:
            odds_str = str(over_price)
        elif under_price:
            odds_str = str(under_price)
        else:
            odds_str = "N/A"

        data.append({
            "Book": row["dfs_book"] or "Unknown",
            "Player": row["player_name"],
            "Market": row["market"],
            "Line": row["line_value"],
            "Odds (Pinnacle)": odds_str,
            "Win Prob": row["fair_win_prob"],
            "EV %": row["ev_percentage"],
            "Timestamp": row["timestamp"],
        })

    return pd.DataFrame(data, columns=columns)


def log_bet(
    date: str,
    book: str,
    stake: float,
    expected_ev: float,
    player_market: Optional[str] = None,
) -> int:
    """Record a new placed bet slip (legacy function).

    Legacy function for tracking individual bets. Consider using create_slip()
    for modern slip-based tracking with multiple legs.

    Args:
        date: Date of bet placement (string format, e.g., '2024-01-15')
        book: Bookmaker name
        stake: Amount wagered
        expected_ev: Expected value percentage at time of bet
        player_market: Optional description of player and market

    Returns:
        Database row ID of the inserted bet

    SQL Operations:
        - INSERT INTO placed_bets
        - Table affected: placed_bets
        - Initial status set to 'Pending'

    Examples:
        >>> bet_id = log_bet(
        ...     date="2024-01-15",
        ...     book="PrizePicks",
        ...     stake=25.0,
        ...     expected_ev=3.5,
        ...     player_market="LeBron James Over 25.5 Points"
        ... )
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO placed_bets (date, book, player_market, stake, expected_ev, status)
        VALUES (?, ?, ?, ?, ?, 'Pending')
        """,
        (date, book, player_market, stake, expected_ev),
    )

    bet_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return bet_id


def update_bet_status(
    bet_id: int,
    status: str,
    actual_payout: float = 0.0,
) -> bool:
    """Update the status and payout of a placed bet (legacy function).

    Updates the outcome of a previously logged bet. Valid statuses are
    Pending, Won, Lost, or Push. Returns False for invalid status values.

    Args:
        bet_id: Database ID of the bet to update
        status: New status ('Pending', 'Won', 'Lost', or 'Push')
        actual_payout: Actual payout received (default: 0.0 for losses)

    Returns:
        True if update successful, False if invalid status or bet not found

    SQL Operations:
        - UPDATE placed_bets SET status=?, payout=? WHERE id=?
        - Table affected: placed_bets
        - Transaction is committed before closing connection

    Examples:
        >>> # Mark bet as won with payout
        >>> success = update_bet_status(bet_id=123, status="Won", actual_payout=75.0)

        >>> # Mark bet as lost
        >>> success = update_bet_status(bet_id=124, status="Lost", actual_payout=0.0)
    """
    if status not in ("Pending", "Won", "Lost", "Push"):
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE placed_bets
        SET status = ?, payout = ?
        WHERE id = ?
        """,
        (status, actual_payout, bet_id),
    )

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_bet_history(limit: int = 100) -> pd.DataFrame:
    """Retrieve placed bet history as a formatted DataFrame (legacy function).

    Queries the placed_bets table and formats for display. Includes profit/loss
    calculations based on bet status. Uses type-safe conversions for financial data.

    Args:
        limit: Maximum number of bets to retrieve (default: 100)

    Returns:
        DataFrame with columns: ID, Date, Book, Player/Market, Stake, Payout,
        Status, Expected EV, P/L. Returns empty DataFrame if no bets or table
        doesn't exist.

    SQL Operations:
        - SELECT FROM placed_bets ORDER BY date DESC, timestamp DESC LIMIT ?
        - Table queried: placed_bets
        - Handles OperationalError if table doesn't exist

    Examples:
        >>> history = get_bet_history(limit=20)
        >>> if not history.empty:
        ...     print(f"Last {len(history)} bets:")
        ...     print(history[['Date', 'Book', 'Status', 'P/L']].head())
    """
    columns = [
        "ID",
        "Date",
        "Book",
        "Player/Market",
        "Stake",
        "Payout",
        "Status",
        "Expected EV",
        "P/L",
    ]

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, date, book, player_market, stake, payout, status, expected_ev
            FROM placed_bets
            ORDER BY date DESC, timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        logger.error(f"Database operation failed in get_bet_history: {e}", exc_info=True)
        conn.close()
        return pd.DataFrame(columns=columns)

    conn.close()

    if not rows:
        return pd.DataFrame(columns=columns)

    data = []
    for row in rows:
        # Type-safe extraction from database
        stake = safe_float(row["stake"], default=0.0) if row["stake"] is not None else 0.0
        payout = safe_float(row["payout"], default=0.0) if row["payout"] is not None else 0.0
        status = row["status"]

        # Calculate P/L based on status
        if status == "Won":
            pl = payout - stake
        elif status == "Lost":
            pl = -stake
        elif status == "Push":
            pl = 0.0
        else:
            pl = None  # Pending

        data.append({
            "ID": row["id"],
            "Date": row["date"],
            "Book": row["book"],
            "Player/Market": row["player_market"] or "N/A",
            "Stake": f"${stake:.2f}",
            "Payout": f"${payout:.2f}" if payout else "-",
            "Status": status,
            "Expected EV": f"{row['expected_ev']:+.1f}%" if row["expected_ev"] else "N/A",
            "P/L": f"${pl:+.2f}" if pl is not None else "-",
        })

    return pd.DataFrame(data, columns=columns)


# ==================== SLIP-BASED TRACKING ====================

def create_slip(
    book: str,
    stake: float,
    legs: list[dict],
    note: Optional[str] = None,
) -> int:
    """
    Create a new bet slip with multiple legs.

    Args:
        book: The sportsbook (e.g., 'PrizePicks', 'Underdog')
        stake: The amount wagered
        legs: List of dicts with keys: player, market, line
        note: Optional note for the slip

    Returns:
        The slip ID

    Raises:
        ValueError: If stake is invalid or legs list is empty
    """
    # Validate stake amount
    stake_value = safe_float(stake, default=0.0)
    if stake_value <= 0:
        raise ValueError(f"Stake must be greater than 0, got {stake}")

    # Validate legs is not empty
    if not legs or not isinstance(legs, list):
        raise ValueError("Legs must be a non-empty list")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Insert the slip (parent)
        cursor.execute(
            """
            INSERT INTO slips (book, stake, note)
            VALUES (?, ?, ?)
            """,
            (book, stake_value, note),
        )
        slip_id = cursor.lastrowid

        # Insert each leg (children) with type-safe extraction
        for i, leg in enumerate(legs):
            if not isinstance(leg, dict):
                logger.warning(f"Leg {i} is not a dict, skipping: {leg}")
                continue

            player = safe_dict_get(leg, "player", default="Unknown", expected_type=str)
            market = safe_dict_get(leg, "market", default="Unknown", expected_type=str)
            line_raw = leg.get("line")
            line = safe_float(line_raw, default=0.0) if line_raw is not None else 0.0

            cursor.execute(
                """
                INSERT INTO slip_legs (slip_id, player, market, line)
                VALUES (?, ?, ?, ?)
                """,
                (slip_id, player, market, line),
            )

        conn.commit()
        return slip_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create slip: {e}", exc_info=True)
        raise
    finally:
        conn.close()


def update_slip_status(
    slip_id: int,
    payout: float,
) -> bool:
    """Update the payout of a slip and auto-determine status.

    Resolves a bet slip by recording the actual payout and automatically
    calculating the status based on payout vs original stake. Uses type-safe
    conversions and validates payout is non-negative.

    Args:
        slip_id: Database ID of the slip to update
        payout: Actual payout amount received (0.0 for lost bets)

    Returns:
        True if update successful, False if slip not found

    Status Logic:
        - payout > stake: 'Profit' (winning slip)
        - payout == stake: 'Push' (refund)
        - 0 < payout < stake: 'Partial' (partial payout)
        - payout == 0: 'Lost' (losing slip)

    SQL Operations:
        - SELECT stake FROM slips WHERE id=?
        - UPDATE slips SET status=?, payout=? WHERE id=?
        - Tables affected: slips
        - Transaction is committed before closing connection

    Examples:
        >>> # Resolve winning 2-leg slip ($10 stake, 3x payout)
        >>> success = update_slip_status(slip_id=42, payout=30.0)
        >>> # Result: status='Profit'

        >>> # Resolve losing slip
        >>> success = update_slip_status(slip_id=43, payout=0.0)
        >>> # Result: status='Lost'
    """
    conn = get_connection()
    cursor = conn.cursor()

    # First, get the stake for this slip
    cursor.execute("SELECT stake FROM slips WHERE id = ?", (slip_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    # Type-safe extraction of stake from database
    stake_raw = row["stake"]
    stake = safe_float(stake_raw, default=0.0) if stake_raw is not None else 0.0

    # Validate payout is non-negative
    payout_value = safe_float(payout, default=0.0)
    if payout_value < 0:
        logger.warning(f"Negative payout value {payout_value} for slip {slip_id}, using 0.0")
        payout_value = 0.0

    # Determine status based on payout vs stake
    if payout_value > stake:
        status = "Profit"
    elif payout_value == stake:
        status = "Push"
    elif payout_value > 0:
        status = "Partial"
    else:
        status = "Lost"

    cursor.execute(
        """
        UPDATE slips
        SET status = ?, payout = ?
        WHERE id = ?
        """,
        (status, payout_value, slip_id),
    )

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_slip_legs(slip_id: int) -> list[dict]:
    """Get all legs (individual picks) for a specific slip.

    Retrieves the detailed breakdown of all picks that make up a bet slip.

    Args:
        slip_id: Database ID of the slip

    Returns:
        List of dictionaries with keys: id, player, market, line, outcome
        Empty list if slip has no legs or doesn't exist

    SQL Operations:
        - SELECT id, player, market, line, outcome FROM slip_legs WHERE slip_id=?
        - Table queried: slip_legs

    Examples:
        >>> legs = get_slip_legs(slip_id=42)
        >>> for leg in legs:
        ...     print(f"{leg['player']} - {leg['market']} @ {leg['line']}")
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, player, market, line, outcome
        FROM slip_legs
        WHERE slip_id = ?
        """,
        (slip_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_all_slips(limit: int = 100) -> pd.DataFrame:
    """Retrieve all bet slips with their legs as a formatted DataFrame.

    Fetches slip data and joins with leg information to create a comprehensive
    view of all tracked bets. Formats picks as abbreviated strings for display.

    Args:
        limit: Maximum number of slips to retrieve (default: 100)

    Returns:
        DataFrame with columns: ID, Book, Legs, Picks, Stake, Payout, Status,
        P/L, Timestamp. Picks are formatted as "LastName O/U line" (e.g.,
        "James O25.5"). Returns empty DataFrame if no slips or table doesn't exist.

    SQL Operations:
        - SELECT FROM slips ORDER BY timestamp DESC LIMIT ?
        - For each slip: SELECT FROM slip_legs WHERE slip_id=?
        - Tables queried: slips, slip_legs
        - Handles OperationalError if tables don't exist

    Examples:
        >>> slips = get_all_slips(limit=50)
        >>> if not slips.empty:
        ...     pending = slips[slips['Status'] == 'Pending']
        ...     print(f"{len(pending)} pending slips")
    """
    columns = [
        "ID",
        "Book",
        "Legs",
        "Picks",
        "Stake",
        "Payout",
        "Status",
        "P/L",
        "Timestamp",
    ]

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get all slips
        cursor.execute(
            """
            SELECT id, book, stake, payout, status, note, timestamp
            FROM slips
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        slips = cursor.fetchall()
    except sqlite3.OperationalError as e:
        logger.error(f"Database operation failed in get_all_slips: {e}", exc_info=True)
        conn.close()
        return pd.DataFrame(columns=columns)

    if not slips:
        conn.close()
        return pd.DataFrame(columns=columns)

    data = []
    for slip in slips:
        slip_id = slip["id"]
        # Type-safe extraction from database
        stake = safe_float(slip["stake"], default=0.0) if slip["stake"] is not None else 0.0
        payout = safe_float(slip["payout"], default=0.0) if slip["payout"] is not None else 0.0
        status = slip["status"]

        # Get legs for this slip
        cursor.execute(
            """
            SELECT player, market, line
            FROM slip_legs
            WHERE slip_id = ?
            """,
            (slip_id,),
        )
        legs = cursor.fetchall()
        num_legs = len(legs)

        # Build picks summary (e.g., "LeBron O25.5, Curry O4.5")
        picks_list = []
        for leg in legs:
            player = leg["player"] or "?"
            market = leg["market"] or ""
            line_raw = leg["line"]
            # Type-safe conversion of line value
            line = safe_float(line_raw, default=0.0) if line_raw is not None else 0.0
            # Shorten player name and format
            short_name = player.split()[-1] if player else "?"
            if "over" in market.lower():
                picks_list.append(f"{short_name} O{line}")
            elif "under" in market.lower():
                picks_list.append(f"{short_name} U{line}")
            else:
                picks_list.append(f"{short_name} {line}")
        picks_summary = ", ".join(picks_list[:3])
        if num_legs > 3:
            picks_summary += f" +{num_legs - 3}"

        # Calculate P/L
        if status == "Won":
            pl = payout - stake
        elif status == "Lost":
            pl = -stake
        elif status == "Push":
            pl = 0.0
        else:
            pl = None

        data.append({
            "ID": slip_id,
            "Book": slip["book"],
            "Legs": num_legs,
            "Picks": picks_summary,
            "Stake": f"${stake:.2f}",
            "Payout": f"${payout:.2f}" if payout else "-",
            "Status": status,
            "P/L": f"${pl:+.2f}" if pl is not None else "-",
            "Timestamp": slip["timestamp"],
        })

    conn.close()
    return pd.DataFrame(data, columns=columns)


def get_slip_analytics() -> dict:
    """Calculate comprehensive analytics from slip history.

    Aggregates all slip results to compute performance metrics including ROI,
    win rate, profit/loss tracking, and bankroll progression over time.

    Returns:
        Dictionary with keys:
        - total_profit (float): Net profit/loss across all slips
        - total_staked (float): Total amount wagered
        - roi (float): Return on investment as percentage
        - win_rate (float): Win percentage (wins / total_decided)
        - wins (int): Number of winning slips
        - losses (int): Number of losing slips (includes partial losses)
        - pending (int): Number of unresolved slips
        - bankroll_history (list[float]): Bankroll progression starting at 100.0

    SQL Operations:
        - SELECT stake, payout, status FROM slips
        - Table queried: slips
        - Handles OperationalError if table doesn't exist (returns default values)

    Examples:
        >>> analytics = get_slip_analytics()
        >>> print(f"Total P/L: ${analytics['total_profit']:.2f}")
        >>> print(f"ROI: {analytics['roi']:.1f}%")
        >>> print(f"Win Rate: {analytics['win_rate']:.1f}%")
        >>> print(f"Record: {analytics['wins']}-{analytics['losses']}")
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT stake, payout, status
            FROM slips
            """
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        logger.error(f"Database operation failed in get_slip_analytics: {e}", exc_info=True)
        conn.close()
        return {
            "total_profit": 0.0,
            "total_staked": 0.0,
            "roi": 0.0,
            "win_rate": 0.0,
            "wins": 0,
            "losses": 0,
            "pending": 0,
            "bankroll_history": [100.0],
        }

    conn.close()

    total_staked = 0.0
    total_profit = 0.0
    wins = 0
    losses = 0
    pending = 0
    bankroll_history = [100.0]

    for row in rows:
        # Type-safe extraction from database row
        stake_raw = row["stake"]
        payout_raw = row["payout"]
        status = row["status"]

        # Safe conversion to float with fallback to 0.0
        stake = safe_float(stake_raw, default=0.0) if stake_raw is not None else 0.0
        payout = safe_float(payout_raw, default=0.0) if payout_raw is not None else 0.0

        if status == "Pending":
            pending += 1
        elif status in ("Won", "Profit"):
            wins += 1
            total_staked += stake
            profit = payout - stake
            total_profit += profit
            bankroll_history.append(bankroll_history[-1] + profit)
        elif status == "Lost":
            losses += 1
            total_staked += stake
            total_profit -= stake
            bankroll_history.append(bankroll_history[-1] - stake)
        elif status == "Partial":
            # Partial payout - count as loss but with partial return
            losses += 1
            total_staked += stake
            net = payout - stake  # Will be negative
            total_profit += net
            bankroll_history.append(bankroll_history[-1] + net)
        elif status == "Push":
            total_staked += stake
            bankroll_history.append(bankroll_history[-1])

    total_decided = wins + losses
    win_rate = (wins / total_decided * 100) if total_decided > 0 else 0.0
    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0.0

    return {
        "total_profit": total_profit,
        "total_staked": total_staked,
        "roi": roi,
        "win_rate": win_rate,
        "wins": wins,
        "losses": losses,
        "pending": pending,
        "bankroll_history": bankroll_history,
    }


def get_historical_hit_rate(
    player_name: str,
    market: str,
    line_direction: str = None,
    limit: int = 8,
) -> list[int]:
    """Get historical hit rate pattern for similar picks from resolved bets.

    Queries resolved bet slips to find historical outcomes for the same player
    and market type. Useful for identifying hot/cold streaks and informing
    bet selection. Only includes results from settled slips (Won, Lost, etc.).

    Args:
        player_name: Player name to match exactly
        market: Market type (e.g., 'Points', 'Assists', 'Player Points Over')
        line_direction: Optional direction filter ('over' or 'under'). If None,
            automatically extracted from market string if it contains 'over' or 'under'
        limit: Number of most recent results to return (default: 8)

    Returns:
        List of integers representing recent hit history:
        - 1 for hit/win
        - 0 for miss/loss
        Returns empty list if no historical data exists or table doesn't exist.

    SQL Operations:
        - SELECT sl.outcome FROM slip_legs sl INNER JOIN slips s
        - Filters by player name, market pattern (LIKE), and resolved status
        - Ordered by timestamp DESC
        - Tables queried: slip_legs (sl), slips (s)
        - Handles OperationalError if tables don't exist

    Examples:
        >>> # Get last 8 outcomes for LeBron points overs
        >>> history = get_historical_hit_rate(
        ...     player_name="LeBron James",
        ...     market="Player Points Over"
        ... )
        >>> print(history)  # e.g., [1, 0, 1, 1, 0, 1, 1, 1]
        >>> hit_rate = sum(history) / len(history) if history else 0
        >>> print(f"Historical hit rate: {hit_rate:.1%}")
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Determine line direction from market name if not provided
        if line_direction is None:
            market_lower = market.lower()
            if "over" in market_lower:
                line_direction = "over"
            elif "under" in market_lower:
                line_direction = "under"

        # Query for historical outcomes from resolved slips
        # Match on player and market type, filter by resolved slips only
        if line_direction:
            # Match market direction (over/under)
            cursor.execute(
                """
                SELECT sl.outcome
                FROM slip_legs sl
                INNER JOIN slips s ON sl.slip_id = s.id
                WHERE sl.player = ?
                AND LOWER(sl.market) LIKE ?
                AND s.status IN ('Won', 'Lost', 'Profit', 'Partial')
                AND sl.outcome IS NOT NULL
                ORDER BY s.timestamp DESC
                LIMIT ?
                """,
                (player_name, f"%{line_direction}%", limit),
            )
        else:
            # Match player and general market without direction
            cursor.execute(
                """
                SELECT sl.outcome
                FROM slip_legs sl
                INNER JOIN slips s ON sl.slip_id = s.id
                WHERE sl.player = ?
                AND LOWER(sl.market) LIKE ?
                AND s.status IN ('Won', 'Lost', 'Profit', 'Partial')
                AND sl.outcome IS NOT NULL
                ORDER BY s.timestamp DESC
                LIMIT ?
                """,
                (player_name, f"%{market.lower()}%", limit),
            )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        # Convert outcomes to binary (1 for win, 0 for loss)
        hit_pattern = []
        for row in rows:
            outcome = row["outcome"]
            if outcome and outcome.lower() in ("win", "won", "hit", "1"):
                hit_pattern.append(1)
            elif outcome and outcome.lower() in ("loss", "lost", "miss", "0"):
                hit_pattern.append(0)
            # Skip rows with unclear outcomes

        return hit_pattern[:limit]

    except sqlite3.OperationalError as e:
        logger.error(f"Database operation failed in get_historical_hit_rate: {e}", exc_info=True)
        # Table doesn't exist or query error
        conn.close()
        return []
