"""
app/controllers/admin_controller.py
-------------------------------------
Controller for Admin Panel operations.

Routing
-------
AdminPanel (View) → AdminController → AdminService / EventService → Repositories → DB
"""

from PySide6.QtCore import QObject, Signal

from app.services import AdminService, EventService, ImportResult
from app.models   import GroupInfo, AuditEntry, EventInfo


class AdminController(QObject):
    """Controller for admin panel: group management, boosts, events."""

    # Signals
    groups_updated  = Signal()
    boosts_updated  = Signal()
    event_created   = Signal(int)     # EventID
    error_occurred  = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._admin_service = AdminService()
        self._event_service = EventService()
        self._admin_name    = ""

    def set_admin_name(self, name: str) -> None:
        self._admin_name = name

    def get_admin_name(self) -> str:
        return self._admin_name

    # ── Authentication ─────────────────────────────────────────────

    def authenticate(self, password: str) -> bool:
        return self._admin_service.authenticate(password)

    # ── Groups ─────────────────────────────────────────────────────

    def get_all_groups(self) -> list[GroupInfo]:
        return self._admin_service.get_all_groups()

    def save_groups(self, groups: list[dict]) -> None:
        try:
            self._admin_service.save_groups(self._admin_name, groups)
            self.groups_updated.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def delete_group(self, group_id: int, group_name: str) -> None:
        try:
            self._admin_service.delete_group(self._admin_name, group_id, group_name)
            self.groups_updated.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Boosts ─────────────────────────────────────────────────────

    def set_employee_boost(self, emp_no: str, multiplier: int) -> None:
        try:
            self._admin_service.set_employee_boost(self._admin_name, emp_no, multiplier)
            self.boosts_updated.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def set_department_boost(self, dept_name: str, multiplier: int) -> None:
        try:
            self._admin_service.set_department_boost(self._admin_name, dept_name, multiplier)
            self.boosts_updated.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def get_department_boosts(self) -> dict[str, int]:
        return self._admin_service.get_department_boosts()

    def get_employee_boost(self, emp_no: str) -> int:
        return self._admin_service.get_employee_boost(emp_no)

    def get_all_departments(self) -> list[str]:
        return self._admin_service.get_all_departments()

    # ── Events ─────────────────────────────────────────────────────

    def create_event(self, event_name: str) -> int | None:
        try:
            eid = self._event_service.create_event(event_name)
            self._admin_service.log(
                self._admin_name, f"Created event: {event_name} (ID={eid})"
            )
            self.event_created.emit(eid)
            return eid
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return None

    def import_csv(self, filepath: str, event_id: int | None = None) -> ImportResult:
        result = self._event_service.import_csv(filepath, event_id)
        if not result.errors:
            self._admin_service.log(
                self._admin_name,
                f"Imported CSV (event={event_id}): {result.total} rows, "
                f"{result.inserted} new, {result.updated} updated",
            )
        return result

    def import_employees_csv(self, filepath: str) -> ImportResult:
        """Import employees only (Department mode) — no event linking."""
        return self.import_csv(filepath, event_id=None)

    def get_active_events(self) -> list[EventInfo]:
        return self._event_service.get_active_events()

    def get_participants(self, event_id: int):
        return self._event_service.get_participants(event_id)

    # ── Audit ──────────────────────────────────────────────────────

    def get_audit_log(self, limit: int = 100) -> list[AuditEntry]:
        return self._admin_service.get_audit_log(limit)
