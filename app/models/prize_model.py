"""
app/models/prize_model.py
--------------------------
Repository for Prizes and PrizeCategories.
"""

from dataclasses import dataclass
from .database_manager import DatabaseManager


@dataclass
class PrizeCategory:
    category_id:   int
    category_name: str   # 'Minor' | 'Major' | 'Grand'


@dataclass
class Prize:
    prize_id:      int
    category_id:   int
    category_name: str
    prize_name:    str
    quantity:      int
    is_active:     bool


class PrizeRepository:
    """CRUD operations for Prizes and PrizeCategories tables."""

    def __init__(self) -> None:
        self._db = DatabaseManager()

    # ── Categories ─────────────────────────────────────────────────

    def get_categories(self) -> list[PrizeCategory]:
        rows = self._db.fetch_all(
            "SELECT CategoryID, CategoryName FROM PrizeCategories ORDER BY CategoryID"
        )
        return [PrizeCategory(r["CategoryID"], r["CategoryName"]) for r in rows]

    def get_category_by_name(self, name: str) -> PrizeCategory | None:
        row = self._db.fetch_one(
            "SELECT CategoryID, CategoryName FROM PrizeCategories WHERE CategoryName = ?",
            (name,),
        )
        return PrizeCategory(row["CategoryID"], row["CategoryName"]) if row else None

    # ── Prizes ─────────────────────────────────────────────────────

    def get_all_prizes(self) -> list[Prize]:
        rows = self._db.fetch_all(
            """
            SELECT p.PrizeID, p.CategoryID, c.CategoryName,
                   p.PrizeName, p.Quantity, p.IsActive
            FROM   Prizes p
            JOIN   PrizeCategories c ON c.CategoryID = p.CategoryID
            WHERE  p.IsActive = 1
            ORDER  BY c.CategoryID, p.PrizeID
            """
        )
        return [
            Prize(
                r["PrizeID"], r["CategoryID"], r["CategoryName"],
                r["PrizeName"], r["Quantity"], bool(r["IsActive"]),
            )
            for r in rows
        ]

    def get_prizes_by_category(self, category_name: str) -> list[Prize]:
        return [p for p in self.get_all_prizes() if p.category_name == category_name]

    def add_prize(self, category_name: str, prize_name: str, quantity: int) -> int:
        """Insert a new prize; returns the new PrizeID."""
        cat = self.get_category_by_name(category_name)
        if cat is None:
            raise ValueError(f"Unknown category: {category_name}")
        return self._db.execute(
            "INSERT INTO Prizes (CategoryID, PrizeName, Quantity) VALUES (?, ?, ?)",
            (cat.category_id, prize_name, quantity),
        )

    def delete_prize(self, prize_id: int) -> None:
        """Soft-delete a prize by marking it inactive."""
        self._db.execute(
            "UPDATE Prizes SET IsActive = 0 WHERE PrizeID = ?",
            (prize_id,),
        )
