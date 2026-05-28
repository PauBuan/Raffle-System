"""
app/services/event_service.py
------------------------------
Business logic for Event Mode — event session naming and tracking.

v3.0 changes:
    - Removed import_csv() — CSV upload moved to DIY Mode
    - Event Mode now draws from full _Employees table (no filtered participant list)
    - Events are purely for audit traceability (session naming)
"""

import logging

from app.models import EventRepository, EventInfo

logger = logging.getLogger(__name__)


class EventService:
    """Event lifecycle — create, query, deactivate sessions for audit."""

    def __init__(self) -> None:
        self._events = EventRepository()

    def create_event(self, event_name: str) -> int:
        """Create a new event session; returns EventID."""
        event_id = self._events.create_event(event_name)
        logger.info("Created event '%s' (ID=%d)", event_name, event_id)
        return event_id

    def get_active_events(self) -> list[EventInfo]:
        return self._events.get_active_events()

    def get_event_by_id(self, event_id: int) -> EventInfo | None:
        return self._events.get_event_by_id(event_id)

    def deactivate_event(self, event_id: int) -> None:
        self._events.deactivate_event(event_id)
        logger.info("Deactivated event ID=%d", event_id)
