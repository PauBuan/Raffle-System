"""
app/models/orm_models.py
-------------------------
SQLAlchemy ORM model definitions for all Raffle System tables.

All tables use underscore-prefixed names (v2.0 convention):
    _Employees, _PrizeCategories, _Prizes, _RaffleWinners,
    _Groups, _GroupDepartments, _Events, _EventParticipants,
    _AdminAuditLog, _DepartmentSettings
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey,
)
from sqlalchemy.orm import validates
from .database_manager import Base


class Employee(Base):
    """Master employee list — raffle participants."""
    __tablename__ = "_Employees"

    EmpNo                = Column(String(20), primary_key=True)
    EmpName              = Column(String(100), nullable=False)
    Department           = Column(String(100), nullable=False)
    Building             = Column(String(10),  nullable=False, default='LTI')
    WinChanceMultiplier  = Column(Integer, default=1)

    @validates('Building')
    def validate_building(self, key, value):
        if value not in ('LTI', 'CIP'):
            raise ValueError(f"Building must be 'LTI' or 'CIP', got: {value!r}")
        return value


class PrizeCategory(Base):
    """Fixed prize tiers: Minor, Major, Grand."""
    __tablename__ = "_PrizeCategories"

    CategoryID   = Column(Integer, primary_key=True, autoincrement=True)
    CategoryName = Column(String(50), nullable=False)


class Prize(Base):
    """Prize slots within a category."""
    __tablename__ = "_Prizes"

    PrizeID     = Column(Integer, primary_key=True, autoincrement=True)
    CategoryID  = Column(Integer, ForeignKey("_PrizeCategories.CategoryID"), nullable=False)
    PrizeName   = Column(String(200), nullable=False)
    WinnerCount = Column(Integer, default=1)       # renamed from Quantity
    IsActive    = Column(Boolean, default=True)


class RaffleWinner(Base):
    """Record of every drawn winner — audit trail."""
    __tablename__ = "_RaffleWinners"

    WinnerID    = Column(Integer, primary_key=True, autoincrement=True)
    PrizeID     = Column(Integer, ForeignKey("_Prizes.PrizeID"), nullable=False)
    EmpNo       = Column(String(20), ForeignKey("_Employees.EmpNo"), nullable=False)
    Department  = Column(String(100), nullable=False)
    DrawnAt     = Column(DateTime, default=datetime.utcnow)
    IsRedraw    = Column(Boolean, default=False)
    IsConfirmed = Column(Boolean, default=False)     # Grand prize: pending until confirmed
    EventID     = Column(Integer, ForeignKey("_Events.EventID"), nullable=True)


class Group(Base):
    """Named groupings of departments for prize allocation."""
    __tablename__ = "_Groups"

    GroupID         = Column(Integer, primary_key=True, autoincrement=True)
    GroupName       = Column(String(100), nullable=False)
    BuildingTag     = Column(String(10), nullable=True)   # 'LTI' | 'CIP' | None
    AllocatedPrizes = Column(Integer, default=0)
    Status          = Column(String(20), nullable=False, default='NOT SET')


class GroupDepartment(Base):
    """Junction: which departments belong to which group."""
    __tablename__ = "_GroupDepartments"

    ID         = Column(Integer, primary_key=True, autoincrement=True)
    GroupID    = Column(Integer, ForeignKey("_Groups.GroupID"), nullable=False)
    Department = Column(String(100), nullable=False)


class Event(Base):
    """Named raffle events with optional participant scope."""
    __tablename__ = "_Events"

    EventID   = Column(Integer, primary_key=True, autoincrement=True)
    EventName = Column(String(150), nullable=False)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    IsActive  = Column(Boolean, default=True)


class EventParticipant(Base):
    """Employees linked to a specific event."""
    __tablename__ = "_EventParticipants"

    ID      = Column(Integer, primary_key=True, autoincrement=True)
    EventID = Column(Integer, ForeignKey("_Events.EventID"), nullable=False)
    EmpNo   = Column(String(20), ForeignKey("_Employees.EmpNo"), nullable=False)


class AdminAuditLog(Base):
    """Audit trail for admin / dev mode changes."""
    __tablename__ = "_AdminAuditLog"

    LogID       = Column(Integer, primary_key=True, autoincrement=True)
    AdminName   = Column(String(100), nullable=False)
    ChangesMade = Column(Text, nullable=False)
    ChangedAt   = Column(DateTime, default=datetime.utcnow)


class DepartmentSettings(Base):
    """Per-department win chance multiplier."""
    __tablename__ = "_DepartmentSettings"

    DeptName              = Column(String(100), primary_key=True)
    WinChanceMultiplier   = Column(Integer, default=1)
