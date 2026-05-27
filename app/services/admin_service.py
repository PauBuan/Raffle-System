"""
app/services/admin_service.py
------------------------------
Business logic for Admin Panel — group management, win-chance boosts, audit logging.
"""

import logging

from app.models import (
    GroupRepository, GroupInfo,
    AdminRepository, AuditEntry,
    EmployeeRepository,
)
from config.admin import ADMIN_PASSWORD

logger = logging.getLogger(__name__)


class AdminService:
    """Admin panel operations — groups, boosts, audit."""

    def __init__(self) -> None:
        self._groups    = GroupRepository()
        self._admin     = AdminRepository()
        self._employees = EmployeeRepository()

    # ── Authentication ─────────────────────────────────────────────

    @staticmethod
    def authenticate(password: str) -> bool:
        """Check admin password. Returns True if correct."""
        return password == ADMIN_PASSWORD

    # ── Group Management ───────────────────────────────────────────

    def get_all_groups(self) -> list[GroupInfo]:
        return self._groups.get_all_groups()

    def save_groups(self, admin_name: str, groups: list[dict]) -> None:
        """Save group configuration and log the action."""
        self._groups.save_groups(groups)
        desc = f"Updated {len(groups)} group(s): " + ", ".join(
            g.get("group_name", "?") for g in groups
        )
        self._admin.log_action(admin_name, desc)
        logger.info("Admin %s: %s", admin_name, desc)

    def delete_group(self, admin_name: str, group_id: int, group_name: str) -> None:
        """Delete a group and log the action."""
        self._groups.delete_group(group_id)
        desc = f"Deleted group: {group_name} (ID={group_id})"
        self._admin.log_action(admin_name, desc)
        logger.info("Admin %s: %s", admin_name, desc)

    # ── Win Chance Boosts ──────────────────────────────────────────

    def set_employee_boost(self, admin_name: str, emp_no: str, multiplier: int) -> None:
        """Set win chance multiplier for an employee and log."""
        self._admin.set_employee_boost(emp_no, multiplier)
        desc = f"Boosted EmpNo {emp_no} to {multiplier}x"
        self._admin.log_action(admin_name, desc)
        logger.info("Admin %s: %s", admin_name, desc)

    def set_department_boost(self, admin_name: str, dept_name: str, multiplier: int) -> None:
        """Set win chance multiplier for a department and log."""
        self._admin.set_department_boost(dept_name, multiplier)
        desc = f"Boosted Dept {dept_name} to {multiplier}x"
        self._admin.log_action(admin_name, desc)
        logger.info("Admin %s: %s", admin_name, desc)

    def get_department_boosts(self) -> dict[str, int]:
        return self._admin.get_department_boosts()

    def get_employee_boost(self, emp_no: str) -> int:
        return self._admin.get_employee_boost(emp_no)

    # ── Audit Log ──────────────────────────────────────────────────

    def get_audit_log(self, limit: int = 100) -> list[AuditEntry]:
        return self._admin.get_audit_log(limit)

    def log(self, admin_name: str, description: str) -> None:
        """Generic audit log entry."""
        self._admin.log_action(admin_name, description)

    # ── Helpers ────────────────────────────────────────────────────

    def get_all_departments(self) -> list[str]:
        return self._employees.get_all_departments()
