"""Database connection and query management for EV Engine."""

import sqlite3
from datetime import datetime
from typing import Optional

import pandas as pd

from .config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Initialize the database with required tables."""
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

    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_odds_snapshot_event
        ON odds_snapshot(event_id, player_name, market_key)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bets_ev
        ON bets(ev_percentage DESC)
    """)

    conn.commit()
    conn.close()


def initialize_db() -> None:
    """Ensure all required tables exist with correct columns."""
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
    """Insert a single odds snapshot record."""
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
    """Insert multiple odds snapshot records in a single transaction."""
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
    """Insert a calculated bet opportunity."""
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
    """Retrieve the latest odds snapshots with optional filtering."""
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
    """Retrieve bets with EV above the specified threshold."""
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
    """Get the latest Pinnacle over/under odds for a specific player and line."""
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
    """Remove odds snapshots older than the specified number of days."""
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
    """Clear all records from the bets table."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM bets")
        rows_deleted = cursor.rowcount
        conn.commit()
    except sqlite3.OperationalError:
        # Table doesn't exist yet, nothing to clear
        rows_deleted = 0
    finally:
        conn.close()

    return rows_deleted


def get_all_opportunities() -> pd.DataFrame:
    """Retrieve top 200 bet opportunities from the bets table as a DataFrame."""
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
    except sqlite3.OperationalError:
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
    """Record a new placed bet slip."""
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
    """Update the status and payout of a placed bet."""
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
    """Retrieve placed bet history as a DataFrame."""
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
    except sqlite3.OperationalError:
        conn.close()
        return pd.DataFrame(columns=columns)

    conn.close()

    if not rows:
        return pd.DataFrame(columns=columns)

    data = []
    for row in rows:
        stake = row["stake"] or 0.0
        payout = row["payout"] or 0.0
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
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Insert the slip (parent)
    cursor.execute(
        """
        INSERT INTO slips (book, stake, note)
        VALUES (?, ?, ?)
        """,
        (book, stake, note),
    )
    slip_id = cursor.lastrowid

    # Insert each leg (children)
    for leg in legs:
        cursor.execute(
            """
            INSERT INTO slip_legs (slip_id, player, market, line)
            VALUES (?, ?, ?, ?)
            """,
            (slip_id, leg.get("player"), leg.get("market"), leg.get("line")),
        )

    conn.commit()
    conn.close()
    return slip_id


def update_slip_status(
    slip_id: int,
    payout: float,
) -> bool:
    """
    Update the payout of a slip and auto-determine status.

    Status logic based on payout vs stake:
    - payout > stake: 'Profit'
    - payout == stake: 'Push'
    - 0 < payout < stake: 'Partial'
    - payout == 0: 'Lost'
    """
    conn = get_connection()
    cursor = conn.cursor()

    # First, get the stake for this slip
    cursor.execute("SELECT stake FROM slips WHERE id = ?", (slip_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    stake = row["stake"] or 0.0

    # Determine status based on payout vs stake
    if payout > stake:
        status = "Profit"
    elif payout == stake:
        status = "Push"
    elif payout > 0:
        status = "Partial"
    else:
        status = "Lost"

    cursor.execute(
        """
        UPDATE slips
        SET status = ?, payout = ?
        WHERE id = ?
        """,
        (status, payout, slip_id),
    )

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_slip_legs(slip_id: int) -> list[dict]:
    """Get all legs for a specific slip."""
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
    """Retrieve all slips with their legs as a DataFrame."""
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
    except sqlite3.OperationalError:
        conn.close()
        return pd.DataFrame(columns=columns)

    if not slips:
        conn.close()
        return pd.DataFrame(columns=columns)

    data = []
    for slip in slips:
        slip_id = slip["id"]
        stake = slip["stake"] or 0.0
        payout = slip["payout"] or 0.0
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
            line = leg["line"]
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
    """Calculate analytics from slip history."""
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
    except sqlite3.OperationalError:
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
        stake = row["stake"] or 0.0
        payout = row["payout"] or 0.0
        status = row["status"]

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
