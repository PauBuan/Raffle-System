"""
app/views/dialogs/event_wizard.py
----------------------------------
Multi-step event creation wizard for Event Mode.
Step 1: Event details → Step 2: Upload CSV → Step 3: Confirm & Create
"""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QColor

from app.controllers.admin_controller import AdminController
from config.settings import COLORS


class EventWizard(QDialog):
    """
    3-step wizard for creating a new event with CSV participant import.
    """

    def __init__(self, admin_ctrl: AdminController, parent=None) -> None:
        super().__init__(parent)
        self._admin_ctrl = admin_ctrl
        self._csv_path = ""
        self._event_name = ""
        self._event_id = None
        self._preview_rows: list[dict] = []

        self.setWindowTitle("New Event Setup")
        self.setFixedSize(620, 520)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("wizard_card")
        card.setStyleSheet(f"""
            QFrame#wizard_card {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        card.setGraphicsEffect(shadow)

        root = QVBoxLayout(card)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(6)

        # Header
        header = QHBoxLayout()
        title = QLabel("🎉  New Event Setup")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_gold']}; background: transparent;")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("X")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['text_muted']};
                border: none; font-size: 16px; font-weight: 700; border-radius: 16px;
            }}
            QPushButton:hover {{ background: {COLORS['accent_red']}; color: #fff; }}
        """)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        root.addLayout(header)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {COLORS['border']};")
        root.addWidget(div)
        root.addSpacing(8)

        # Stacked pages
        self._pages = QStackedWidget()

        # Step 1 — Event Name
        self._pages.addWidget(self._build_step1())
        # Step 2 — Upload CSV
        self._pages.addWidget(self._build_step2())
        # Step 3 — Confirm
        self._pages.addWidget(self._build_step3())

        root.addWidget(self._pages)
        outer.addWidget(card)

    def _build_step1(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        step = QLabel("Step 1 of 3 — Event Details")
        step.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; letter-spacing: 1px;")
        layout.addWidget(step)

        layout.addSpacing(12)

        lbl = QLabel("EVENT NAME")
        lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600; letter-spacing: 1px;")
        layout.addWidget(lbl)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Annual Raffle 2025")
        self._name_edit.setStyleSheet(f"""
            background-color: {COLORS['bg_card2']}; border: 1px solid {COLORS['border']};
            border-radius: 8px; padding: 10px 14px; color: {COLORS['text_primary']}; font-size: 14px;
        """)
        layout.addWidget(self._name_edit)

        self._step1_error = QLabel("")
        self._step1_error.setStyleSheet(f"color: {COLORS['accent_red']}; font-size: 11px;")
        self._step1_error.hide()
        layout.addWidget(self._step1_error)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        next_btn = self._make_primary_btn("Next →")
        next_btn.clicked.connect(self._go_step2)
        btn_row.addWidget(next_btn)
        layout.addLayout(btn_row)

        return page

    def _build_step2(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        step = QLabel("Step 2 of 3 — Upload Participants")
        step.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; letter-spacing: 1px;")
        layout.addWidget(step)

        layout.addSpacing(6)

        # Template download
        tmpl_row = QHBoxLayout()
        tmpl_lbl = QLabel("CSV Template (EmpNo, EmpName, Department):")
        tmpl_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        tmpl_row.addWidget(tmpl_lbl)
        tmpl_row.addStretch()

        tmpl_btn = QPushButton("⬇  Download Template")
        tmpl_btn.setCursor(Qt.PointingHandCursor)
        tmpl_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['accent_blue']};
                border: 1px solid {COLORS['accent_blue']}; border-radius: 6px;
                padding: 4px 14px; font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_blue']}; color: #000; }}
        """)
        tmpl_btn.clicked.connect(self._download_template)
        tmpl_row.addWidget(tmpl_btn)
        layout.addLayout(tmpl_row)

        # File picker
        file_row = QHBoxLayout()
        self._file_lbl = QLabel("No file selected")
        self._file_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        file_row.addWidget(self._file_lbl)
        file_row.addStretch()
        choose_btn = QPushButton("📂  Choose CSV File")
        choose_btn.setCursor(Qt.PointingHandCursor)
        choose_btn.clicked.connect(self._choose_csv)
        file_row.addWidget(choose_btn)
        layout.addLayout(file_row)

        # Preview table
        preview_lbl = QLabel("Preview (first 5 rows):")
        preview_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(preview_lbl)

        self._preview_table = QTableWidget()
        self._preview_table.setColumnCount(3)
        self._preview_table.setHorizontalHeaderLabels(["EmpNo", "EmpName", "Department"])
        self._preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._preview_table.verticalHeader().hide()
        self._preview_table.setMaximumHeight(160)
        layout.addWidget(self._preview_table)

        self._parsed_lbl = QLabel("")
        self._parsed_lbl.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 12px;")
        layout.addWidget(self._parsed_lbl)

        layout.addStretch()

        btn_row = QHBoxLayout()
        back_btn = self._make_secondary_btn("← Back")
        back_btn.clicked.connect(lambda: self._pages.setCurrentIndex(0))
        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        next_btn = self._make_primary_btn("Next →")
        next_btn.clicked.connect(self._go_step3)
        btn_row.addWidget(next_btn)
        layout.addLayout(btn_row)

        return page

    def _build_step3(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        step = QLabel("Step 3 of 3 — Confirm & Create")
        step.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; letter-spacing: 1px;")
        layout.addWidget(step)

        layout.addSpacing(12)

        self._confirm_info = QLabel("")
        self._confirm_info.setWordWrap(True)
        self._confirm_info.setStyleSheet(f"""
            color: {COLORS['text_primary']}; font-size: 14px;
            background: {COLORS['bg_card2']}; border-radius: 8px;
            padding: 16px; border: 1px solid {COLORS['border']};
        """)
        layout.addWidget(self._confirm_info)

        layout.addStretch()

        btn_row = QHBoxLayout()
        back_btn = self._make_secondary_btn("← Back")
        back_btn.clicked.connect(lambda: self._pages.setCurrentIndex(1))
        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        create_btn = self._make_primary_btn("✓  Create Event & Start")
        create_btn.clicked.connect(self._create_event)
        btn_row.addWidget(create_btn)
        layout.addLayout(btn_row)

        return page

    # ── Navigation ─────────────────────────────────────────────────

    def _go_step2(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._step1_error.setText("Event name is required.")
            self._step1_error.show()
            return
        self._event_name = name
        self._step1_error.hide()
        self._pages.setCurrentIndex(1)

    def _go_step3(self) -> None:
        if not self._csv_path:
            return
        # Collect unique departments from preview
        depts = sorted(set(r.get("Department", "") for r in self._preview_rows if r.get("Department")))
        self._confirm_info.setText(
            f"Event Name:    {self._event_name}\n"
            f"Participants:  {len(self._preview_rows)} employees\n"
            f"Departments:   {', '.join(depts) if depts else 'N/A'}"
        )
        self._pages.setCurrentIndex(2)

    def _create_event(self) -> None:
        """Create event, import CSV, and close."""
        eid = self._admin_ctrl.create_event(self._event_name)
        if eid:
            self._event_id = eid
            result = self._admin_ctrl.import_csv(self._csv_path, eid)
            # Could show result summary, but just accept for now
            self.accept()

    # ── File handling ──────────────────────────────────────────────

    def _choose_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Participant CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return
        self._csv_path = path
        self._file_lbl.setText(f"Selected: {os.path.basename(path)}  ✓")
        self._file_lbl.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 12px;")
        self._parse_preview()

    def _parse_preview(self) -> None:
        """Parse first 5 rows of CSV for preview."""
        import csv
        self._preview_rows = []
        try:
            with open(self._csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._preview_rows.append(row)

            # Show first 5
            self._preview_table.setRowCount(0)
            for i, row in enumerate(self._preview_rows[:5]):
                self._preview_table.insertRow(i)
                self._preview_table.setItem(i, 0, QTableWidgetItem(row.get("EmpNo", "")))
                self._preview_table.setItem(i, 1, QTableWidgetItem(row.get("EmpName", "")))
                self._preview_table.setItem(i, 2, QTableWidgetItem(row.get("Department", "")))

            self._parsed_lbl.setText(f"Parsed: {len(self._preview_rows)} employees")
        except Exception as exc:
            self._parsed_lbl.setText(f"Error: {exc}")
            self._parsed_lbl.setStyleSheet(f"color: {COLORS['accent_red']}; font-size: 12px;")

    def _download_template(self) -> None:
        """Save the CSV template to a user-chosen path."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV Template", "participant_template.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write("EmpNo,EmpName,Department\n")

    def get_event_id(self) -> int | None:
        return self._event_id

    # ── Button helpers ─────────────────────────────────────────────

    def _make_primary_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_gold']}; color: #000; border: none;
                border-radius: 8px; padding: 0 28px; font-weight: 700; font-size: 13px;
            }}
            QPushButton:hover {{ background: #ffe94d; }}
        """)
        return btn

    def _make_secondary_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']}; border-radius: 8px;
                padding: 0 24px; font-weight: 600; font-size: 13px;
            }}
            QPushButton:hover {{ border-color: {COLORS['text_primary']}; color: {COLORS['text_primary']}; }}
        """)
        return btn

    # Allow dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
