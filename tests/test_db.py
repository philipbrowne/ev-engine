"""Comprehensive unit tests for database operations in src/db.py."""

import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
import pytest

from src import db


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""

    @pytest.mark.unit
    def test_initialize_db_creates_all_tables(self, temp_db):
        """Verify all required tables are created."""
        db.initialize_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check that all 5 tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['bets', 'odds_snapshot', 'placed_bets', 'slip_legs', 'slips']
        assert set(expected_tables).issubset(set(tables)), \
            f"Expected tables {expected_tables}, got {tables}"

        conn.close()

    @pytest.mark.unit
    def test_initialize_db_creates_all_indexes(self, temp_db):
        """Verify all required indexes are created."""
        db.initialize_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check that all 5 indexes exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        expected_indexes = [
            'idx_odds_snapshot_event',
            'idx_bets_ev',
            'idx_placed_bets_date',
            'idx_slips_status',
            'idx_slip_legs_slip',
        ]

        assert set(expected_indexes).issubset(set(indexes)), \
            f"Expected indexes {expected_indexes}, got {indexes}"

        conn.close()

    @pytest.mark.unit
    def test_initialize_db_correct_odds_snapshot_schema(self, temp_db):
        """Verify odds_snapshot table has correct schema."""
        db.initialize_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(odds_snapshot)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        expected_columns = {
            'id': 'INTEGER',
            'event_id': 'TEXT',
            'sport_key': 'TEXT',
            'bookmaker': 'TEXT',
            'market_key': 'TEXT',
            'player_name': 'TEXT',
            'selection': 'TEXT',
            'price': 'REAL',
            'point': 'REAL',
            'timestamp': 'DATETIME',
        }

        for col_name, col_type in expected_columns.items():
            assert col_name in columns, f"Column {col_name} not found"
            assert columns[col_name] == col_type, \
                f"Column {col_name} has type {columns[col_name]}, expected {col_type}"

        conn.close()

    @pytest.mark.unit
    def test_initialize_db_correct_slips_schema(self, temp_db):
        """Verify slips table has correct schema."""
        db.initialize_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(slips)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        expected_columns = {
            'id': 'INTEGER',
            'book': 'TEXT',
            'stake': 'REAL',
            'payout': 'REAL',
            'status': 'TEXT',
            'note': 'TEXT',
            'timestamp': 'DATETIME',
        }

        for col_name, col_type in expected_columns.items():
            assert col_name in columns, f"Column {col_name} not found"

        conn.close()

    @pytest.mark.unit
    def test_initialize_db_foreign_key_constraint(self, temp_db):
        """Verify foreign key constraint on slip_legs table."""
        db.initialize_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_key_list(slip_legs)")
        fk_info = cursor.fetchall()

        assert len(fk_info) > 0, "No foreign keys found on slip_legs"
        # Check that it references slips table
        assert fk_info[0][2] == 'slips', "Foreign key should reference slips table"

        conn.close()

    @pytest.mark.unit
    def test_initialize_db_idempotent(self, temp_db):
        """Verify initialize_db can be called multiple times safely."""
        db.initialize_db()
        db.initialize_db()
        db.initialize_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Should still have all tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['bets', 'odds_snapshot', 'placed_bets', 'slip_legs', 'slips']
        assert set(expected_tables).issubset(set(tables))

        conn.close()


class TestOddsOperations:
    """Test odds snapshot operations."""

    @pytest.mark.integration
    def test_insert_odds_snapshot_single_record(self, initialized_db):
        """Test inserting a single odds snapshot record."""
        row_id = db.insert_odds_snapshot(
            event_id='test123',
            sport_key='basketball_nba',
            bookmaker='pinnacle',
            market_key='player_points',
            player_name='LeBron James',
            selection='Over',
            price=-110,
            point=25.5,
        )

        assert row_id > 0, "Should return a valid row ID"

        # Verify it was inserted
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM odds_snapshot")
        count = cursor.fetchone()[0]
        assert count == 1
        conn.close()

    @pytest.mark.integration
    def test_insert_odds_snapshot_with_custom_timestamp(self, initialized_db):
        """Test inserting odds snapshot with custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        row_id = db.insert_odds_snapshot(
            event_id='test123',
            sport_key='basketball_nba',
            bookmaker='pinnacle',
            market_key='player_points',
            player_name='LeBron James',
            selection='Over',
            price=-110,
            point=25.5,
            timestamp=custom_time,
        )

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM odds_snapshot WHERE id = ?", (row_id,))
        stored_timestamp = cursor.fetchone()[0]
        conn.close()

        # SQLite stores datetime as string without 'T' separator
        assert '2024-01-01 12:00:00' in stored_timestamp or custom_time.isoformat() in stored_timestamp

    @pytest.mark.integration
    def test_insert_odds_batch_multiple_records(self, initialized_db, sample_odds_data):
        """Test inserting multiple odds records in a batch."""
        count = db.insert_odds_batch(sample_odds_data)

        assert count == len(sample_odds_data), \
            f"Should insert {len(sample_odds_data)} records, got {count}"

        # Verify all were inserted
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM odds_snapshot")
        db_count = cursor.fetchone()[0]
        assert db_count == len(sample_odds_data)
        conn.close()

    @pytest.mark.integration
    def test_insert_odds_batch_empty_list(self, initialized_db):
        """Test inserting empty list of odds."""
        count = db.insert_odds_batch([])
        assert count == 0, "Should return 0 for empty list"

    @pytest.mark.integration
    def test_insert_odds_batch_initializes_db(self, temp_db):
        """Verify insert_odds_batch initializes database if needed."""
        sample_data = [{
            'event_id': 'test123',
            'sport_key': 'basketball_nba',
            'bookmaker': 'pinnacle',
            'market_key': 'player_points',
            'player_name': 'LeBron James',
            'selection': 'Over',
            'price': -110,
            'point': 25.5,
            'timestamp': datetime.now(),
        }]

        # Database not initialized yet
        count = db.insert_odds_batch(sample_data)

        assert count == 1, "Should insert even when DB not initialized"

    @pytest.mark.integration
    def test_get_latest_odds_no_filters(self, initialized_db, sample_odds_data):
        """Test retrieving latest odds without filters."""
        db.insert_odds_batch(sample_odds_data)

        results = db.get_latest_odds()

        assert len(results) == len(sample_odds_data)
        assert all(isinstance(r, dict) for r in results)

    @pytest.mark.integration
    def test_get_latest_odds_with_sport_filter(self, initialized_db):
        """Test retrieving odds filtered by sport."""
        # Insert odds for different sports
        nba_odds = {
            'event_id': 'nba1',
            'sport_key': 'basketball_nba',
            'bookmaker': 'pinnacle',
            'market_key': 'player_points',
            'player_name': 'LeBron James',
            'selection': 'Over',
            'price': -110,
            'point': 25.5,
            'timestamp': datetime.now(),
        }
        nfl_odds = {
            'event_id': 'nfl1',
            'sport_key': 'americanfootball_nfl',
            'bookmaker': 'pinnacle',
            'market_key': 'player_pass_tds',
            'player_name': 'Patrick Mahomes',
            'selection': 'Over',
            'price': -110,
            'point': 2.5,
            'timestamp': datetime.now(),
        }

        db.insert_odds_batch([nba_odds, nfl_odds])

        results = db.get_latest_odds(sport_key='basketball_nba')

        assert len(results) == 1
        assert results[0]['sport_key'] == 'basketball_nba'

    @pytest.mark.integration
    def test_get_latest_odds_with_bookmaker_filter(self, initialized_db):
        """Test retrieving odds filtered by bookmaker."""
        pinnacle_odds = {
            'event_id': 'test1',
            'sport_key': 'basketball_nba',
            'bookmaker': 'pinnacle',
            'market_key': 'player_points',
            'player_name': 'LeBron James',
            'selection': 'Over',
            'price': -110,
            'point': 25.5,
            'timestamp': datetime.now(),
        }
        prizepicks_odds = {
            'event_id': 'test1',
            'sport_key': 'basketball_nba',
            'bookmaker': 'prizepicks',
            'market_key': 'player_points',
            'player_name': 'LeBron James',
            'selection': 'Over',
            'price': -120,
            'point': 25.5,
            'timestamp': datetime.now(),
        }

        db.insert_odds_batch([pinnacle_odds, prizepicks_odds])

        results = db.get_latest_odds(bookmaker='pinnacle')

        assert len(results) == 1
        assert results[0]['bookmaker'] == 'pinnacle'

    @pytest.mark.integration
    def test_get_latest_odds_limit(self, initialized_db):
        """Test limit parameter on get_latest_odds."""
        # Insert 10 records
        odds_list = []
        for i in range(10):
            odds_list.append({
                'event_id': f'test{i}',
                'sport_key': 'basketball_nba',
                'bookmaker': 'pinnacle',
                'market_key': 'player_points',
                'player_name': f'Player {i}',
                'selection': 'Over',
                'price': -110,
                'point': 25.5,
                'timestamp': datetime.now(),
            })

        db.insert_odds_batch(odds_list)

        results = db.get_latest_odds(limit=5)

        assert len(results) == 5, "Should respect limit parameter"

    @pytest.mark.integration
    def test_get_pinnacle_odds_for_player_found(self, initialized_db):
        """Test getting Pinnacle odds for a specific player and line."""
        # Insert both Over and Under for the same player/market/point with same timestamp
        now = datetime.now()
        odds_data = [
            {
                'event_id': 'test123',
                'sport_key': 'basketball_nba',
                'bookmaker': 'pinnacle',
                'market_key': 'player_points',
                'player_name': 'LeBron James',
                'selection': 'Over',
                'price': -110,
                'point': 25.5,
                'timestamp': now,
            },
            {
                'event_id': 'test123',
                'sport_key': 'basketball_nba',
                'bookmaker': 'pinnacle',
                'market_key': 'player_points',
                'player_name': 'LeBron James',
                'selection': 'Under',
                'price': -110,
                'point': 25.5,
                'timestamp': now,
            },
        ]
        db.insert_odds_batch(odds_data)

        result = db.get_pinnacle_odds_for_player(
            player_name='LeBron James',
            market_key='player_points',
            point=25.5,
        )

        assert result is not None
        assert result['player_name'] == 'LeBron James'
        assert result['market_key'] == 'player_points'
        assert result['point'] == 25.5
        assert 'over_price' in result
        assert 'under_price' in result
        assert result['over_price'] == -110
        assert result['under_price'] == -110

    @pytest.mark.integration
    def test_get_pinnacle_odds_for_player_not_found(self, initialized_db):
        """Test getting Pinnacle odds when no data exists."""
        result = db.get_pinnacle_odds_for_player(
            player_name='Nonexistent Player',
            market_key='player_points',
            point=25.5,
        )

        assert result is None

    @pytest.mark.integration
    def test_clear_old_snapshots(self, initialized_db):
        """Test removing old odds snapshots."""
        # Insert old and new records
        old_time = datetime.now() - timedelta(days=10)
        new_time = datetime.now()

        old_odds = {
            'event_id': 'old1',
            'sport_key': 'basketball_nba',
            'bookmaker': 'pinnacle',
            'market_key': 'player_points',
            'player_name': 'Old Player',
            'selection': 'Over',
            'price': -110,
            'point': 25.5,
            'timestamp': old_time,
        }
        new_odds = {
            'event_id': 'new1',
            'sport_key': 'basketball_nba',
            'bookmaker': 'pinnacle',
            'market_key': 'player_points',
            'player_name': 'New Player',
            'selection': 'Over',
            'price': -110,
            'point': 25.5,
            'timestamp': new_time,
        }

        db.insert_odds_batch([old_odds, new_odds])

        # Clear snapshots older than 7 days
        deleted = db.clear_old_snapshots(days=7)

        assert deleted == 1, "Should delete 1 old record"

        # Verify only new record remains
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM odds_snapshot")
        count = cursor.fetchone()[0]
        assert count == 1
        conn.close()


class TestBetOperations:
    """Test bet opportunity operations."""

    @pytest.mark.integration
    def test_insert_bet_single_record(self, initialized_db, sample_bet_data):
        """Test inserting a single bet opportunity."""
        row_id = db.insert_bet(**sample_bet_data)

        assert row_id > 0, "Should return a valid row ID"

        # Verify insertion
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bets")
        count = cursor.fetchone()[0]
        assert count == 1
        conn.close()

    @pytest.mark.integration
    def test_insert_bet_with_custom_timestamp(self, initialized_db, sample_bet_data):
        """Test inserting bet with custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        sample_bet_data['timestamp'] = custom_time

        row_id = db.insert_bet(**sample_bet_data)

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM bets WHERE id = ?", (row_id,))
        stored_timestamp = cursor.fetchone()[0]
        conn.close()

        # SQLite stores datetime as string without 'T' separator
        assert '2024-01-01 12:00:00' in stored_timestamp or custom_time.isoformat() in stored_timestamp

    @pytest.mark.integration
    def test_get_best_bets_default_parameters(self, initialized_db):
        """Test getting best bets with default parameters."""
        # Insert bets with different EV
        for i, ev in enumerate([2.5, 5.0, 7.5, 10.0]):
            db.insert_bet(
                event_id=f'test{i}',
                player_name=f'Player {i}',
                market='Player Points Over',
                line_value=25.5,
                pinnacle_over_price=-110,
                pinnacle_under_price=-110,
                fair_win_prob=0.52,
                ev_percentage=ev,
                dfs_book='prizepicks',
            )

        results = db.get_best_bets()

        assert len(results) == 4
        assert all(isinstance(r, dict) for r in results)
        # Should be sorted by EV descending
        assert results[0]['ev_percentage'] == 10.0
        assert results[-1]['ev_percentage'] == 2.5

    @pytest.mark.integration
    def test_get_best_bets_min_ev_filter(self, initialized_db):
        """Test filtering bets by minimum EV."""
        # Insert bets with different EV
        for i, ev in enumerate([2.5, 5.0, 7.5, 10.0]):
            db.insert_bet(
                event_id=f'test{i}',
                player_name=f'Player {i}',
                market='Player Points Over',
                line_value=25.5,
                pinnacle_over_price=-110,
                pinnacle_under_price=-110,
                fair_win_prob=0.52,
                ev_percentage=ev,
                dfs_book='prizepicks',
            )

        results = db.get_best_bets(min_ev=5.0)

        assert len(results) == 3, "Should only return bets with EV >= 5.0"
        assert all(r['ev_percentage'] >= 5.0 for r in results)

    @pytest.mark.integration
    def test_get_best_bets_limit(self, initialized_db):
        """Test limit parameter on get_best_bets."""
        # Insert 10 bets
        for i in range(10):
            db.insert_bet(
                event_id=f'test{i}',
                player_name=f'Player {i}',
                market='Player Points Over',
                line_value=25.5,
                pinnacle_over_price=-110,
                pinnacle_under_price=-110,
                fair_win_prob=0.52,
                ev_percentage=5.0 + i,
                dfs_book='prizepicks',
            )

        results = db.get_best_bets(limit=5)

        assert len(results) == 5, "Should respect limit parameter"

    @pytest.mark.integration
    def test_clear_bets_success(self, initialized_db):
        """Test clearing all bets from the bets table."""
        # Insert some bets
        for i in range(5):
            db.insert_bet(
                event_id=f'test{i}',
                player_name=f'Player {i}',
                market='Player Points Over',
                line_value=25.5,
                pinnacle_over_price=-110,
                pinnacle_under_price=-110,
                fair_win_prob=0.52,
                ev_percentage=5.0,
                dfs_book='prizepicks',
            )

        deleted = db.clear_bets()

        assert deleted == 5, "Should delete all 5 records"

        # Verify table is empty
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bets")
        count = cursor.fetchone()[0]
        assert count == 0
        conn.close()

    @pytest.mark.unit
    def test_clear_bets_handles_missing_table(self, temp_db, mocker):
        """Test clear_bets handles missing table gracefully."""
        mock_logger = mocker.patch('src.db.logger')

        # Don't initialize DB - table won't exist
        deleted = db.clear_bets()

        assert deleted == 0, "Should return 0 when table doesn't exist"
        mock_logger.error.assert_called_once()

    @pytest.mark.integration
    def test_get_all_opportunities_with_data(self, initialized_db):
        """Test getting all opportunities as DataFrame."""
        # Insert some bets
        db.insert_bet(
            event_id='test1',
            player_name='LeBron James',
            market='Player Points Over',
            line_value=25.5,
            pinnacle_over_price=-110,
            pinnacle_under_price=-105,
            fair_win_prob=0.52,
            ev_percentage=5.5,
            dfs_book='prizepicks',
        )

        df = db.get_all_opportunities()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert 'Book' in df.columns
        assert 'Player' in df.columns
        assert 'Market' in df.columns
        assert 'Line' in df.columns
        assert 'EV %' in df.columns
        assert df.iloc[0]['Player'] == 'LeBron James'

    @pytest.mark.integration
    def test_get_all_opportunities_empty_table(self, initialized_db):
        """Test get_all_opportunities returns empty DataFrame when no data."""
        df = db.get_all_opportunities()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert 'Book' in df.columns

    @pytest.mark.unit
    def test_get_all_opportunities_handles_missing_table(self, temp_db, mocker):
        """Test get_all_opportunities handles missing table."""
        mock_logger = mocker.patch('src.db.logger')

        df = db.get_all_opportunities()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        mock_logger.error.assert_called_once()

    @pytest.mark.integration
    def test_get_all_opportunities_formats_odds(self, initialized_db):
        """Test that odds are formatted correctly in output."""
        # Insert bet with only over price
        db.insert_bet(
            event_id='test1',
            player_name='Player 1',
            market='Player Points Over',
            line_value=25.5,
            pinnacle_over_price=-110,
            pinnacle_under_price=None,
            fair_win_prob=0.52,
            ev_percentage=5.5,
            dfs_book='prizepicks',
        )

        # Insert bet with both prices
        db.insert_bet(
            event_id='test2',
            player_name='Player 2',
            market='Player Points Over',
            line_value=25.5,
            pinnacle_over_price=-110,
            pinnacle_under_price=-105,
            fair_win_prob=0.52,
            ev_percentage=5.5,
            dfs_book='prizepicks',
        )

        # Insert bet with only under price
        db.insert_bet(
            event_id='test3',
            player_name='Player 3',
            market='Player Points Under',
            line_value=25.5,
            pinnacle_over_price=None,
            pinnacle_under_price=-115,
            fair_win_prob=0.52,
            ev_percentage=5.5,
            dfs_book='prizepicks',
        )

        # Insert bet with no prices
        db.insert_bet(
            event_id='test4',
            player_name='Player 4',
            market='Player Points Over',
            line_value=25.5,
            pinnacle_over_price=None,
            pinnacle_under_price=None,
            fair_win_prob=0.52,
            ev_percentage=5.5,
            dfs_book='prizepicks',
        )

        df = db.get_all_opportunities()

        assert len(df) == 4
        # Check that different formats exist
        odds_values = df['Odds (Pinnacle)'].values
        assert any('-110/-105' in str(v) for v in odds_values)  # Both prices
        assert any(v == '-110' for v in odds_values)  # Only over
        assert any(v == '-115' for v in odds_values)  # Only under
        assert any(v == 'N/A' for v in odds_values)  # No prices


class TestPlacedBetsOperations:
    """Test legacy placed_bets operations."""

    @pytest.mark.integration
    def test_log_bet_success(self, initialized_db):
        """Test logging a placed bet."""
        bet_id = db.log_bet(
            date='2024-01-01',
            book='PrizePicks',
            stake=10.0,
            expected_ev=5.5,
            player_market='LeBron James O25.5',
        )

        assert bet_id > 0

        # Verify insertion
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM placed_bets WHERE id = ?", (bet_id,))
        row = cursor.fetchone()
        assert row is not None
        conn.close()

    @pytest.mark.integration
    def test_update_bet_status_to_won(self, initialized_db):
        """Test updating bet status to Won."""
        bet_id = db.log_bet(
            date='2024-01-01',
            book='PrizePicks',
            stake=10.0,
            expected_ev=5.5,
        )

        success = db.update_bet_status(bet_id, 'Won', actual_payout=30.0)

        assert success is True

        # Verify update
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status, payout FROM placed_bets WHERE id = ?", (bet_id,))
        row = cursor.fetchone()
        assert row[0] == 'Won'
        assert row[1] == 30.0
        conn.close()

    @pytest.mark.integration
    def test_update_bet_status_to_lost(self, initialized_db):
        """Test updating bet status to Lost."""
        bet_id = db.log_bet(
            date='2024-01-01',
            book='PrizePicks',
            stake=10.0,
            expected_ev=5.5,
        )

        success = db.update_bet_status(bet_id, 'Lost', actual_payout=0.0)

        assert success is True

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status, payout FROM placed_bets WHERE id = ?", (bet_id,))
        row = cursor.fetchone()
        assert row[0] == 'Lost'
        assert row[1] == 0.0
        conn.close()

    @pytest.mark.integration
    def test_update_bet_status_invalid_status(self, initialized_db):
        """Test that invalid status is rejected."""
        bet_id = db.log_bet(
            date='2024-01-01',
            book='PrizePicks',
            stake=10.0,
            expected_ev=5.5,
        )

        success = db.update_bet_status(bet_id, 'InvalidStatus')

        assert success is False

    @pytest.mark.integration
    def test_update_bet_status_nonexistent_bet(self, initialized_db):
        """Test updating status of nonexistent bet."""
        success = db.update_bet_status(99999, 'Won', actual_payout=30.0)

        assert success is False

    @pytest.mark.integration
    def test_get_bet_history_with_data(self, initialized_db):
        """Test retrieving bet history as DataFrame."""
        # Insert some bets
        bet_id1 = db.log_bet(
            date='2024-01-01',
            book='PrizePicks',
            stake=10.0,
            expected_ev=5.5,
            player_market='LeBron James O25.5',
        )
        db.update_bet_status(bet_id1, 'Won', actual_payout=30.0)

        bet_id2 = db.log_bet(
            date='2024-01-02',
            book='Underdog',
            stake=10.0,
            expected_ev=3.5,
            player_market='Curry O27.5',
        )
        db.update_bet_status(bet_id2, 'Lost', actual_payout=0.0)

        df = db.get_bet_history()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'ID' in df.columns
        assert 'Status' in df.columns
        assert 'P/L' in df.columns

    @pytest.mark.integration
    def test_get_bet_history_empty(self, initialized_db):
        """Test get_bet_history returns empty DataFrame when no data."""
        df = db.get_bet_history()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    @pytest.mark.unit
    def test_get_bet_history_handles_missing_table(self, temp_db, mocker):
        """Test get_bet_history handles missing table."""
        mock_logger = mocker.patch('src.db.logger')

        df = db.get_bet_history()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        mock_logger.error.assert_called_once()

    @pytest.mark.integration
    def test_get_bet_history_calculates_pl(self, initialized_db):
        """Test that P/L is calculated correctly."""
        # Won bet
        bet_id1 = db.log_bet(date='2024-01-01', book='PrizePicks', stake=10.0, expected_ev=5.5)
        db.update_bet_status(bet_id1, 'Won', actual_payout=30.0)

        # Lost bet
        bet_id2 = db.log_bet(date='2024-01-02', book='PrizePicks', stake=10.0, expected_ev=5.5)
        db.update_bet_status(bet_id2, 'Lost', actual_payout=0.0)

        # Push
        bet_id3 = db.log_bet(date='2024-01-03', book='PrizePicks', stake=10.0, expected_ev=5.5)
        db.update_bet_status(bet_id3, 'Push', actual_payout=10.0)

        # Pending
        bet_id4 = db.log_bet(date='2024-01-04', book='PrizePicks', stake=10.0, expected_ev=5.5)

        df = db.get_bet_history()

        assert len(df) == 4
        # Won: +20.0
        won_row = df[df['ID'] == bet_id1].iloc[0]
        assert '+20.00' in won_row['P/L']

        # Lost: -10.0
        lost_row = df[df['ID'] == bet_id2].iloc[0]
        assert '-10.00' in lost_row['P/L']

        # Push: 0.0
        push_row = df[df['ID'] == bet_id3].iloc[0]
        assert '0.00' in push_row['P/L'] or push_row['P/L'] == '$+0.00'

        # Pending: -
        pending_row = df[df['ID'] == bet_id4].iloc[0]
        assert pending_row['P/L'] == '-'

    @pytest.mark.integration
    def test_get_bet_history_limit(self, initialized_db):
        """Test limit parameter on get_bet_history."""
        # Insert 10 bets
        for i in range(10):
            db.log_bet(
                date=f'2024-01-{i+1:02d}',
                book='PrizePicks',
                stake=10.0,
                expected_ev=5.5,
            )

        df = db.get_bet_history(limit=5)

        assert len(df) == 5


class TestSlipOperations:
    """Test slip-based tracking operations."""

    @pytest.mark.integration
    def test_create_slip_success(self, initialized_db, sample_slip_legs):
        """Test creating a slip with multiple legs."""
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=sample_slip_legs,
        )

        assert slip_id > 0

        # Verify slip was created
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM slips WHERE id = ?", (slip_id,))
        slip = cursor.fetchone()
        assert slip is not None

        # Verify legs were created
        cursor.execute("SELECT COUNT(*) FROM slip_legs WHERE slip_id = ?", (slip_id,))
        leg_count = cursor.fetchone()[0]
        assert leg_count == len(sample_slip_legs)
        conn.close()

    @pytest.mark.integration
    def test_create_slip_with_note(self, initialized_db, sample_slip_legs):
        """Test creating slip with a note."""
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=sample_slip_legs,
            note='Test slip',
        )

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT note FROM slips WHERE id = ?", (slip_id,))
        note = cursor.fetchone()[0]
        assert note == 'Test slip'
        conn.close()

    @pytest.mark.integration
    def test_create_slip_invalid_stake(self, initialized_db, sample_slip_legs):
        """Test that invalid stake raises ValueError."""
        with pytest.raises(ValueError, match="Stake must be greater than 0"):
            db.create_slip(
                book='PrizePicks',
                stake=0.0,
                legs=sample_slip_legs,
            )

        with pytest.raises(ValueError, match="Stake must be greater than 0"):
            db.create_slip(
                book='PrizePicks',
                stake=-10.0,
                legs=sample_slip_legs,
            )

    @pytest.mark.integration
    def test_create_slip_empty_legs(self, initialized_db):
        """Test that empty legs list raises ValueError."""
        with pytest.raises(ValueError, match="Legs must be a non-empty list"):
            db.create_slip(
                book='PrizePicks',
                stake=10.0,
                legs=[],
            )

    @pytest.mark.integration
    def test_create_slip_invalid_legs(self, initialized_db):
        """Test that invalid legs parameter raises ValueError."""
        with pytest.raises(ValueError, match="Legs must be a non-empty list"):
            db.create_slip(
                book='PrizePicks',
                stake=10.0,
                legs=None,
            )

    @pytest.mark.integration
    def test_update_slip_status_to_profit(self, initialized_db, sample_slip_legs):
        """Test updating slip status to Profit."""
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=sample_slip_legs,
        )

        success = db.update_slip_status(slip_id, payout=30.0)

        assert success is True

        # Verify status is Profit
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status, payout FROM slips WHERE id = ?", (slip_id,))
        row = cursor.fetchone()
        assert row[0] == 'Profit'
        assert row[1] == 30.0
        conn.close()

    @pytest.mark.integration
    def test_update_slip_status_to_lost(self, initialized_db, sample_slip_legs):
        """Test updating slip status to Lost."""
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=sample_slip_legs,
        )

        success = db.update_slip_status(slip_id, payout=0.0)

        assert success is True

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM slips WHERE id = ?", (slip_id,))
        status = cursor.fetchone()[0]
        assert status == 'Lost'
        conn.close()

    @pytest.mark.integration
    def test_update_slip_status_to_push(self, initialized_db, sample_slip_legs):
        """Test updating slip status to Push."""
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=sample_slip_legs,
        )

        success = db.update_slip_status(slip_id, payout=10.0)

        assert success is True

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM slips WHERE id = ?", (slip_id,))
        status = cursor.fetchone()[0]
        assert status == 'Push'
        conn.close()

    @pytest.mark.integration
    def test_update_slip_status_to_partial(self, initialized_db, sample_slip_legs):
        """Test updating slip status to Partial."""
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=sample_slip_legs,
        )

        success = db.update_slip_status(slip_id, payout=5.0)

        assert success is True

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM slips WHERE id = ?", (slip_id,))
        status = cursor.fetchone()[0]
        assert status == 'Partial'
        conn.close()

    @pytest.mark.integration
    def test_update_slip_status_negative_payout(self, initialized_db, sample_slip_legs, mocker):
        """Test that negative payout is handled gracefully."""
        mock_logger = mocker.patch('src.db.logger')

        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=sample_slip_legs,
        )

        success = db.update_slip_status(slip_id, payout=-5.0)

        assert success is True
        mock_logger.warning.assert_called_once()

        # Should be set to Lost (payout = 0)
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status, payout FROM slips WHERE id = ?", (slip_id,))
        row = cursor.fetchone()
        assert row[0] == 'Lost'
        assert row[1] == 0.0
        conn.close()

    @pytest.mark.integration
    def test_update_slip_status_nonexistent_slip(self, initialized_db):
        """Test updating nonexistent slip returns False."""
        success = db.update_slip_status(99999, payout=30.0)

        assert success is False

    @pytest.mark.integration
    def test_get_slip_legs(self, initialized_db, sample_slip_legs):
        """Test retrieving legs for a slip."""
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=sample_slip_legs,
        )

        legs = db.get_slip_legs(slip_id)

        assert len(legs) == len(sample_slip_legs)
        assert all(isinstance(leg, dict) for leg in legs)
        assert legs[0]['player'] == sample_slip_legs[0]['player']

    @pytest.mark.integration
    def test_get_slip_legs_nonexistent_slip(self, initialized_db):
        """Test getting legs for nonexistent slip."""
        legs = db.get_slip_legs(99999)

        assert legs == []

    @pytest.mark.integration
    def test_get_all_slips_with_data(self, initialized_db, sample_slip_legs):
        """Test getting all slips as DataFrame."""
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=sample_slip_legs,
        )
        db.update_slip_status(slip_id, payout=30.0)

        df = db.get_all_slips()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert 'ID' in df.columns
        assert 'Book' in df.columns
        assert 'Legs' in df.columns
        assert 'Picks' in df.columns
        assert 'Stake' in df.columns
        assert 'Status' in df.columns
        assert 'P/L' in df.columns

    @pytest.mark.integration
    def test_get_all_slips_empty(self, initialized_db):
        """Test get_all_slips returns empty DataFrame when no data."""
        df = db.get_all_slips()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    @pytest.mark.unit
    def test_get_all_slips_handles_missing_table(self, temp_db, mocker):
        """Test get_all_slips handles missing table."""
        mock_logger = mocker.patch('src.db.logger')

        df = db.get_all_slips()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        mock_logger.error.assert_called_once()

    @pytest.mark.integration
    def test_get_all_slips_formats_picks(self, initialized_db):
        """Test that picks are formatted correctly."""
        legs = [
            {'player': 'LeBron James', 'market': 'Player Points Over', 'line': 25.5},
            {'player': 'Stephen Curry', 'market': 'Player Assists Over', 'line': 6.5},
        ]

        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=legs)

        df = db.get_all_slips()

        picks = df.iloc[0]['Picks']
        assert 'James O25.5' in picks or 'O25.5' in picks
        assert 'Curry O6.5' in picks or 'O6.5' in picks

    @pytest.mark.integration
    def test_get_all_slips_formats_picks_with_under(self, initialized_db):
        """Test that Under picks are formatted correctly."""
        legs = [
            {'player': 'LeBron James', 'market': 'Player Points Under', 'line': 25.5},
            {'player': 'Stephen Curry', 'market': 'Player Assists Under', 'line': 6.5},
        ]

        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=legs)

        df = db.get_all_slips()

        picks = df.iloc[0]['Picks']
        assert 'U25.5' in picks
        assert 'U6.5' in picks

    @pytest.mark.integration
    def test_get_all_slips_formats_picks_no_direction(self, initialized_db):
        """Test that picks without Over/Under are formatted correctly."""
        legs = [
            {'player': 'LeBron James', 'market': 'Player Points', 'line': 25.5},
            {'player': 'Stephen Curry', 'market': 'Player Assists', 'line': 6.5},
        ]

        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=legs)

        df = db.get_all_slips()

        picks = df.iloc[0]['Picks']
        assert '25.5' in picks
        assert '6.5' in picks

    @pytest.mark.integration
    def test_get_all_slips_formats_picks_more_than_three(self, initialized_db):
        """Test that slips with more than 3 legs show +N."""
        legs = [
            {'player': 'Player 1', 'market': 'Player Points Over', 'line': 25.5},
            {'player': 'Player 2', 'market': 'Player Points Over', 'line': 20.5},
            {'player': 'Player 3', 'market': 'Player Points Over', 'line': 15.5},
            {'player': 'Player 4', 'market': 'Player Points Over', 'line': 10.5},
            {'player': 'Player 5', 'market': 'Player Points Over', 'line': 5.5},
        ]

        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=legs)

        df = db.get_all_slips()

        picks = df.iloc[0]['Picks']
        assert '+2' in picks  # Should show first 3 picks + "+2"

    @pytest.mark.integration
    def test_get_all_slips_status_won_edge_case(self, initialized_db, sample_slip_legs):
        """Test P/L calculation for status 'Won' (edge case)."""
        # Manually set status to 'Won' to test edge case
        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)

        # Manually update status to 'Won' instead of 'Profit'
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("UPDATE slips SET status = ?, payout = ? WHERE id = ?", ('Won', 30.0, slip_id))
        conn.commit()
        conn.close()

        df = db.get_all_slips()

        pl = df.iloc[0]['P/L']
        assert '+20.00' in pl or pl == '$+20.00'

    @pytest.mark.integration
    def test_get_all_slips_status_push_edge_case(self, initialized_db, sample_slip_legs):
        """Test P/L calculation for status 'Push' (edge case)."""
        # Manually set status to 'Push' to test edge case
        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)

        # Manually update status to 'Push'
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("UPDATE slips SET status = ?, payout = ? WHERE id = ?", ('Push', 10.0, slip_id))
        conn.commit()
        conn.close()

        df = db.get_all_slips()

        pl = df.iloc[0]['P/L']
        assert '0.00' in pl or pl == '$+0.00'

    @pytest.mark.integration
    def test_get_all_slips_limit(self, initialized_db, sample_slip_legs):
        """Test limit parameter on get_all_slips."""
        # Create 10 slips
        for i in range(10):
            db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)

        df = db.get_all_slips(limit=5)

        assert len(df) == 5


class TestSlipAnalytics:
    """Test slip analytics operations."""

    @pytest.mark.integration
    def test_get_slip_analytics_empty(self, initialized_db):
        """Test analytics with no slips."""
        analytics = db.get_slip_analytics()

        assert isinstance(analytics, dict)
        assert analytics['total_profit'] == 0.0
        assert analytics['total_staked'] == 0.0
        assert analytics['roi'] == 0.0
        assert analytics['win_rate'] == 0.0
        assert analytics['wins'] == 0
        assert analytics['losses'] == 0
        assert analytics['pending'] == 0
        assert len(analytics['bankroll_history']) == 1
        assert analytics['bankroll_history'][0] == 100.0

    @pytest.mark.integration
    def test_get_slip_analytics_with_wins_and_losses(self, initialized_db, sample_slip_legs):
        """Test analytics calculation with wins and losses."""
        # Create 2 winning slips
        slip1 = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)
        db.update_slip_status(slip1, payout=30.0)

        slip2 = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)
        db.update_slip_status(slip2, payout=30.0)

        # Create 1 losing slip
        slip3 = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)
        db.update_slip_status(slip3, payout=0.0)

        analytics = db.get_slip_analytics()

        assert analytics['wins'] == 2
        assert analytics['losses'] == 1
        assert analytics['total_staked'] == 30.0
        assert analytics['total_profit'] == 30.0  # 2*20 - 10
        assert analytics['win_rate'] == pytest.approx(66.67, rel=0.1)
        assert analytics['roi'] == pytest.approx(100.0, rel=0.1)  # 30/30 * 100

    @pytest.mark.integration
    def test_get_slip_analytics_with_pending(self, initialized_db, sample_slip_legs):
        """Test analytics counts pending slips correctly."""
        # Create pending slip
        db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)

        analytics = db.get_slip_analytics()

        assert analytics['pending'] == 1
        assert analytics['wins'] == 0
        assert analytics['losses'] == 0

    @pytest.mark.integration
    def test_get_slip_analytics_with_push(self, initialized_db, sample_slip_legs):
        """Test analytics handles push correctly."""
        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)
        db.update_slip_status(slip_id, payout=10.0)

        analytics = db.get_slip_analytics()

        assert analytics['total_staked'] == 10.0
        assert analytics['total_profit'] == 0.0
        assert analytics['wins'] == 0
        assert analytics['losses'] == 0

    @pytest.mark.integration
    def test_get_slip_analytics_bankroll_history(self, initialized_db, sample_slip_legs):
        """Test bankroll history is calculated correctly."""
        # Win
        slip1 = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)
        db.update_slip_status(slip1, payout=30.0)

        # Loss
        slip2 = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)
        db.update_slip_status(slip2, payout=0.0)

        analytics = db.get_slip_analytics()

        bankroll = analytics['bankroll_history']
        assert len(bankroll) == 3  # Starting + 2 slips
        assert bankroll[0] == 100.0
        assert bankroll[1] == 120.0  # 100 + 20 profit
        assert bankroll[2] == 110.0  # 120 - 10 loss

    @pytest.mark.unit
    def test_get_slip_analytics_handles_missing_table(self, temp_db, mocker):
        """Test analytics handles missing table."""
        mock_logger = mocker.patch('src.db.logger')

        analytics = db.get_slip_analytics()

        assert isinstance(analytics, dict)
        assert analytics['total_profit'] == 0.0
        mock_logger.error.assert_called_once()

    @pytest.mark.integration
    def test_get_slip_analytics_partial_payout(self, initialized_db, sample_slip_legs):
        """Test analytics with partial payout."""
        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)
        db.update_slip_status(slip_id, payout=5.0)

        analytics = db.get_slip_analytics()

        assert analytics['losses'] == 1  # Partial counts as loss
        assert analytics['total_staked'] == 10.0
        assert analytics['total_profit'] == -5.0  # 5 - 10


class TestHistoricalHitRate:
    """Test historical hit rate operations."""

    @pytest.mark.integration
    def test_get_historical_hit_rate_with_data(self, initialized_db):
        """Test getting historical hit rate with existing data."""
        # Create a slip with legs that have outcomes
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=[
                {'player': 'LeBron James', 'market': 'Player Points Over', 'line': 25.5},
            ],
        )

        # Manually set outcome in slip_legs
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE slip_legs SET outcome = ? WHERE slip_id = ?",
            ('Win', slip_id)
        )
        conn.commit()

        # Mark slip as resolved
        cursor.execute(
            "UPDATE slips SET status = ? WHERE id = ?",
            ('Profit', slip_id)
        )
        conn.commit()
        conn.close()

        # Query hit rate
        hit_rate = db.get_historical_hit_rate(
            player_name='LeBron James',
            market='Player Points Over',
        )

        assert len(hit_rate) == 1
        assert hit_rate[0] == 1

    @pytest.mark.integration
    def test_get_historical_hit_rate_no_data(self, initialized_db):
        """Test getting hit rate when no historical data exists."""
        hit_rate = db.get_historical_hit_rate(
            player_name='Nonexistent Player',
            market='Player Points Over',
        )

        assert hit_rate == []

    @pytest.mark.integration
    def test_get_historical_hit_rate_with_line_direction(self, initialized_db):
        """Test hit rate filtering by line direction."""
        # Create slip with over bet
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=[
                {'player': 'LeBron James', 'market': 'Player Points Over', 'line': 25.5},
            ],
        )

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE slip_legs SET outcome = ? WHERE slip_id = ?",
            ('Win', slip_id)
        )
        cursor.execute(
            "UPDATE slips SET status = ? WHERE id = ?",
            ('Profit', slip_id)
        )
        conn.commit()
        conn.close()

        # Query with line direction
        hit_rate = db.get_historical_hit_rate(
            player_name='LeBron James',
            market='Player Points Over',
            line_direction='over',
        )

        assert len(hit_rate) == 1
        assert hit_rate[0] == 1

    @pytest.mark.integration
    def test_get_historical_hit_rate_mixed_outcomes(self, initialized_db):
        """Test hit rate with mixed win/loss outcomes."""
        # Create multiple slips
        for outcome in ['Win', 'Loss', 'Win', 'Win', 'Loss']:
            slip_id = db.create_slip(
                book='PrizePicks',
                stake=10.0,
                legs=[
                    {'player': 'LeBron James', 'market': 'Player Points Over', 'line': 25.5},
                ],
            )

            conn = sqlite3.connect(initialized_db)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE slip_legs SET outcome = ? WHERE slip_id = ?",
                (outcome, slip_id)
            )
            status = 'Profit' if outcome == 'Win' else 'Lost'
            cursor.execute(
                "UPDATE slips SET status = ? WHERE id = ?",
                (status, slip_id)
            )
            conn.commit()
            conn.close()

        hit_rate = db.get_historical_hit_rate(
            player_name='LeBron James',
            market='Player Points Over',
        )

        assert len(hit_rate) == 5
        assert hit_rate.count(1) == 3  # 3 wins
        assert hit_rate.count(0) == 2  # 2 losses

    @pytest.mark.integration
    def test_get_historical_hit_rate_respects_limit(self, initialized_db):
        """Test that hit rate respects the limit parameter."""
        # Create 10 slips
        for i in range(10):
            slip_id = db.create_slip(
                book='PrizePicks',
                stake=10.0,
                legs=[
                    {'player': 'LeBron James', 'market': 'Player Points Over', 'line': 25.5},
                ],
            )

            conn = sqlite3.connect(initialized_db)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE slip_legs SET outcome = ? WHERE slip_id = ?",
                ('Win', slip_id)
            )
            cursor.execute(
                "UPDATE slips SET status = ? WHERE id = ?",
                ('Profit', slip_id)
            )
            conn.commit()
            conn.close()

        hit_rate = db.get_historical_hit_rate(
            player_name='LeBron James',
            market='Player Points Over',
            limit=5,
        )

        assert len(hit_rate) == 5

    @pytest.mark.unit
    def test_get_historical_hit_rate_handles_missing_table(self, temp_db, mocker):
        """Test hit rate handles missing table."""
        mock_logger = mocker.patch('src.db.logger')

        hit_rate = db.get_historical_hit_rate(
            player_name='LeBron James',
            market='Player Points Over',
        )

        assert hit_rate == []
        mock_logger.error.assert_called_once()

    @pytest.mark.integration
    def test_get_historical_hit_rate_skips_unclear_outcomes(self, initialized_db):
        """Test that unclear outcomes are skipped."""
        slip_id = db.create_slip(
            book='PrizePicks',
            stake=10.0,
            legs=[
                {'player': 'LeBron James', 'market': 'Player Points Over', 'line': 25.5},
            ],
        )

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE slip_legs SET outcome = ? WHERE slip_id = ?",
            ('Unknown', slip_id)
        )
        cursor.execute(
            "UPDATE slips SET status = ? WHERE id = ?",
            ('Profit', slip_id)
        )
        conn.commit()
        conn.close()

        hit_rate = db.get_historical_hit_rate(
            player_name='LeBron James',
            market='Player Points Over',
        )

        assert len(hit_rate) == 0  # Unclear outcome should be skipped


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.unit
    def test_get_connection_creates_connection(self, temp_db):
        """Test that get_connection returns a valid connection."""
        conn = db.get_connection()

        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row

        conn.close()

    @pytest.mark.unit
    def test_create_slip_handles_exception(self, initialized_db, mocker):
        """Test create_slip rolls back on exception."""
        mock_logger = mocker.patch('src.db.logger')

        # Create invalid legs that will cause an error during insertion
        invalid_legs = [
            {'player': 'Test', 'market': 'Test', 'line': 'invalid'},  # Invalid line type
        ]

        with pytest.raises(Exception):
            # Mock the cursor to raise an exception
            with patch('src.db.get_connection') as mock_conn:
                mock_cursor = MagicMock()
                mock_cursor.execute.side_effect = sqlite3.OperationalError("Test error")
                mock_conn.return_value.cursor.return_value = mock_cursor
                mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
                mock_conn.return_value.__exit__ = MagicMock()

                db.create_slip(book='PrizePicks', stake=10.0, legs=invalid_legs)

    @pytest.mark.integration
    def test_create_slip_handles_invalid_leg_dict(self, initialized_db, mocker):
        """Test create_slip handles non-dict legs gracefully."""
        mock_logger = mocker.patch('src.db.logger')

        # Include a non-dict leg
        legs = [
            {'player': 'LeBron James', 'market': 'Player Points Over', 'line': 25.5},
            "invalid_leg",  # Not a dict
            {'player': 'Stephen Curry', 'market': 'Player Assists Over', 'line': 6.5},
        ]

        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=legs)

        # Should still succeed, but log warning
        assert slip_id > 0
        mock_logger.warning.assert_called()

        # Should have only 2 legs (skipped the invalid one)
        slip_legs = db.get_slip_legs(slip_id)
        assert len(slip_legs) == 2

    @pytest.mark.integration
    def test_add_slip_leg(self, initialized_db):
        """Test add_slip_leg functionality (implicitly tested in create_slip)."""
        # This function doesn't exist in the API but the functionality is in create_slip
        legs = [
            {'player': 'LeBron James', 'market': 'Player Points Over', 'line': 25.5},
        ]

        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=legs)

        # Manually add another leg
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO slip_legs (slip_id, player, market, line) VALUES (?, ?, ?, ?)",
            (slip_id, 'Stephen Curry', 'Player Assists Over', 6.5)
        )
        conn.commit()
        conn.close()

        # Verify both legs exist
        slip_legs = db.get_slip_legs(slip_id)
        assert len(slip_legs) == 2


class TestDataIntegrity:
    """Test data integrity and type safety."""

    @pytest.mark.integration
    def test_insert_bet_with_none_prices(self, initialized_db):
        """Test inserting bet with None for optional price fields."""
        row_id = db.insert_bet(
            event_id='test1',
            player_name='LeBron James',
            market='Player Points Over',
            line_value=25.5,
            pinnacle_over_price=None,
            pinnacle_under_price=None,
            fair_win_prob=0.52,
            ev_percentage=5.5,
        )

        assert row_id > 0

    @pytest.mark.integration
    def test_slip_with_zero_line(self, initialized_db):
        """Test slip can handle zero line value."""
        legs = [
            {'player': 'Player 1', 'market': 'Test Market', 'line': 0.0},
        ]

        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=legs)

        assert slip_id > 0

        slip_legs = db.get_slip_legs(slip_id)
        assert slip_legs[0]['line'] == 0.0

    @pytest.mark.integration
    def test_update_slip_status_with_float_payout(self, initialized_db, sample_slip_legs):
        """Test updating slip with float payout."""
        slip_id = db.create_slip(book='PrizePicks', stake=10.0, legs=sample_slip_legs)

        success = db.update_slip_status(slip_id, payout=25.75)

        assert success is True

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT payout FROM slips WHERE id = ?", (slip_id,))
        payout = cursor.fetchone()[0]
        assert payout == pytest.approx(25.75)
        conn.close()

    @pytest.mark.integration
    def test_get_all_opportunities_handles_null_book(self, initialized_db):
        """Test get_all_opportunities handles NULL dfs_book."""
        db.insert_bet(
            event_id='test1',
            player_name='LeBron James',
            market='Player Points Over',
            line_value=25.5,
            pinnacle_over_price=-110,
            pinnacle_under_price=-110,
            fair_win_prob=0.52,
            ev_percentage=5.5,
            dfs_book=None,
        )

        df = db.get_all_opportunities()

        assert len(df) == 1
        assert df.iloc[0]['Book'] == 'Unknown'

    @pytest.mark.integration
    def test_transaction_rollback_on_error(self, initialized_db):
        """Test that transactions roll back on error."""
        initial_count_conn = sqlite3.connect(initialized_db)
        cursor = initial_count_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM slips")
        initial_count = cursor.fetchone()[0]
        initial_count_conn.close()

        # Try to create slip with invalid data that causes error
        with patch('src.db.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            # First execute succeeds (slip insert), second fails (leg insert)
            mock_cursor.execute.side_effect = [None, sqlite3.OperationalError("Test error")]
            mock_cursor.lastrowid = 1
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.rollback = MagicMock()
            mock_conn.return_value.close = MagicMock()

            legs = [{'player': 'Test', 'market': 'Test', 'line': 25.5}]

            with pytest.raises(sqlite3.OperationalError):
                db.create_slip(book='PrizePicks', stake=10.0, legs=legs)

            # Verify rollback was called
            mock_conn.return_value.rollback.assert_called_once()

    @pytest.mark.integration
    def test_datetime_defaults(self, initialized_db):
        """Test that datetime defaults are applied correctly."""
        # Insert without timestamp
        row_id = db.insert_odds_snapshot(
            event_id='test1',
            sport_key='basketball_nba',
            bookmaker='pinnacle',
            market_key='player_points',
            player_name='LeBron James',
            selection='Over',
            price=-110,
            point=25.5,
        )

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM odds_snapshot WHERE id = ?", (row_id,))
        timestamp = cursor.fetchone()[0]
        conn.close()

        assert timestamp is not None
        # Should be recent (within last minute)
        timestamp_dt = datetime.fromisoformat(timestamp)
        assert (datetime.now() - timestamp_dt).total_seconds() < 60
