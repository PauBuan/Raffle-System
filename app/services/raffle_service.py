"""
app/services/raffle_service.py
-------------------------------
Business Logic Layer (BLL).

Routing
-------
Controllers → RaffleService → Repositories (Models) → SQLAlchemy → DB

This layer owns all draw logic, eligibility checks, group-based draws,
Grand confirm/redraw, and prize deduplication rules.
It never touches Qt directly.
"""

import random
import logging
from dataclasses import dataclass, field

from app.models import (
    Employee, EmployeeRepository,
    Prize, PrizeRepository,
    Winner, WinnerRepository,
    GroupRepository,
)
from config.settings import CATEGORY_GRAND

logger = logging.getLogger(__name__)


@dataclass
class DrawResult:
    """Value object returned by every draw operation."""
    winners:          list[Winner]
    prize:            Prize
    is_redraw:        bool = False
    error:            str  = ""
    pending_employees: list[Employee] = field(default_factory=list)  # Grand: not yet saved


@dataclass
class AddPrizeResult:
    """Value object returned by add_prize."""
    prize:           Prize
    was_deduplicated: bool = False
    new_total:       int  = 0


class RaffleService:
    """
    Orchestrates raffle draws across Minor, Major, and Grand categories.
    One instance per application lifetime.
    """

    def __init__(self) -> None:
        self._employees = EmployeeRepository()
        self._prizes    = PrizeRepository()
        self._winners   = WinnerRepository()
        self._groups    = GroupRepository()

    # ── Department helpers ─────────────────────────────────────────

    def get_departments(self) -> list[str]:
        return self._employees.get_all_departments()

    # ── Prize management ───────────────────────────────────────────

    def get_prizes_by_category(self, category: str) -> list[Prize]:
        return self._prizes.get_prizes_by_category(category)

    def get_all_prizes(self) -> list[Prize]:
        return self._prizes.get_all_prizes()

    def add_prize(self, category: str, prize_name: str, winner_count: int) -> AddPrizeResult:
        """
        Add a new prize with deduplication.
        If same name + category + IsActive exists, increments WinnerCount.
        """
        prize_id, was_deduped = self._prizes.add_prize(category, prize_name, winner_count)

        # Retrieve the full prize object
        prizes = self._prizes.get_prizes_by_category(category)
        prize = None
        for p in prizes:
            if p.prize_id == prize_id:
                prize = p
                break

        if prize is None:
            # Fallback: find by name
            for p in reversed(prizes):
                if p.prize_name == prize_name and p.is_active:
                    prize = p
                    break

        if prize is None:
            raise RuntimeError("Failed to retrieve prize after add.")

        return AddPrizeResult(
            prize=prize,
            was_deduplicated=was_deduped,
            new_total=prize.winner_count,
        )

    def delete_prize(self, prize_id: int) -> None:
        self._prizes.delete_prize(prize_id)

    # ── Standard draw ──────────────────────────────────────────────

    def draw(
        self,
        prize_id:     int,
        department:   str,
        winner_count: int = 1,
        is_redraw:    bool = False,
        event_id:     int | None = None,
        whitelist:    set[str] | None = None,
    ) -> DrawResult:
        """
        Perform a raffle draw for the given prize.

        Rules
        -----
        - Grand:  exclude confirmed prior Grand winners.
        - Minor / Major: no exclusions unless redraw.
        - winner_count is user-supplied (from spinbox).
        - Redraw: a fresh random selection (existing records kept for audit).
        - whitelist: if provided, only employees in this set are eligible.
        """
        prize = self._get_prize_or_raise(prize_id)

        # Determine exclusion list
        excluded: list[str] = []
        if prize.category_name == CATEGORY_GRAND:
            excluded = self._winners.get_grand_winner_emp_nos()

        eligible = self._employees.get_eligible(
            department, excluded, weighted=True, whitelist=whitelist,
        )
        if not eligible:
            return DrawResult(
                winners=[], prize=prize, is_redraw=is_redraw,
                error="No eligible employees to draw from.",
            )

        # Validate count
        count = max(1, min(winner_count, len(eligible)))
        drawn: list[Employee] = random.sample(eligible, count)

        # Remove duplicates from weighted sampling
        seen = set()
        unique_drawn = []
        for emp in drawn:
            if emp.emp_no not in seen:
                seen.add(emp.emp_no)
                unique_drawn.append(emp)
        drawn = unique_drawn[:count]

        # Persist
        winner_objects: list[Winner] = []
        for emp in drawn:
            wid = self._winners.record_winner(
                prize_id, emp.emp_no, emp.department, is_redraw,
                is_confirmed=(prize.category_name != CATEGORY_GRAND),
                event_id=event_id,
            )
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
            logger.info(
                "Drew winner: %s (%s) for prize '%s'",
                emp.emp_name, emp.emp_no, prize.prize_name,
            )

        # Standard draws consume remaining winner slots for the prize.
        if not is_redraw and count > 0:
            self._prizes.decrement_winner_count(prize_id, count)

        return DrawResult(winners=winner_objects, prize=prize, is_redraw=is_redraw)

    def redraw(self, prize_id: int, department: str, winner_count: int = 1,
               whitelist: set[str] | None = None) -> DrawResult:
        """Convenience wrapper that sets is_redraw=True."""
        return self.draw(prize_id, department, winner_count, is_redraw=True,
                         whitelist=whitelist)

    # ── Group-based draw (Minor/Major) ─────────────────────────────

    def draw_grouped(
        self,
        prize_id:   int,
        event_id:   int | None = None,
    ) -> DrawResult:
        """
        Draw using group-based allocation.
        For each group, draw Group.AllocatedPrizes winners from that group's
        departments. All winners are combined — the split is not visible in UI.
        """
        prize = self._get_prize_or_raise(prize_id)
        groups = self._groups.get_all_groups()

        if not groups:
            return DrawResult(
                winners=[], prize=prize,
                error="No groups configured. Contact admin for group setup.",
            )

        excluded: list[str] = []
        if prize.category_name == CATEGORY_GRAND:
            excluded = self._winners.get_grand_winner_emp_nos()

        all_winners: list[Winner] = []

        for group in groups:
            if not group.departments or group.allocated_prizes <= 0:
                continue

            pool = self._employees.get_eligible_from_departments(
                group.departments, excluded, weighted=True,
            )
            if not pool:
                continue

            count = min(group.allocated_prizes, len(pool))
            drawn = random.sample(pool, count)

            # Remove weighted duplicates
            seen = set()
            unique = []
            for emp in drawn:
                if emp.emp_no not in seen:
                    seen.add(emp.emp_no)
                    unique.append(emp)

            for emp in unique:
                wid = self._winners.record_winner(
                    prize_id, emp.emp_no, emp.department,
                    is_confirmed=True, event_id=event_id,
                )
                all_winners.append(
                    Winner(
                        winner_id=wid,
                        prize_id=prize_id,
                        prize_name=prize.prize_name,
                        category_name=prize.category_name,
                        emp_no=emp.emp_no,
                        emp_name=emp.emp_name,
                        department=emp.department,
                        drawn_at="",
                        is_redraw=False,
                    )
                )
                # Add to exclusion list so no one wins twice across groups
                excluded.append(emp.emp_no)

        if all_winners:
            self._prizes.decrement_winner_count(prize_id, len(all_winners))

        return DrawResult(winners=all_winners, prize=prize)

    # ── Grand prize draw (pending until confirmed) ─────────────────

    def draw_grand(
        self,
        prize_id:   int,
        lti_count:  int = 1,
        cip_count:  int = 2,
        whitelist:  set[str] | None = None,
    ) -> DrawResult:
        """
        Draw Grand prize winners from LTI and CIP building groups.
        Winners are NOT saved to DB — they are returned as pending_employees.
        The controller holds them in memory until confirm_grand_winner() is called.

        Fallback: if no building groups are configured, draw from ALL employees.
        """
        prize = self._get_prize_or_raise(prize_id)
        building_groups = self._groups.get_building_groups()

        excluded = self._winners.get_grand_winner_emp_nos()
        pending: list[Employee] = []

        if building_groups:
            # ── Group-based Grand draw (LTI / CIP) ─────────────────
            for tag, count in [("LTI", lti_count), ("CIP", cip_count)]:
                group = building_groups.get(tag)
                if not group or not group.departments:
                    continue

                pool = self._employees.get_eligible_from_departments(
                    group.departments, excluded + [e.emp_no for e in pending],
                    whitelist=whitelist,
                )
                if not pool:
                    continue

                actual = min(count, len(pool))
                drawn = random.sample(pool, actual)
                pending.extend(drawn)
        else:
            # ── Fallback: no building groups configured ────────────
            # Draw from ALL employees so Grand works without admin setup
            logger.info(
                "No building groups configured — Grand draw using all employees."
            )
            total_count = lti_count + cip_count
            pool = self._employees.get_eligible(
                "ALL", excluded, weighted=True, whitelist=whitelist,
            )
            if pool:
                # Deduplicate weighted pool for sampling
                seen = set()
                unique_pool = []
                for emp in pool:
                    if emp.emp_no not in seen:
                        seen.add(emp.emp_no)
                        unique_pool.append(emp)

                actual = min(total_count, len(unique_pool))
                pending = random.sample(unique_pool, actual)

        if not pending:
            return DrawResult(
                winners=[], prize=prize,
                error="No eligible employees for Grand draw. "
                      "Check that employees exist and building groups "
                      "are configured (or use fallback: all employees).",
            )

        return DrawResult(
            winners=[],
            prize=prize,
            pending_employees=pending,
        )

    def confirm_grand_winner(
        self,
        prize_id: int,
        emp: Employee,
        event_id: int | None = None,
    ) -> Winner:
        """
        Confirm a Grand prize pending winner — saves to DB with IsConfirmed = True.
        """
        wid = self._winners.record_winner(
            prize_id, emp.emp_no, emp.department,
            is_confirmed=True, event_id=event_id,
        )
        # Decrement winner count for the prize
        self._prizes.decrement_winner_count(prize_id, 1)

        prize = self._get_prize_or_raise(prize_id)
        return Winner(
            winner_id=wid,
            prize_id=prize_id,
            prize_name=prize.prize_name,
            category_name=prize.category_name,
            emp_no=emp.emp_no,
            emp_name=emp.emp_name,
            department=emp.department,
            drawn_at="",
            is_redraw=False,
            is_confirmed=True,
        )

    # ── Grand reset ────────────────────────────────────────────────

    def reset_grand_eligibility(self) -> int:
        """Reset all confirmed Grand winners so they can participate again."""
        return self._winners.reset_grand_eligibility()

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
