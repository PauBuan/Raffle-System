"""
config/database.py
------------------
Centralised database configuration for the Raffle System.
All connection parameters are defined here so every tier reads
from a single source of truth.

Data‑Flow Routing
-----------------
Every database call follows this exact path — no shortcuts:

    User Action (Qt event)
            │
            ▼
    DrawPanel / WinnersView              [View]           app/views/
            │  calls method on
            ▼
    RaffleController                     [Controller]     app/controllers/
            │  calls method on
            ▼
    RaffleService                        [Service / BLL]  app/services/
            │  calls method on
            ▼
    EmployeeRepository / PrizeRepository
    / WinnerRepository                   [Model / DAL]    app/models/
            │  calls
            ▼
    DatabaseManager.fetch_all() / execute()               app/models/database_manager.py
            │  opens context‑managed connection
            ▼
    pyodbc  →  SQL Server 2019           [Database]       localhost / RaffleSystemDB

Configuration Routing
---------------------
    config/database.py   →  DB_CONFIG  (this file — single source of truth)
        ↓  imported by
    app/models/database_manager.py  →  DatabaseManager (singleton)
        ↓  used by
    app/models/employee_model.py    →  EmployeeRepository
    app/models/prize_model.py       →  PrizeRepository
    app/models/winner_model.py      →  WinnerRepository
        ↓  used by
    app/services/raffle_service.py  →  RaffleService
        ↓  used by
    app/controllers/raffle_controller.py  →  RaffleController
        ↓  used by
    app/views/**                    →  DrawPanel, WinnersView, MainWindow
"""

from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """
    Holds all SQL Server connection parameters.

    Active Target
    -------------
    Server :  localhost
    Database: RaffleSystemDB
    Auth   :  Windows (Trusted Connection)
    Driver :  ODBC Driver 17 for SQL Server
    """

    # ── Connection parameters ──────────────────────────────────────
    SERVER:   str = "localhost"               # SQL Server host
    DATABASE: str = "RaffleSystemDB"          # Target database
    DRIVER:   str = "ODBC Driver 17 for SQL Server"

    # Trusted (Windows) auth — set to False and fill USER/PASSWORD
    # if using SQL auth.
    TRUSTED_CONNECTION: bool = True
    USER:     str = ""
    PASSWORD: str = ""

    # ── Pool / retry settings ──────────────────────────────────────
    CONNECT_TIMEOUT: int = 10   # seconds before connection attempt fails
    MAX_RETRIES:     int = 3

    # ── SQLite fallback (for offline / demo mode) ──────────────────
    USE_SQLITE_FALLBACK: bool = False         # Disabled — using SQL Server
    SQLITE_PATH: str = "database/raffle_demo.db"

    def build_connection_string(self) -> str:
        """
        Return a pyodbc connection string based on current config.

        Routing
        -------
        DatabaseManager.__init__()
            → DB_CONFIG.build_connection_string()
            → pyodbc.connect(conn_str)
            → SQL Server 2019 at localhost/RaffleSystemDB
        """
        base = (
            f"DRIVER={{{self.DRIVER}}};"
            f"SERVER={self.SERVER};"
            f"DATABASE={self.DATABASE};"
            f"Timeout={self.CONNECT_TIMEOUT};"
        )
        if self.TRUSTED_CONNECTION:
            return base + "Trusted_Connection=yes;"
        return base + f"UID={self.USER};PWD={self.PASSWORD};"


# ── Singleton instance ─────────────────────────────────────────────
# Imported by: app/models/database_manager.py  →  DatabaseManager
# The entire application reads connection settings from this object.
DB_CONFIG = DatabaseConfig()
