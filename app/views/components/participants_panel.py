"""
app/views/components/participants_panel.py
-------------------------------------------
Live participant list for both Department Mode and Event Mode.
Searchable table showing all participants with Won? status.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QLineEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QColor

from app.controllers import RaffleController
from app.services    import EventService
from config.settings import COLORS


class ParticipantsPanel(QWidget):
    """
    Live participant list for both modes.
    - Department mode: shows employees from the uploaded CSV session.
    - Event mode: shows participants linked to the active event.
    """

    def __init__(self, controller: RaffleController, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = controller
        self._event_service = EventService()
        self._all_participants: list = []
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        self._title_lbl = QLabel("👥  Participants")
        self._title_lbl.setObjectName("title")
        header.addWidget(self._title_lbl)
        header.addStretch()

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        header.addWidget(self._count_lbl)

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        # Search
        search_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍  Search by name, EmpNo, or department...")
        self._search_edit.setStyleSheet(f"""
            background-color: {COLORS['bg_card2']}; border: 1px solid {COLORS['border']};
            border-radius: 8px; padding: 8px 14px; color: {COLORS['text_primary']};
        """)
        self._search_edit.textChanged.connect(self._filter)
        search_row.addWidget(self._search_edit)
        root.addLayout(search_row)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["EmpNo", "Name", "Department", "Won?"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().hide()
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"QTableWidget {{ alternate-background-color: {COLORS['bg_card2']}; }}")
        root.addWidget(self._table)

    def _connect_signals(self) -> None:
        self._ctrl.session_updated.connect(self.refresh)
        self._ctrl.draw_completed.connect(lambda _: self.refresh())
        self._ctrl.grand_confirmed.connect(lambda _: self.refresh())

    # ── Data loading ───────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload participants based on current mode."""
        mode = self._ctrl.get_mode()

        if mode == "department":
            self._refresh_department_mode()
        else:
            self._refresh_event_mode()

    def _refresh_department_mode(self) -> None:
        """Load participants from the session CSV whitelist."""
        self._title_lbl.setText("👥  Session Participants")

        session_emp_nos = self._ctrl.get_session_participants()
        if not session_emp_nos:
            self._table.setRowCount(0)
            self._count_lbl.setText("No participants loaded")
            return

        # Get Employee objects for the whitelist
        employees = self._ctrl.get_session_employees()

        # Build unified participant-like objects
        all_winners = self._ctrl.load_all_winners()
        winner_emp_nos = {w.emp_no for w in all_winners}

        self._all_participants = []
        for emp in employees:
            self._all_participants.append(_Participant(
                emp_no=emp.emp_no,
                emp_name=emp.emp_name,
                department=emp.department,
                has_won=emp.emp_no in winner_emp_nos,
            ))

        self._count_lbl.setText(f"{len(self._all_participants)} participants")
        self._populate(self._all_participants)

    def _refresh_event_mode(self) -> None:
        """Load participants from the active event."""
        self._title_lbl.setText("👥  Event Participants")

        event_id = self._ctrl.get_event_id()
        if not event_id:
            self._table.setRowCount(0)
            self._count_lbl.setText("No active event")
            return

        raw_participants = self._event_service.get_participants(event_id)

        # Check who has won
        all_winners = self._ctrl.load_all_winners()
        winner_emp_nos = {w.emp_no for w in all_winners}

        self._all_participants = []
        for p in raw_participants:
            self._all_participants.append(_Participant(
                emp_no=p.emp_no,
                emp_name=p.emp_name,
                department=p.department,
                has_won=p.emp_no in winner_emp_nos,
            ))

        self._count_lbl.setText(f"{len(self._all_participants)} participants")
        self._populate(self._all_participants)

    # ── Filtering ──────────────────────────────────────────────────

    def _filter(self, text: str) -> None:
        """Filter displayed participants by search text."""
        query = text.lower().strip()
        if not query:
            self._populate(self._all_participants)
            return

        filtered = [
            p for p in self._all_participants
            if query in p.emp_no.lower()
            or query in p.emp_name.lower()
            or query in p.department.lower()
        ]
        self._populate(filtered)

    def _populate(self, participants: list) -> None:
        self._table.setRowCount(0)
        for i, p in enumerate(participants):
            self._table.insertRow(i)

            empno = QTableWidgetItem(p.emp_no)
            empno.setForeground(QColor(COLORS['accent_blue']))
            empno.setFont(QFont("Consolas", 11, QFont.Bold))
            self._table.setItem(i, 0, empno)

            self._table.setItem(i, 1, QTableWidgetItem(p.emp_name))
            self._table.setItem(i, 2, QTableWidgetItem(p.department))

            won_item = QTableWidgetItem("Yes" if p.has_won else "No")
            won_item.setTextAlignment(Qt.AlignCenter)
            if p.has_won:
                won_item.setForeground(QColor(COLORS['accent_gold']))
                won_item.setFont(QFont("Segoe UI", 11, QFont.Bold))
            else:
                won_item.setForeground(QColor(COLORS['text_muted']))
            self._table.setItem(i, 3, won_item)


class _Participant:
    """Lightweight participant data holder (used by both modes)."""
    __slots__ = ("emp_no", "emp_name", "department", "has_won")

    def __init__(self, emp_no: str, emp_name: str, department: str, has_won: bool = False):
        self.emp_no = emp_no
        self.emp_name = emp_name
        self.department = department
        self.has_won = has_won
