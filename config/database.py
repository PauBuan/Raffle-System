"""
config/database.py
------------------
MSSQL-only database configuration for the Raffle System v2.0.
All connection parameters are defined here — single source of truth.

ONLY edit this file to change DB connection.

Configuration Routing
---------------------
    config/database.py   →  get_connection_url()  (this file)
        ↓  imported by
    app/models/database_manager.py  →  create_engine(url)
        ↓  SessionLocal used by
    app/models/*_repository.py      →  all repositories
        ↓  used by
    app/services/*                  →  business logic
        ↓  used by
    app/controllers/*               →  presentation controllers
        ↓  used by
    app/views/**                    →  UI layer
"""

# ── Connection parameters ──────────────────────────────────────
SERVER   = "localhost"                    # or "your-server\\SQLEXPRESS", or IP:1433
DATABASE = "RaffleSystemDB"
DRIVER   = "ODBC+Driver+17+for+SQL+Server"

# Auth — choose one:
TRUSTED_CONNECTION = True     # Windows auth (set USER/PASSWORD to "")
USER     = ""
PASSWORD = ""


def get_connection_url() -> str:
    """
    Return a full SQLAlchemy connection string for MSSQL via pyodbc.

    Routing
    -------
    database_manager.py  →  create_engine(get_connection_url())
        → SQLAlchemy engine  →  SQL Server 2019
    """
    if TRUSTED_CONNECTION:
        return (
            f"mssql+pyodbc://{SERVER}/{DATABASE}"
            f"?driver={DRIVER}&trusted_connection=yes"
        )
    return (
        f"mssql+pyodbc://{USER}:{PASSWORD}@{SERVER}/{DATABASE}"
        f"?driver={DRIVER}"
    )
