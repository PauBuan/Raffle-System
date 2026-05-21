# -*- coding: utf-8 -*-
"""
verify_db.py
------------
Database connection and schema verification for the Raffle System.

Usage
-----
    python verify_db.py

Routing
-------
    verify_db.py  →  config/database.py (DB_CONFIG)
                  →  pyodbc  →  SQL Server 2019 at localhost / RaffleSystemDB

This script validates:
    1. pyodbc is installed and importable
    2. SQL Server connection succeeds with the configured credentials
    3. All 5 expected tables exist (from database/schema.sql)
    4. Each table has the expected columns
    5. Seed data row counts are reported
"""

import sys

# ── Colour helpers for terminal output ─────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}[PASS]{RESET}"
FAIL = f"{RED}[FAIL]{RESET}"
WARN = f"{YELLOW}[WARN]{RESET}"
INFO = f"{CYAN}[INFO]{RESET}"


def header(title: str) -> None:
    width = 60
    print(f"\n{BOLD}{'=' * width}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"  {'=' * width}{RESET}")


def section(title: str) -> None:
    print(f"\n{BOLD}-- {title} --{RESET}")


# ── Expected schema (from database/schema.sql) ────────────────────
EXPECTED_TABLES = {
    "Employees": [
        "EmpNo", "EmpName", "Department",
    ],
    "PrizeCategories": [
        "CategoryID", "CategoryName",
    ],
    "Prizes": [
        "PrizeID", "CategoryID", "PrizeName", "Quantity", "IsActive",
    ],
    "RaffleWinners": [
        "WinnerID", "PrizeID", "EmpNo", "Department", "DrawnAt", "IsRedraw",
    ],
    "RaffleSession": [
        "SessionID", "SessionName", "Department", "CreatedAt", "IsActive",
    ],
}


def main() -> int:
    header("Raffle System - Database Verification")
    errors = 0

    # ── 1. Check pyodbc ────────────────────────────────────────────
    section("1. Driver check")
    try:
        import pyodbc
        print(f"  {PASS}  pyodbc {pyodbc.version} is installed")
    except ImportError:
        print(f"  {FAIL}  pyodbc is NOT installed")
        print(f"         Run: pip install pyodbc")
        return 1

    # ── 2. Load config ─────────────────────────────────────────────
    section("2. Configuration")
    try:
        from config.database import DB_CONFIG
        print(f"  {INFO}  Server   : {DB_CONFIG.SERVER}")
        print(f"  {INFO}  Database : {DB_CONFIG.DATABASE}")
        print(f"  {INFO}  Driver   : {DB_CONFIG.DRIVER}")
        print(f"  {INFO}  Auth     : {'Windows (Trusted)' if DB_CONFIG.TRUSTED_CONNECTION else 'SQL Auth'}")
        print(f"  {INFO}  Timeout  : {DB_CONFIG.CONNECT_TIMEOUT}s")
        conn_str = DB_CONFIG.build_connection_string()
    except Exception as exc:
        print(f"  {FAIL}  Could not load config: {exc}")
        return 1

    # ── 3. Test connection ─────────────────────────────────────────
    section("3. Connection test")
    try:
        conn = pyodbc.connect(conn_str, timeout=DB_CONFIG.CONNECT_TIMEOUT)
        print(f"  {PASS}  Connected to SQL Server successfully")
    except pyodbc.InterfaceError as exc:
        print(f"  {FAIL}  Interface error — is SQL Server running?")
        print(f"         {exc}")
        return 1
    except pyodbc.OperationalError as exc:
        print(f"  {FAIL}  Operational error — check credentials / network")
        print(f"         {exc}")
        return 1
    except Exception as exc:
        print(f"  {FAIL}  Unexpected error: {exc}")
        return 1

    # ── 4. Verify database exists ──────────────────────────────────
    section("4. Database verification")
    cur = conn.cursor()
    try:
        cur.execute("SELECT DB_NAME()")
        db_name = cur.fetchone()[0]
        if db_name == DB_CONFIG.DATABASE:
            print(f"  {PASS}  Active database: {db_name}")
        else:
            print(f"  {WARN}  Expected '{DB_CONFIG.DATABASE}', got '{db_name}'")
            errors += 1
    except Exception as exc:
        print(f"  {FAIL}  Could not query database name: {exc}")
        errors += 1

    # ── 5. Validate tables ─────────────────────────────────────────
    section("5. Table verification")
    try:
        cur.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
        )
        existing_tables = {row[0] for row in cur.fetchall()}
    except Exception as exc:
        print(f"  {FAIL}  Could not query INFORMATION_SCHEMA: {exc}")
        conn.close()
        return 1

    for table_name, expected_cols in EXPECTED_TABLES.items():
        if table_name in existing_tables:
            print(f"  {PASS}  Table '{table_name}' exists")

            # Check columns
            cur.execute(
                "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
                (table_name,),
            )
            columns = cur.fetchall()
            actual_col_names = [c[0] for c in columns]

            missing_cols = [c for c in expected_cols if c not in actual_col_names]
            if missing_cols:
                print(f"         {FAIL}  Missing columns: {', '.join(missing_cols)}")
                errors += 1
            else:
                print(f"         {PASS}  All {len(expected_cols)} expected columns present")

            # Print column details
            for col_name, data_type, nullable, max_len in columns:
                size = f"({max_len})" if max_len else ""
                null_flag = "NULL" if nullable == "YES" else "NOT NULL"
                marker = "  " if col_name in expected_cols else f"  {YELLOW}(extra){RESET} "
                print(f"           {marker}  {col_name:<20s} {data_type}{size:<12s}  {null_flag}")
        else:
            print(f"  {FAIL}  Table '{table_name}' is MISSING")
            errors += 1

    # Extra tables not in schema
    extra = existing_tables - set(EXPECTED_TABLES.keys())
    if extra:
        print(f"\n  {WARN}  Extra tables not in schema.sql: {', '.join(sorted(extra))}")

    # ── 6. Seed data check ─────────────────────────────────────────
    section("6. Seed data verification")
    seed_checks = [
        ("PrizeCategories", 3,  "categories (Minor, Major, Grand)"),
        ("Employees",       15, "employees"),
        ("Prizes",          6,  "prizes"),
    ]
    for table, expected_min, label in seed_checks:
        if table not in existing_tables:
            print(f"  {FAIL}  Cannot check {label} — table missing")
            errors += 1
            continue
        try:
            cur.execute(f"SELECT COUNT(*) FROM [{table}]")
            count = cur.fetchone()[0]
            if count >= expected_min:
                print(f"  {PASS}  {table}: {count} rows ({label})")
            elif count == 0:
                print(f"  {WARN}  {table}: 0 rows — seed data not loaded")
                print(f"         Run database/schema.sql to insert seed data.")
            else:
                print(f"  {WARN}  {table}: {count} rows (expected >={expected_min} from seed)")
        except Exception as exc:
            print(f"  {FAIL}  Error querying {table}: {exc}")
            errors += 1

    # Check RaffleWinners (may be empty — that's OK)
    if "RaffleWinners" in existing_tables:
        cur.execute("SELECT COUNT(*) FROM RaffleWinners")
        w_count = cur.fetchone()[0]
        print(f"  {INFO}  RaffleWinners: {w_count} rows (draw history)")

    conn.close()

    # ── Summary ────────────────────────────────────────────────────
    section("Summary")
    if errors == 0:
        print(f"\n  {GREEN}{BOLD}All checks passed!{RESET}")
        print(f"  Database '{DB_CONFIG.DATABASE}' on '{DB_CONFIG.SERVER}' is ready.\n")
        return 0
    else:
        print(f"\n  {RED}{BOLD}{errors} issue(s) found.{RESET}")
        print(f"  Review the errors above and fix before running the app.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
