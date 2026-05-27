"""
app.models package
------------------
Data Access Layer — ORM models, repositories, and the SQLAlchemy session manager.
"""

from .database_manager import get_session, Base, engine, verify_connection

# ORM models
from .orm_models import (
    Employee as EmployeeORM,
    PrizeCategory as PrizeCategoryORM,
    Prize as PrizeORM,
    RaffleWinner as RaffleWinnerORM,
    Group as GroupORM,
    GroupDepartment as GroupDepartmentORM,
    Event as EventORM,
    EventParticipant as EventParticipantORM,
    AdminAuditLog as AdminAuditLogORM,
    DepartmentSettings as DepartmentSettingsORM,
)

# Repositories + dataclasses
from .employee_repository import Employee, EmployeeRepository
from .prize_repository    import Prize, PrizeCategory, PrizeRepository
from .winner_repository   import Winner, WinnerRepository
from .group_repository    import GroupInfo, GroupRepository
from .event_repository    import EventInfo, ParticipantInfo, EventRepository
from .admin_repository    import AuditEntry, AdminRepository
