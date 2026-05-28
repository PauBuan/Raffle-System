"""
app/controllers/raffle_controller.py
--------------------------------------
Presentation Controller Layer.

Routing
-------
Views → RaffleController → RaffleService → Models → DB

The controller translates UI events into service calls and emits Qt
signals so views can update themselves without knowing each other.

v3.0 changes:
    - Three-mode support: department / event / diy
    - DIY participant management (in-memory list)
    - can_draw_grouped() guard for Event Mode
    - group_draw_logged signal for allocation logs
    - Removed session_emp_nos whitelist (replaced by DIY mode)
"""

from PySide6.QtCore import QObject, Signal

from app.services import RaffleService, DrawResult, AddPrizeResult
from app.models   import Prize, Winner, Employee, EmployeeRepository, GroupRepository
from config.settings import CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND


class RaffleController(QObject):
    """
    Central controller wired to the main window and all screens.
    Emits typed signals after every meaningful operation.
    """

    # Emitted after a successful draw
    draw_completed  = Signal(object)   # DrawResult

    # Emitted when Grand draw ran, awaiting confirmation
    grand_pending   = Signal(object)   # DrawResult (with pending_employees)

    # Emitted when a Grand winner is confirmed and saved
    grand_confirmed = Signal(object)   # Winner

    # Emitted when the prize list changes
    prizes_updated  = Signal()

    # Emitted when the active department changes
    department_set  = Signal(str)

    # Emitted when mode changes ('department', 'event', or 'diy')
    mode_changed    = Signal(str)

    # Emitted when active event is selected
    event_set       = Signal(object)   # EventInfo or None

    # Emitted on any error
    error_occurred  = Signal(str)

    # Emitted when DIY participant list changes
    diy_list_updated = Signal()

    # Emitted after a grouped draw with allocation log entries
    group_draw_logged = Signal(object)  # list[GroupLogEntry]

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service    = RaffleService()
        self._department = ""
        self._mode       = "department"   # 'department' | 'event' | 'diy'
        self._event_id   = None           # active EventID in event mode
        self._pending_grand: list[Employee] = []   # Grand winners not yet confirmed
        self._pending_prize_id: int | None = None
        self._diy_participants: list[dict] = []    # DIY mode in-memory list

    # ── Mode ───────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        """Set drawing mode: 'department', 'event', or 'diy'."""
        self._mode = mode
        # Clear DIY list when switching away from DIY
        if mode != "diy":
            self._diy_participants = []
        # Clear event when not in event mode
        if mode != "event":
            self._event_id = None
        self.mode_changed.emit(mode)

    def get_mode(self) -> str:
        return self._mode

    def set_event(self, event_id: int | None) -> None:
        """Set the active event for event mode."""
        self._event_id = event_id
        self.event_set.emit(event_id)

    def get_event_id(self) -> int | None:
        return self._event_id

    # ── DIY participant management ─────────────────────────────────

    def add_diy_participant(self, emp_no: str, emp_name: str, department: str) -> bool:
        """Add a participant to the DIY list. Returns False if duplicate."""
        if any(p['EmpNo'] == emp_no for p in self._diy_participants):
            return False
        self._diy_participants.append({
            'EmpNo': emp_no,
            'EmpName': emp_name,
            'Department': department,
        })
        self.diy_list_updated.emit()
        return True

    def remove_diy_participant(self, emp_no: str) -> None:
        """Remove a participant from the DIY list by EmpNo."""
        self._diy_participants = [
            p for p in self._diy_participants if p['EmpNo'] != emp_no
        ]
        self.diy_list_updated.emit()

    def clear_diy_participants(self) -> None:
        """Clear the entire DIY participant list."""
        self._diy_participants = []
        self.diy_list_updated.emit()

    def get_diy_participants(self) -> list[dict]:
        return self._diy_participants

    def lookup_employee(self, emp_no: str) -> Employee | None:
        """Look up employee by EmpNo for DIY auto-fill."""
        return EmployeeRepository().lookup(emp_no)

    # ── Group readiness guard (Event Mode) ─────────────────────────

    def can_draw_grouped(self) -> tuple[bool, str]:
        """Returns (True, '') if all groups are READY, else (False, reason)."""
        ready, not_ready = GroupRepository().are_all_groups_ready()
        if not ready:
            return False, f"Groups not ready: {', '.join(not_ready)}"
        return True, ""

    # ── Department ─────────────────────────────────────────────────

    def set_department(self, department: str) -> None:
        self._department = department
        self.department_set.emit(department)

    def get_department(self) -> str:
        return self._department

    def load_departments(self) -> list[str]:
        return self._service.get_departments()

    # ── Prizes ─────────────────────────────────────────────────────

    def load_prizes(self, category: str | None = None) -> list[Prize]:
        if category:
            return self._service.get_prizes_by_category(category)
        return self._service.get_all_prizes()

    def add_prize(self, category: str, prize_name: str, winner_count: int) -> AddPrizeResult | None:
        """Add a prize (with deduplication). Returns AddPrizeResult or None on error."""
        try:
            result = self._service.add_prize(category, prize_name, winner_count)
            self.prizes_updated.emit()
            return result
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return None

    def delete_prize(self, prize_id: int) -> None:
        try:
            self._service.delete_prize(prize_id)
            self.prizes_updated.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Draw ───────────────────────────────────────────────────────

    def start_draw(self, prize_id: int, winner_count: int = 1) -> None:
        """Trigger a draw based on the current mode."""
        if self._mode == "diy":
            return self._draw_diy(prize_id, winner_count)

        if self._mode == "event":
            return self._draw_event_grouped(prize_id)

        # Department mode — flat draw
        if not self._department:
            self.error_occurred.emit("No department selected.")
            return
        try:
            result = self._service.draw(
                prize_id, self._department, winner_count,
                event_id=self._event_id,
            )
            if result.error:
                self.error_occurred.emit(result.error)
            else:
                self.prizes_updated.emit()
                self.draw_completed.emit(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def _draw_diy(self, prize_id: int, winner_count: int) -> None:
        """DIY mode draw from in-memory participant list."""
        if not self._diy_participants:
            self.error_occurred.emit("No DIY participants added.")
            return
        try:
            result = self._service.draw(
                prize_id, "ALL", winner_count,
                diy_pool=self._diy_participants,
            )
            if result.error:
                self.error_occurred.emit(result.error)
            else:
                self.prizes_updated.emit()
                self.draw_completed.emit(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def _draw_event_grouped(self, prize_id: int) -> None:
        """Event mode grouped draw."""
        try:
            result = self._service.draw_grouped(
                prize_id, event_id=self._event_id,
            )
            if result.error:
                self.error_occurred.emit(result.error)
            else:
                self.prizes_updated.emit()
                self.draw_completed.emit(result)
                # Emit group allocation logs
                if result.group_logs:
                    self.group_draw_logged.emit(result.group_logs)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def start_redraw(self, prize_id: int, winner_count: int = 1) -> None:
        """Trigger a redraw (Major / Grand only)."""
        if self._mode == "diy":
            if not self._diy_participants:
                self.error_occurred.emit("No DIY participants.")
                return
            try:
                result = self._service.redraw(
                    prize_id, "ALL", winner_count,
                    diy_pool=self._diy_participants,
                )
                if result.error:
                    self.error_occurred.emit(result.error)
                else:
                    self.draw_completed.emit(result)
            except Exception as exc:
                self.error_occurred.emit(str(exc))
            return

        if not self._department:
            self.error_occurred.emit("No department selected.")
            return
        try:
            result = self._service.redraw(
                prize_id, self._department, winner_count,
            )
            if result.error:
                self.error_occurred.emit(result.error)
            else:
                self.draw_completed.emit(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Grand prize draw (pending until confirmed) ─────────────────

    def start_grand_draw(self, prize_id: int, lti_count: int = 1, cip_count: int = 2) -> None:
        """
        Trigger a Grand prize draw.
        Winners are NOT saved to DB — held in controller state until confirmed.
        """
        try:
            diy_pool = self._diy_participants if self._mode == "diy" else None
            result = self._service.draw_grand(
                prize_id, lti_count, cip_count,
                diy_pool=diy_pool,
            )
            if result.error:
                self.error_occurred.emit(result.error)
            else:
                self._pending_grand = result.pending_employees
                self._pending_prize_id = prize_id
                self.grand_pending.emit(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def confirm_grand_winner(self, emp: Employee) -> None:
        """Confirm a pending Grand winner — saves to DB."""
        if self._pending_prize_id is None:
            self.error_occurred.emit("No pending Grand draw to confirm.")
            return
        try:
            winner = self._service.confirm_grand_winner(
                self._pending_prize_id, emp, event_id=self._event_id,
            )
            # Remove confirmed employee from pending list
            self._pending_grand = [
                e for e in self._pending_grand if e.emp_no != emp.emp_no
            ]
            self.grand_confirmed.emit(winner)
            self.prizes_updated.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def redraw_grand(self) -> None:
        """Discard pending Grand result and run a fresh draw."""
        if self._pending_prize_id is None:
            return
        self._pending_grand = []
        # Re-run with same parameters (controller re-triggers)
        self.start_grand_draw(self._pending_prize_id)

    def get_pending_grand(self) -> list[Employee]:
        return self._pending_grand

    # ── Grand reset ────────────────────────────────────────────────

    def reset_grand_eligibility(self) -> int:
        """Reset all confirmed Grand winners for re-eligibility."""
        try:
            count = self._service.reset_grand_eligibility()
            return count
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return 0

    # ── Winners ────────────────────────────────────────────────────

    def load_all_winners(self) -> list[Winner]:
        return self._service.get_all_winners()

    def load_winners_by_category(self, category: str) -> list[Winner]:
        return self._service.get_winners_by_category(category)

    def load_recent_winners(self, limit: int = 30) -> list[Winner]:
        return self._service.get_recent_winners(limit)
