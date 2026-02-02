# EV Engine Database Schema

## Overview

- **Database type**: SQLite
- **Location**: `data/ev_engine.db`
- **Purpose**: Store odds snapshots, EV opportunities, and bet tracking
- **Schema version**: v1 (initial schema)
- **Size considerations**: SQLite handles databases up to ~281 TB theoretically, but performance degrades with large datasets. Typical usage for EV Engine: 10-100 MB for moderate historical data.
- **Backup recommendations**:
  - Daily backups before running odds updates
  - Keep 7-30 days of backup history
  - Store backups outside the application directory
  - Use SQLite's `.backup` command for safe, consistent backups

## Database Architecture

### Why SQLite was chosen

SQLite is ideal for EV Engine because:
- **Zero configuration**: No separate database server to install or maintain
- **File-based**: Single file makes backups and portability trivial
- **ACID compliant**: Ensures data integrity even during crashes
- **Fast for reads**: Excellent performance for analytical queries
- **Python integration**: Built into Python's standard library
- **Low complexity**: Perfect for single-user desktop applications

### Limitations

Be aware of these SQLite constraints:
- **Single writer**: Only one process can write at a time (database locking)
- **No concurrent writes**: Multi-threaded writes can cause "database locked" errors
- **Limited data types**: TEXT, INTEGER, REAL, BLOB (no native datetime or decimal)
- **No network access**: Cannot be accessed remotely without additional tools
- **Performance**: Large datasets (>100GB) or high write concurrency may degrade performance

### When to consider migrating to PostgreSQL

Consider PostgreSQL if you:
- Need multi-user access (multiple bettors sharing a database)
- Require concurrent writes (real-time updates from multiple sources)
- Want to deploy a web dashboard accessible across devices
- Need advanced data types (JSON, arrays, geometric data)
- Handle massive datasets (>100GB)
- Require row-level security or complex permissions

## Entity Relationship Diagram

```
┌─────────────────┐
│ odds_snapshot   │
│ ─────────────── │
│ PK id           │
│    event_id     │ ─┐
│    sport_key    │  │
│    bookmaker    │  │
│    market_key   │  │
│    player_name  │  │
│    selection    │  │
│    price        │  │
│    point        │  │
│    timestamp    │  │
└─────────────────┘  │
                     │ (used for EV calculation)
                     │
                     ▼
              ┌─────────────────┐
              │ bets            │
              │ ─────────────── │
              │ PK id           │
              │    event_id     │ ◄─── References event_id (not enforced FK)
              │    player_name  │
              │    market       │
              │    line_value   │
              │    pinnacle_... │
              │    fair_win_... │
              │    ev_percen... │
              │    dfs_book     │
              │    timestamp    │
              └─────────────────┘


┌─────────────────┐              ┌─────────────────┐
│ placed_bets     │              │ slips           │
│ (LEGACY)        │              │ ─────────────── │
│ ─────────────── │              │ PK id           │
│ PK id           │              │    book         │
│    date         │              │    stake        │
│    book         │              │    payout       │
│    player_mar.. │              │    status       │
│    stake        │              │    note         │
│    payout       │              │    timestamp    │
│    status       │              └────────┬────────┘
│    expected_ev  │                       │
│    timestamp    │                       │ 1
└─────────────────┘                       │
                                          │
                                          │ (CASCADE DELETE)
                                          │
                                          │ N
                                   ┌──────▼──────────┐
                                   │ slip_legs       │
                                   │ ─────────────── │
                                   │ PK id           │
                                   │ FK slip_id      │
                                   │    player       │
                                   │    market       │
                                   │    line         │
                                   │    outcome      │
                                   └─────────────────┘
```

**Relationships**:
- `slips` (1) ──── (many) `slip_legs` - One slip has many legs (picks)
- `bets` references `event_id` from `odds_snapshot` (logical, not enforced)
- `placed_bets` is legacy and independent (no foreign keys)

**Cardinality**:
- One slip can have 1-N legs (typically 2-6 for parlays)
- Deleting a slip cascades to delete all its legs
- One event can generate multiple bet opportunities

## Tables

### Table: odds_snapshot

**Purpose**: Raw odds data snapshot from The Odds API. Stores point-in-time bookmaker odds for player props to track line movements and calculate fair value.

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | No | Primary key (auto-increment) |
| event_id | TEXT | No | Unique event identifier from The Odds API |
| sport_key | TEXT | No | Sport identifier (e.g., 'basketball_nba', 'icehockey_nhl') |
| bookmaker | TEXT | No | Bookmaker key (e.g., 'pinnacle', 'fanduel', 'draftkings') |
| market_key | TEXT | No | Market type (e.g., 'player_points', 'player_assists', 'player_rebounds') |
| player_name | TEXT | No | Full player name (e.g., 'LeBron James') |
| selection | TEXT | No | Bet direction: 'Over' or 'Under' |
| price | REAL | No | American odds (e.g., -110, +150, -200) |
| point | REAL | No | Line value (e.g., 25.5 points, 5.5 assists) |
| timestamp | DATETIME | No | When odds were captured (default: CURRENT_TIMESTAMP) |

**Indexes**:
- `idx_odds_snapshot_event` on (event_id, player_name, market_key) - Speeds up lookups for specific player props

**Typical Row Count**:
- Varies based on API usage and retention policy
- ~1000-5000 rows per day for active monitoring
- ~30,000-150,000 rows per month if storing 30-day history

**Retention**:
- Historical data kept indefinitely by default
- Use `clear_old_snapshots(days=30)` to purge old data

**Sample Query**:
```sql
-- Get latest Pinnacle odds for NBA player points
SELECT * FROM odds_snapshot
WHERE sport_key = 'basketball_nba'
  AND bookmaker = 'pinnacle'
  AND market_key = 'player_points'
ORDER BY timestamp DESC
LIMIT 20;
```

**Sample Data**:
```
id | event_id | sport_key | bookmaker | market_key | player_name | selection | price | point | timestamp
---|----------|-----------|-----------|------------|-------------|-----------|-------|-------|-------------------
1  | abc123   | basketball_nba | pinnacle | player_points | LeBron James | Over | -110 | 25.5 | 2026-02-01 10:30:00
2  | abc123   | basketball_nba | pinnacle | player_points | LeBron James | Under | -110 | 25.5 | 2026-02-01 10:30:00
3  | abc123   | basketball_nba | fanduel | player_points | LeBron James | Over | +100 | 25.5 | 2026-02-01 10:30:15
```

---

### Table: bets

**Purpose**: Calculated EV opportunities. Stores betting opportunities with positive expected value by comparing Pinnacle's sharp odds against DFS sportsbooks.

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | No | Primary key (auto-increment) |
| event_id | TEXT | No | Event identifier (references odds_snapshot.event_id) |
| player_name | TEXT | No | Full player name |
| market | TEXT | No | Market description (e.g., 'Player Points Over', 'Player Assists Under') |
| line_value | REAL | No | Line value (e.g., 25.5, 5.5) |
| pinnacle_over_price | INTEGER | Yes | Pinnacle's over odds (NULL if not available) |
| pinnacle_under_price | INTEGER | Yes | Pinnacle's under odds (NULL if not available) |
| fair_win_prob | REAL | No | Calculated fair win probability from Pinnacle odds (0.0-1.0) |
| ev_percentage | REAL | No | Expected value as percentage (e.g., 5.2 = 5.2% edge) |
| dfs_book | TEXT | Yes | DFS sportsbook offering the +EV line (e.g., 'PrizePicks', 'Underdog') |
| timestamp | DATETIME | No | When EV was calculated (default: CURRENT_TIMESTAMP) |

**Indexes**:
- `idx_bets_ev` on (ev_percentage DESC) - Optimizes sorting by best EV opportunities

**Typical Row Count**:
- Cleared and repopulated on each refresh
- Usually 50-500 active opportunities
- Best opportunities (>3% EV) typically 20-100 rows

**Retention**:
- Table is cleared with `clear_bets()` before each odds update
- Historical EV opportunities are not retained (use odds_snapshot for history)

**Sample Query**:
```sql
-- Get top 10 EV opportunities above 3%
SELECT
  player_name,
  market,
  line_value,
  pinnacle_over_price || '/' || pinnacle_under_price as pinnacle_odds,
  ROUND(fair_win_prob * 100, 1) || '%' as win_prob,
  ROUND(ev_percentage, 2) || '%' as ev,
  dfs_book
FROM bets
WHERE ev_percentage >= 3.0
ORDER BY ev_percentage DESC
LIMIT 10;
```

**Sample Data**:
```
id | event_id | player_name | market | line_value | pinnacle_over | pinnacle_under | fair_win_prob | ev_percentage | dfs_book | timestamp
---|----------|-------------|--------|------------|---------------|----------------|---------------|---------------|----------|-------------------
1  | abc123   | LeBron James | Player Points Over | 25.5 | -110 | -110 | 0.52 | 5.2 | PrizePicks | 2026-02-01 10:35:00
2  | xyz789   | Steph Curry | Player 3-Pointers Over | 4.5 | -120 | +100 | 0.545 | 4.5 | Underdog | 2026-02-01 10:35:00
```

---

### Table: placed_bets (Legacy)

**Purpose**: Original single-bet tracking system. Kept for backward compatibility but deprecated in favor of the slips/slip_legs system.

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | No | Primary key (auto-increment) |
| date | TEXT | No | Bet placement date (YYYY-MM-DD format) |
| book | TEXT | No | Sportsbook name |
| player_market | TEXT | Yes | Description of the bet (free-form text) |
| stake | REAL | No | Amount wagered |
| payout | REAL | No | Actual payout (default: 0.0) |
| status | TEXT | No | 'Pending', 'Won', 'Lost', or 'Push' (default: 'Pending') |
| expected_ev | REAL | Yes | Expected EV percentage at time of bet |
| timestamp | DATETIME | No | When bet was logged (default: CURRENT_TIMESTAMP) |

**Indexes**:
- `idx_placed_bets_date` on (date DESC) - Optimizes date-based queries

**Typical Row Count**: Legacy data only, no longer actively used

**Retention**: Kept indefinitely for historical records

**Deprecation Note**: Use `slips` and `slip_legs` tables for new bet tracking. This table remains for historical data and backward compatibility only.

**Sample Query**:
```sql
-- Get all pending legacy bets
SELECT * FROM placed_bets
WHERE status = 'Pending'
ORDER BY date DESC;
```

---

### Table: slips

**Purpose**: Parent table for modern bet slip tracking. Represents a single bet slip (which may contain multiple picks/legs).

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | No | Primary key (auto-increment) |
| book | TEXT | No | Sportsbook name (e.g., 'PrizePicks', 'Underdog', 'Fliff') |
| stake | REAL | No | Amount wagered (must be > 0) |
| payout | REAL | No | Actual payout received (default: 0.0) |
| status | TEXT | No | 'Pending', 'Profit', 'Lost', 'Push', or 'Partial' (default: 'Pending') |
| note | TEXT | Yes | Optional note or comment about the slip |
| timestamp | DATETIME | No | When slip was created (default: CURRENT_TIMESTAMP) |

**Indexes**:
- `idx_slips_status` on (status, timestamp DESC) - Optimizes filtering by status and sorting by date

**Typical Row Count**:
- Grows over time as slips are created
- Typical usage: 10-100 slips per week

**Retention**: Kept indefinitely for performance tracking

**Status Logic**:
- **Pending**: Slip not yet resolved
- **Profit**: payout > stake (winning slip)
- **Lost**: payout = 0 (all legs lost)
- **Push**: payout = stake (voided/pushed)
- **Partial**: 0 < payout < stake (some legs lost in a flex parlay)

**Sample Query**:
```sql
-- Get all pending slips
SELECT id, book, stake, note, timestamp
FROM slips
WHERE status = 'Pending'
ORDER BY timestamp DESC;
```

**Sample Data**:
```
id | book | stake | payout | status | note | timestamp
---|------|-------|--------|--------|------|-------------------
1  | PrizePicks | 25.00 | 62.50 | Profit | Good NBA slate | 2026-01-30 19:00:00
2  | Underdog | 10.00 | 0.00 | Lost | NULL | 2026-01-30 20:15:00
3  | PrizePicks | 50.00 | 0.00 | Pending | High confidence | 2026-02-01 18:00:00
```

---

### Table: slip_legs

**Purpose**: Child table for individual picks within a slip. Each row represents one player prop pick on a parlay/slip.

**Schema**:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | No | Primary key (auto-increment) |
| slip_id | INTEGER | No | Foreign key to slips.id (CASCADE DELETE) |
| player | TEXT | No | Player name |
| market | TEXT | No | Market description (e.g., 'Player Points Over', 'Player Assists Under') |
| line | REAL | Yes | Line value (e.g., 25.5, 5.5) |
| outcome | TEXT | Yes | Individual leg result: 'Win', 'Lost', or NULL (pending) |

**Foreign Keys**:
- `slip_id` → `slips.id` (ON DELETE CASCADE)

**Indexes**:
- `idx_slip_legs_slip` on (slip_id) - Optimizes joins with slips table

**Relationships**:
- One slip has many legs (1:N relationship)
- Deleting a slip automatically deletes all its legs (CASCADE DELETE)

**Typical Row Count**:
- ~2-6 legs per slip on average
- If you have 100 slips with avg 4 legs = ~400 rows

**Retention**: Kept indefinitely, deleted automatically when parent slip is deleted

**Sample Query**:
```sql
-- Get all legs for a specific slip
SELECT player, market, line, outcome
FROM slip_legs
WHERE slip_id = 1;
```

**Sample Data**:
```
id | slip_id | player | market | line | outcome
---|---------|--------|--------|------|--------
1  | 1 | LeBron James | Player Points Over | 25.5 | Win
2  | 1 | Steph Curry | Player 3-Pointers Over | 4.5 | Win
3  | 1 | Kevin Durant | Player Assists Over | 6.5 | Win
4  | 2 | Luka Doncic | Player Points Over | 30.5 | Lost
5  | 2 | Giannis Antetokounmpo | Player Rebounds Over | 11.5 | Win
```

---

## Indexes

All indexes are created with `IF NOT EXISTS` to be idempotent.

| Index Name | Table | Columns | Purpose |
|------------|-------|---------|---------|
| idx_odds_snapshot_event | odds_snapshot | (event_id, player_name, market_key) | Speeds up lookups for specific player props in an event. Composite index covers most common query patterns. |
| idx_bets_ev | bets | (ev_percentage DESC) | Optimizes sorting by highest EV opportunities. Descending order matches typical query pattern. |
| idx_placed_bets_date | placed_bets | (date DESC) | Speeds up date-based queries for legacy bet history. Descending order for recent-first queries. |
| idx_slips_status | slips | (status, timestamp DESC) | Enables fast filtering by status (e.g., Pending, Profit) and sorting by most recent. Covers common dashboard queries. |
| idx_slip_legs_slip | slip_legs | (slip_id) | Optimizes joining slip_legs with slips table and fetching all legs for a slip. |

**Index Usage Tips**:
- Indexes are automatically used when WHERE/ORDER BY clauses match indexed columns
- Use `EXPLAIN QUERY PLAN` to verify index usage
- Composite indexes work left-to-right (idx_odds_snapshot_event works for event_id alone, or event_id+player_name, or all three)

---

## Data Flow

### 1. Odds Data Flow

**API → odds_snapshot → EV calculation → bets table**

```
┌─────────────────┐
│  The Odds API   │
│  (REST API)     │
└────────┬────────┘
         │ fetch_odds()
         ▼
┌─────────────────┐
│ Raw odds data   │
│ (Python dicts)  │
└────────┬────────┘
         │ insert_odds_batch()
         ▼
┌─────────────────┐
│ odds_snapshot   │
│ (historical)    │
└────────┬────────┘
         │ get_pinnacle_odds_for_player()
         │ calculate_ev()
         ▼
┌─────────────────┐
│ bets            │
│ (current +EV)   │
└────────┬────────┘
         │ get_all_opportunities()
         ▼
┌─────────────────┐
│ Dashboard UI    │
│ (display top EV)│
└─────────────────┘
```

**Process**:
1. Fetch odds from The Odds API for multiple bookmakers
2. Store raw odds snapshots in `odds_snapshot` table
3. Calculate fair odds using Pinnacle as benchmark
4. Find +EV opportunities by comparing DFS books to Pinnacle
5. Store opportunities in `bets` table (cleared on each refresh)
6. Display top opportunities in dashboard

---

### 2. Bet Tracking Flow

**User creates slip → slips table → slip_legs table → resolve slip**

```
User Action: "Create 3-leg parlay on PrizePicks"
         │
         ▼
┌─────────────────┐
│ create_slip()   │
│ - book          │
│ - stake         │
│ - legs[]        │
└────────┬────────┘
         │ INSERT INTO slips
         ▼
┌─────────────────┐
│ slips           │
│ id=1, status=   │
│ 'Pending'       │
└────────┬────────┘
         │ slip_id = 1
         │ INSERT INTO slip_legs (3 rows)
         ▼
┌─────────────────┐
│ slip_legs       │
│ Leg 1: LeBron   │
│ Leg 2: Curry    │
│ Leg 3: Durant   │
└────────┬────────┘
         │
         │ (bet resolves)
         │
         ▼
┌─────────────────┐
│update_slip_     │
│status()         │
│ - payout=$62.50 │
└────────┬────────┘
         │ UPDATE slips
         │ SET status='Profit', payout=62.50
         ▼
┌─────────────────┐
│ slips           │
│ id=1, status=   │
│ 'Profit'        │
└─────────────────┘
```

**Process**:
1. User creates a slip with multiple picks (legs)
2. Insert parent record into `slips` table
3. Insert child records into `slip_legs` table (one per pick)
4. User waits for event results
5. User resolves slip with payout amount
6. System auto-determines status based on payout vs stake

---

### 3. Analytics Flow

**Query slips + slip_legs → calculate metrics → display in dashboard**

```
┌─────────────────┐      ┌─────────────────┐
│ slips           │ JOIN │ slip_legs       │
│ (parent data)   │◄────►│ (pick details)  │
└────────┬────────┘      └─────────────────┘
         │
         │ get_slip_analytics()
         ▼
┌─────────────────────────────┐
│ Calculate:                  │
│ - Total profit/loss         │
│ - Total staked              │
│ - ROI %                     │
│ - Win rate %                │
│ - Bankroll history          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────┐
│ Dashboard UI    │
│ - Charts        │
│ - Metrics       │
│ - History table │
└─────────────────┘
```

**Process**:
1. Query all slips with their legs
2. Calculate aggregate metrics (profit, ROI, win rate)
3. Build bankroll history timeline
4. Display analytics in dashboard with charts

---

## Common Queries

### Get top EV opportunities

```sql
-- Top 20 bets with highest EV percentage
SELECT
  player_name,
  market,
  line_value,
  ROUND(fair_win_prob * 100, 1) || '%' as win_prob,
  ROUND(ev_percentage, 2) || '%' as ev,
  dfs_book
FROM bets
ORDER BY ev_percentage DESC
LIMIT 20;
```

### Get all pending slips

```sql
-- All slips awaiting resolution
SELECT
  id,
  book,
  stake,
  note,
  timestamp
FROM slips
WHERE status = 'Pending'
ORDER BY timestamp DESC;
```

### Calculate win rate

```sql
-- Win rate excluding pending and pushes
SELECT
  COUNT(CASE WHEN status IN ('Profit', 'Won') THEN 1 END) as wins,
  COUNT(CASE WHEN status IN ('Lost', 'Partial') THEN 1 END) as losses,
  ROUND(
    COUNT(CASE WHEN status IN ('Profit', 'Won') THEN 1 END) * 100.0 /
    COUNT(CASE WHEN status NOT IN ('Pending', 'Push') THEN 1 END),
    2
  ) as win_rate_pct
FROM slips
WHERE status NOT IN ('Pending', 'Push');
```

### Calculate ROI

```sql
-- Return on investment across all resolved slips
SELECT
  SUM(stake) as total_staked,
  SUM(payout - stake) as total_profit,
  ROUND(SUM(payout - stake) / SUM(stake) * 100, 2) as roi_pct
FROM slips
WHERE status NOT IN ('Pending');
```

### Get historical hit rate for a player/market

```sql
-- Last 8 outcomes for LeBron James points overs
SELECT
  sl.outcome,
  s.timestamp,
  s.status as slip_status
FROM slip_legs sl
INNER JOIN slips s ON sl.slip_id = s.id
WHERE sl.player = 'LeBron James'
  AND LOWER(sl.market) LIKE '%points%over%'
  AND s.status IN ('Won', 'Lost', 'Profit', 'Partial')
  AND sl.outcome IS NOT NULL
ORDER BY s.timestamp DESC
LIMIT 8;
```

### Get slip details with all legs

```sql
-- Get complete slip information including all picks
SELECT
  s.id,
  s.book,
  s.stake,
  s.payout,
  s.status,
  sl.player,
  sl.market,
  sl.line,
  sl.outcome
FROM slips s
LEFT JOIN slip_legs sl ON s.id = sl.slip_id
WHERE s.id = 1
ORDER BY sl.id;
```

### Find best bookmaker by win rate

```sql
-- Win rate by sportsbook
SELECT
  book,
  COUNT(*) as total_slips,
  COUNT(CASE WHEN status IN ('Profit', 'Won') THEN 1 END) as wins,
  ROUND(
    COUNT(CASE WHEN status IN ('Profit', 'Won') THEN 1 END) * 100.0 /
    COUNT(*),
    2
  ) as win_rate_pct,
  SUM(payout - stake) as total_profit
FROM slips
WHERE status NOT IN ('Pending')
GROUP BY book
ORDER BY win_rate_pct DESC;
```

### Get daily profit/loss

```sql
-- P/L by day
SELECT
  DATE(timestamp) as date,
  COUNT(*) as slips,
  SUM(stake) as total_stake,
  SUM(payout) as total_payout,
  SUM(payout - stake) as profit_loss
FROM slips
WHERE status NOT IN ('Pending')
GROUP BY DATE(timestamp)
ORDER BY date DESC
LIMIT 30;
```

### Find most profitable player props

```sql
-- Top players by profit (from resolved slips)
SELECT
  sl.player,
  COUNT(*) as times_bet,
  COUNT(CASE WHEN sl.outcome IN ('Win', 'Won') THEN 1 END) as wins,
  ROUND(
    COUNT(CASE WHEN sl.outcome IN ('Win', 'Won') THEN 1 END) * 100.0 / COUNT(*),
    2
  ) as hit_rate_pct
FROM slip_legs sl
INNER JOIN slips s ON sl.slip_id = s.id
WHERE s.status NOT IN ('Pending')
  AND sl.outcome IS NOT NULL
GROUP BY sl.player
HAVING COUNT(*) >= 5
ORDER BY hit_rate_pct DESC
LIMIT 20;
```

---

## Database Maintenance

### Backup

**Manual backup** (recommended before major updates):
```bash
sqlite3 data/ev_engine.db ".backup data/ev_engine_backup.db"
```

**Automated backup script** (add to cron):
```bash
#!/bin/bash
# backup_db.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/path/to/backups"
sqlite3 /Users/pbrow2/apps/ev-engine/data/ev_engine.db ".backup ${BACKUP_DIR}/ev_engine_${TIMESTAMP}.db"
# Keep only last 30 days
find ${BACKUP_DIR} -name "ev_engine_*.db" -mtime +30 -delete
```

**Restore from backup**:
```bash
# Stop application first
cp data/ev_engine_backup.db data/ev_engine.db
```

### Vacuum (optimize database)

Reclaims unused space after deletions:
```sql
VACUUM;
```

**When to use**:
- After deleting large amounts of old data
- Database file size hasn't shrunk after deletions
- Once per month for routine maintenance

**Run via CLI**:
```bash
sqlite3 data/ev_engine.db "VACUUM;"
```

### Analyze (update statistics)

Updates query optimizer statistics for better performance:
```sql
ANALYZE;
```

**When to use**:
- After bulk inserts or deletes
- When queries seem slower than expected
- Once per week for active databases

**Run via CLI**:
```bash
sqlite3 data/ev_engine.db "ANALYZE;"
```

### Clear old data (if needed)

**Clear odds snapshots older than 30 days**:
```sql
DELETE FROM odds_snapshot
WHERE timestamp < date('now', '-30 days');
```

**Or use built-in function**:
```python
from src.db import clear_old_snapshots
rows_deleted = clear_old_snapshots(days=30)
print(f"Deleted {rows_deleted} old snapshots")
```

**Clear all bets** (done automatically on refresh):
```python
from src.db import clear_bets
clear_bets()
```

### Check database integrity

```bash
sqlite3 data/ev_engine.db "PRAGMA integrity_check;"
```

Should return: `ok`

### View database size

```bash
du -h data/ev_engine.db
```

---

## Performance Considerations

### Index usage for common queries

**Well-indexed queries** (use existing indexes):
```sql
-- Uses idx_bets_ev
SELECT * FROM bets ORDER BY ev_percentage DESC LIMIT 20;

-- Uses idx_slips_status
SELECT * FROM slips WHERE status = 'Pending' ORDER BY timestamp DESC;

-- Uses idx_slip_legs_slip
SELECT * FROM slip_legs WHERE slip_id = 1;

-- Uses idx_odds_snapshot_event
SELECT * FROM odds_snapshot
WHERE event_id = 'abc123' AND player_name = 'LeBron James';
```

**Unindexed queries** (may be slow on large datasets):
```sql
-- Full table scan on dfs_book
SELECT * FROM bets WHERE dfs_book = 'PrizePicks';

-- Full table scan on player
SELECT * FROM slip_legs WHERE player = 'LeBron James';
```

### Query optimization tips

1. **Use WHERE before JOIN** - Filter early to reduce rows
2. **SELECT only needed columns** - Avoid `SELECT *` in production code
3. **Use LIMIT** - Prevent returning massive result sets
4. **Add indexes** - For frequently queried columns (but don't over-index)
5. **Use transactions** - Batch multiple INSERTs in one transaction

**Example optimization**:
```sql
-- Slow (full table scan)
SELECT * FROM slip_legs WHERE player LIKE '%James%';

-- Better (but still needs index on player)
SELECT player, market, line FROM slip_legs WHERE player = 'LeBron James';
```

### When to use EXPLAIN QUERY PLAN

Check if indexes are being used:
```sql
EXPLAIN QUERY PLAN
SELECT * FROM bets WHERE ev_percentage > 5.0 ORDER BY ev_percentage DESC;
```

Output should show: `SEARCH bets USING INDEX idx_bets_ev`

If you see `SCAN TABLE` instead of `SEARCH ... USING INDEX`, consider adding an index.

### Typical query performance benchmarks

**Small database (<10MB, <50K rows)**:
- Simple SELECT with index: <1ms
- Complex JOIN with aggregation: 5-20ms
- Full table scan: 10-50ms

**Medium database (10-100MB, 50K-500K rows)**:
- Simple SELECT with index: 1-5ms
- Complex JOIN with aggregation: 20-100ms
- Full table scan: 100-500ms

**Large database (>100MB, >500K rows)**:
- Consider archiving old data
- Add more targeted indexes
- Use pagination (LIMIT + OFFSET)
- Consider migrating to PostgreSQL

---

## Schema Migrations

### Current version

**v1** (initial schema) - Created via `initialize_db()`

No formal migration system in place yet.

### How to handle schema changes

**Current approach** (manual):
1. Backup database
2. Write SQL ALTER TABLE statements
3. Test on backup copy
4. Apply to production database

**Example - Add column to slips table**:
```python
import sqlite3
conn = sqlite3.connect('data/ev_engine.db')
cursor = conn.cursor()
cursor.execute("ALTER TABLE slips ADD COLUMN odds_multiplier REAL")
conn.commit()
conn.close()
```

### Future migration strategy

**Consider using Alembic** (SQLAlchemy migration tool):
- Track schema versions
- Automated migration scripts
- Rollback capability
- Team collaboration on schema changes

**Or use custom migration system**:
```python
# migrations/001_add_odds_multiplier.py
def upgrade(conn):
    conn.execute("ALTER TABLE slips ADD COLUMN odds_multiplier REAL")

def downgrade(conn):
    # SQLite doesn't support DROP COLUMN easily
    # Would need to recreate table
    pass
```

---

## Data Integrity

### Constraints enforced

**Primary keys**:
- All tables have auto-increment INTEGER primary keys
- Ensures unique row identification

**NOT NULL constraints**:
- Critical fields like `event_id`, `player_name`, `stake` cannot be NULL
- Prevents incomplete data

**DEFAULT values**:
- `timestamp` defaults to CURRENT_TIMESTAMP
- `status` defaults to 'Pending'
- `payout` defaults to 0.0

**Foreign key cascades**:
- `slip_legs.slip_id` → `slips.id` ON DELETE CASCADE
- Deleting a slip automatically removes all its legs
- Maintains referential integrity

**Note**: Foreign keys must be enabled in SQLite:
```python
conn = sqlite3.connect(DATABASE_PATH)
conn.execute("PRAGMA foreign_keys = ON")
```

### Triggers (if any)

**Currently**: No triggers implemented

**Future possibilities**:
- Auto-update `timestamp` on row modification
- Validate status transitions (Pending → Won/Lost, not Won → Pending)
- Calculate aggregate stats on slip resolution

### Data validation at application level

Validation is done in Python code, not database constraints:

- **Stake validation**: `create_slip()` ensures stake > 0
- **Status validation**: `update_bet_status()` only allows valid statuses
- **Type safety**: `safe_float()` and `safe_dict_get()` prevent type errors
- **Leg validation**: `create_slip()` requires non-empty legs list

**Example**:
```python
# From db.py
stake_value = safe_float(stake, default=0.0)
if stake_value <= 0:
    raise ValueError(f"Stake must be greater than 0, got {stake}")
```

---

## Backup & Recovery

### Backup frequency recommendations

**Recommended schedule**:
- **Before each odds refresh**: Automatic backup before `clear_bets()` and `insert_odds_batch()`
- **Daily**: Automated backup at end of day
- **Weekly**: Full backup with retention for 4-12 weeks
- **Before major updates**: Manual backup before upgrading application code

### Automated backup scripts

**Daily backup (add to cron or Task Scheduler)**:
```bash
#!/bin/bash
# daily_backup.sh
BACKUP_DIR="/Users/pbrow2/backups/ev-engine"
TIMESTAMP=$(date +%Y%m%d)
DB_PATH="/Users/pbrow2/apps/ev-engine/data/ev_engine.db"

# Create backup
sqlite3 "${DB_PATH}" ".backup ${BACKUP_DIR}/ev_engine_${TIMESTAMP}.db"

# Compress backup
gzip "${BACKUP_DIR}/ev_engine_${TIMESTAMP}.db"

# Delete backups older than 30 days
find "${BACKUP_DIR}" -name "ev_engine_*.db.gz" -mtime +30 -delete

echo "Backup completed: ev_engine_${TIMESTAMP}.db.gz"
```

**Crontab entry** (backup daily at 3 AM):
```
0 3 * * * /Users/pbrow2/apps/ev-engine/scripts/daily_backup.sh
```

### Recovery procedures

**Scenario 1: Database corrupted**
```bash
# Check integrity first
sqlite3 data/ev_engine.db "PRAGMA integrity_check;"

# If corrupted, restore from latest backup
cp /Users/pbrow2/backups/ev-engine/ev_engine_20260201.db data/ev_engine.db

# Verify integrity
sqlite3 data/ev_engine.db "PRAGMA integrity_check;"
```

**Scenario 2: Accidental data deletion**
```bash
# Find most recent backup before deletion
ls -lt /Users/pbrow2/backups/ev-engine/

# Restore specific backup
cp /Users/pbrow2/backups/ev-engine/ev_engine_20260131.db data/ev_engine.db
```

**Scenario 3: Partial recovery (extract specific table)**
```bash
# Export specific table from backup
sqlite3 /path/to/backup.db ".mode insert slips" ".output slips_backup.sql" "SELECT * FROM slips;"

# Import into current database
sqlite3 data/ev_engine.db < slips_backup.sql
```

### Data export options

**Export to CSV**:
```bash
sqlite3 -header -csv data/ev_engine.db "SELECT * FROM slips;" > slips_export.csv
```

**Export to SQL dump**:
```bash
sqlite3 data/ev_engine.db .dump > ev_engine_dump.sql
```

**Export specific table to JSON** (via Python):
```python
import sqlite3
import json

conn = sqlite3.connect('data/ev_engine.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM slips")
rows = [dict(row) for row in cursor.fetchall()]

with open('slips_export.json', 'w') as f:
    json.dump(rows, f, indent=2, default=str)
```

---

## Troubleshooting

### Common database issues

#### 1. Database locked

**Symptoms**: `sqlite3.OperationalError: database is locked`

**Causes**:
- Multiple processes trying to write simultaneously
- Long-running transaction not committed
- Application crashed without closing connection

**Solutions**:
```python
# Increase timeout
conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)

# Ensure connections are always closed
try:
    # database operations
    conn.commit()
finally:
    conn.close()

# Use context manager (auto-closes)
with sqlite3.connect(DATABASE_PATH) as conn:
    cursor = conn.cursor()
    cursor.execute("...")
    conn.commit()
```

**Last resort** (if database is stuck):
```bash
# Kill all processes using the database
lsof | grep ev_engine.db
kill <PID>
```

#### 2. Corrupted database

**Symptoms**:
- `PRAGMA integrity_check` returns errors
- Unexpected crashes when querying
- `database disk image is malformed`

**Solutions**:
```bash
# Attempt repair using dump and restore
sqlite3 data/ev_engine.db ".dump" | sqlite3 data/ev_engine_repaired.db

# Verify integrity
sqlite3 data/ev_engine_repaired.db "PRAGMA integrity_check;"

# If successful, replace original
mv data/ev_engine.db data/ev_engine.db.corrupted
mv data/ev_engine_repaired.db data/ev_engine.db
```

**Prevention**:
- Regular backups
- Use transactions properly
- Don't kill application mid-write

#### 3. Slow queries

**Symptoms**:
- Dashboard takes >5 seconds to load
- Queries timeout
- Application feels sluggish

**Diagnosis**:
```sql
-- Check if indexes are being used
EXPLAIN QUERY PLAN SELECT * FROM bets WHERE ev_percentage > 5;

-- Check database statistics
PRAGMA page_count;
PRAGMA page_size;
-- Database size = page_count × page_size
```

**Solutions**:
```sql
-- Update statistics
ANALYZE;

-- Add missing indexes
CREATE INDEX idx_bets_dfs_book ON bets(dfs_book);

-- Vacuum to defragment
VACUUM;
```

**Code-level optimization**:
```python
# Bad: Multiple queries
for slip_id in slip_ids:
    legs = get_slip_legs(slip_id)  # N queries

# Good: Single query with JOIN
cursor.execute("""
    SELECT sl.* FROM slip_legs sl
    WHERE sl.slip_id IN (?, ?, ?)
""", slip_ids)
```

#### 4. Disk space issues

**Symptoms**:
- `database or disk is full`
- Cannot insert new records

**Check disk space**:
```bash
df -h /Users/pbrow2/apps/ev-engine/data
du -h data/ev_engine.db
```

**Solutions**:
```python
# Clear old odds snapshots
from src.db import clear_old_snapshots
clear_old_snapshots(days=7)

# Vacuum to reclaim space
import sqlite3
conn = sqlite3.connect('data/ev_engine.db')
conn.execute("VACUUM")
conn.close()
```

**Check database size reduction**:
```bash
du -h data/ev_engine.db  # Before and after VACUUM
```

---

## Sample Data

### odds_snapshot sample
```sql
INSERT INTO odds_snapshot (event_id, sport_key, bookmaker, market_key, player_name, selection, price, point, timestamp) VALUES
('nba_abc123', 'basketball_nba', 'pinnacle', 'player_points', 'LeBron James', 'Over', -110, 25.5, '2026-02-01 18:00:00'),
('nba_abc123', 'basketball_nba', 'pinnacle', 'player_points', 'LeBron James', 'Under', -110, 25.5, '2026-02-01 18:00:00'),
('nba_abc123', 'basketball_nba', 'fanduel', 'player_points', 'LeBron James', 'Over', -105, 25.5, '2026-02-01 18:00:30');
```

### bets sample
```sql
INSERT INTO bets (event_id, player_name, market, line_value, pinnacle_over_price, pinnacle_under_price, fair_win_prob, ev_percentage, dfs_book) VALUES
('nba_abc123', 'LeBron James', 'Player Points Over', 25.5, -110, -110, 0.524, 5.2, 'PrizePicks'),
('nba_xyz789', 'Steph Curry', 'Player 3-Pointers Over', 4.5, -120, +100, 0.545, 4.5, 'Underdog');
```

### slips sample
```sql
INSERT INTO slips (book, stake, payout, status, note) VALUES
('PrizePicks', 25.00, 62.50, 'Profit', 'Good NBA slate'),
('Underdog', 10.00, 0.00, 'Lost', NULL),
('PrizePicks', 50.00, 0.00, 'Pending', 'High confidence plays');
```

### slip_legs sample
```sql
INSERT INTO slip_legs (slip_id, player, market, line, outcome) VALUES
(1, 'LeBron James', 'Player Points Over', 25.5, 'Win'),
(1, 'Steph Curry', 'Player 3-Pointers Over', 4.5, 'Win'),
(1, 'Kevin Durant', 'Player Assists Over', 6.5, 'Win'),
(2, 'Luka Doncic', 'Player Points Over', 30.5, 'Lost'),
(3, 'Giannis Antetokounmpo', 'Player Rebounds Over', 11.5, NULL);
```

---

## Migration to PostgreSQL (Future)

### When to consider migration

Migrate to PostgreSQL if you need:
- **Multi-user access**: Multiple bettors or team collaboration
- **Web deployment**: Public or shared dashboard accessible from multiple devices
- **Concurrent writes**: Real-time updates from multiple data sources
- **Advanced features**: JSON columns, full-text search, geospatial data
- **Scalability**: Handling >100GB of data or high transaction volume
- **Enterprise features**: Row-level security, replication, advanced backup

### Benefits of PostgreSQL

**Performance**:
- Better handling of concurrent connections
- More sophisticated query optimizer
- Parallel query execution

**Features**:
- Native JSON/JSONB support for storing API responses
- Advanced indexing (GiST, GIN, BRIN)
- Full-text search
- Window functions and CTEs

**Reliability**:
- Point-in-time recovery
- Streaming replication
- Hot standby servers

**Security**:
- Row-level security policies
- Advanced authentication (LDAP, Kerberos)
- Encryption at rest and in transit

### Migration steps

**1. Install PostgreSQL**:
```bash
brew install postgresql
brew services start postgresql
```

**2. Export SQLite data**:
```bash
sqlite3 data/ev_engine.db .dump > ev_engine_dump.sql
```

**3. Create PostgreSQL database**:
```sql
CREATE DATABASE ev_engine;
\c ev_engine
```

**4. Convert SQLite dump to PostgreSQL**:
- Replace `INTEGER PRIMARY KEY AUTOINCREMENT` with `SERIAL PRIMARY KEY`
- Replace `DATETIME` with `TIMESTAMP`
- Replace `REAL` with `NUMERIC` or `FLOAT`
- Remove `IF NOT EXISTS` from CREATE INDEX (use separate checks)

**5. Import data**:
```bash
psql -U postgres -d ev_engine < ev_engine_postgres.sql
```

**6. Update Python code**:
```python
# Replace sqlite3 with psycopg2
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    return psycopg2.connect(
        dbname="ev_engine",
        user="postgres",
        password="yourpassword",
        host="localhost",
        cursor_factory=RealDictCursor
    )
```

### Schema differences to consider

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Auto-increment | INTEGER PRIMARY KEY AUTOINCREMENT | SERIAL or IDENTITY |
| Boolean | INTEGER (0/1) | BOOLEAN |
| Date/Time | TEXT or INTEGER | TIMESTAMP, DATE, TIME |
| JSON | TEXT | JSON or JSONB |
| Array | TEXT (serialized) | ARRAY |
| Case sensitivity | Case-insensitive LIKE | Case-sensitive, use ILIKE |
| Alter table | Limited (can't drop columns easily) | Full ALTER support |

**Example migration**:
```sql
-- SQLite
CREATE TABLE slips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- PostgreSQL
CREATE TABLE slips (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Appendix

### Quick reference

**Connect to database**:
```bash
sqlite3 data/ev_engine.db
```

**Common SQLite commands**:
```sql
.tables                  -- List all tables
.schema slips            -- Show CREATE statement for table
.mode column             -- Pretty print output
.headers on              -- Show column headers
.exit                    -- Exit SQLite shell
```

**Connection string** (for Python):
```python
DATABASE_PATH = "data/ev_engine.db"
conn = sqlite3.connect(DATABASE_PATH)
```

### External resources

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [SQLite Performance Tuning](https://www.sqlite.org/queryplanner.html)
- [SQL Style Guide](https://www.sqlstyle.guide/)
- [Alembic (migrations)](https://alembic.sqlalchemy.org/)

---

**Last updated**: 2026-02-01
**Schema version**: v1
**Maintained by**: EV Engine development team
