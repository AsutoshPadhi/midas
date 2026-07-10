"""Create and initialize the local SQLite database in the db directory."""

from pathlib import Path
import sqlite3


def initialize_database() -> Path:
    db_dir = Path(__file__).parent
    schema_path = db_dir / "schema.sql"
    database_path = db_dir / "midas.sqlite3"

    schema_sql = schema_path.read_text(encoding="utf-8")

    with sqlite3.connect(database_path) as connection:
        connection.executescript(schema_sql)
        connection.commit()

    return database_path


if __name__ == "__main__":
    created_db_path = initialize_database()
    print(f"SQLite database initialized at: {created_db_path}")
