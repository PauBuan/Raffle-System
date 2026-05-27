"""
app/controllers/raffle_controller.py
--------------------------------------
Presentation Controller Layer.

Routing
-------
Views → RaffleController → RaffleService → Models → DB

The controller translates UI events into service calls and emits Qt
signals so views can update themselves without knowing each other.
"""

from PySide6.QtCore import QObject, Signal

from app.services import RaffleService, DrawResult, AddPrizeResult
from app.models   import Prize, Winner, Employee
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

    # Emitted when mode changes ('department' or 'event')
    mode_changed    = Signal(str)

    # Emitted when active event is selected
    event_set       = Signal(object)   # EventInfo or None

    # Emitted on any error
    error_occurred  = Signal(str)

    # Emitted when session participants are set (department mode CSV import)
    session_updated = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service    = RaffleService()
        self._department = ""
        self._mode       = "department"   # 'department' | 'event'
        self._event_id   = None           # active EventID in event mode
        self._pending_grand: list[Employee] = []   # Grand winners not yet confirmed
        self._pending_prize_id: int | None = None
        self._session_emp_nos: set[str] | None = None  # CSV whitelist for dept mode

    # ── Mode ───────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        """Set drawing mode: 'department' or 'event'."""
        self._mode = mode
        if mode != "department":
            self._session_emp_nos = None   # clear whitelist in event mode
        self.mode_changed.emit(mode)

    def get_mode(self) -> str:
        return self._mode

    # ── Session participants (department mode) ─────────────────────

    def set_session_participants(self, emp_nos: set[str]) -> None:
        """Set the whitelist of EmpNos from the uploaded CSV."""
        self._session_emp_nos = emp_nos
        self.session_updated.emit()

    def get_session_participants(self) -> set[str] | None:
        return self._session_emp_nos

    def get_session_employees(self) -> list[Employee]:
        """Return Employee objects for the session whitelist."""
        if not self._session_emp_nos:
            return []
        from app.models import EmployeeRepository
        return EmployeeRepository().get_by_emp_nos(self._session_emp_nos)

    def set_event(self, event_id: int | None) -> None:
        """Set the active event for event mode."""
        self._event_id = event_id
        self.event_set.emit(event_id)

    def get_event_id(self) -> int | None:
        return self._event_id

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
        """Trigger a standard draw and emit the result."""
        if not self._department:
            self.error_occurred.emit("No department selected.")
            return
        try:
            result = self._service.draw(
                prize_id, self._department, winner_count,
                event_id=self._event_id,
                whitelist=self._session_emp_nos,
            )
            if result.error:
                self.error_occurred.emit(result.error)
            else:
                self.prizes_updated.emit()
                self.draw_completed.emit(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def start_redraw(self, prize_id: int, winner_count: int = 1) -> None:
        """Trigger a redraw (Major / Grand only) and emit the result."""
        if not self._department:
            self.error_occurred.emit("No department selected.")
            return
        try:
            result = self._service.redraw(
                prize_id, self._department, winner_count,
                whitelist=self._session_emp_nos,
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
            result = self._service.draw_grand(
                prize_id, lti_count, cip_count,
                whitelist=self._session_emp_nos,
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
