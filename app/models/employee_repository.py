"""
app/models/employee_repository.py
----------------------------------
Repository for Employee data — SQLAlchemy ORM.
All queries are isolated here; services receive plain Python objects.

v3.0 changes:
    - Employee dataclass now includes `building` field
    - Added get_eligible_by_building() for Event Mode group draws
    - Added get_all_with_win_status() for Participants panel
    - upsert() accepts optional building param
"""

from dataclasses import dataclass
from .database_manager import get_session
from .orm_models import (
    Employee as EmployeeORM,
    DepartmentSettings,
    RaffleWinner as RaffleWinnerORM,
)


@dataclass
class Employee:
    emp_no:     str
    emp_name:   str
    department: str
    building:   str = "LTI"


class EmployeeRepository:
    """CRUD operations for the _Employees table."""

    def get_all_departments(self) -> list[str]:
        """Return sorted list of distinct department names."""
        with get_session() as session:
            rows = (
                session.query(EmployeeORM.Department)
                .distinct()
                .order_by(EmployeeORM.Department)
                .all()
            )
            return [r[0] for r in rows]

    def get_all(self) -> list[Employee]:
        """Return all employees (used for 'All Employees' / Whole Tip selection)."""
        with get_session() as session:
            rows = (
                session.query(EmployeeORM)
                .order_by(EmployeeORM.EmpName)
                .all()
            )
            return [
                Employee(
                    emp_no=r.EmpNo, emp_name=r.EmpName,
                    department=r.Department, building=r.Building,
                )
                for r in rows
            ]

    def get_by_department(self, department: str) -> list[Employee]:
        """Return all employees belonging to *department*."""
        with get_session() as session:
            rows = (
                session.query(EmployeeORM)
                .filter(EmployeeORM.Department == department)
                .order_by(EmployeeORM.EmpName)
                .all()
            )
            return [
                Employee(
                    emp_no=r.EmpNo, emp_name=r.EmpName,
                    department=r.Department, building=r.Building,
                )
                for r in rows
            ]

    def get_by_departments(self, departments: list[str]) -> list[Employee]:
        """Return all employees whose department is in the given list."""
        with get_session() as session:
            rows = (
                session.query(EmployeeORM)
                .filter(EmployeeORM.Department.in_(departments))
                .order_by(EmployeeORM.EmpName)
                .all()
            )
            return [
                Employee(
                    emp_no=r.EmpNo, emp_name=r.EmpName,
                    department=r.Department, building=r.Building,
                )
                for r in rows
            ]

    def get_by_building(self, building: str) -> list[Employee]:
        """Return all employees in a specific building (LTI or CIP)."""
        with get_session() as session:
            rows = (
                session.query(EmployeeORM)
                .filter(EmployeeORM.Building == building)
                .order_by(EmployeeORM.EmpName)
                .all()
            )
            return [
                Employee(
                    emp_no=r.EmpNo, emp_name=r.EmpName,
                    department=r.Department, building=r.Building,
                )
                for r in rows
            ]

    # ── Eligibility queries ────────────────────────────────────────

    def get_eligible(
        self,
        department: str,
        exclude_emp_nos: list[str],
        weighted: bool = False,
        whitelist: set[str] | None = None,
    ) -> list[Employee]:
        """
        Return employees in *department* who are NOT in *exclude_emp_nos*.

        If department == 'ALL', return from all departments.
        If weighted == True, repeat each employee by their multiplier.
        If whitelist is provided, only employees in the whitelist are considered.
        """
        if department == "ALL":
            all_emps = self.get_all()
        else:
            all_emps = self.get_by_department(department)

        excluded = set(exclude_emp_nos)
        eligible = [e for e in all_emps if e.emp_no not in excluded]

        # Restrict to session whitelist (CSV-imported employees)
        if whitelist is not None:
            eligible = [e for e in eligible if e.emp_no in whitelist]

        if weighted:
            eligible = self._apply_weighting(eligible)

        return eligible

    def get_eligible_by_building(
        self,
        building: str,
        exclude_emp_nos: list[str],
        weighted: bool = False,
    ) -> list[Employee]:
        """Return eligible employees from a specific building (LTI or CIP)."""
        all_emps = self.get_by_building(building)
        excluded = set(exclude_emp_nos)
        eligible = [e for e in all_emps if e.emp_no not in excluded]

        if weighted:
            eligible = self._apply_weighting(eligible)

        return eligible

    def get_eligible_from_departments(
        self,
        departments: list[str],
        exclude_emp_nos: list[str],
        weighted: bool = False,
        whitelist: set[str] | None = None,
    ) -> list[Employee]:
        """Return eligible employees from a specific list of departments."""
        all_emps = self.get_by_departments(departments)
        excluded = set(exclude_emp_nos)
        eligible = [e for e in all_emps if e.emp_no not in excluded]

        # Restrict to session whitelist (CSV-imported employees)
        if whitelist is not None:
            eligible = [e for e in eligible if e.emp_no in whitelist]

        if weighted:
            eligible = self._apply_weighting(eligible)

        return eligible

    def get_by_emp_nos(self, emp_nos: set[str]) -> list[Employee]:
        """Return employees whose EmpNo is in the given set."""
        with get_session() as session:
            rows = (
                session.query(EmployeeORM)
                .filter(EmployeeORM.EmpNo.in_(emp_nos))
                .order_by(EmployeeORM.EmpName)
                .all()
            )
            return [
                Employee(
                    emp_no=r.EmpNo, emp_name=r.EmpName,
                    department=r.Department, building=r.Building,
                )
                for r in rows
            ]

    def get_all_with_win_status(self, event_id: int | None) -> list[dict]:
        """Return all employees annotated with whether they won in the given event."""
        with get_session() as session:
            employees = session.query(EmployeeORM).order_by(EmployeeORM.EmpName).all()

            winners: set[str] = set()
            if event_id:
                winner_rows = (
                    session.query(RaffleWinnerORM.EmpNo)
                    .filter(RaffleWinnerORM.EventID == event_id)
                    .all()
                )
                winners = {r[0] for r in winner_rows}

            return [
                {
                    "emp_no": emp.EmpNo,
                    "emp_name": emp.EmpName,
                    "department": emp.Department,
                    "building": emp.Building,
                    "has_won": emp.EmpNo in winners,
                }
                for emp in employees
            ]

    def lookup(self, emp_no: str) -> Employee | None:
        """Look up a single employee by EmpNo (for DIY auto-fill)."""
        with get_session() as session:
            r = session.query(EmployeeORM).get(emp_no)
            if not r:
                return None
            return Employee(
                emp_no=r.EmpNo, emp_name=r.EmpName,
                department=r.Department, building=r.Building,
            )

    # ── Weighting ──────────────────────────────────────────────────

    def _apply_weighting(self, employees: list[Employee]) -> list[Employee]:
        """Repeat each employee in the pool by their win chance multiplier."""
        with get_session() as session:
            # Get employee-level multipliers
            emp_multipliers = {}
            for emp in employees:
                orm_emp = session.query(EmployeeORM).get(emp.emp_no)
                if orm_emp:
                    emp_multipliers[emp.emp_no] = orm_emp.WinChanceMultiplier or 1

            # Get department-level multipliers
            dept_multipliers = {}
            dept_settings = session.query(DepartmentSettings).all()
            for ds in dept_settings:
                dept_multipliers[ds.DeptName] = ds.WinChanceMultiplier or 1

        weighted: list[Employee] = []
        for emp in employees:
            emp_mult  = emp_multipliers.get(emp.emp_no, 1)
            dept_mult = dept_multipliers.get(emp.department, 1)
            total = emp_mult * dept_mult
            weighted.extend([emp] * total)

        return weighted

    # ── Upsert ─────────────────────────────────────────────────────

    def upsert(self, emp_no: str, emp_name: str, department: str,
               building: str = "LTI") -> str:
        """Insert or update an employee. Returns 'inserted' or 'updated'."""
        with get_session() as session:
            existing = session.query(EmployeeORM).get(emp_no)
            if existing:
                existing.EmpName = emp_name
                existing.Department = department
                existing.Building = building
                return "updated"
            else:
                session.add(EmployeeORM(
                    EmpNo=emp_no, EmpName=emp_name,
                    Department=department, Building=building,
                ))
                return "inserted"
