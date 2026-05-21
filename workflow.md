# Raffle System — Full Workflow Documentation

> **Version:** 1.0.0  
> **Stack:** Python 3.11+, PySide6, SQL Server 2019 (SQLite fallback)  
> **Architecture:** N-Tier MVC with OOP and Modular Architecture

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [File Structure](#2-file-structure)
3. [Database Layer](#3-database-layer)
4. [Data Routing](#4-data-routing)
5. [Model Layer](#5-model-layer)
6. [Service Layer](#6-service-layer)
7. [Controller Layer](#7-controller-layer)
8. [View Layer](#8-view-layer)
9. [Loading Screens](#9-loading-screens)
10. [Prize Management Workflow](#10-prize-management-workflow)
11. [Draw Workflows](#11-draw-workflows)
12. [Winners View Workflow](#12-winners-view-workflow)
13. [Department Filtering Workflow](#13-department-filtering-workflow)
14. [Setup & Running](#14-setup--running)
15. [Configuration Reference](#15-configuration-reference)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                 Presentation Layer               │
│    MainWindow → DrawPanel / WinnersView          │
│    Loading Screens (Minor / Major / Grand)       │
├─────────────────────────────────────────────────┤
│               Controller Layer                   │
│           RaffleController (Qt Signals)          │
├─────────────────────────────────────────────────┤
│               Service Layer (BLL)                │
│              RaffleService                       │
├─────────────────────────────────────────────────┤
│           Model / Repository Layer               │
│  EmployeeRepository  PrizeRepository             │
│  WinnerRepository                                │
├─────────────────────────────────────────────────┤
│             Data Access Layer (DAL)              │
│              DatabaseManager                     │
├─────────────────────────────────────────────────┤
│                   Database                       │
│   SQL Server 2019  ──or──  SQLite (fallback)     │
└─────────────────────────────────────────────────┘
```

The system uses **N-Tier separation**:
- Views never touch repositories or raw SQL.
- Services contain all business rules (eligibility, draw counts, exclusion).
- Controllers translate Qt events into service calls and emit signals back to views.
- Repositories own all SQL; higher tiers see only Python dataclasses.

---

## 2. File Structure

```
raffle_system/
│
├── main.py                          # Entry point
├── requirements.txt
│
├── config/
│   ├── __init__.py
│   ├── database.py                  # DB connection config (SERVER, DATABASE, AUTH)
│   └── settings.py                  # App constants, colour palette
│
├── database/
│   ├── schema.sql                   # SQL Server DDL + seed data
│   └── raffle_demo.db               # Auto-created SQLite fallback
│
└── app/
    ├── __init__.py
    │
    ├── models/                      # Data Access Layer
    │   ├── __init__.py
    │   ├── database_manager.py      # Connection pool, query helpers
    │   ├── employee_model.py        # Employee entity + repository
    │   ├── prize_model.py           # Prize/PrizeCategory entity + repository
    │   └── winner_model.py          # Winner entity + repository
    │
    ├── services/                    # Business Logic Layer
    │   ├── __init__.py
    │   └── raffle_service.py        # Draw logic, eligibility, redraw
    │
    ├── controllers/                 # Presentation Controller Layer
    │   ├── __init__.py
    │   └── raffle_controller.py     # Qt signal bridge
    │
    ├── views/                       # Presentation Layer
    │   ├── __init__.py
    │   ├── main_window.py           # Application shell + tab layout
    │   │
    │   ├── components/
    │   │   ├── __init__.py
    │   │   ├── draw_panel.py        # Per-category draw UI (reused 3×)
    │   │   └── winners_view.py      # Grouped winners + recent section
    │   │
    │   ├── screens/
    │   │   ├── __init__.py
    │   │   ├── minor_loading_screen.py   # Staggered list reveal
    │   │   ├── major_loading_screen.py   # Large card reveal
    │   │   └── grand_loading_screen.py  # Slot machine character reveal
    │   │
    │   └── dialogs/
    │       ├── __init__.py
    │       └── add_prize_dialog.py  # Add prize modal
    │
    └── utils/
        ├── __init__.py
        ├── styles.py                # Global Qt stylesheet
        └── helpers.py               # show_error, confirm, badge_color
```

---

## 3. Database Layer

### Tables

| Table | Purpose |
|---|---|
| `Employees` | Master employee list (`EmpNo`, `EmpName`, `Department`) |
| `PrizeCategories` | Fixed tiers: Minor (1), Major (2), Grand (3) |
| `Prizes` | Prize slots with `Quantity` (number of winners per draw) |
| `RaffleWinners` | Audit log of every drawn winner, including redraws |
| `RaffleSession` | Optional: tracks the active session/event scope |

### Connection Strategy

```
config/database.py  →  DatabaseManager._test_connection()
    │
    ├─ pyodbc available?  →  Try SQL Server 2019
    │       Success  →  use SQL Server
    │       Failure  →  log warning
    │
    └─ USE_SQLITE_FALLBACK = True  →  create/open raffle_demo.db
```

**SQL Server (production):** Edit `config/database.py`:
```python
SERVER   = "your-server\\SQLEXPRESS"   # or IP:port
DATABASE = "RaffleSystemDB"
DRIVER   = "ODBC Driver 17 for SQL Server"
TRUSTED_CONNECTION = True              # Windows auth
# -- or --
TRUSTED_CONNECTION = False
USER     = "sa"
PASSWORD = "your-password"
```

**SQLite (demo/offline):** Set `USE_SQLITE_FALLBACK = True` (default).
The database file is created automatically at `database/raffle_demo.db`
with seed categories, employees, and prizes on first run.

---

## 4. Data Routing

Every database call follows this exact path — no shortcuts:

```
User Action (Qt event)
        │
        ▼
   DrawPanel / WinnersView   [View]
        │  calls method on
        ▼
  RaffleController            [Controller]
        │  calls method on
        ▼
   RaffleService              [Service / BLL]
        │  calls method on
        ▼
  *Repository                 [Model / DAL]
        │  calls
        ▼
  DatabaseManager.fetch_all() / execute()
        │  opens context-managed connection
        ▼
  SQL Server 2019  ──or──  SQLite
```

Results travel back up the same path.  
The controller emits a **Qt Signal** (`draw_completed`, `prizes_updated`, etc.)  
which the view connects to at startup — views never call the DB directly.

---

## 5. Model Layer

### `DatabaseManager` (Singleton)
- `get_connection()` — context manager; commits on clean exit, rolls back on error
- `fetch_all(sql, params)` → `list[dict]`
- `fetch_one(sql, params)` → `dict | None`
- `execute(sql, params)` → `int` (last insert id)

### `EmployeeRepository`
- `get_all_departments()` → `list[str]`
- `get_by_department(dept)` → `list[Employee]`
- `get_eligible(dept, exclude_emp_nos)` → `list[Employee]` *(Grand prize exclusion)*

### `PrizeRepository`
- `get_all_prizes()` → `list[Prize]`
- `get_prizes_by_category(name)` → `list[Prize]`
- `add_prize(category, name, quantity)` → `int` (PrizeID)
- `delete_prize(prize_id)` — soft delete (`IsActive = 0`)

### `WinnerRepository`
- `record_winner(prize_id, emp_no, dept, is_redraw)` → `int`
- `get_all_winners()` → `list[Winner]`
- `get_winners_by_category(category)` → `list[Winner]`
- `get_grand_winner_emp_nos()` → `list[str]` *(for exclusion)*
- `get_recent_winners(limit=30)` → `list[Winner]`

---

## 6. Service Layer

### `RaffleService.draw(prize_id, department, is_redraw)`

```
1. Fetch Prize record by prize_id
2. If category == Grand:
       excluded = WinnerRepository.get_grand_winner_emp_nos()
   Else:
       excluded = []
3. eligible = EmployeeRepository.get_eligible(department, excluded)
4. If eligible is empty → return DrawResult(error=...)
5. count = 1  (Grand)  OR  prize.quantity  (Minor/Major)
6. drawn = random.sample(eligible, min(count, len(eligible)))
7. For each drawn employee:
       WinnerRepository.record_winner(prize_id, emp_no, dept, is_redraw)
8. Return DrawResult(winners, prize, is_redraw)
```

Key business rules enforced here:
- **Grand prize** — always exactly 1 winner; previous Grand winners are excluded permanently.
- **Minor / Major** — draw `Quantity` winners simultaneously; no exclusion (unless redraw).
- **Redraw** — a fresh random draw; original records are kept for audit (`IsRedraw = 1`).

---

## 7. Controller Layer

`RaffleController` exposes these **Qt Signals**:

| Signal | Payload | Emitted when |
|---|---|---|
| `draw_completed` | `DrawResult` | Successful draw or redraw |
| `prizes_updated` | *(none)* | Prize added or deleted |
| `department_set` | `str` | Active department changes |
| `error_occurred` | `str` | Any error in service/model |

Views connect to signals in their `__init__`; they never call services directly.

---

## 8. View Layer

### `MainWindow`
Shell window with a 4-tab layout:
- **Minor** tab → `DrawPanel(CATEGORY_MINOR, controller)`
- **Major** tab → `DrawPanel(CATEGORY_MAJOR, controller)`
- **Grand** tab → `DrawPanel(CATEGORY_GRAND, controller)`
- **Winners** tab → `WinnersView(controller)`

### `DrawPanel`
Reusable component (instantiated once per category):
- Prize table (name, quantity, ID)
- Department combo box (filters the eligible pool)
- **Draw** button → `controller.start_draw(prize_id)`
- **Redraw** button *(Major / Grand only)* → `controller.start_redraw(prize_id)`
- Add / Remove prize buttons
- `QStackedWidget` to switch between control panel and loading screen

### `WinnersView`
- `QTabWidget` with Minor / Major / Grand sub-tabs
- Each sub-tab is a sortable `QTableWidget`
- Sort options: Draw Order / Name A–Z / Name Z–A
- Recent Winners section (bottom splitter panel, Top 30)

---

## 9. Loading Screens

Each screen is pushed onto `DrawPanel`'s `QStackedWidget` after a draw.

### Minor — `MinorLoadingScreen`
- List format, staggered reveal
- Each row: rank badge → name → EmpNo → department badge
- Rows appear one-by-one every **280 ms**
- Left border accent in **green**
- Scroll area accommodates large winner counts

### Major — `MajorLoadingScreen`
- Large card format (100 px height), fewer winners
- Circular number badge, trophy icon
- Cards appear one-by-one every **700 ms**
- **Blue** accent border

### Grand — `GrandLoadingScreen`
- Slot machine: one character of the EmpNo revealed per cell
- Each character revealed every **3 000 ms** (`SLOT_CHAR_INTERVAL_MS`)
- Example: `OJT26A02` → 8 ticks × 3 s = 24 s total animation
- After all characters: winner name, department, and confetti label appear
- **Gold** accent throughout

All screens have a **"← Back to Draw"** overlay button.

---

## 10. Prize Management Workflow

```
User clicks "＋ Add Prize"
        │
        ▼
AddPrizeDialog opens
  ┌ Category   (combo: Minor / Major / Grand)
  ├ Prize Name (text input)
  └ Quantity   (spin box, 1–100)
        │  dialog.accept()
        ▼
RaffleController.add_prize(category, name, quantity)
        │
        ▼
RaffleService.add_prize()
        │
        ▼
PrizeRepository.add_prize()  →  INSERT INTO Prizes
        │
        ▼
controller.prizes_updated signal → DrawPanel.refresh_prizes()
```

```
User selects row, clicks "✕ Remove"
        │
        ▼
confirm dialog
        │  confirmed
        ▼
RaffleController.delete_prize(prize_id)
        │
        ▼
PrizeRepository.delete_prize()  →  UPDATE IsActive = 0
        │
        ▼
prizes_updated signal → refresh_prizes()
```

---

## 11. Draw Workflows

### Standard Draw

```
User selects Prize row
User clicks "🎲 Draw [Category]"
        │
        ▼
DrawPanel._on_draw()
  → controller.start_draw(prize_id)
        │
        ▼
RaffleService.draw(prize_id, department, is_redraw=False)
  1. Load prize
  2. Build exclusion list (Grand only)
  3. Fetch eligible employees
  4. random.sample(eligible, count)
  5. WinnerRepository.record_winner() × count
  6. Return DrawResult
        │
        ▼
controller.draw_completed signal → DrawPanel._on_draw_completed(result)
        │
        ▼
DrawPanel._show_loading_screen(result)
  Minor → MinorLoadingScreen.start_reveal()   (staggered list)
  Major → MajorLoadingScreen.start_reveal()   (large cards)
  Grand → GrandLoadingScreen.start_reveal()   (slot machine)
```

### Redraw (Major / Grand only)

Same flow but `controller.start_redraw(prize_id)` is called.  
`is_redraw=True` is stored in `RaffleWinners.IsRedraw` for audit.  
Previous winner records are **not deleted**.

---

## 12. Winners View Workflow

```
User opens "📋 Winners" tab
        │
        ▼
WinnersView.__init__() → self.refresh()
        │
        ▼
For each category tab:
    controller.load_winners_by_category(cat)
    → WinnerRepository.get_winners_by_category()
    → populate QTableWidget

Recent Winners section:
    controller.load_recent_winners(30)
    → WinnerRepository.get_recent_winners(30)
    → populate bottom table
```

**Sorting:**
- "Draw Order" — default, newest first (ORDER BY DrawnAt DESC)
- "Name A–Z" — Python-side sort by emp_name ascending
- "Name Z–A" — Python-side sort descending

User can click "↻ Refresh" at any time to reload from DB.

---

## 13. Department Filtering Workflow

```
Application starts
        │
        ▼
DrawPanel.__init__()
  → controller.load_departments()
  → EmployeeRepository.get_all_departments()
  → SELECT DISTINCT Department FROM Employees
  → Populate QComboBox
        │
User selects department
        │
        ▼
QComboBox.currentTextChanged → controller.set_department(dept)
  → controller._department = dept
  → controller.department_set signal emitted
        │
On Draw:
        │
        ▼
RaffleService.draw(prize_id, department=controller._department)
  → EmployeeRepository.get_eligible(department, excluded)
  → SELECT * FROM Employees WHERE Department = ?  (AND NOT IN excluded)
```

Each draw is **exclusively from the selected department**.  
Switching departments mid-session is safe — the next draw picks up the new selection.

---

## 14. Setup & Running

### Prerequisites

```bash
# Python 3.11+
pip install -r requirements.txt
```

For SQL Server mode, install the ODBC driver:
- Windows: [Microsoft ODBC Driver 17 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Linux: `apt install unixodbc-dev msodbcsql17`

### Database Setup (SQL Server)

```sql
-- 1. Create database
CREATE DATABASE RaffleSystemDB;
USE RaffleSystemDB;

-- 2. Run schema
-- Execute contents of database/schema.sql
```

### Configuration

Edit `config/database.py`:
```python
SERVER              = "localhost\\SQLEXPRESS"
DATABASE            = "RaffleSystemDB"
TRUSTED_CONNECTION  = True      # Windows auth
USE_SQLITE_FALLBACK = False      # Disable demo mode
```

### Run

```bash
cd raffle_system
python main.py
```

For demo mode (no SQL Server needed), leave `USE_SQLITE_FALLBACK = True`.

---

## 15. Configuration Reference

### `config/database.py — DatabaseConfig`

| Field | Default | Description |
|---|---|---|
| `SERVER` | `localhost\\SQLEXPRESS` | SQL Server host / instance |
| `DATABASE` | `RaffleSystemDB` | Target database name |
| `DRIVER` | `ODBC Driver 17 for SQL Server` | pyodbc driver string |
| `TRUSTED_CONNECTION` | `True` | Windows auth vs SQL auth |
| `USER` | `""` | SQL auth username |
| `PASSWORD` | `""` | SQL auth password |
| `CONNECT_TIMEOUT` | `10` | Seconds before connection attempt fails |
| `USE_SQLITE_FALLBACK` | `True` | Auto-fallback to SQLite if SQL Server unreachable |
| `SQLITE_PATH` | `database/raffle_demo.db` | SQLite file location |

### `config/settings.py`

| Constant | Default | Description |
|---|---|---|
| `SLOT_CHAR_INTERVAL_MS` | `3000` | Grand prize: ms between each character reveal |
| `RECENT_WINNERS_LIMIT` | `30` | Max rows in Recent Winners section |
| `CATEGORY_MINOR/MAJOR/GRAND` | string literals | Must match DB seed values |

---

*End of Workflow Documentation*
