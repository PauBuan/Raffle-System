"""
app/models/database_manager.py
-------------------------------
Data Access Layer (DAL).

Routing
-------
All database I/O flows through DatabaseManager.
Upper tiers (Services → Controllers → Views) NEVER import pyodbc
or sqlite3 directly; they call DatabaseManager methods only.

Connection strategy
-------------------
1. Attempt SQL Server 2019 connection via pyodbc.
2. If that fails AND USE_SQLITE_FALLBACK is True, fall back to
   an SQLite file so the app runs in demo/offline mode.
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    logger.warning("pyodbc not found — SQLite fallback will be used.")

from config.database import DB_CONFIG


class DatabaseManager:
    """
    Singleton-style database manager.
    Provides a context-managed connection and generic execute helpers.
    """

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    # ── Initialisation ─────────────────────────────────────────────

    def __init__(self) -> None:
        if self._initialised:
            return
        self._use_sqlite = False
        self._sqlite_path = DB_CONFIG.SQLITE_PATH
        self._conn_str = DB_CONFIG.build_connection_string()
        self._test_connection()
        self._initialised = True

    def _test_connection(self) -> None:
        """Try SQL Server; fall back to SQLite if needed."""
        if PYODBC_AVAILABLE:
            try:
                conn = pyodbc.connect(self._conn_str, timeout=DB_CONFIG.CONNECT_TIMEOUT)
                conn.close()
                logger.info("SQL Server connection verified.")
                return
            except Exception as exc:
                logger.warning("SQL Server unavailable: %s", exc)

        if DB_CONFIG.USE_SQLITE_FALLBACK:
            logger.info("Using SQLite fallback: %s", self._sqlite_path)
            self._use_sqlite = True
            self._bootstrap_sqlite()
        else:
            raise ConnectionError("Cannot connect to SQL Server and fallback is disabled.")

    # ── Context manager ────────────────────────────────────────────

    @contextmanager
    def get_connection(self):
        """
        Yield an open DB connection.  Commits on clean exit, rolls back
        on exception, always closes.
        """
        if self._use_sqlite:
            conn = sqlite3.connect(self._sqlite_path)
            conn.row_factory = sqlite3.Row
        else:
            conn = pyodbc.connect(self._conn_str)

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Generic helpers ────────────────────────────────────────────

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute a SELECT and return all rows as a list of dicts."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        """Execute a SELECT and return the first row as a dict, or None."""
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: tuple = ()) -> int:
        """
        Execute an INSERT / UPDATE / DELETE.
        Returns the last inserted rowid (SQLite) or SCOPE_IDENTITY()
        (SQL Server).

        Routing
        -------
        *Repository.record_winner() / add_prize()
            → DatabaseManager.execute(INSERT …)
            → SQL Server  →  SCOPE_IDENTITY()
            ──or──
            → SQLite      →  cursor.lastrowid
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            if self._use_sqlite:
                return cur.lastrowid
            # SQL Server: retrieve the identity of the just-inserted row
            cur.execute("SELECT SCOPE_IDENTITY()")
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

    def execute_many(self, sql: str, param_list: list[tuple]) -> None:
        """Bulk-execute an INSERT / UPDATE."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(sql, param_list)

    # ── SQLite bootstrap ───────────────────────────────────────────

    def _bootstrap_sqlite(self) -> None:
        """Create tables and seed data in the SQLite demo database."""
        import os, pathlib
        pathlib.Path(self._sqlite_path).parent.mkdir(parents=True, exist_ok=True)

        ddl = """
        CREATE TABLE IF NOT EXISTS PrizeCategories (
            CategoryID   INTEGER PRIMARY KEY AUTOINCREMENT,
            CategoryName TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Prizes (
            PrizeID   INTEGER PRIMARY KEY AUTOINCREMENT,
            CategoryID INTEGER NOT NULL,
            PrizeName TEXT NOT NULL,
            Quantity  INTEGER NOT NULL DEFAULT 1,
            IsActive  INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS Employees (
            EmpNo      TEXT PRIMARY KEY,
            EmpName    TEXT NOT NULL,
            Department TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS RaffleWinners (
            WinnerID   INTEGER PRIMARY KEY AUTOINCREMENT,
            PrizeID    INTEGER NOT NULL,
            EmpNo      TEXT NOT NULL,
            Department TEXT NOT NULL,
            DrawnAt    TEXT NOT NULL DEFAULT (datetime('now')),
            IsRedraw   INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS RaffleSession (
            SessionID   INTEGER PRIMARY KEY AUTOINCREMENT,
            SessionName TEXT NOT NULL,
            Department  TEXT NOT NULL,
            CreatedAt   TEXT NOT NULL DEFAULT (datetime('now')),
            IsActive    INTEGER NOT NULL DEFAULT 1
        );
        """

        conn = sqlite3.connect(self._sqlite_path)
        conn.executescript(ddl)

        # Seed categories only if empty
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM PrizeCategories")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO PrizeCategories (CategoryName) VALUES (?)",
                [("Minor",), ("Major",), ("Grand",)],
            )
            cur.executemany(
                "INSERT INTO Employees (EmpNo, EmpName, Department) VALUES (?,?,?)",
                [
                    ("EMP001", "Juan dela Cruz",    "Engineering"),
                    ("EMP002", "Maria Santos",      "Engineering"),
                    ("EMP003", "Pedro Reyes",       "Engineering"),
                    ("EMP004", "Ana Gonzalez",      "HR"),
                    ("EMP005", "Jose Ramos",        "HR"),
                    ("EMP006", "Luz Fernandez",     "HR"),
                    ("EMP007", "Carlos Villanueva", "Finance"),
                    ("EMP008", "Elena Torres",      "Finance"),
                    ("EMP009", "Roberto Aquino",    "Finance"),
                    ("EMP010", "Maricel Bautista",  "Marketing"),
                    ("EMP011", "Andres Castillo",   "Marketing"),
                    ("EMP012", "Cristina Lim",      "Marketing"),
                    ("OJT26A01", "OJT Intern Alpha","Engineering"),
                    ("OJT26A02", "OJT Intern Beta", "Engineering"),
                    ("OJT26A03", "OJT Intern Gamma","HR"),
                ],
            )
            cur.executemany(
                "INSERT INTO Prizes (CategoryID, PrizeName, Quantity) VALUES (?,?,?)",
                [
                    (1, "Gift Card P500",   5),
                    (1, "Consolation Pack", 3),
                    (2, 'Smart TV 32"',     2),
                    (2, "Air Fryer",        1),
                    (3, "Laptop",           1),
                    (3, "Motorcycle",       1),
                ],
            )
        conn.commit()
        conn.close()
