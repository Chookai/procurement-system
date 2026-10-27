import hashlib
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


class Database:
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def connect(self):
        with psycopg.connect(
            self.settings.database_url, row_factory=dict_row, connect_timeout=5
        ) as connection:
            connection.execute(
                sql.SQL("SET search_path TO {}").format(
                    sql.Identifier(self.settings.schema)
                )
            )
            yield connection

    def migrate(self):
        with psycopg.connect(
            self.settings.database_url, row_factory=dict_row
        ) as connection:
            connection.execute("SELECT pg_advisory_xact_lock(7723001)")
            connection.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(self.settings.schema)
                )
            )
            connection.execute(
                sql.SQL("SET search_path TO {}").format(
                    sql.Identifier(self.settings.schema)
                )
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            for path in sorted(
                (Path(__file__).resolve().parents[1] / "migrations").glob("*.sql")
            ):
                source = path.read_text()
                checksum = hashlib.sha256(source.encode()).hexdigest()
                existing = connection.execute(
                    "SELECT checksum FROM schema_migrations WHERE name=%s", (path.name,)
                ).fetchone()
                if existing:
                    if existing["checksum"] != checksum:
                        raise RuntimeError("Applied migration changed: " + path.name)
                    continue
                connection.execute(source)
                connection.execute(
                    "INSERT INTO schema_migrations (name, checksum) VALUES (%s,%s)",
                    (path.name, checksum),
                )
