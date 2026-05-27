"""
app/views/dialogs/session_setup_dialog.py
-------------------------------------------
Department Mode session setup dialog.
Prompts the user for a Raffle Session name and CSV participant file.
Includes a downloadable sample CSV template.
"""

import os
import csv
import shutil

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from config.settings import COLORS


# Path to the bundled template
_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "assets", "participant_template.csv"
)


class SessionSetupDialog(QDialog):
    """
    Department‑Mode session setup.
    Collects a session name and an optional CSV upload before entering the draw UI.

    Attributes after accepted:
        session_name  (str)   — user‑entered raffle session name
        csv_path      (str)   — selected CSV path (empty if skipped)
        preview_rows  (list)  — parsed rows from the CSV (may be empty)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.session_name = ""
        self.csv_path = ""
        self.preview_rows: list[dict] = []

        self.setWindowTitle("Raffle Session Setup")
        self.setFixedSize(620, 560)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────

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
        root.setSpacing(8)

        # ── Header ─────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("🏢  Raffle Session Setup")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(
            f"color: {COLORS['accent_gold']}; background: transparent;"
        )
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("X")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['text_muted']};
                border: none; font-size: 16px; font-weight: 700;
                border-radius: 16px;
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
        root.addSpacing(12)

        # ── Session Name ───────────────────────────────────────────
        name_lbl = QLabel("SESSION NAME")
        name_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; "
            f"font-weight: 600; letter-spacing: 1px;"
        )
        root.addWidget(name_lbl)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Midyear Raffle 2025")
        self._name_edit.setStyleSheet(f"""
            background-color: {COLORS['bg_card2']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px; padding: 10px 14px;
            color: {COLORS['text_primary']}; font-size: 14px;
        """)
        root.addWidget(self._name_edit)

        self._name_error = QLabel("")
        self._name_error.setStyleSheet(
            f"color: {COLORS['accent_red']}; font-size: 11px;"
        )
        self._name_error.hide()
        root.addWidget(self._name_error)

        root.addSpacing(10)

        # ── CSV Upload ─────────────────────────────────────────────
        csv_header = QLabel("UPLOAD PARTICIPANTS (CSV)")
        csv_header.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; "
            f"font-weight: 600; letter-spacing: 1px;"
        )
        root.addWidget(csv_header)

        # Template download row
        tmpl_row = QHBoxLayout()
        tmpl_lbl = QLabel("Format: EmpNo, EmpName, Department")
        tmpl_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px;"
        )
        tmpl_row.addWidget(tmpl_lbl)
        tmpl_row.addStretch()

        tmpl_btn = QPushButton("⬇  Download Sample CSV")
        tmpl_btn.setCursor(Qt.PointingHandCursor)
        tmpl_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['accent_blue']};
                border: 1px solid {COLORS['accent_blue']};
                border-radius: 6px; padding: 4px 14px;
                font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_blue']}; color: #000;
            }}
        """)
        tmpl_btn.clicked.connect(self._download_template)
        tmpl_row.addWidget(tmpl_btn)
        root.addLayout(tmpl_row)

        # File picker
        file_row = QHBoxLayout()
        self._file_lbl = QLabel("No file selected")
        self._file_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px;"
        )
        file_row.addWidget(self._file_lbl)
        file_row.addStretch()

        choose_btn = QPushButton("📂  Choose CSV")
        choose_btn.setCursor(Qt.PointingHandCursor)
        choose_btn.clicked.connect(self._choose_csv)
        file_row.addWidget(choose_btn)
        root.addLayout(file_row)

        # Preview table
        preview_lbl = QLabel("Preview (first 5 rows):")
        preview_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px;"
        )
        root.addWidget(preview_lbl)

        self._preview_table = QTableWidget()
        self._preview_table.setColumnCount(3)
        self._preview_table.setHorizontalHeaderLabels(
            ["EmpNo", "EmpName", "Department"]
        )
        self._preview_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self._preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._preview_table.verticalHeader().hide()
        self._preview_table.setMaximumHeight(140)
        root.addWidget(self._preview_table)

        self._parsed_lbl = QLabel("")
        self._parsed_lbl.setStyleSheet(
            f"color: {COLORS['accent_green']}; font-size: 12px;"
        )
        root.addWidget(self._parsed_lbl)

        root.addStretch()

        # ── Buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        start_btn = QPushButton("✓  Start Raffle Session")
        start_btn.setFixedHeight(42)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_gold']}; color: #000;
                border: none; border-radius: 8px;
                padding: 0 32px; font-weight: 700; font-size: 14px;
            }}
            QPushButton:hover {{ background: #ffe94d; }}
        """)
        start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(start_btn)
        root.addLayout(btn_row)

        outer.addWidget(card)

    # ── Actions ────────────────────────────────────────────────────

    def _on_start(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._name_error.setText("Please enter a session name.")
            self._name_error.show()
            return
        if not self.csv_path:
            self._name_error.setText("Please upload a CSV file.")
            self._name_error.show()
            return

        self._name_error.hide()
        self.session_name = name
        self.accept()

    def _choose_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Participant CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return
        self.csv_path = path
        self._file_lbl.setText(f"Selected: {os.path.basename(path)}  ✓")
        self._file_lbl.setStyleSheet(
            f"color: {COLORS['accent_green']}; font-size: 12px;"
        )
        self._parse_preview()

    def _parse_preview(self) -> None:
        """Parse first rows of CSV for preview."""
        self.preview_rows = []
        try:
            with open(self.csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.preview_rows.append(row)

            self._preview_table.setRowCount(0)
            for i, row in enumerate(self.preview_rows[:5]):
                self._preview_table.insertRow(i)
                self._preview_table.setItem(
                    i, 0, QTableWidgetItem(row.get("EmpNo", ""))
                )
                self._preview_table.setItem(
                    i, 1, QTableWidgetItem(row.get("EmpName", ""))
                )
                self._preview_table.setItem(
                    i, 2, QTableWidgetItem(row.get("Department", ""))
                )

            self._parsed_lbl.setText(
                f"Parsed: {len(self.preview_rows)} employees"
            )
            self._parsed_lbl.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-size: 12px;"
            )
            self._name_error.hide()
        except Exception as exc:
            self._parsed_lbl.setText(f"Error: {exc}")
            self._parsed_lbl.setStyleSheet(
                f"color: {COLORS['accent_red']}; font-size: 12px;"
            )

    def _download_template(self) -> None:
        """Save the sample CSV template to a user-chosen location."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Sample CSV Template",
            "participant_template.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        # Copy bundled template or write fresh
        if os.path.isfile(_TEMPLATE_PATH):
            shutil.copy2(_TEMPLATE_PATH, path)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write("EmpNo,EmpName,Department\n")

    # ── Dragging ───────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, "_drag_pos") and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
