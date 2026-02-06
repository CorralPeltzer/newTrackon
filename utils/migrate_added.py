"""Migration script to convert the 'added' column from TEXT (D-M-YYYY) to INTEGER (unix timestamp).

Usage: python utils/migrate_added.py [path_to_db]
Default path: data/trackon.db
"""

import sqlite3
import sys
from datetime import UTC, datetime


def parse_added_date(date_str: str) -> int:
    """Convert 'D-M-YYYY' text date to unix timestamp."""
    parts = date_str.split("-")
    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    dt = datetime(year, month, day, tzinfo=UTC)
    return int(dt.timestamp())


def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Read all current added values
    rows = c.execute("SELECT host, added FROM status").fetchall()
    print(f"Migrating {len(rows)} trackers...")

    # Create new table with INTEGER column
    c.execute("""CREATE TABLE status_new (
        host          TEXT NOT NULL,
        url           TEXT NOT NULL,
        ip            TEXT,
        latency       INTEGER,
        last_checked  INTEGER,
        interval      INTEGER,
        status        INTEGER,
        uptime        INTEGER,
        country       TEXT,
        country_code  TEXT,
        network       TEXT,
        added         INTEGER,
        historic      TEXT,
        last_downtime INTEGER,
        last_uptime   INTEGER,
        PRIMARY KEY (host)
    )""")

    # Copy data, converting added dates
    c.execute("""INSERT INTO status_new
        SELECT host, url, ip, latency, last_checked, interval, status, uptime,
               country, country_code, network, 0, historic, last_downtime, last_uptime
        FROM status""")

    # Update the converted timestamps
    for row in rows:
        host = row["host"]
        added_str = row["added"]
        try:
            timestamp = parse_added_date(added_str)
        except (ValueError, IndexError):
            print(f"  Warning: could not parse '{added_str}' for {host}, using 0")
            timestamp = 0
        c.execute("UPDATE status_new SET added = ? WHERE host = ?", (timestamp, host))

    # Swap tables
    c.execute("DROP TABLE status")
    c.execute("ALTER TABLE status_new RENAME TO status")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/trackon.db"
    migrate(db_path)
