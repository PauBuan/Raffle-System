"""
app/models/employee_model.py
-----------------------------
Repository for Employee data.
All SQL is isolated here — services receive plain Python dicts/objects.
"""

from dataclasses import dataclass
from .database_manager import DatabaseManager


@dataclass
class Employee:
    emp_no:     str
    emp_name:   str
    department: str


class EmployeeRepository:
    """CRUD operations for the Employees table."""

    def __init__(self) -> None:
        self._db = DatabaseManager()

    def get_all_departments(self) -> list[str]:
        """Return sorted list of distinct department names."""
        rows = self._db.fetch_all(
            "SELECT DISTINCT Department FROM Employees ORDER BY Department"
        )
        return [r["Department"] for r in rows]

    def get_by_department(self, department: str) -> list[Employee]:
        """Return all employees belonging to *department*."""
        rows = self._db.fetch_all(
            "SELECT EmpNo, EmpName, Department FROM Employees "
            "WHERE Department = ? ORDER BY EmpName",
            (department,),
        )
        return [
            Employee(emp_no=r["EmpNo"], emp_name=r["EmpName"], department=r["Department"])
            for r in rows
        ]

    def get_eligible(self, department: str, exclude_emp_nos: list[str]) -> list[Employee]:
        """
        Return employees in *department* who are NOT in *exclude_emp_nos*.
        Used for Grand prize draws where previous winners are filtered out.
        """
        all_emps = self.get_by_department(department)
        excluded = set(exclude_emp_nos)
        return [e for e in all_emps if e.emp_no not in excluded]
