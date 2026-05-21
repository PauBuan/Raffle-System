"""
app/models/winner_model.py
---------------------------
Repository for RaffleWinners table.
"""

from dataclasses import dataclass
from datetime import datetime
from .database_manager import DatabaseManager


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


class WinnerRepository:
    """CRUD operations for the RaffleWinners table."""

    def __init__(self) -> None:
        self._db = DatabaseManager()

    def record_winner(
        self, prize_id: int, emp_no: str, department: str, is_redraw: bool = False
    ) -> int:
        """Insert a winner record; returns new WinnerID."""
        return self._db.execute(
            "INSERT INTO RaffleWinners (PrizeID, EmpNo, Department, IsRedraw) "
            "VALUES (?, ?, ?, ?)",
            (prize_id, emp_no, department, 1 if is_redraw else 0),
        )

    def get_all_winners(self) -> list[Winner]:
        """Return all winners ordered by category then draw time."""
        rows = self._db.fetch_all(
            """
            SELECT w.WinnerID, w.PrizeID, p.PrizeName, c.CategoryName,
                   w.EmpNo, e.EmpName, w.Department, w.DrawnAt, w.IsRedraw
            FROM   RaffleWinners w
            JOIN   Prizes p          ON p.PrizeID    = w.PrizeID
            JOIN   PrizeCategories c ON c.CategoryID = p.CategoryID
            JOIN   Employees e       ON e.EmpNo      = w.EmpNo
            ORDER  BY c.CategoryID, w.DrawnAt DESC
            """
        )
        return [self._row_to_winner(r) for r in rows]

    def get_winners_by_category(self, category_name: str) -> list[Winner]:
        rows = self._db.fetch_all(
            """
            SELECT w.WinnerID, w.PrizeID, p.PrizeName, c.CategoryName,
                   w.EmpNo, e.EmpName, w.Department, w.DrawnAt, w.IsRedraw
            FROM   RaffleWinners w
            JOIN   Prizes p          ON p.PrizeID    = w.PrizeID
            JOIN   PrizeCategories c ON c.CategoryID = p.CategoryID
            JOIN   Employees e       ON e.EmpNo      = w.EmpNo
            WHERE  c.CategoryName = ?
            ORDER  BY w.DrawnAt DESC
            """,
            (category_name,),
        )
        return [self._row_to_winner(r) for r in rows]

    def get_grand_winner_emp_nos(self) -> list[str]:
        """
        Return EmpNos of ALL previous Grand prize winners.
        Used to exclude them from future Grand draws.
        """
        rows = self._db.fetch_all(
            """
            SELECT DISTINCT w.EmpNo
            FROM   RaffleWinners w
            JOIN   Prizes p          ON p.PrizeID    = w.PrizeID
            JOIN   PrizeCategories c ON c.CategoryID = p.CategoryID
            WHERE  c.CategoryName = 'Grand'
            """
        )
        return [r["EmpNo"] for r in rows]

    def get_recent_winners(self, limit: int = 30) -> list[Winner]:
        """
        Return the most recent winners, capped at *limit*.

        Routing
        -------
        WinnersView.refresh()  →  controller.load_recent_winners()
        →  RaffleService.get_recent_winners()  →  here
        →  DatabaseManager.fetch_all()  →  SQL Server (TOP) or SQLite (LIMIT)
        """
        if self._db._use_sqlite:
            sql = """
                SELECT w.WinnerID, w.PrizeID, p.PrizeName, c.CategoryName,
                       w.EmpNo, e.EmpName, w.Department, w.DrawnAt, w.IsRedraw
                FROM   RaffleWinners w
                JOIN   Prizes p          ON p.PrizeID    = w.PrizeID
                JOIN   PrizeCategories c ON c.CategoryID = p.CategoryID
                JOIN   Employees e       ON e.EmpNo      = w.EmpNo
                ORDER  BY w.DrawnAt DESC
                LIMIT  ?
            """
        else:
            sql = """
                SELECT TOP(?) w.WinnerID, w.PrizeID, p.PrizeName, c.CategoryName,
                       w.EmpNo, e.EmpName, w.Department, w.DrawnAt, w.IsRedraw
                FROM   RaffleWinners w
                JOIN   Prizes p          ON p.PrizeID    = w.PrizeID
                JOIN   PrizeCategories c ON c.CategoryID = p.CategoryID
                JOIN   Employees e       ON e.EmpNo      = w.EmpNo
                ORDER  BY w.DrawnAt DESC
            """
        rows = self._db.fetch_all(sql, (limit,))
        return [self._row_to_winner(r) for r in rows]

    # ── Private helpers ────────────────────────────────────────────

    @staticmethod
    def _row_to_winner(r: dict) -> "Winner":
        return Winner(
            winner_id=r["WinnerID"],
            prize_id=r["PrizeID"],
            prize_name=r["PrizeName"],
            category_name=r["CategoryName"],
            emp_no=r["EmpNo"],
            emp_name=r["EmpName"],
            department=r["Department"],
            drawn_at=str(r["DrawnAt"]),
            is_redraw=bool(r["IsRedraw"]),
        )
