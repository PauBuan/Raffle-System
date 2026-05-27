"""
app/models/event_repository.py
-------------------------------
Repository for _Events and _EventParticipants — SQLAlchemy ORM.
"""

from dataclasses import dataclass
from .database_manager import get_session
from .orm_models import (
    Event as EventORM,
    EventParticipant as EventParticipantORM,
    Employee as EmployeeORM,
)


@dataclass
class EventInfo:
    event_id:   int
    event_name: str
    created_at: str
    is_active:  bool


@dataclass
class ParticipantInfo:
    emp_no:     str
    emp_name:   str
    department: str
    has_won:    bool = False


class EventRepository:
    """CRUD operations for _Events and _EventParticipants tables."""

    def create_event(self, event_name: str) -> int:
        """Create a new event; returns the EventID."""
        with get_session() as session:
            event = EventORM(EventName=event_name, IsActive=True)
            session.add(event)
            session.flush()
            return event.EventID

    def get_active_events(self) -> list[EventInfo]:
        """Return all active events."""
        with get_session() as session:
            rows = (
                session.query(EventORM)
                .filter(EventORM.IsActive == True)
                .order_by(EventORM.CreatedAt.desc())
                .all()
            )
            return [
                EventInfo(
                    event_id=r.EventID,
                    event_name=r.EventName,
                    created_at=str(r.CreatedAt) if r.CreatedAt else "",
                    is_active=bool(r.IsActive),
                )
                for r in rows
            ]

    def get_event_by_id(self, event_id: int) -> EventInfo | None:
        """Return a single event by ID."""
        with get_session() as session:
            r = session.query(EventORM).get(event_id)
            if not r:
                return None
            return EventInfo(
                event_id=r.EventID,
                event_name=r.EventName,
                created_at=str(r.CreatedAt) if r.CreatedAt else "",
                is_active=bool(r.IsActive),
            )

    def add_participant(self, event_id: int, emp_no: str) -> bool:
        """
        Link an employee to an event.
        Returns True if added, False if already linked.
        """
        with get_session() as session:
            existing = (
                session.query(EventParticipantORM)
                .filter(
                    EventParticipantORM.EventID == event_id,
                    EventParticipantORM.EmpNo == emp_no,
                )
                .first()
            )
            if existing:
                return False
            session.add(EventParticipantORM(EventID=event_id, EmpNo=emp_no))
            return True

    def get_participants(self, event_id: int) -> list[ParticipantInfo]:
        """Return all participants for an event with employee details."""
        with get_session() as session:
            rows = (
                session.query(EventParticipantORM, EmployeeORM)
                .join(EmployeeORM, EmployeeORM.EmpNo == EventParticipantORM.EmpNo)
                .filter(EventParticipantORM.EventID == event_id)
                .order_by(EmployeeORM.EmpName)
                .all()
            )
            return [
                ParticipantInfo(
                    emp_no=emp.EmpNo,
                    emp_name=emp.EmpName,
                    department=emp.Department,
                )
                for _, emp in rows
            ]

    def get_participant_emp_nos(self, event_id: int) -> list[str]:
        """Return just the EmpNos for an event."""
        with get_session() as session:
            rows = (
                session.query(EventParticipantORM.EmpNo)
                .filter(EventParticipantORM.EventID == event_id)
                .all()
            )
            return [r[0] for r in rows]

    def deactivate_event(self, event_id: int) -> None:
        """Mark an event as inactive."""
        with get_session() as session:
            event = session.query(EventORM).get(event_id)
            if event:
                event.IsActive = False
