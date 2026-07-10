"""SQLite database configuration and connection helpers."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import logging

logger = logging.getLogger(__name__)


def init_db():
    """Initialize SQLite database from db/schema.sql."""
    logger.info("Initializing SQLite database...")
    schema_path = Path(__file__).resolve().parents[2] / "db" / "schema.sql"
    with sqlite3.connect(get_db_path()) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        connection.commit()
    logger.info("SQLite database initialized successfully")


def get_db_path() -> str:
    """Return absolute path to the project SQLite database file."""
    return str(Path(__file__).resolve().parents[2] / "db" / "midas.sqlite3")


@contextmanager
def get_connection():
    """Context manager for SQLite connections with FK enforcement."""
    connection = sqlite3.connect(get_db_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
