"""
app/models/admin_repository.py
-------------------------------
Repository for _AdminAuditLog and _DepartmentSettings — SQLAlchemy ORM.
"""

from dataclasses import dataclass
from .database_manager import get_session
from .orm_models import (
    AdminAuditLog as AuditORM,
    DepartmentSettings as DeptSettingsORM,
    Employee as EmployeeORM,
)


@dataclass
class AuditEntry:
    log_id:       int
    admin_name:   str
    changes_made: str
    changed_at:   str


class AdminRepository:
    """CRUD operations for _AdminAuditLog and _DepartmentSettings."""

    # ── Audit Log ──────────────────────────────────────────────────

    def log_action(self, admin_name: str, description: str) -> int:
        """Record an admin action in the audit log; returns LogID."""
        with get_session() as session:
            entry = AuditORM(AdminName=admin_name, ChangesMade=description)
            session.add(entry)
            session.flush()
            return entry.LogID

    def get_audit_log(self, limit: int = 100) -> list[AuditEntry]:
        """Return recent audit entries."""
        with get_session() as session:
            rows = (
                session.query(AuditORM)
                .order_by(AuditORM.ChangedAt.desc())
                .limit(limit)
                .all()
            )
            return [
                AuditEntry(
                    log_id=r.LogID,
                    admin_name=r.AdminName,
                    changes_made=r.ChangesMade,
                    changed_at=str(r.ChangedAt) if r.ChangedAt else "",
                )
                for r in rows
            ]

    # ── Win Chance Boosts ──────────────────────────────────────────

    def set_employee_boost(self, emp_no: str, multiplier: int) -> None:
        """Set the win chance multiplier for a specific employee."""
        with get_session() as session:
            emp = session.query(EmployeeORM).get(emp_no)
            if emp:
                emp.WinChanceMultiplier = max(1, multiplier)

    def set_department_boost(self, dept_name: str, multiplier: int) -> None:
        """Set the win chance multiplier for a department."""
        with get_session() as session:
            existing = session.query(DeptSettingsORM).get(dept_name)
            if existing:
                existing.WinChanceMultiplier = max(1, multiplier)
            else:
                session.add(DeptSettingsORM(
                    DeptName=dept_name,
                    WinChanceMultiplier=max(1, multiplier),
                ))

    def get_employee_boost(self, emp_no: str) -> int:
        """Return the win chance multiplier for an employee."""
        with get_session() as session:
            emp = session.query(EmployeeORM).get(emp_no)
            return emp.WinChanceMultiplier if emp else 1

    def get_department_boosts(self) -> dict[str, int]:
        """Return all department boost multipliers."""
        with get_session() as session:
            rows = session.query(DeptSettingsORM).all()
            return {r.DeptName: r.WinChanceMultiplier for r in rows}
