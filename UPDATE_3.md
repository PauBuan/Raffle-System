# Raffle System — Update 3 Workflow

> **From Version:** 2.0.0
> **Update Target:** 3.0.0
> **Depends on:** `workflow.md` (v1.0.0) + `CLAUDE.md` (v2.0.0) fully implemented and stable
> **Stack:** Python 3.11+, PySide6, SQLAlchemy ORM, MSSQL (SQL Server 2019)

---

## Table of Contents

1. [3.1 Database — Add `Building` Column to `_Employees`](#31-database--add-building-column-to-_employees)
2. [3.2 Group Status — NOT SET vs READY FOR DRAWING](#32-group-status--not-set-vs-ready-for-drawing)
3. [3.3 Group Drawing Scoped to Event Mode Only](#33-group-drawing-scoped-to-event-mode-only)
4. [3.4 Admin Panel — Group Allocation Logs](#34-admin-panel--group-allocation-logs)
5. [3.5 Event Mode — Rework (No CSV, Pull from `_Employees`)](#35-event-mode--rework-no-csv-pull-from-_employees)
6. [3.6 Drawing Mode Clarification — All Three Modes Defined](#36-drawing-mode-clarification--all-three-modes-defined)
7. [3.7 New Mode — DIY Mode](#37-new-mode--diy-mode)
8. [3.8 Mode Select Screen — Updated UI](#38-mode-select-screen--updated-ui)
9. [3.9 File & Schema Changes Summary](#39-file--schema-changes-summary)
10. [Debugging Checklist — Update 3](#debugging-checklist--update-3)

---

## 3.1 Database — Add `Building` Column to `_Employees`

**Reason:** The group/building bias logic in the admin panel (LTI vs CIP) needs a direct column on the employee record so queries can filter by building without joining through department mappings. This is the authoritative source for building assignment.

### Schema Change

Add `Building` column to `_Employees`:

```sql
ALTER TABLE _Employees
ADD Building NVARCHAR(10) NOT NULL DEFAULT 'LTI'
    CONSTRAINT CHK_Building CHECK (Building IN ('LTI', 'CIP'));
```

Allowed values: **`LTI`** or **`CIP`** — no others. Enforce at DB level with `CHECK` constraint and at ORM level with a validator.

### ORM Model Update (`app/models/orm_models.py`)

```python
from sqlalchemy.orm import validates

class Employee(Base):
    __tablename__ = "_Employees"
    EmpNo              = Column(String(20), primary_key=True)
    EmpName            = Column(String(100), nullable=False)
    Department         = Column(String(100), nullable=False)
    Building           = Column(String(10),  nullable=False, default='LTI')  # NEW
    WinChanceMultiplier = Column(Integer, default=1)

    @validates('Building')
    def validate_building(self, key, value):
        if value not in ('LTI', 'CIP'):
            raise ValueError(f"Building must be 'LTI' or 'CIP', got: {value!r}")
        return value
```

### Repository Update (`app/models/employee_repository.py`)

All existing queries that build an eligible pool must now be able to filter by `Building` when in Event Mode group draws:

```python
def get_eligible_by_building(
    self,
    building: str,
    exclude_emp_nos: list[str] = []
) -> list[Employee]:
    with get_session() as session:
        q = session.query(Employee).filter(Employee.Building == building)
        if exclude_emp_nos:
            q = q.filter(Employee.EmpNo.notin_(exclude_emp_nos))
        return q.all()

def get_eligible_by_department(
    self,
    department: str,
    exclude_emp_nos: list[str] = []
) -> list[Employee]:
    # unchanged from Update 2, kept for Department Mode
    ...

def get_all_eligible(self, exclude_emp_nos: list[str] = []) -> list[Employee]:
    # for Whole Tip / all-company draws
    ...
```

### Seeding / Migration Note

When running the migration on an existing DB, existing employees should be assigned a default Building value. Provide a one-time migration script:

```sql
-- database/migrations/003_add_building.sql
ALTER TABLE _Employees ADD Building NVARCHAR(10) NOT NULL DEFAULT 'LTI';
ALTER TABLE _Employees ADD CONSTRAINT CHK_Building CHECK (Building IN ('LTI','CIP'));
-- Admin must then manually update CIP employees via admin panel or direct SQL.
```

---

## 3.2 Group Status — NOT SET vs READY FOR DRAWING

**Reason:** Prevent a draw from proceeding under group/event mode if the admin hasn't finalized group assignments. The system needs to know whether the admin has committed and confirmed the groupings.

### Schema Change

Add `Status` column to `_Groups`:

```sql
ALTER TABLE _Groups
ADD Status NVARCHAR(20) NOT NULL DEFAULT 'NOT SET'
    CONSTRAINT CHK_GroupStatus CHECK (Status IN ('NOT SET', 'READY FOR DRAWING'));
```

### ORM Model Update

```python
class Group(Base):
    __tablename__ = "_Groups"
    GroupID          = Column(Integer, primary_key=True, autoincrement=True)
    GroupName        = Column(String(100), nullable=False)
    BuildingTag      = Column(String(10), nullable=True)   # 'LTI' | 'CIP' | None
    AllocatedPrizes  = Column(Integer, default=0)
    Status           = Column(String(20), nullable=False, default='NOT SET')  # NEW
```

### Status Transition Rules

| Action | Status Becomes |
|---|---|
| Group created or edited (departments changed, allocation changed) | `NOT SET` |
| Admin clicks **"Confirm & Ready"** button in Admin Panel | `READY FOR DRAWING` |
| Any edit after confirming (reopen and save without re-confirming) | `NOT SET` |

**Rule:** A group draw in Event Mode can only proceed if **all groups involved in the current draw have `Status = 'READY FOR DRAWING'`**. If any group is `NOT SET`, the Draw button is disabled and shows a tooltip:

```
"Group setup incomplete. Ask your admin to confirm group assignments."
```

### Admin Panel UI Changes

In the Group Management section, each group row shows a status badge:

```
┌───────────────────────────────────────────────────────────────┐
│  Group Management                                             │
│                                                               │
│  ┌──────────────┬──────────────┬───────────┬───────────────┐  │
│  │ Group Name   │ Departments  │ Allocated │ Status        │  │
│  ├──────────────┼──────────────┼───────────┼───────────────┤  │
│  │ Group 1      │ ISD, HR      │ 5         │ 🔴 NOT SET    │  │
│  │ Group 2      │ LOD, SPD     │ 5         │ 🟢 READY      │  │
│  │ LTI Building │ (by Building)│ 1         │ 🔴 NOT SET    │  │
│  │ CIP Building │ (by Building)│ 2         │ 🟢 READY      │  │
│  └──────────────┴──────────────┴───────────┴───────────────┘  │
│                                                               │
│  [ + New Group ]  [ ✏ Edit Selected ]  [ 🗑 Delete ]          │
│  [ ✓ Confirm & Mark Ready ]                                   │
└───────────────────────────────────────────────────────────────┘
```

- **"Confirm & Mark Ready"** sets the selected group's `Status = 'READY FOR DRAWING'` and writes to audit log.
- Any subsequent edit (via "✏ Edit Selected") automatically reverts status to `NOT SET` and requires re-confirmation.

### Service Logic (`app/services/admin_service.py`)

```python
def confirm_group_ready(self, group_id: int, admin_name: str):
    with get_session() as session:
        group = session.get(Group, group_id)
        group.Status = 'READY FOR DRAWING'
        session.commit()
    self.log(admin_name, f"Group '{group.GroupName}' confirmed as READY FOR DRAWING")

def mark_group_not_set(self, group_id: int):
    """Called automatically whenever a group is edited."""
    with get_session() as session:
        group = session.get(Group, group_id)
        group.Status = 'NOT SET'
        session.commit()
```

### Controller Guard (`app/controllers/raffle_controller.py`)

```python
def can_draw_grouped(self) -> tuple[bool, str]:
    """Returns (True, '') if all active groups are READY, else (False, reason)."""
    groups = self.group_repo.get_active_groups()
    not_ready = [g.GroupName for g in groups if g.Status != 'READY FOR DRAWING']
    if not_ready:
        return False, f"Groups not ready: {', '.join(not_ready)}"
    return True, ''
```

Draw button in `DrawPanel` checks `controller.can_draw_grouped()` before calling `start_draw()`. If not ready: disable button, show tooltip.

---

## 3.3 Group Drawing Scoped to Event Mode Only

**Rule:** Group-based draws (split by department group or building) only apply in **Event Mode**. Department Mode and DIY Mode use flat pool draws with no group bias.

### Enforcement Points

**`RaffleService`:**

```python
def draw(self, prize_id, winner_count, mode, department=None, event_id=None, diy_pool=None):
    if mode == 'department':
        # Flat draw from single department — no groups, no bias
        pool = self.employee_repo.get_eligible_by_department(department, excluded)

    elif mode == 'event':
        # Group-based draw — uses _Groups, AllocatedPrizes, Building/Dept assignments
        # Requires all groups READY FOR DRAWING (guard checked in controller)
        return self._draw_grouped(prize_id, winner_count, excluded)

    elif mode == 'diy':
        # Flat draw from DIY participant list only — no groups, no bias
        pool = diy_pool  # list[Employee-like objects] passed from controller
```

**`DrawPanel` (View):**
- Group controls (group selector, allocation display) are **only visible** when mode is `event`.
- In `department` and `diy` modes these UI elements are hidden entirely — not just disabled.

**`ModeSelectScreen`:** The mode label descriptions shown to the user make this explicit (see Section 3.8).

---

## 3.4 Admin Panel — Group Allocation Logs

**Reason:** Admin needs visible in-panel confirmation that the bias happened correctly for each group. These are ephemeral draw-time logs shown inside the Admin Panel, separate from the hidden `_AdminAuditLog` audit trail.

### New In-Panel Log Display

Add a **"Draw Allocation Log"** section at the bottom of the Admin Panel Group Management tab:

```
┌──────────────────────────────────────────────────────────────────┐
│  Draw Allocation Log                              [ Clear Log ]  │
│ ─────────────────────────────────────────────────────────────── │
│  [14:32:01]  ✅ Group 1 (ISD, HR) → 5 winners drawn             │
│  [14:32:01]  ✅ Group 2 (LOD, SPD) → 5 winners drawn            │
│  [14:35:44]  ✅ LTI Building → 1 winner drawn                   │
│  [14:35:44]  ✅ CIP Building → 2 winners drawn                  │
│  [14:40:10]  ⚠ Group 1 (ISD, HR) — only 3 eligible, drew 3     │
└──────────────────────────────────────────────────────────────────┘
```

Log format:
- `✅` — draw succeeded, full allocation filled
- `⚠` — draw succeeded but pool was smaller than allocation (drew what was available)
- `❌` — draw failed (empty pool)

### Implementation

**Service — emit log entries after each group draw:**

```python
# In RaffleService._draw_grouped()

group_logs = []
for group in active_groups:
    pool = self._get_pool_for_group(group)
    allocated = group.AllocatedPrizes
    actual_drawn = min(allocated, len(pool))
    drawn = random.sample(pool, actual_drawn)

    if actual_drawn == allocated:
        status = 'ok'
        msg = f"Group '{group.GroupName}' → {actual_drawn} winner(s) drawn"
    else:
        status = 'warn'
        msg = f"Group '{group.GroupName}' — only {len(pool)} eligible, drew {actual_drawn}"

    group_logs.append({'status': status, 'message': msg, 'time': datetime.now()})
    # record winners...

return DrawResult(winners=all_winners, group_logs=group_logs)
```

**Controller:** Emit a new signal `group_draw_logged(list[dict])` after a grouped draw.

**AdminPanel:** Connects to `group_draw_logged` signal (if panel is open) and appends entries to the log list widget. Log is in-memory only — clears on "Clear Log" button or panel close. Also written to `_AdminAuditLog` for persistence:

```python
# Each group_log entry also writes to _AdminAuditLog
AdminAuditLog(AdminName="[SYSTEM]", ChangesMade=msg, ChangedAt=entry['time'])
```

---

## 3.5 Event Mode — Rework (No CSV, Pull from `_Employees`)

**What changes:** In Update 2, Event Mode prompted a CSV upload to define participants. This is removed. Event Mode now always draws from the **full `_Employees` table** — every registered employee is a potential participant.

### What to Remove

- `app/views/dialogs/event_wizard.py` — delete the CSV upload wizard entirely
- `app/services/event_service.py` — remove `import_csv()` method
- `_EventParticipants` table — no longer needed for Event Mode (keep table if DIY Mode uses it, see 3.7, but disconnect from Event Mode)
- `assets/participant_template.csv` — move to DIY Mode (see 3.7)

### What Event Mode Now Is

Event Mode = draw from all of `_Employees`, scoped by **Building** and **Department Group** as configured in the Admin Panel.

The "event" is really the organizational context (building groupings, department groupings, bias) — not a filtered list of invitees.

### Updated `_Events` Table Purpose

`_Events` is now used only to name/track the raffle session for audit purposes — not to filter participants.

```python
class Event(Base):
    __tablename__ = "_Events"
    EventID   = Column(Integer, primary_key=True, autoincrement=True)
    EventName = Column(String(150), nullable=False)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    IsActive  = Column(Boolean, default=True)
    # No longer linked to _EventParticipants for pool scoping
```

When the user enters Event Mode, they give the session a name (e.g., "Christmas Party 2025"). This name is stored in the active `_Events` record and tagged on every `_RaffleWinners` row via `EventID` for audit traceability.

### Event Mode Setup Flow (Simplified)

```
User selects Event Mode
        │
        ▼
Prompt: "Event Name" (text input)  +  [ Start Event ]
        │
        ▼
EventService.create_event(name)  →  INSERT _Events  →  return EventID
        │
        ▼
Controller sets active_event_id = EventID
        │
        ▼
Guard check: are all required Groups READY FOR DRAWING?
    No  →  show warning banner: "Contact your admin to finalize group setup"
    Yes →  unlock Draw buttons
        │
        ▼
Draw proceeds using full _Employees pool, split by Groups
```

### Participants Panel — Updated (Section 2.3 Revision)

The **"👥 Participants"** panel now always shows **all `_Employees`** (with search/filter):

- Columns: EmpNo | EmpName | Department | Building | Won? (Yes/No for current event)
- No longer sourced from `_EventParticipants`
- Filter controls: Department dropdown, Building dropdown (LTI / CIP / All)

```python
# employee_repository.py
def get_all_with_win_status(self, event_id: int) -> list[dict]:
    """Returns all employees annotated with whether they won in the given event."""
    with get_session() as session:
        employees = session.query(Employee).all()
        winners = {
            w.EmpNo for w in
            session.query(RaffleWinner).filter(RaffleWinner.EventID == event_id).all()
        }
        return [
            {**emp.__dict__, 'HasWon': emp.EmpNo in winners}
            for emp in employees
        ]
```

---

## 3.6 Drawing Mode Clarification — All Three Modes Defined

This section formally replaces Section 2.1 of CLAUDE.md with the corrected three-mode definition.

| Mode | Pool Source | Group Bias? | Use Case |
|---|---|---|---|
| **Department** | `_Employees` filtered by one department | ❌ None | Single-department draws; focused per team |
| **Event** | All of `_Employees` | ✅ Yes — Building + Dept groups (Admin-configured) | Big company-wide events; bias by building/group |
| **DIY** | User-supplied list (form entry or CSV upload) | ❌ None | Custom draws for specific people not necessarily in `_Employees`; external guests, ad-hoc lists |

**Key rules:**
- Group configuration and group bias only activates in **Event Mode**.
- Department Mode ignores groups entirely.
- DIY Mode ignores groups entirely; draws only from the user-built list.

---

## 3.7 New Mode — DIY Mode

**Purpose:** The user manually builds a participant list for the draw, either by typing entries in a form or uploading a CSV. Only people in this custom list are eligible to win.

### DIY Participant Entry — Two Input Options

The DIY panel presents a two-tab approach:

```
┌─────────────────────────────────────────────────────────────────┐
│  DIY Mode — Build Your Participant List                         │
│                                                                 │
│  [  Manual Entry  ] [  Upload CSV  ]                            │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│  ── Manual Entry Tab ──                                         │
│  EmpNo:       [___________]                                     │
│  EmpName:     [_______________________]                         │
│  Department:  [___________]                                     │
│                                                                 │
│                          [ + Add to List ]                      │
│                                                                 │
│  ── OR Upload CSV Tab ──                                        │
│  [ ⬇ Download CSV Template ]  (EmpNo, EmpName, Department)     │
│  [ 📂 Choose CSV File ]                                         │
│  Selected: my_list.csv ✓                                        │
│  Preview: 12 participants loaded                                │
│                          [ Load into List ]                     │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│  Current Participants (8):                                      │
│  ┌──────────┬──────────────────┬────────────┬────────────────┐  │
│  │ EmpNo    │ EmpName          │ Department │                │  │
│  │ OJT26A01 │ Juan Dela Cruz   │ ISD        │ [ Remove ]     │  │
│  │ MANUAL01 │ Guest Speaker    │ External   │ [ Remove ]     │  │
│  └──────────┴──────────────────┴────────────┴────────────────┘  │
│                                                                 │
│  [ 🗑 Clear All ]              [ ▶ Proceed to Draw ]            │
└─────────────────────────────────────────────────────────────────┘
```

### Rules

- Entries do **not** need to exist in `_Employees`. DIY is fully freeform — it accepts guests, externals, or any EmpNo/Name pair.
- If an EmpNo matches an existing `_Employees` record, auto-fill EmpName and Department as a convenience (but the user can override).
- Duplicate EmpNo in the list → show inline error: `"EmpNo already in list"`, do not add.
- Minimum 1 participant to proceed to draw.
- The DIY list is **session-only** (in-memory). It is not persisted to the database. Closing or changing modes clears it.
- Winners drawn in DIY Mode are still recorded in `_RaffleWinners` with whatever EmpNo/Name/Dept was supplied. `EventID` is NULL for DIY draws.

### DIY Pool in Service

```python
# DIY participants passed as a plain list of dicts, not ORM objects
# RaffleService.draw() when mode='diy':

pool = [
    SimpleNamespace(EmpNo=p['EmpNo'], EmpName=p['EmpName'], Department=p['Department'])
    for p in diy_participants
]
drawn = random.sample(pool, min(winner_count, len(pool)))
```

Winners are recorded using the supplied values directly — no FK enforcement on EmpNo for DIY draws (use `NOCHECK` or nullable FK, or insert to a staging area — document the choice clearly in code comments).

### CSV Template

The `assets/participant_template.csv` (originally for Event Mode, now removed from there per 3.5) moves here:

```csv
EmpNo,EmpName,Department
OJT26A01,Sample Name,ISD
```

Wire the "Download Template" button to copy this file to a user-chosen path (same as the Update 2 implementation, just relocated to DIY Mode).

### Controller State

```python
# RaffleController additions for DIY mode:
self._diy_participants: list[dict] = []   # in-memory only

def add_diy_participant(self, emp_no, emp_name, department):
    ...
def remove_diy_participant(self, emp_no):
    ...
def clear_diy_participants(self):
    self._diy_participants = []
def get_diy_participants(self) -> list[dict]:
    return self._diy_participants
```

---

## 3.8 Mode Select Screen — Updated UI

Replace the two-button screen from Update 2 (`Department | Event`) with a three-button layout. Update the descriptions to clearly reflect the intent of each mode.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELECT DRAWING MODE                          │
│                                                                 │
│  ┌──────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │  🏢 Department   │  │  🎉 Event        │  │  ✏ DIY        │  │
│  │                  │  │                 │  │               │  │
│  │  Draw within a   │  │  Company-wide   │  │  Build your   │  │
│  │  single          │  │  draw using all │  │  own list.    │  │
│  │  department.     │  │  employees,     │  │  Manual entry │  │
│  │                  │  │  split by       │  │  or CSV       │  │
│  │  No group bias.  │  │  building &     │  │  upload.      │  │
│  │                  │  │  group bias.    │  │               │  │
│  └──────────────────┘  └─────────────────┘  └───────────────┘  │
│                                                                 │
│  Event Mode note: Requires admin group setup to be READY.      │
└─────────────────────────────────────────────────────────────────┘
```

### Mode Select Logic

```python
# views/screens/mode_select_screen.py

def on_event_selected(self):
    """Check group readiness before allowing Event Mode entry."""
    ok, reason = self.controller.can_draw_grouped()
    if not ok:
        # Still allow entry but show a persistent warning banner in the draw panel
        self.controller.set_mode('event')
        self.show_warning(f"Group setup incomplete. {reason}")
    else:
        self.controller.set_mode('event')
    self.navigate_to_draw_panel()

def on_department_selected(self):
    self.controller.set_mode('department')
    self.navigate_to_draw_panel()

def on_diy_selected(self):
    self.controller.set_mode('diy')
    self.navigate_to_diy_panel()
```

---

## 3.9 File & Schema Changes Summary

### New / Modified Files

| File | Change |
|---|---|
| `app/models/orm_models.py` | Add `Building` to `Employee`; add `Status` to `Group` |
| `app/models/employee_repository.py` | Add `get_eligible_by_building()`, update `get_all_with_win_status()` |
| `app/models/group_repository.py` | Add `get_active_groups()`, update status queries |
| `app/services/raffle_service.py` | Mode-aware `draw()` dispatch; group log emission in `_draw_grouped()` |
| `app/services/admin_service.py` | Add `confirm_group_ready()`, `mark_group_not_set()` |
| `app/services/event_service.py` | Remove `import_csv()`; simplify to session naming only |
| `app/controllers/raffle_controller.py` | Add `_diy_participants` state; add `can_draw_grouped()` guard; new `group_draw_logged` signal; DIY participant management methods |
| `app/controllers/admin_controller.py` | Add `confirm_group_ready()` and `mark_group_not_set()` wiring |
| `app/views/screens/mode_select_screen.py` | Three-button layout; event readiness guard on Event selection |
| `app/views/dialogs/event_wizard.py` | **Delete** — replaced by simple event-name prompt inline |
| `app/views/dialogs/admin_panel.py` | Add status badge column; "Confirm & Mark Ready" button; allocation log panel |
| `app/views/components/diy_panel.py` | **New** — manual entry form + CSV upload + participant list |
| `app/views/components/participants_panel.py` | Update to source from `_Employees` + Building filter |
| `assets/participant_template.csv` | Move from Event Mode context to DIY Mode context |
| `database/migrations/003_add_building.sql` | New migration file |
| `database/migrations/004_add_group_status.sql` | New migration file |

### New DB Migration Files

```sql
-- database/migrations/003_add_building.sql
ALTER TABLE _Employees
ADD Building NVARCHAR(10) NOT NULL DEFAULT 'LTI'
    CONSTRAINT CHK_Building CHECK (Building IN ('LTI','CIP'));

-- database/migrations/004_add_group_status.sql
ALTER TABLE _Groups
ADD Status NVARCHAR(20) NOT NULL DEFAULT 'NOT SET'
    CONSTRAINT CHK_GroupStatus CHECK (Status IN ('NOT SET','READY FOR DRAWING'));
```

### Signals Updated

| Signal | Change |
|---|---|
| `group_draw_logged` | **New** — payload: `list[dict]` with `{status, message, time}` per group |
| `mode_changed` | Now emits `'department'`, `'event'`, or `'diy'` |
| `diy_list_updated` | **New** — emitted when DIY participant list changes; no payload |

---

## Debugging Checklist — Update 3

Before closing out Update 3:

- [ ] `Building` column exists in `_Employees` with `CHECK (IN ('LTI','CIP'))`; ORM validator rejects invalid values
- [ ] New employees without an explicit Building default to `'LTI'`
- [ ] `Status` column exists in `_Groups`; new groups default to `'NOT SET'`
- [ ] Any edit to a group (departments, allocation) automatically resets Status to `'NOT SET'`
- [ ] "Confirm & Mark Ready" sets Status to `'READY FOR DRAWING'` and writes to `_AdminAuditLog`
- [ ] Draw button in Event Mode is disabled (with tooltip) if any group is `NOT SET`
- [ ] Draw button in Event Mode enables when all groups are `READY FOR DRAWING`
- [ ] Department Mode draws from department only — no group logic runs
- [ ] DIY Mode draws from in-memory list only — no group logic runs
- [ ] Event Mode draws from full `_Employees`, split per group allocations
- [ ] After a grouped draw, allocation log entries appear in Admin Panel with correct group names, counts, and ✅/⚠/❌ indicators
- [ ] Each group log entry also writes to `_AdminAuditLog` with AdminName = `"[SYSTEM]"`
- [ ] `event_wizard.py` is deleted; Event Mode entry is now just a name prompt
- [ ] Event Mode Participants panel shows all `_Employees` with Building filter working
- [ ] DIY manual entry form adds to in-memory list; duplicates rejected
- [ ] DIY CSV upload parses and loads into in-memory list; preview shows correctly
- [ ] DIY list cleared when mode changes or app restarts
- [ ] DIY winners recorded in `_RaffleWinners` with provided EmpNo/Name/Dept; `EventID` is NULL
- [ ] Mode select screen shows three buttons with correct descriptions
- [ ] Selecting Event Mode when groups are NOT SET shows warning but still allows entry

---

*End of Update 3 Workflow — v3.0.0*
