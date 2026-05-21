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

from app.services import RaffleService, DrawResult
from app.models   import Prize, Winner
from config.settings import CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND


class RaffleController(QObject):
    """
    Central controller wired to the main window and all screens.
    Emits typed signals after every meaningful operation.
    """

    # Emitted after a successful draw
    draw_completed  = Signal(object)   # DrawResult

    # Emitted when the prize list changes
    prizes_updated  = Signal()

    # Emitted when the active department changes
    department_set  = Signal(str)

    # Emitted on any error
    error_occurred  = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service    = RaffleService()
        self._department = ""

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

    def add_prize(self, category: str, prize_name: str, quantity: int) -> None:
        try:
            self._service.add_prize(category, prize_name, quantity)
            self.prizes_updated.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def delete_prize(self, prize_id: int) -> None:
        try:
            self._service.delete_prize(prize_id)
            self.prizes_updated.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Draw ───────────────────────────────────────────────────────

    def start_draw(self, prize_id: int) -> None:
        """Trigger a standard draw and emit the result."""
        if not self._department:
            self.error_occurred.emit("No department selected.")
            return
        try:
            result = self._service.draw(prize_id, self._department)
            if result.error:
                self.error_occurred.emit(result.error)
            else:
                self.draw_completed.emit(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def start_redraw(self, prize_id: int) -> None:
        """Trigger a redraw (Major / Grand only) and emit the result."""
        if not self._department:
            self.error_occurred.emit("No department selected.")
            return
        try:
            result = self._service.redraw(prize_id, self._department)
            if result.error:
                self.error_occurred.emit(result.error)
            else:
                self.draw_completed.emit(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Winners ────────────────────────────────────────────────────

    def load_all_winners(self) -> list[Winner]:
        return self._service.get_all_winners()

    def load_winners_by_category(self, category: str) -> list[Winner]:
        return self._service.get_winners_by_category(category)

    def load_recent_winners(self, limit: int = 30) -> list[Winner]:
        return self._service.get_recent_winners(limit)
