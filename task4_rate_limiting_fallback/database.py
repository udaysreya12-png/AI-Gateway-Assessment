
import sqlite3
from pathlib import Path

# Store the database on disk inside the Task 4 folder.
DB_PATH = Path(__file__).resolve().parent / "rate_limits.db"


def get_connection():
    """Create a SQLite database connection."""
    connection = sqlite3.connect(
        DB_PATH,
        timeout=30
    )
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def initialize_database():
    """Create the token usage table if it does not exist."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_key TEXT NOT NULL,
                tokens INTEGER NOT NULL CHECK (tokens > 0),
                timestamp REAL NOT NULL
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_tenant_timestamp
            ON token_usage (tenant_key, timestamp)
        """)

        connection.commit()


if __name__ == "__main__":
    initialize_database()
    print("SQLite database initialized successfully.")
    print(f"Database location: {DB_PATH}")
