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

v3.0 changes:
    - Mode-aware draw() dispatch (department / event / diy)
    - Group log entries in DrawResult for allocation tracking
    - draw_grand() uses Building column directly (not dept groups)
    - DIY mode: draws from in-memory list passed by controller
"""

import random
import logging
from datetime import datetime
from dataclasses import dataclass, field
from types import SimpleNamespace

from app.models import (
    Employee, EmployeeRepository,
    Prize, PrizeRepository,
    Winner, WinnerRepository,
    GroupRepository,
)
from config.settings import CATEGORY_GRAND

logger = logging.getLogger(__name__)


@dataclass
class GroupLogEntry:
    """Single log entry for a group draw allocation."""
    status:  str   # 'ok' | 'warn' | 'error'
    message: str
    time:    datetime = field(default_factory=datetime.now)


@dataclass
class DrawResult:
    """Value object returned by every draw operation."""
    winners:          list[Winner]
    prize:            Prize
    is_redraw:        bool = False
    error:            str  = ""
    pending_employees: list[Employee] = field(default_factory=list)  # Grand: not yet saved
    group_logs:       list[GroupLogEntry] = field(default_factory=list)


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

    # ── Standard draw (Department + DIY modes) ─────────────────────

    def draw(
        self,
        prize_id:     int,
        department:   str,
        winner_count: int = 1,
        is_redraw:    bool = False,
        event_id:     int | None = None,
        whitelist:    set[str] | None = None,
        diy_pool:     list[dict] | None = None,
    ) -> DrawResult:
        """
        Perform a raffle draw for the given prize.

        Modes
        -----
        - Department: draws from single department (flat, no groups)
        - Event: should use draw_grouped() instead (this is for non-grouped draws)
        - DIY: if diy_pool is provided, draws only from that in-memory list

        Rules
        -----
        - Grand: exclude confirmed prior Grand winners.
        - Minor / Major: no exclusions unless redraw.
        - winner_count is user-supplied (from spinbox).
        - Redraw: a fresh random selection (existing records kept for audit).
        - whitelist: if provided, only employees in this set are eligible.
        """
        prize = self._get_prize_or_raise(prize_id)

        # ── DIY mode: draw from in-memory pool ────────────────────
        if diy_pool is not None:
            return self._draw_diy(prize, diy_pool, winner_count, is_redraw)

        # ── Standard mode (department / fallback) ─────────────────
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
               whitelist: set[str] | None = None,
               diy_pool: list[dict] | None = None) -> DrawResult:
        """Convenience wrapper that sets is_redraw=True."""
        return self.draw(prize_id, department, winner_count, is_redraw=True,
                         whitelist=whitelist, diy_pool=diy_pool)

    # ── DIY draw (from in-memory list) ─────────────────────────────

    def _draw_diy(
        self,
        prize:        Prize,
        diy_pool:     list[dict],
        winner_count: int,
        is_redraw:    bool = False,
    ) -> DrawResult:
        """Draw from a DIY participant list (in-memory, no DB lookup)."""
        if not diy_pool:
            return DrawResult(
                winners=[], prize=prize, is_redraw=is_redraw,
                error="DIY participant list is empty.",
            )

        # Exclude prior Grand winners
        excluded: set[str] = set()
        if prize.category_name == CATEGORY_GRAND:
            excluded = set(self._winners.get_grand_winner_emp_nos())

        pool = [
            SimpleNamespace(
                emp_no=p['EmpNo'], emp_name=p['EmpName'], department=p['Department'],
            )
            for p in diy_pool
            if p['EmpNo'] not in excluded
        ]

        if not pool:
            return DrawResult(
                winners=[], prize=prize, is_redraw=is_redraw,
                error="No eligible participants in DIY list.",
            )

        count = max(1, min(winner_count, len(pool)))
        drawn = random.sample(pool, count)

        winner_objects: list[Winner] = []
        for p in drawn:
            wid = self._winners.record_winner(
                prize.prize_id, p.emp_no, p.department, is_redraw,
                is_confirmed=(prize.category_name != CATEGORY_GRAND),
                event_id=None,  # DIY has no event
            )
            winner_objects.append(
                Winner(
                    winner_id=wid,
                    prize_id=prize.prize_id,
                    prize_name=prize.prize_name,
                    category_name=prize.category_name,
                    emp_no=p.emp_no,
                    emp_name=p.emp_name,
                    department=p.department,
                    drawn_at="",
                    is_redraw=is_redraw,
                )
            )
            logger.info(
                "DIY drew winner: %s (%s) for prize '%s'",
                p.emp_name, p.emp_no, prize.prize_name,
            )

        if not is_redraw and count > 0:
            self._prizes.decrement_winner_count(prize.prize_id, count)

        return DrawResult(winners=winner_objects, prize=prize, is_redraw=is_redraw)

    # ── Group-based draw (Event Mode only — Minor/Major) ───────────

    def draw_grouped(
        self,
        prize_id:   int,
        event_id:   int | None = None,
    ) -> DrawResult:
        """
        Draw using group-based allocation (Event Mode only).
        For each group, draw Group.AllocatedPrizes winners from that group's
        departments. Returns combined winners + allocation logs.
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
        group_logs: list[GroupLogEntry] = []

        for group in groups:
            if not group.departments or group.allocated_prizes <= 0:
                continue

            pool = self._employees.get_eligible_from_departments(
                group.departments, excluded, weighted=True,
            )

            if not pool:
                group_logs.append(GroupLogEntry(
                    status="error",
                    message=f"Group '{group.group_name}' — empty pool, no winners drawn",
                ))
                continue

            allocated = group.allocated_prizes
            count = min(allocated, len(pool))
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

            # Build log entry
            actual = len(unique)
            if actual == allocated:
                group_logs.append(GroupLogEntry(
                    status="ok",
                    message=f"Group '{group.group_name}' → {actual} winner(s) drawn",
                ))
            else:
                group_logs.append(GroupLogEntry(
                    status="warn",
                    message=(
                        f"Group '{group.group_name}' — only {len(pool)} eligible, "
                        f"drew {actual} of {allocated} allocated"
                    ),
                ))

        if all_winners:
            self._prizes.decrement_winner_count(prize_id, len(all_winners))

        return DrawResult(
            winners=all_winners, prize=prize, group_logs=group_logs,
        )

    # ── Grand prize draw (pending until confirmed) ─────────────────

    def draw_grand(
        self,
        prize_id:   int,
        lti_count:  int = 1,
        cip_count:  int = 2,
        whitelist:  set[str] | None = None,
        diy_pool:   list[dict] | None = None,
    ) -> DrawResult:
        """
        Draw Grand prize winners by building (LTI / CIP).
        Winners are NOT saved to DB — they are returned as pending_employees.
        The controller holds them in memory until confirm_grand_winner() is called.

        v3.0: Uses Employee.Building column directly for building-based draws.
        Falls back to all employees if no employees in either building.
        """
        prize = self._get_prize_or_raise(prize_id)
        excluded = self._winners.get_grand_winner_emp_nos()
        pending: list[Employee] = []

        # DIY mode grand draw
        if diy_pool is not None:
            pool = [
                Employee(
                    emp_no=p['EmpNo'], emp_name=p['EmpName'],
                    department=p['Department'], building='LTI',
                )
                for p in diy_pool
                if p['EmpNo'] not in set(excluded)
            ]
            total = lti_count + cip_count
            if pool:
                actual = min(total, len(pool))
                pending = random.sample(pool, actual)

        else:
            # Building-based Grand draw using Employee.Building
            for tag, count in [("LTI", lti_count), ("CIP", cip_count)]:
                pool = self._employees.get_eligible_by_building(
                    tag, excluded + [e.emp_no for e in pending],
                    weighted=True,
                )
                if not pool:
                    logger.info("No eligible employees in building %s for Grand", tag)
                    continue

                # Deduplicate weighted pool
                seen = set()
                unique_pool = []
                for emp in pool:
                    if emp.emp_no not in seen:
                        seen.add(emp.emp_no)
                        unique_pool.append(emp)

                actual = min(count, len(unique_pool))
                pending.extend(random.sample(unique_pool, actual))

            # Fallback: if neither building had employees, draw from ALL
            if not pending:
                logger.info(
                    "No building-based employees found — Grand draw using all employees."
                )
                total_count = lti_count + cip_count
                pool = self._employees.get_eligible(
                    "ALL", excluded, weighted=True, whitelist=whitelist,
                )
                if pool:
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
                error="No eligible employees for Grand draw.",
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
