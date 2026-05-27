"""
app/models/database_manager.py
-------------------------------
Data Access Layer (DAL) — SQLAlchemy engine and session management.

Routing
-------
All database I/O flows through SQLAlchemy sessions obtained via get_session().
Upper tiers (Services → Controllers → Views) NEVER import pyodbc
or sqlite3 directly; they use get_session() only.

Connection strategy
-------------------
MSSQL only via SQLAlchemy + pyodbc dialect.  No fallback.
If SQL Server is unreachable, the app raises a clear startup error.
"""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config.database import get_connection_url

logger = logging.getLogger(__name__)

# ── SQLAlchemy engine ──────────────────────────────────────────────
_url = get_connection_url()
engine = create_engine(_url, pool_pre_ping=True)

# ── Session factory ────────────────────────────────────────────────
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ── Declarative base for all ORM models ────────────────────────────
Base = declarative_base()


@contextmanager
def get_session():
    """
    Context-managed SQLAlchemy session.

    Usage
    -----
        with get_session() as session:
            results = session.query(Employee).all()
            session.add(new_record)
            # auto-commits on clean exit, rolls back on exception

    Routing
    -------
    All *Repository classes call get_session() to obtain a session.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_connection() -> bool:
    """
    Test the database connection at startup.
    Returns True if connection succeeds, raises ConnectionError otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        logger.info("SQL Server connection verified via SQLAlchemy.")
        return True
    except Exception as exc:
        msg = (
            f"Cannot connect to SQL Server.\n"
            f"  URL: {_url.split('@')[-1] if '@' in _url else _url}\n"
            f"  Error: {exc}"
        )
        logger.error(msg)
        raise ConnectionError(msg) from exc
