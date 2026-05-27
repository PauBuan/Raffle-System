"""
app/services/event_service.py
------------------------------
Business logic for Event Mode — event creation, CSV import, participant management.
"""

import csv
import logging
from dataclasses import dataclass

from app.models import (
    EmployeeRepository,
    EventRepository, EventInfo, ParticipantInfo,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Summary of a CSV import operation."""
    total:    int = 0
    inserted: int = 0
    updated:  int = 0
    skipped:  int = 0
    errors:   list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class EventService:
    """Event lifecycle and participant management."""

    def __init__(self) -> None:
        self._events    = EventRepository()
        self._employees = EmployeeRepository()

    def create_event(self, event_name: str) -> int:
        """Create a new event; returns EventID."""
        return self._events.create_event(event_name)

    def get_active_events(self) -> list[EventInfo]:
        return self._events.get_active_events()

    def get_event_by_id(self, event_id: int) -> EventInfo | None:
        return self._events.get_event_by_id(event_id)

    def get_participants(self, event_id: int) -> list[ParticipantInfo]:
        return self._events.get_participants(event_id)

    def import_csv(self, filepath: str, event_id: int | None = None) -> ImportResult:
        """
        Parse a CSV file and upsert employees.
        If *event_id* is provided, also links them to that event.

        Expected columns: EmpNo, EmpName, Department

        For each row:
        1. Upsert into _Employees (insert if not exists, update name/dept if exists)
        2. If event_id: Insert into _EventParticipants (skip if already linked)
        """
        result = ImportResult()

        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)

                # Validate required columns
                if not reader.fieldnames:
                    result.errors.append("CSV file is empty or has no headers.")
                    return result

                required = {"EmpNo", "EmpName", "Department"}
                actual = set(reader.fieldnames)
                missing = required - actual
                if missing:
                    result.errors.append(f"Missing required columns: {', '.join(missing)}")
                    return result

                for row_num, row in enumerate(reader, start=2):
                    result.total += 1
                    emp_no     = row.get("EmpNo", "").strip()
                    emp_name   = row.get("EmpName", "").strip()
                    department = row.get("Department", "").strip()

                    if not emp_no or not emp_name or not department:
                        result.errors.append(f"Row {row_num}: missing required field(s)")
                        continue

                    try:
                        # Upsert employee
                        action = self._employees.upsert(emp_no, emp_name, department)
                        if action == "inserted":
                            result.inserted += 1
                        else:
                            result.updated += 1

                        # Link to event (if event mode)
                        if event_id:
                            added = self._events.add_participant(event_id, emp_no)
                            if not added:
                                result.skipped += 1

                    except Exception as exc:
                        result.errors.append(f"Row {row_num}: {exc}")

        except FileNotFoundError:
            result.errors.append(f"File not found: {filepath}")
        except Exception as exc:
            result.errors.append(f"Failed to read CSV: {exc}")

        logger.info(
            "CSV import (event=%s): total=%d inserted=%d updated=%d skipped=%d errors=%d",
            event_id, result.total, result.inserted, result.updated,
            result.skipped, len(result.errors),
        )
        return result

    def import_employees_csv(self, filepath: str) -> ImportResult:
        """Import employees from CSV without linking to any event (Department mode)."""
        return self.import_csv(filepath, event_id=None)

