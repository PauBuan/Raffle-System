"""
app/services/raffle_service.py
-------------------------------
Business Logic Layer (BLL).

Routing
-------
Controllers → RaffleService → Repositories (Models) → DatabaseManager → DB

This layer owns all draw logic, eligibility checks, and redraw rules.
It never touches Qt directly.
"""

import random
import logging
from dataclasses import dataclass

from app.models import (
    Employee, EmployeeRepository,
    Prize, PrizeRepository,
    Winner, WinnerRepository,
)
from config.settings import CATEGORY_GRAND

logger = logging.getLogger(__name__)


@dataclass
class DrawResult:
    """Value object returned by every draw operation."""
    winners:     list[Winner]
    prize:       Prize
    is_redraw:   bool = False
    error:       str  = ""


class RaffleService:
    """
    Orchestrates raffle draws across Minor, Major, and Grand categories.
    One instance per application lifetime.
    """

    def __init__(self) -> None:
        self._employees  = EmployeeRepository()
        self._prizes     = PrizeRepository()
        self._winners    = WinnerRepository()

    # ── Department helpers ─────────────────────────────────────────

    def get_departments(self) -> list[str]:
        return self._employees.get_all_departments()

    # ── Prize management ───────────────────────────────────────────

    def get_prizes_by_category(self, category: str) -> list[Prize]:
        return self._prizes.get_prizes_by_category(category)

    def get_all_prizes(self) -> list[Prize]:
        return self._prizes.get_all_prizes()

    def add_prize(self, category: str, prize_name: str, quantity: int) -> Prize:
        """Add a new prize and return the full Prize object."""
        new_id = self._prizes.add_prize(category, prize_name, quantity)
        prizes = self._prizes.get_prizes_by_category(category)
        for p in prizes:
            if p.prize_id == new_id:
                return p
        raise RuntimeError("Failed to retrieve newly created prize.")

    def delete_prize(self, prize_id: int) -> None:
        self._prizes.delete_prize(prize_id)

    # ── Draw operations ────────────────────────────────────────────

    def draw(
        self,
        prize_id:   int,
        department: str,
        is_redraw:  bool = False,
    ) -> DrawResult:
        """
        Perform a raffle draw for the given prize.

        Rules
        -----
        - Grand:  exclude all prior Grand winners; draw exactly 1.
        - Minor / Major: draw *quantity* winners (no exclusions unless redraw).
        - Redraw: a fresh random selection (existing records kept for audit).
        """
        prize = self._get_prize_or_raise(prize_id)

        # Determine exclusion list
        excluded: list[str] = []
        if prize.category_name == CATEGORY_GRAND:
            excluded = self._winners.get_grand_winner_emp_nos()

        eligible = self._employees.get_eligible(department, excluded)
        if not eligible:
            return DrawResult(
                winners=[], prize=prize, is_redraw=is_redraw,
                error="No eligible employees to draw from.",
            )

        # Determine how many to draw
        count = 1 if prize.category_name == CATEGORY_GRAND else prize.quantity
        count = min(count, len(eligible))

        drawn: list[Employee] = random.sample(eligible, count)

        # Persist
        winner_objects: list[Winner] = []
        for emp in drawn:
            wid = self._winners.record_winner(prize_id, emp.emp_no, department, is_redraw)
            winner_objects.append(
                Winner(
                    winner_id=wid,
                    prize_id=prize_id,
                    prize_name=prize.prize_name,
                    category_name=prize.category_name,
                    emp_no=emp.emp_no,
                    emp_name=emp.emp_name,
                    department=emp.department,
                    drawn_at="",
                    is_redraw=is_redraw,
                )
            )
            logger.info("Drew winner: %s (%s) for prize '%s'", emp.emp_name, emp.emp_no, prize.prize_name)

        return DrawResult(winners=winner_objects, prize=prize, is_redraw=is_redraw)

    def redraw(self, prize_id: int, department: str) -> DrawResult:
        """Convenience wrapper that sets is_redraw=True."""
        return self.draw(prize_id, department, is_redraw=True)

    # ── Winner queries ─────────────────────────────────────────────

    def get_all_winners(self) -> list[Winner]:
        return self._winners.get_all_winners()

    def get_winners_by_category(self, category: str) -> list[Winner]:
        return self._winners.get_winners_by_category(category)

    def get_recent_winners(self, limit: int = 30) -> list[Winner]:
        return self._winners.get_recent_winners(limit)

    # ── Private helpers ────────────────────────────────────────────

    def _get_prize_or_raise(self, prize_id: int) -> Prize:
        for p in self._prizes.get_all_prizes():
            if p.prize_id == prize_id:
                return p
        raise ValueError(f"Prize ID {prize_id} not found.")
