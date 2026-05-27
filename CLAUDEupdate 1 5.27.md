# Raffle System — Claude Agent Update Workflow

> **Base Version:** 1.0.0
> **Update Target:** 2.0.0
> **Stack:** Python 3.11+, PySide6, SQLAlchemy ORM, MSSQL (SQL Server 2019)
> **Architecture:** N-Tier MVC with OOP and Modular Architecture
> **Reference:** See `workflow.md` v1.0.0 for original baseline documentation.

---

## Table of Contents

1. [Update 1 — Core System Overhaul](#update-1--core-system-overhaul)
   - [1.1 SQLAlchemy Migration](#11-sqlalchemy-migration--sqlite-removal)
   - [1.2 Updated Table Names & Schema](#12-updated-table-names--schema)
   - [1.3 Prize Deduplication Logic](#13-prize-deduplication-logic)
   - [1.4 Winner Count — User-Defined](#14-winner-count--user-defined)
   - [1.5 All Employees (Whole Tip) Selection](#15-all-employees-whole-tip-selection)
   - [1.6 Minor/Major — Group-Based Prize Allocation](#16-minormajor--group-based-prize-allocation)
   - [1.7 Grand Prize — Building Groups & Confirm/Redraw Flow](#17-grand-prize--building-groups--confirmredraw-flow)
   - [1.8 Grand Prize Reset](#18-grand-prize-reset)
   - [1.9 UI Animations](#19-ui-animations)
2. [Debugging Checkpoint](#debugging-checkpoint)
3. [Update 2 — Event Mode, Admin Panel & Extended Features](#update-2--event-mode-admin-panel--extended-features)
   - [2.1 Drawing Mode Selection: Department vs Event](#21-drawing-mode-selection-department-vs-event)
   - [2.2 Event Mode — CSV Participant Import](#22-event-mode--csv-participant-import)
   - [2.3 Live Participant List During Event](#23-live-participant-list-during-event)
   - [2.4 Secret Admin Dev Mode](#24-secret-admin-dev-mode)
   - [2.5 Admin Panel Features](#25-admin-panel-features)
4. [Updated File Structure](#updated-file-structure)
5. [Updated Data Routing](#updated-data-routing)
6. [Updated Database Layer](#updated-database-layer)
7. [Updated Configuration Reference](#updated-configuration-reference)

---

## Update 1 — Core System Overhaul

### 1.1 SQLAlchemy Migration & SQLite Removal

**Goal:** Remove the dual-DB fallback entirely. Use SQLAlchemy ORM exclusively with MSSQL. Centralize all DB routing so connection details are easy to swap in one place.

**What to delete:**
- `database/raffle_demo.db` — remove file and any seed/creation logic
- All `USE_SQLITE_FALLBACK` logic in `config/database.py` and `DatabaseManager`
- Any `sqlite3` imports or conditional branches in `database_manager.py`

**What to create/replace:**

`config/database.py` — single source of truth for DB config:
```python
# config/database.py
# ─────────────────────────────────────────────
# ONLY edit this file to change DB connection.
# ─────────────────────────────────────────────

SERVER   = "your-server\\SQLEXPRESS"   # or IP:1433
DATABASE = "RaffleSystemDB"
DRIVER   = "ODBC+Driver+17+for+SQL+Server"

# Auth — choose one:
TRUSTED_CONNECTION = True     # Windows auth (set USER/PASSWORD to "")
USER     = ""
PASSWORD = ""

# Derived connection string (do NOT edit below this line)
def get_connection_url() -> str:
    if TRUSTED_CONNECTION:
        return (
            f"mssql+pyodbc://{SERVER}/{DATABASE}"
            f"?driver={DRIVER}&trusted_connection=yes"
        )
    return (
        f"mssql+pyodbc://{USER}:{PASSWORD}@{SERVER}/{DATABASE}"
        f"?driver={DRIVER}"
    )
```

`app/models/database_manager.py` — SQLAlchemy engine/session setup:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.database import get_connection_url

engine = create_engine(get_connection_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_session():
    """Context-managed session. Use with `with get_session() as session:`"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

All repositories must use `get_session()` — no raw `pyodbc` connections anywhere.

---

### 1.2 Updated Table Names & Schema

Rename all tables to match the new naming convention (underscore-prefixed):

| Old Name | New Name |
|---|---|
| `Employees` | `_Employees` |
| `PrizeCategories` | `_PrizeCategories` |
| `Prizes` | `_Prizes` |
| `RaffleWinners` | `_RaffleWinners` |

Add new tables:

| New Table | Purpose |
|---|---|
| `_Groups` | Named groupings of departments (for Minor/Major allocation and Grand building groups) |
| `_GroupDepartments` | Junction: which departments belong to which group |
| `_Events` | Named raffle events with optional participant scope |
| `_EventParticipants` | Employees linked to a specific event |
| `_AdminAuditLog` | Audit trail for admin/dev mode changes |

**SQLAlchemy ORM Models** (place in `app/models/orm_models.py`):

```python
# Abbreviated — implement all columns per original schema.sql, using new names.

class Employee(Base):
    __tablename__ = "_Employees"
    EmpNo      = Column(String(20), primary_key=True)
    EmpName    = Column(String(100), nullable=False)
    Department = Column(String(100), nullable=False)

class PrizeCategory(Base):
    __tablename__ = "_PrizeCategories"
    CategoryID   = Column(Integer, primary_key=True)
    CategoryName = Column(String(50), nullable=False)   # Minor | Major | Grand

class Prize(Base):
    __tablename__ = "_Prizes"
    PrizeID      = Column(Integer, primary_key=True, autoincrement=True)
    CategoryID   = Column(Integer, ForeignKey("_PrizeCategories.CategoryID"))
    PrizeName    = Column(String(100), nullable=False)
    WinnerCount  = Column(Integer, default=1)   # renamed from Quantity — user-defined
    IsActive     = Column(Boolean, default=True)

class RaffleWinner(Base):
    __tablename__ = "_RaffleWinners"
    WinnerID    = Column(Integer, primary_key=True, autoincrement=True)
    PrizeID     = Column(Integer, ForeignKey("_Prizes.PrizeID"))
    EmpNo       = Column(String(20), ForeignKey("_Employees.EmpNo"))
    Department  = Column(String(100))
    DrawnAt     = Column(DateTime, default=datetime.utcnow)
    IsRedraw    = Column(Boolean, default=False)
    IsConfirmed = Column(Boolean, default=False)   # Grand prize only
    EventID     = Column(Integer, ForeignKey("_Events.EventID"), nullable=True)

class Group(Base):
    __tablename__ = "_Groups"
    GroupID     = Column(Integer, primary_key=True, autoincrement=True)
    GroupName   = Column(String(100), nullable=False)
    BuildingTag = Column(String(10), nullable=True)  # 'LTI' | 'CIP' | None
    AllocatedPrizes = Column(Integer, default=0)    # for Minor/Major group allocation

class GroupDepartment(Base):
    __tablename__ = "_GroupDepartments"
    ID           = Column(Integer, primary_key=True, autoincrement=True)
    GroupID      = Column(Integer, ForeignKey("_Groups.GroupID"))
    Department   = Column(String(100), nullable=False)

class Event(Base):
    __tablename__ = "_Events"
    EventID    = Column(Integer, primary_key=True, autoincrement=True)
    EventName  = Column(String(150), nullable=False)
    CreatedAt  = Column(DateTime, default=datetime.utcnow)
    IsActive   = Column(Boolean, default=True)

class EventParticipant(Base):
    __tablename__ = "_EventParticipants"
    ID       = Column(Integer, primary_key=True, autoincrement=True)
    EventID  = Column(Integer, ForeignKey("_Events.EventID"))
    EmpNo    = Column(String(20), ForeignKey("_Employees.EmpNo"))

class AdminAuditLog(Base):
    __tablename__ = "_AdminAuditLog"
    LogID       = Column(Integer, primary_key=True, autoincrement=True)
    AdminName   = Column(String(100), nullable=False)
    ChangesMade = Column(Text, nullable=False)
    ChangedAt   = Column(DateTime, default=datetime.utcnow)
```

---

### 1.3 Prize Deduplication Logic

**Rule:** If a prize with the same `CategoryID` and `PrizeName` already exists (and `IsActive = True`), do not insert a duplicate — instead, add the new `WinnerCount` to the existing record.

**Service logic in `RaffleService.add_prize(category, name, winner_count)`:**

```
1. Query _Prizes WHERE CategoryID = category AND PrizeName = name AND IsActive = True
2. If exists:
       existing.WinnerCount += winner_count
       session.commit()
       emit prizes_updated
       return existing.PrizeID
3. Else:
       INSERT new Prize row
       emit prizes_updated
       return new PrizeID
```

**UI change in `AddPrizeDialog`:**
- Rename "Quantity" label → **"Number of Winners"**
- After submission, if deduplicated, show a toast/info: `"Added to existing prize '{name}' — total winners: {new_count}"`

---

### 1.4 Winner Count — User-Defined

**Rule:** The number of winners for any draw is now set by the user at draw time, **not** derived from prize quantity. The only constraint: must be ≥ 1 and ≤ number of eligible employees.

**UI change in `DrawPanel`:**
- Add a **`QSpinBox`** labeled `"Winners to draw:"` beside the Draw button. Default: 1. Min: 1. Max: dynamically set to `len(eligible_pool)` when a prize is selected.
- Pass this value as `winner_count` to `controller.start_draw(prize_id, winner_count)`.

**Service change in `RaffleService.draw()`:**
```
# Old:
count = 1 if Grand else prize.WinnerCount

# New:
count = user_supplied_winner_count  # passed from controller
# Validate: 1 ≤ count ≤ len(eligible)
```

> **Note:** The `WinnerCount` column on `_Prizes` is now informational/default only. The draw logic uses the runtime user input.

---

### 1.5 All Employees (Whole Tip) Selection

**Rule:** A "Whole Tip" option in the department selector draws from **all employees** regardless of department. This ignores group assignments for the pool — it's a flat pool of everyone eligible.

**UI change in `DrawPanel`:**
- Add **"🏢 All Employees (Whole Tip)"** as the first/default entry in the department `QComboBox`.

**Service change:**
```python
if department == "ALL":
    eligible = session.query(Employee).all()
else:
    eligible = session.query(Employee).filter(Employee.Department == department).all()
```

- For Grand prize, previously-confirmed Grand winners are still excluded even under "All Employees".

---

### 1.6 Minor/Major — Group-Based Prize Allocation

**Goal:** Support grouped draws where prizes are allocated evenly across groups — the process is hidden from the audience; only winners appear.

**Admin setup (via Admin Panel, see 2.5):**
- Admin creates groups: e.g., `Group 1 = [ISD, HR]`, `Group 2 = [LOD, SPD]`
- Admin assigns `AllocatedPrizes` to each group: e.g., 5 prizes each out of 10 total.

**Draw flow (hidden from main UI — runs silently in service layer):**

```
RaffleService.draw_grouped(prize_id, winner_count, mode='group')

For each Group:
    1. pool = all eligible employees whose Department ∈ Group.departments
    2. group_count = Group.AllocatedPrizes  (pre-set by admin)
    3. drawn = random.sample(pool, min(group_count, len(pool)))
    4. Record each winner: RaffleWinner(PrizeID, EmpNo, ..., IsConfirmed=True)

Return all winners across all groups combined → loading screen reveals them
```

- The split per group is **not shown** in the winner announcement — all winners are revealed together in the standard loading screen animation.
- Groups and their allocations are configured in Admin Panel and stored in `_Groups` + `_GroupDepartments`.

---

### 1.7 Grand Prize — Building Groups & Confirm/Redraw Flow

**Grand prize building groups:**
- Two groups: **LTI** and **CIP** (set via `BuildingTag` on `_Groups`).
- Default allocation: 1 winner from LTI, 2 winners from CIP.
- This allocation is admin-configurable.

**Draw flow:**
```
RaffleService.draw_grand(prize_id, winner_count_per_building)

For LTI group:
    pool = eligible employees with dept in LTI building group
    drawn_LTI = random.sample(pool, lti_count)

For CIP group:
    pool = eligible employees with dept in CIP building group
    drawn_CIP = random.sample(pool, cip_count)

All drawn → GrandLoadingScreen (slot machine reveal, one employee at a time)
# Winners are NOT recorded yet at this point
```

**Confirm/Redraw UI (shown after Grand loading screen):**

After the slot machine finishes revealing each winner:
- Show a **confirmation panel** (replaces or overlays the loading screen):
  ```
  ┌─────────────────────────────────────────────┐
  │  🏆 GRAND PRIZE WINNER                       │
  │  [Name]  —  [Dept]  —  [EmpNo]              │
  │                                             │
  │   [ ↻ Re-draw ]       [ ✓ Confirm Win ]     │
  └─────────────────────────────────────────────┘
  ```
- **Confirm Win** → calls `RaffleService.confirm_grand_winner(emp_no, prize_id)` → inserts record with `IsConfirmed = True`
- **Re-draw** → discards the pending result (no DB write), runs `draw_grand()` again, reveals new winner via slot machine

**Service:**
```python
# Pending winners are held in memory (controller state) until confirmed.
# Only on confirm:
WinnerRepository.record_winner(..., IsConfirmed=True)
```

---

### 1.8 Grand Prize Reset

**Purpose:** Reset the eligibility exclusion so previously-confirmed Grand winners can participate again (e.g., new event year).

**Location:** Admin Panel (see 2.5) and optionally a button in the Grand draw tab (visible to all or admin-only — decide per deployment).

**Service:**
```python
def reset_grand_eligibility(self):
    """Set IsConfirmed = False for all Grand prize winners, restoring eligibility."""
    session.query(RaffleWinner)\
        .join(Prize).join(PrizeCategory)\
        .filter(PrizeCategory.CategoryName == 'Grand', RaffleWinner.IsConfirmed == True)\
        .update({RaffleWinner.IsConfirmed: False})
    session.commit()
```

- In `EmployeeRepository.get_eligible()` for Grand: only exclude where `IsConfirmed = True`.

---

### 1.9 UI Animations

Enhance existing and add new animations:

| Screen | Enhancement |
|---|---|
| `MinorLoadingScreen` | Add slide-in from left per row + subtle fade. Keep 280 ms stagger. |
| `MajorLoadingScreen` | Add card flip (Y-axis CSS/Qt transform) before showing winner name. Keep 700 ms. |
| `GrandLoadingScreen` | Add particle burst (confetti) on final reveal. Gold shimmer pulse on winner card. |
| `DrawPanel` | Add a brief button pulse animation when "Draw" is clicked before transitioning. |
| General | Add smooth `QPropertyAnimation` transitions when switching `QStackedWidget` pages. |
| Confirm/Redraw panel | Animate in from bottom with a slide-up + fade when grand reveal finishes. |

All animation durations should be constants in `config/settings.py` so they're easy to tune.

---

## Debugging Checkpoint

> **Before starting Update 2, fully test and stabilize Update 1.**

Checklist for the agent to verify before proceeding:

- [ ] SQLAlchemy sessions open, commit, and rollback correctly for all repository methods
- [ ] No `sqlite3`, `USE_SQLITE_FALLBACK`, or `pyodbc` raw connection code remains
- [ ] All four table renames (`_Employees`, `_PrizeCategories`, `_Prizes`, `_RaffleWinners`) applied in ORM models and all query references
- [ ] Adding an existing prize name → increments `WinnerCount`, no duplicate row
- [ ] Adding a new prize name → inserts new row correctly
- [ ] Winner count spinbox passes value correctly through controller → service → draw
- [ ] "All Employees" selection draws from full pool; Grand exclusion still applies
- [ ] Group-based Minor/Major draw splits pool correctly per `AllocatedPrizes` without revealing the split in UI
- [ ] Grand prize slot machine runs; winner is NOT in DB until Confirm is clicked
- [ ] Re-draw on Grand clears pending state and runs a fresh draw
- [ ] Grand reset marks all confirmed grand winners as eligible again
- [ ] All animations play without freezing the UI thread (use `QTimer` / `QThread` where needed)

---

## Update 2 — Event Mode, Admin Panel & Extended Features

> **Only begin this section after the Debugging Checkpoint above passes.**

---

### 2.1 Drawing Mode Selection: Department vs Event

**On app launch (or via a top-level toggle):** Show a mode selection screen before the main draw UI.

**UI — Mode Selection Dialog / Screen:**
```
┌─────────────────────────────────────────────────────┐
│              SELECT DRAWING MODE                    │
│                                                     │
│   [ 🏢 Department Mode ]   [ 🎉 Event Mode ]         │
└─────────────────────────────────────────────────────┘
```

**Department Mode:** Identical to v1.0 behaviour — department combo box with "All Employees" option. No event context.

**Event Mode:**
- Show a dropdown of active `_Events`.
- If no events exist or no groups are configured: show a message: `"No event configured. Contact your admin for group designation."`
- Draw pool is scoped to `_EventParticipants` for the selected event.

Store the selected mode + event in `RaffleController` state. Pass to service on every draw call.

---

### 2.2 Event Mode — CSV Participant Import

**Step-by-step wizard UI (QWizard or custom QStackedWidget):**

**Step 1 — Event Details:**
```
┌─────────────────────────────────────────────┐
│  New Event Setup                            │
│  Event Name: [_________________________]    │
│                                             │
│               [ Next → ]                   │
└─────────────────────────────────────────────┘
```

**Step 2 — Upload Participants:**
```
┌────────────────────────────────────────────────────────┐
│  Upload Participant List                               │
│                                                        │
│  Download CSV Template: [ ⬇ template.csv ]             │
│  (EmpNo, EmpName, Department)                          │
│                                                        │
│  [ 📂 Choose CSV File ]                                │
│  Selected: participants.csv  ✓                         │
│                                                        │
│  Preview (first 5 rows):                               │
│  ┌──────────┬──────────────┬────────────┐              │
│  │ EmpNo    │ EmpName      │ Department │              │
│  │ OJT26A01 │ Juan Dela... │ ISD        │              │
│  │ ...      │ ...          │ ...        │              │
│  └──────────┴──────────────┴────────────┘              │
│  Parsed: 45 employees                                  │
│                                                        │
│  [ ← Back ]              [ Next → ]                   │
└────────────────────────────────────────────────────────┘
```

**Step 3 — Confirm & Link:**
```
┌───────────────────────────────────────────────────────┐
│  Confirm Event                                        │
│  Event Name:    Annual Raffle 2025                    │
│  Participants:  45 employees                          │
│  Departments:   ISD, HR, LOD, SPD, CIP               │
│                                                       │
│  [ ← Back ]         [ ✓ Create Event & Start ]       │
└───────────────────────────────────────────────────────┘
```

**CSV parsing logic:**
```python
# In EventService.import_csv(filepath, event_id):
# 1. Parse CSV with csv.DictReader, expected columns: EmpNo, EmpName, Department
# 2. For each row:
#    a. Upsert into _Employees (insert if not exists, update name/dept if exists)
#    b. Insert into _EventParticipants (EventID, EmpNo) — skip if already linked
# 3. Return summary: {total, inserted, updated, skipped, errors[]}
```

**CSV Template download:** Provide a static `assets/participant_template.csv` and wire the "Download Template" button to copy it to a user-chosen path.

---

### 2.3 Live Participant List During Event

In Event Mode, add a **"👥 Participants"** tab (or side panel) visible while the event is active:

- Shows a searchable `QTableWidget` of all `_EventParticipants` for the active event.
- Columns: EmpNo | EmpName | Department | Won? (Yes/No based on `_RaffleWinners`)
- **Refresh** button to reload.
- **Purpose:** Emcee/operator can verify who is included and check if someone has already won.

---

### 2.4 Secret Admin Dev Mode

**Trigger:** Global keyboard shortcut `Ctrl+Shift+X` (registered on `MainWindow`).

**Behavior:**
1. Change window title to `"RAFFLE SYSTEM — ⚠ DEV MODE"`.
2. Show a login dialog:

```
┌──────────────────────────────────────────┐
│  🔐 Admin Access                         │
│                                          │
│  Admin Name: [______________________]    │
│  Password:   [••••••••••••••••••••••]   │
│                                          │
│  [ Cancel ]          [ Enter Dev Mode ]  │
└──────────────────────────────────────────┘
```

- Password is a **hardcoded string in `config/admin.py`** (not in DB). Example:
  ```python
  ADMIN_PASSWORD = "raffle@dev2025"
  ```
- Name field is free-text (any admin name — used for audit).
- On success: open `AdminPanel` window.
- On failure: show error, allow retry.

**Audit logging (all admin actions write to `_AdminAuditLog`):**
```python
AdminAuditLog(
    AdminName   = entered_name,
    ChangesMade = "Created group: Group1 (ISD, HR)",
    ChangedAt   = datetime.utcnow()
)
```

All `AdminPanel` actions must call `AdminAuditService.log(admin_name, description)` before committing the change.

This is a hidden background process — no visible audit log in the main UI.

---

### 2.5 Admin Panel Features

`AdminPanel` is a separate `QDialog` (modal) opened only from Dev Mode login.

#### Feature 1 — Department Grouping

```
┌──────────────────────────────────────────────────────────┐
│  Admin Panel — Group Management                          │
│                                                          │
│  Groups:                    Departments in Group:        │
│  ┌──────────────────┐       ┌──────────────────────┐    │
│  │ Group 1 (Minor)  │  →    │ ISD                  │    │
│  │ Group 2 (Minor)  │       │ HR                   │    │
│  │ LTI Building     │       └──────────────────────┘    │
│  │ CIP Building     │                                    │
│  └──────────────────┘                                    │
│                                                          │
│  [ + New Group ]  [ ✏ Edit ]  [ 🗑 Delete ]              │
│                                                          │
│  Allocated Prizes per Group:                             │
│  Group 1: [ 5 ▲▼ ]    Group 2: [ 5 ▲▼ ]                │
│                                                          │
│  Grand Building Tags:                                    │
│  LTI Winners: [ 1 ▲▼ ]    CIP Winners: [ 2 ▲▼ ]        │
│                                                          │
│  [ Save Changes ]                                        │
└──────────────────────────────────────────────────────────┘
```

**Service: `AdminService.save_groups(groups_payload)`**
- Upsert `_Groups` rows.
- Rebuild `_GroupDepartments` for each group (delete existing, reinsert).
- Log audit: `"Updated group assignments: ..."`

#### Feature 2 — Win Chance Weighting

Allows admin to increase the probability of an employee or department winning by adding them multiple times to the draw pool (weighted sampling).

```
┌──────────────────────────────────────────────────────────┐
│  Admin Panel — Win Chance Boost                          │
│                                                          │
│  Search Employee: [_________________]  [ 🔍 ]            │
│  ┌──────────────────────────────────────────────────┐    │
│  │ OJT26A01  │ Juan Dela Cruz  │ ISD  │ Boost: [3] │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  Department Boost:                                       │
│  ISD: [1 ▲▼]   HR: [2 ▲▼]   LOD: [1 ▲▼]               │
│                                                          │
│  [ Save Boosts ]                                         │
└──────────────────────────────────────────────────────────┘
```

**Implementation:**
- Add `WinChanceMultiplier` column (Integer, default 1) to `_Employees`.
- Add `DeptWinChanceMultiplier` column to a new `_DepartmentSettings` table.
- In `EmployeeRepository.get_eligible()`, repeat each employee in the pool `WinChanceMultiplier × DeptMultiplier` times before calling `random.sample()`.
- Admin setting is persisted to DB; audit log records: `"Boosted EmpNo OJT26A01 to 3x, Dept HR to 2x"`

---

## Updated File Structure

```
raffle_system/
│
├── main.py
├── requirements.txt
│
├── config/
│   ├── __init__.py
│   ├── database.py           # MSSQL-only config + get_connection_url()
│   ├── settings.py           # Animation constants, limits, category names
│   └── admin.py              # ADMIN_PASSWORD (hardcoded, not in DB)
│
├── assets/
│   └── participant_template.csv   # CSV template for event participant import
│
├── database/
│   └── schema.sql            # SQLAlchemy-compatible DDL for all _Tables
│
└── app/
    ├── __init__.py
    │
    ├── models/
    │   ├── __init__.py
    │   ├── database_manager.py    # SQLAlchemy engine, SessionLocal, get_session()
    │   ├── orm_models.py          # All ORM table definitions (_Employees, etc.)
    │   ├── employee_repository.py
    │   ├── prize_repository.py
    │   ├── winner_repository.py
    │   ├── group_repository.py    # NEW: _Groups, _GroupDepartments
    │   ├── event_repository.py    # NEW: _Events, _EventParticipants
    │   └── admin_repository.py    # NEW: _AdminAuditLog, _DepartmentSettings
    │
    ├── services/
    │   ├── __init__.py
    │   ├── raffle_service.py      # draw(), draw_grouped(), draw_grand(), confirm_grand(), reset_grand()
    │   ├── event_service.py       # NEW: create_event(), import_csv(), get_participants()
    │   └── admin_service.py       # NEW: save_groups(), save_boosts(), log()
    │
    ├── controllers/
    │   ├── __init__.py
    │   ├── raffle_controller.py   # Updated signals + mode state (Department/Event)
    │   └── admin_controller.py    # NEW: admin panel controller
    │
    ├── views/
    │   ├── __init__.py
    │   ├── main_window.py         # Updated: mode selector on launch, Ctrl+Shift+X handler
    │   │
    │   ├── components/
    │   │   ├── __init__.py
    │   │   ├── draw_panel.py          # Updated: winner count spinbox, All Employees option
    │   │   ├── winners_view.py
    │   │   └── participants_panel.py  # NEW: live participant list for Event mode
    │   │
    │   ├── screens/
    │   │   ├── __init__.py
    │   │   ├── mode_select_screen.py       # NEW: Department vs Event selection
    │   │   ├── minor_loading_screen.py     # Updated animations
    │   │   ├── major_loading_screen.py     # Updated animations
    │   │   └── grand_loading_screen.py     # Updated animations + confirm/redraw panel
    │   │
    │   ├── dialogs/
    │   │   ├── __init__.py
    │   │   ├── add_prize_dialog.py         # Updated: "Number of Winners" label
    │   │   ├── admin_login_dialog.py       # NEW: Dev mode login
    │   │   ├── admin_panel.py              # NEW: group management + win chance UI
    │   │   └── event_wizard.py             # NEW: multi-step event creation wizard
    │   │
    │   └── grand_confirm_panel.py          # NEW: confirm/redraw overlay for Grand prize
    │
    └── utils/
        ├── __init__.py
        ├── styles.py
        └── helpers.py          # Updated: toast notification helper, CSV export helper
```

---

## Updated Data Routing

```
User Action (Qt event)
        │
        ▼
   View / Dialog / Screen
        │  calls method on
        ▼
  Controller (Raffle / Admin)       ← holds mode state (Dept/Event), pending Grand winner
        │  calls method on
        ▼
   Service (Raffle / Event / Admin) ← all business rules, grouping logic, weighting
        │  calls method on
        ▼
  Repository (*_repository.py)      ← all SQLAlchemy ORM queries, no raw SQL
        │  uses
        ▼
  get_session() → SQLAlchemy engine
        │
        ▼
  SQL Server 2019 (MSSQL only — no fallback)
```

Signal table additions:

| Signal | Payload | Emitted when |
|---|---|---|
| `draw_completed` | `DrawResult` | Successful draw or redraw |
| `grand_pending` | `list[Employee]` | Grand draw ran, awaiting confirmation |
| `grand_confirmed` | `WinnerRecord` | Grand winner confirmed and saved |
| `prizes_updated` | *(none)* | Prize added, modified, or deleted |
| `department_set` | `str` | Active department changes |
| `mode_changed` | `str` | `'department'` or `'event'` |
| `event_set` | `Event` | Active event selected |
| `error_occurred` | `str` | Any error in service/model |

---

## Updated Database Layer

### Connection (MSSQL only)

```
config/database.py  →  get_connection_url()
        │
        ▼
database_manager.py  →  create_engine(url, pool_pre_ping=True)
        │
        ▼
SessionLocal()  →  used by all repositories via get_session()
```

No fallback. If SQL Server is unreachable, the app raises a clear startup error with the connection string printed (minus password) for diagnosis.

### Tables Summary

| Table | Key Columns |
|---|---|
| `_Employees` | EmpNo (PK), EmpName, Department, WinChanceMultiplier |
| `_PrizeCategories` | CategoryID (PK), CategoryName |
| `_Prizes` | PrizeID (PK), CategoryID (FK), PrizeName, WinnerCount, IsActive |
| `_RaffleWinners` | WinnerID (PK), PrizeID (FK), EmpNo (FK), DrawnAt, IsRedraw, IsConfirmed, EventID (FK nullable) |
| `_Groups` | GroupID (PK), GroupName, BuildingTag, AllocatedPrizes |
| `_GroupDepartments` | ID (PK), GroupID (FK), Department |
| `_Events` | EventID (PK), EventName, CreatedAt, IsActive |
| `_EventParticipants` | ID (PK), EventID (FK), EmpNo (FK) |
| `_AdminAuditLog` | LogID (PK), AdminName, ChangesMade, ChangedAt |
| `_DepartmentSettings` | DeptName (PK), WinChanceMultiplier |

---

## Updated Configuration Reference

### `config/database.py`

| Field | Description |
|---|---|
| `SERVER` | SQL Server host/instance |
| `DATABASE` | Target DB name |
| `DRIVER` | pyodbc driver string (URL-encoded in `get_connection_url()`) |
| `TRUSTED_CONNECTION` | True = Windows auth |
| `USER` / `PASSWORD` | SQL auth credentials (if `TRUSTED_CONNECTION = False`) |
| `get_connection_url()` | Returns full SQLAlchemy connection string — only place to edit for DB changes |

### `config/settings.py`

| Constant | Default | Description |
|---|---|---|
| `SLOT_CHAR_INTERVAL_MS` | `3000` | Grand: ms per character reveal |
| `MINOR_ROW_INTERVAL_MS` | `280` | Minor: ms between row reveals |
| `MAJOR_CARD_INTERVAL_MS` | `700` | Major: ms between card reveals |
| `RECENT_WINNERS_LIMIT` | `30` | Max rows in Recent Winners |
| `CATEGORY_MINOR/MAJOR/GRAND` | string literals | Must match `_PrizeCategories.CategoryName` |
| `DEFAULT_LTI_WINNERS` | `1` | Grand: default LTI allocation |
| `DEFAULT_CIP_WINNERS` | `2` | Grand: default CIP allocation |

### `config/admin.py`

| Constant | Description |
|---|---|
| `ADMIN_PASSWORD` | Hardcoded Dev Mode password. Change directly in source. Not stored in DB. |

---

*End of Update Workflow — CLAUDE.md v2.0.0*
