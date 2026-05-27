"""
app/models/prize_repository.py
-------------------------------
Repository for Prizes and PrizeCategories — SQLAlchemy ORM.
"""

from dataclasses import dataclass
from .database_manager import get_session
from .orm_models import Prize as PrizeORM, PrizeCategory as PrizeCategoryORM


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
    winner_count:  int        # renamed from quantity
    is_active:     bool


class PrizeRepository:
    """CRUD operations for _Prizes and _PrizeCategories tables."""

    # ── Categories ─────────────────────────────────────────────────

    def get_categories(self) -> list[PrizeCategory]:
        with get_session() as session:
            rows = (
                session.query(PrizeCategoryORM)
                .order_by(PrizeCategoryORM.CategoryID)
                .all()
            )
            return [PrizeCategory(r.CategoryID, r.CategoryName) for r in rows]

    def get_category_by_name(self, name: str) -> PrizeCategory | None:
        with get_session() as session:
            row = (
                session.query(PrizeCategoryORM)
                .filter(PrizeCategoryORM.CategoryName == name)
                .first()
            )
            return PrizeCategory(row.CategoryID, row.CategoryName) if row else None

    # ── Prizes ─────────────────────────────────────────────────────

    def get_all_prizes(self) -> list[Prize]:
        with get_session() as session:
            rows = (
                session.query(PrizeORM, PrizeCategoryORM.CategoryName)
                .join(PrizeCategoryORM, PrizeCategoryORM.CategoryID == PrizeORM.CategoryID)
                .filter(PrizeORM.IsActive == True)
                .order_by(PrizeCategoryORM.CategoryID, PrizeORM.PrizeID)
                .all()
            )
            return [
                Prize(
                    prize_id=p.PrizeID,
                    category_id=p.CategoryID,
                    category_name=cat_name,
                    prize_name=p.PrizeName,
                    winner_count=p.WinnerCount,
                    is_active=bool(p.IsActive),
                )
                for p, cat_name in rows
            ]

    def get_prizes_by_category(self, category_name: str) -> list[Prize]:
        return [p for p in self.get_all_prizes() if p.category_name == category_name]

    def add_prize(self, category_name: str, prize_name: str, winner_count: int) -> tuple[int, bool]:
        """
        Add a prize with deduplication.

        If a prize with the same CategoryID + PrizeName already exists
        (and IsActive = True), add winner_count to the existing record
        instead of creating a duplicate.

        Returns
        -------
        (prize_id, was_deduplicated)
        """
        cat = self.get_category_by_name(category_name)
        if cat is None:
            raise ValueError(f"Unknown category: {category_name}")

        with get_session() as session:
            # Check for existing active prize with same name in same category
            existing = (
                session.query(PrizeORM)
                .filter(
                    PrizeORM.CategoryID == cat.category_id,
                    PrizeORM.PrizeName == prize_name,
                    PrizeORM.IsActive == True,
                )
                .first()
            )

            if existing:
                existing.WinnerCount += winner_count
                return (existing.PrizeID, True)
            else:
                new_prize = PrizeORM(
                    CategoryID=cat.category_id,
                    PrizeName=prize_name,
                    WinnerCount=winner_count,
                    IsActive=True,
                )
                session.add(new_prize)
                session.flush()   # populate PrizeID
                return (new_prize.PrizeID, False)

    def delete_prize(self, prize_id: int) -> None:
        """Soft-delete a prize by marking it inactive."""
        with get_session() as session:
            prize = session.query(PrizeORM).get(prize_id)
            if prize:
                prize.IsActive = False

    def decrement_winner_count(self, prize_id: int, amount: int = 1) -> None:
        """Decrease remaining winner slots; deactivate prize when exhausted."""
        if amount <= 0:
            return
        with get_session() as session:
            prize = session.query(PrizeORM).get(prize_id)
            if prize:
                prize.WinnerCount = max(0, prize.WinnerCount - amount)
                if prize.WinnerCount <= 0:
                    prize.IsActive = False
