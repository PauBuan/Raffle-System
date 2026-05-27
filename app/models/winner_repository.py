"""
app/models/winner_repository.py
--------------------------------
Repository for RaffleWinners table — SQLAlchemy ORM.
"""

from dataclasses import dataclass
from .database_manager import get_session
from .orm_models import (
    RaffleWinner as RaffleWinnerORM,
    Prize as PrizeORM,
    PrizeCategory as PrizeCategoryORM,
    Employee as EmployeeORM,
)


@dataclass
class Winner:
    winner_id:     int
    prize_id:      int
    prize_name:    str
    category_name: str
    emp_no:        str
    emp_name:      str
    department:    str
    drawn_at:      str
    is_redraw:     bool
    is_confirmed:  bool = False


class WinnerRepository:
    """CRUD operations for the _RaffleWinners table."""

    def record_winner(
        self,
        prize_id: int,
        emp_no: str,
        department: str,
        is_redraw: bool = False,
        is_confirmed: bool = False,
        event_id: int | None = None,
    ) -> int:
        """Insert a winner record; returns new WinnerID."""
        with get_session() as session:
            record = RaffleWinnerORM(
                PrizeID=prize_id,
                EmpNo=emp_no,
                Department=department,
                IsRedraw=is_redraw,
                IsConfirmed=is_confirmed,
                EventID=event_id,
            )
            session.add(record)
            session.flush()
            return record.WinnerID

    def get_all_winners(self) -> list[Winner]:
        """Return all winners ordered by category then draw time."""
        with get_session() as session:
            rows = (
                session.query(
                    RaffleWinnerORM, PrizeORM.PrizeName,
                    PrizeCategoryORM.CategoryName, EmployeeORM.EmpName,
                )
                .join(PrizeORM, PrizeORM.PrizeID == RaffleWinnerORM.PrizeID)
                .join(PrizeCategoryORM, PrizeCategoryORM.CategoryID == PrizeORM.CategoryID)
                .join(EmployeeORM, EmployeeORM.EmpNo == RaffleWinnerORM.EmpNo)
                .order_by(PrizeCategoryORM.CategoryID, RaffleWinnerORM.DrawnAt.desc())
                .all()
            )
            return [self._to_winner(w, pn, cn, en) for w, pn, cn, en in rows]

    def get_winners_by_category(self, category_name: str) -> list[Winner]:
        with get_session() as session:
            rows = (
                session.query(
                    RaffleWinnerORM, PrizeORM.PrizeName,
                    PrizeCategoryORM.CategoryName, EmployeeORM.EmpName,
                )
                .join(PrizeORM, PrizeORM.PrizeID == RaffleWinnerORM.PrizeID)
                .join(PrizeCategoryORM, PrizeCategoryORM.CategoryID == PrizeORM.CategoryID)
                .join(EmployeeORM, EmployeeORM.EmpNo == RaffleWinnerORM.EmpNo)
                .filter(PrizeCategoryORM.CategoryName == category_name)
                .order_by(RaffleWinnerORM.DrawnAt.desc())
                .all()
            )
            return [self._to_winner(w, pn, cn, en) for w, pn, cn, en in rows]

    def get_grand_winner_emp_nos(self) -> list[str]:
        """
        Return EmpNos of confirmed Grand prize winners.
        Only IsConfirmed = True winners are excluded from future draws.
        """
        with get_session() as session:
            rows = (
                session.query(RaffleWinnerORM.EmpNo)
                .join(PrizeORM, PrizeORM.PrizeID == RaffleWinnerORM.PrizeID)
                .join(PrizeCategoryORM, PrizeCategoryORM.CategoryID == PrizeORM.CategoryID)
                .filter(
                    PrizeCategoryORM.CategoryName == "Grand",
                    RaffleWinnerORM.IsConfirmed == True,
                )
                .distinct()
                .all()
            )
            return [r[0] for r in rows]

    def get_recent_winners(self, limit: int = 30) -> list[Winner]:
        """Return the most recent winners, capped at *limit*."""
        with get_session() as session:
            rows = (
                session.query(
                    RaffleWinnerORM, PrizeORM.PrizeName,
                    PrizeCategoryORM.CategoryName, EmployeeORM.EmpName,
                )
                .join(PrizeORM, PrizeORM.PrizeID == RaffleWinnerORM.PrizeID)
                .join(PrizeCategoryORM, PrizeCategoryORM.CategoryID == PrizeORM.CategoryID)
                .join(EmployeeORM, EmployeeORM.EmpNo == RaffleWinnerORM.EmpNo)
                .order_by(RaffleWinnerORM.DrawnAt.desc())
                .limit(limit)
                .all()
            )
            return [self._to_winner(w, pn, cn, en) for w, pn, cn, en in rows]

    def reset_grand_eligibility(self) -> int:
        """
        Set IsConfirmed = False for all Grand prize winners,
        restoring their eligibility for future Grand draws.
        Returns the number of records updated.
        """
        with get_session() as session:
            count = (
                session.query(RaffleWinnerORM)
                .join(PrizeORM, PrizeORM.PrizeID == RaffleWinnerORM.PrizeID)
                .join(PrizeCategoryORM, PrizeCategoryORM.CategoryID == PrizeORM.CategoryID)
                .filter(
                    PrizeCategoryORM.CategoryName == "Grand",
                    RaffleWinnerORM.IsConfirmed == True,
                )
                .update({RaffleWinnerORM.IsConfirmed: False}, synchronize_session="fetch")
            )
            return count

    # ── Private helpers ────────────────────────────────────────────

    @staticmethod
    def _to_winner(
        w: RaffleWinnerORM, prize_name: str,
        category_name: str, emp_name: str,
    ) -> Winner:
        return Winner(
            winner_id=w.WinnerID,
            prize_id=w.PrizeID,
            prize_name=prize_name,
            category_name=category_name,
            emp_no=w.EmpNo,
            emp_name=emp_name,
            department=w.Department,
            drawn_at=str(w.DrawnAt) if w.DrawnAt else "",
            is_redraw=bool(w.IsRedraw),
            is_confirmed=bool(w.IsConfirmed),
        )
