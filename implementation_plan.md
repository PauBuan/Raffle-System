# Raffle System v2.0.0 — Full Implementation Plan

Implementing all changes from [CLAUDEupdate 1 5.27.md](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/CLAUDEupdate%201%205.27.md) against the existing v1.0.0 codebase.

---

## Scope Summary

The update document describes **two phases** across **17 feature sections**:

| Phase | Sections | Summary |
|---|---|---|
| **Update 1** (Core Overhaul) | 1.1–1.9 | SQLAlchemy migration, table renames, deduplication, user-defined winner count, All Employees, group-based draws, Grand confirm/redraw, Grand reset, UI animations |
| **Update 2** (Event Mode & Admin) | 2.1–2.5 | Dept vs Event mode, CSV import wizard, live participant list, secret admin dev mode, admin panel (groups + win chance boost) |

Plus: updated file structure, data routing, signal table, schema, config.

---

## User Review Required

> [!IMPORTANT]
> **SQLAlchemy migration is destructive.** The current codebase uses raw `pyodbc`/`sqlite3`. Migrating to SQLAlchemy ORM means:
> - All repository files (`employee_model.py`, `prize_model.py`, `winner_model.py`) will be completely rewritten
> - `database_manager.py` will be replaced with SQLAlchemy engine/session setup
> - The `database/raffle_demo.db` SQLite file and all SQLite fallback code will be removed
> - The existing `database/schema.sql` will be rewritten for the new `_`-prefixed table names

> [!WARNING]
> **Requirements change.** The `requirements.txt` will add `sqlalchemy` and remove direct `sqlite3` usage. The `pyodbc` dependency remains (used by SQLAlchemy's `mssql+pyodbc` dialect). The corrupted entries (`bd2b2-b1abf`, `f3c81-1f5b3`) in the current requirements.txt will be cleaned up.

> [!IMPORTANT]
> **Grand Prize behavior change.** Currently, Grand winners are saved to DB immediately on draw. In v2.0, they are held in memory until explicitly confirmed. This changes the controller to be stateful for Grand draws.

---

## Open Questions

> [!IMPORTANT]
> **1. SQLite fallback removal** — The update doc says to remove SQLite entirely. Should we keep a minimal SQLite/in-memory fallback for local dev/demo testing, or strictly MSSQL-only as specified?

> [!IMPORTANT]
> **2. Database migration** — The existing SQL Server database has tables named `Employees`, `Prizes`, etc. The update renames them to `_Employees`, `_Prizes`, etc. Should we:
> - (a) Just update the ORM models with new names and let the user manually rename tables in SQL Server?
> - (b) Include an `ALTER TABLE ... RENAME` migration script?
> - (c) Have SQLAlchemy `create_all()` create the new tables fresh (data loss)?

> [!IMPORTANT]  
> **3. Execution approach** — This is a very large change (~20+ files created/modified). Should I:
> - (a) Implement everything in one go (Update 1 + Update 2)?
> - (b) Implement Update 1 first, pause for testing, then do Update 2?

---

## Proposed Changes

### Phase 1 — Foundation (Config & Database Layer)

---

#### [MODIFY] [requirements.txt](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/requirements.txt)
- Add `sqlalchemy>=2.0`
- Clean up corrupted entries
- Keep `pyodbc` (used as SQLAlchemy dialect driver)

#### [MODIFY] [database.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/config/database.py)
- Remove `DatabaseConfig` dataclass and `build_connection_string()`
- Replace with flat constants: `SERVER`, `DATABASE`, `DRIVER`, `TRUSTED_CONNECTION`, `USER`, `PASSWORD`
- Add `get_connection_url()` returning SQLAlchemy connection string
- Remove `USE_SQLITE_FALLBACK`, `SQLITE_PATH`, `CONNECT_TIMEOUT`, `MAX_RETRIES`

#### [MODIFY] [settings.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/config/settings.py)
- Bump `APP_VERSION` to `"2.0.0"`
- Add animation constants: `MINOR_ROW_INTERVAL_MS = 280`, `MAJOR_CARD_INTERVAL_MS = 700`
- Add `DEFAULT_LTI_WINNERS = 1`, `DEFAULT_CIP_WINNERS = 2`

#### [NEW] [admin.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/config/admin.py)
- `ADMIN_PASSWORD = "raffle@dev2025"`

#### [MODIFY] [\_\_init\_\_.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/config/__init__.py)
- Update exports for new config structure

---

### Phase 2 — Data Access Layer (Models)

---

#### [MODIFY] [database_manager.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/models/database_manager.py)
- **Complete rewrite.** Remove all `pyodbc`/`sqlite3` code.
- Create `engine = create_engine(get_connection_url(), pool_pre_ping=True)`
- Create `SessionLocal = sessionmaker(...)`
- Create `Base = declarative_base()`
- Add `get_session()` context manager (yield session, commit/rollback/close)

#### [NEW] [orm_models.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/models/orm_models.py)
- Define all 9 ORM model classes:
  - `Employee` (`_Employees`) — add `WinChanceMultiplier` column
  - `PrizeCategory` (`_PrizeCategories`)
  - `Prize` (`_Prizes`) — rename `Quantity` → `WinnerCount`
  - `RaffleWinner` (`_RaffleWinners`) — add `IsConfirmed`, `EventID`
  - `Group` (`_Groups`)
  - `GroupDepartment` (`_GroupDepartments`)
  - `Event` (`_Events`)
  - `EventParticipant` (`_EventParticipants`)
  - `AdminAuditLog` (`_AdminAuditLog`)

#### [MODIFY] [employee_model.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/models/employee_model.py)
- Rename to `employee_repository.py`
- Rewrite all methods to use SQLAlchemy ORM sessions instead of raw SQL
- Keep `Employee` dataclass for backward compat or use ORM model directly
- Add `get_all()` for "All Employees" pool
- Add win-chance weighting support in `get_eligible()`

#### [MODIFY] [prize_model.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/models/prize_model.py)
- Rename to `prize_repository.py`
- Rewrite to use SQLAlchemy ORM
- Add deduplication logic in `add_prize()`: check for existing active prize with same category+name, increment `WinnerCount` if found
- Rename `Quantity` → `WinnerCount` throughout

#### [MODIFY] [winner_model.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/models/winner_model.py)
- Rename to `winner_repository.py`
- Rewrite to use SQLAlchemy ORM
- `record_winner()` — add `IsConfirmed`, `EventID` params
- `get_grand_winner_emp_nos()` — filter by `IsConfirmed = True` only
- Add `reset_grand_eligibility()` method

#### [NEW] [group_repository.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/models/group_repository.py)
- CRUD for `_Groups` and `_GroupDepartments`
- `get_groups()`, `get_group_departments()`, `save_groups()`, `get_building_groups()`

#### [NEW] [event_repository.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/models/event_repository.py)
- CRUD for `_Events` and `_EventParticipants`
- `create_event()`, `add_participants()`, `get_participants()`, `get_active_events()`

#### [NEW] [admin_repository.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/models/admin_repository.py)
- CRUD for `_AdminAuditLog` and `_DepartmentSettings`
- `log_action()`, `get_audit_log()`, `save_boosts()`

#### [MODIFY] [\_\_init\_\_.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/models/__init__.py)
- Update exports for new repository names and ORM models

---

### Phase 3 — Service Layer

---

#### [MODIFY] [raffle_service.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/services/raffle_service.py)
- Update to use new repository classes
- `add_prize()` — return deduplication info (existing prize merged vs new)
- `draw()` — accept `winner_count` from user input instead of using `prize.WinnerCount`
- Add `draw_grouped(prize_id, winner_count, mode='group')` for Minor/Major group-based draws
- Add `draw_grand(prize_id, winner_count_per_building)` — draws from LTI/CIP groups, returns pending winners (NOT saved to DB)
- Add `confirm_grand_winner(emp_no, prize_id)` — saves with `IsConfirmed=True`
- Add `reset_grand_eligibility()` — marks all Grand confirmed winners as unconfirmed
- Support "ALL" department for whole-tip draws

#### [NEW] [event_service.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/services/event_service.py)
- `create_event(name)`, `import_csv(filepath, event_id)`, `get_participants(event_id)`
- CSV parsing with `csv.DictReader`, upsert logic

#### [NEW] [admin_service.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/services/admin_service.py)
- `save_groups(groups_payload)`, `save_boosts(emp_boosts, dept_boosts)`
- `log(admin_name, description)` — wraps audit log insert
- `authenticate(password)` — checks against `ADMIN_PASSWORD`

#### [MODIFY] [\_\_init\_\_.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/services/__init__.py)
- Export new services

---

### Phase 4 — Controller Layer

---

#### [MODIFY] [raffle_controller.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/controllers/raffle_controller.py)
- Add new signals: `grand_pending`, `grand_confirmed`, `mode_changed`, `event_set`
- Add mode state: `_mode` (department/event), `_event`
- `start_draw(prize_id, winner_count)` — pass user-supplied winner count
- Grand draws: hold pending winners in controller state, emit `grand_pending`
- `confirm_grand_winner()` → save + emit `grand_confirmed`
- `redraw_grand()` → discard pending, re-run draw
- `set_mode()`, `set_event()`

#### [NEW] [admin_controller.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/controllers/admin_controller.py)
- Wraps `AdminService` calls
- Signals for group/boost changes

#### [MODIFY] [\_\_init\_\_.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/controllers/__init__.py)
- Export new controller

---

### Phase 5 — View Layer (Update 1 features)

---

#### [MODIFY] [draw_panel.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/components/draw_panel.py)
- Add `QSpinBox` labeled "Winners to draw:" beside Draw button (default 1, max = eligible pool size)
- Add "🏢 All Employees (Whole Tip)" as first entry in department combo
- Pass winner count to `controller.start_draw(prize_id, winner_count)`
- Add button pulse animation on Draw click

#### [MODIFY] [minor_loading_screen.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/screens/minor_loading_screen.py)
- Add slide-in from left per row + subtle fade
- Use `MINOR_ROW_INTERVAL_MS` from settings instead of hardcoded 280

#### [MODIFY] [major_loading_screen.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/screens/major_loading_screen.py)
- Add card flip (Y-axis transform) before showing winner name
- Use `MAJOR_CARD_INTERVAL_MS` from settings instead of hardcoded 700

#### [MODIFY] [grand_loading_screen.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/screens/grand_loading_screen.py)
- Add particle burst (confetti) on final reveal
- Add gold shimmer pulse on winner card
- Integrate with confirm/redraw flow (show confirm panel after reveal)

#### [NEW] [grand_confirm_panel.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/grand_confirm_panel.py)
- Confirm/Redraw overlay panel shown after Grand slot machine reveal
- "✓ Confirm Win" and "↻ Re-draw" buttons
- Slide-up + fade animation

#### [MODIFY] [add_prize_dialog.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/dialogs/add_prize_dialog.py)
- Label already says "NUMBER OF WINNERS" ✓
- Add toast/info after deduplication: "Added to existing prize..."

---

### Phase 6 — View Layer (Update 2 features)

---

#### [NEW] [mode_select_screen.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/screens/mode_select_screen.py)
- Department vs Event mode selection screen
- Two large buttons with icons

#### [NEW] [event_wizard.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/dialogs/event_wizard.py)
- 3-step wizard: Event Details → Upload CSV → Confirm & Create
- CSV template download, file picker, preview table

#### [NEW] [participants_panel.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/components/participants_panel.py)
- Live participant list for Event mode
- Searchable `QTableWidget` with Won? column

#### [NEW] [admin_login_dialog.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/dialogs/admin_login_dialog.py)
- Admin Name + Password fields
- Triggered by `Ctrl+Shift+X`

#### [NEW] [admin_panel.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/dialogs/admin_panel.py)
- Department Grouping management UI
- Win Chance Weighting UI
- Grand building tag allocation

#### [MODIFY] [main_window.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/views/main_window.py)
- Add `Ctrl+Shift+X` keyboard shortcut handler
- Show mode selection on launch
- Update window title for dev mode
- Add smooth `QPropertyAnimation` transitions for `QStackedWidget` page switches

---

### Phase 7 — Schema & Assets

---

#### [MODIFY] [schema.sql](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/database/schema.sql)
- Rewrite with all `_`-prefixed table names
- Add new tables: `_Groups`, `_GroupDepartments`, `_Events`, `_EventParticipants`, `_AdminAuditLog`, `_DepartmentSettings`
- Add new columns: `WinnerCount` (replaces `Quantity`), `IsConfirmed`, `EventID`, `WinChanceMultiplier`, `BuildingTag`, `AllocatedPrizes`

#### [DELETE] [raffle_demo.db](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/database/raffle_demo.db)
- Remove SQLite demo database

#### [NEW] [participant_template.csv](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/assets/participant_template.csv)
- CSV template: `EmpNo,EmpName,Department`

---

### Phase 8 — Utils & Polish

---

#### [MODIFY] [helpers.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/utils/helpers.py)
- Add `show_toast()` — non-blocking info notification for deduplication feedback
- Add `export_csv()` helper

#### [MODIFY] [styles.py](file:///c:/Users/Pau/Documents/OJTDOCS/Raffle%20System/app/utils/styles.py)
- Add styles for new UI components (admin panel, mode selector, confirm panel, event wizard)

---

## File Impact Summary

| Action | Count | Files |
|---|---|---|
| **NEW** | 12 | `config/admin.py`, `app/models/orm_models.py`, `app/models/group_repository.py`, `app/models/event_repository.py`, `app/models/admin_repository.py`, `app/services/event_service.py`, `app/services/admin_service.py`, `app/controllers/admin_controller.py`, `app/views/screens/mode_select_screen.py`, `app/views/dialogs/event_wizard.py`, `app/views/dialogs/admin_login_dialog.py`, `app/views/dialogs/admin_panel.py`, `app/views/components/participants_panel.py`, `app/views/grand_confirm_panel.py`, `assets/participant_template.csv` |
| **MODIFY** | 17 | `requirements.txt`, `config/database.py`, `config/settings.py`, `config/__init__.py`, `database/schema.sql`, `app/models/database_manager.py`, `app/models/employee_model.py`, `app/models/prize_model.py`, `app/models/winner_model.py`, `app/models/__init__.py`, `app/services/raffle_service.py`, `app/services/__init__.py`, `app/controllers/raffle_controller.py`, `app/controllers/__init__.py`, `app/views/main_window.py`, `app/views/components/draw_panel.py`, all 3 loading screens, `app/views/dialogs/add_prize_dialog.py`, `app/utils/helpers.py`, `app/utils/styles.py` |
| **DELETE** | 1 | `database/raffle_demo.db` |

---

## Verification Plan

### Automated Tests
- Run `python main.py` and verify the application launches without import errors
- Verify SQLAlchemy engine connects (or fails gracefully with clear error)
- Test each new repository method independently via a scratch test script

### Manual Verification
- Verify the mode selection screen appears on launch
- Test prize deduplication (add same prize twice → winner count increments)
- Test winner count spinbox passes value correctly through the draw pipeline  
- Test "All Employees" draws from full pool
- Test Grand prize confirm/redraw flow (winner NOT in DB until confirmed)
- Test Grand reset clears eligibility
- Test `Ctrl+Shift+X` opens admin login
- Test admin panel group management
- Test Event mode CSV import wizard
- Verify all animations play smoothly without UI freezes

---

*Estimated effort: ~25-30 files across 8 phases.*
