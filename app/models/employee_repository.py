"""
app/models/employee_repository.py
----------------------------------
Repository for Employee data — SQLAlchemy ORM.
All queries are isolated here; services receive plain Python objects.
"""

from dataclasses import dataclass
from .database_manager import get_session
from .orm_models import Employee as EmployeeORM, DepartmentSettings


@dataclass
class Employee:
    emp_no:     str
    emp_name:   str
    department: str


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
                Employee(emp_no=r.EmpNo, emp_name=r.EmpName, department=r.Department)
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
                Employee(emp_no=r.EmpNo, emp_name=r.EmpName, department=r.Department)
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
                Employee(emp_no=r.EmpNo, emp_name=r.EmpName, department=r.Department)
                for r in rows
            ]

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
                Employee(emp_no=r.EmpNo, emp_name=r.EmpName, department=r.Department)
                for r in rows
            ]

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

    def upsert(self, emp_no: str, emp_name: str, department: str) -> str:
        """Insert or update an employee. Returns 'inserted' or 'updated'."""
        with get_session() as session:
            existing = session.query(EmployeeORM).get(emp_no)
            if existing:
                existing.EmpName = emp_name
                existing.Department = department
                return "updated"
            else:
                session.add(EmployeeORM(
                    EmpNo=emp_no, EmpName=emp_name, Department=department,
                ))
                return "inserted"
