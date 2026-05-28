"""
app/views/components/diy_panel.py
-----------------------------------
DIY Mode panel — manual entry or CSV upload to build a custom participant list.
Session-only (in-memory). Not persisted to DB.
"""

import csv
import os
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTabWidget, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui  import QFont, QColor

from app.controllers import RaffleController
from config.settings import COLORS


class DIYPanel(QWidget):
    """
    DIY Mode participant builder.
    Two input tabs: Manual Entry and CSV Upload.
    Participants are stored in-memory via the controller.
    """

    # Emitted when user clicks "Proceed to Draw"
    proceed_to_draw = Signal()

    def __init__(self, controller: RaffleController, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = controller
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Title
        title = QLabel("✏  DIY Mode — Build Your Participant List")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        root.addWidget(title)

        desc = QLabel(
            "Add participants manually or upload a CSV file. "
            "Only people in this list are eligible to win."
        )
        desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        desc.setWordWrap(True)
        root.addWidget(desc)

        # Input tabs
        input_tabs = QTabWidget()
        input_tabs.setDocumentMode(True)
        input_tabs.addTab(self._build_manual_tab(), "📝  Manual Entry")
        input_tabs.addTab(self._build_csv_tab(), "📂  Upload CSV")
        root.addWidget(input_tabs)

        # Participant table
        table_header = QHBoxLayout()
        self._count_lbl = QLabel("Current Participants (0):")
        self._count_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._count_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        table_header.addWidget(self._count_lbl)
        table_header.addStretch()

        clear_btn = QPushButton("🗑  Clear All")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['accent_red']};
                border: 1px solid {COLORS['accent_red']}; border-radius: 6px;
                padding: 4px 14px; font-weight: 600; font-size: 11px;
            }}
            QPushButton:hover {{ background: {COLORS['accent_red']}; color: #fff; }}
        """)
        clear_btn.clicked.connect(self._on_clear_all)
        table_header.addWidget(clear_btn)
        root.addLayout(table_header)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["EmpNo", "Name", "Department", ""])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.setColumnWidth(3, 80)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().hide()
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            f"QTableWidget {{ alternate-background-color: {COLORS['bg_card2']}; }}"
        )
        root.addWidget(self._table)

        # Bottom bar
        bottom = QHBoxLayout()
        bottom.addStretch()

        self._proceed_btn = QPushButton("▶  Proceed to Draw")
        self._proceed_btn.setCursor(Qt.PointingHandCursor)
        self._proceed_btn.setFixedHeight(44)
        self._proceed_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['accent_blue']}, stop:1 #5a8dee);
                color: #fff; border: none; border-radius: 10px;
                padding: 0 32px; font-size: 14px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #5a8dee; }}
            QPushButton:disabled {{ background: {COLORS['bg_card2']}; color: {COLORS['text_muted']}; }}
        """)
        self._proceed_btn.setEnabled(False)
        self._proceed_btn.clicked.connect(self.proceed_to_draw.emit)
        bottom.addWidget(self._proceed_btn)
        root.addLayout(bottom)

    def _build_manual_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        # Form fields
        form = QHBoxLayout()

        # EmpNo
        emp_col = QVBoxLayout()
        emp_col.addWidget(QLabel("EmpNo:"))
        self._emp_no_edit = QLineEdit()
        self._emp_no_edit.setPlaceholderText("e.g. EMP001")
        self._emp_no_edit.setStyleSheet(self._input_style())
        self._emp_no_edit.editingFinished.connect(self._on_empno_lookup)
        emp_col.addWidget(self._emp_no_edit)
        form.addLayout(emp_col)

        # EmpName
        name_col = QVBoxLayout()
        name_col.addWidget(QLabel("Name:"))
        self._emp_name_edit = QLineEdit()
        self._emp_name_edit.setPlaceholderText("Full name")
        self._emp_name_edit.setStyleSheet(self._input_style())
        name_col.addWidget(self._emp_name_edit)
        form.addLayout(name_col, 2)

        # Department
        dept_col = QVBoxLayout()
        dept_col.addWidget(QLabel("Department:"))
        self._dept_edit = QLineEdit()
        self._dept_edit.setPlaceholderText("e.g. Engineering")
        self._dept_edit.setStyleSheet(self._input_style())
        dept_col.addWidget(self._dept_edit)
        form.addLayout(dept_col)

        layout.addLayout(form)

        # Error label
        self._manual_error = QLabel("")
        self._manual_error.setStyleSheet(f"color: {COLORS['accent_red']}; font-size: 11px;")
        layout.addWidget(self._manual_error)

        # Add button
        add_btn = QPushButton("+ Add to List")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(36)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_green']}; color: #fff;
                border: none; border-radius: 8px; font-weight: 700;
                padding: 0 24px;
            }}
            QPushButton:hover {{ background: #38c97a; }}
        """)
        add_btn.clicked.connect(self._on_add_manual)
        layout.addWidget(add_btn, alignment=Qt.AlignRight)

        return page

    def _build_csv_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        # Template download
        dl_btn = QPushButton("⬇  Download CSV Template")
        dl_btn.setCursor(Qt.PointingHandCursor)
        dl_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['accent_blue']};
                border: 1px solid {COLORS['accent_blue']}; border-radius: 8px;
                padding: 8px 20px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['accent_blue']}; color: #fff; }}
        """)
        dl_btn.clicked.connect(self._on_download_template)
        layout.addWidget(dl_btn, alignment=Qt.AlignLeft)

        # File picker
        file_row = QHBoxLayout()
        choose_btn = QPushButton("📂  Choose CSV File")
        choose_btn.setCursor(Qt.PointingHandCursor)
        choose_btn.setStyleSheet(self._input_style() + " padding: 8px 16px;")
        choose_btn.clicked.connect(self._on_choose_csv)
        file_row.addWidget(choose_btn)

        self._csv_path_lbl = QLabel("No file selected")
        self._csv_path_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        file_row.addWidget(self._csv_path_lbl, 1)
        layout.addLayout(file_row)

        # Preview count
        self._csv_preview_lbl = QLabel("")
        self._csv_preview_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(self._csv_preview_lbl)

        # Load button
        self._load_csv_btn = QPushButton("Load into List")
        self._load_csv_btn.setCursor(Qt.PointingHandCursor)
        self._load_csv_btn.setFixedHeight(36)
        self._load_csv_btn.setEnabled(False)
        self._load_csv_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_green']}; color: #fff;
                border: none; border-radius: 8px; font-weight: 700;
                padding: 0 24px;
            }}
            QPushButton:hover {{ background: #38c97a; }}
            QPushButton:disabled {{ background: {COLORS['bg_card2']}; color: {COLORS['text_muted']}; }}
        """)
        self._load_csv_btn.clicked.connect(self._on_load_csv)
        layout.addWidget(self._load_csv_btn, alignment=Qt.AlignRight)

        self._csv_rows: list[dict] = []
        self._csv_path: str = ""

        return page

    # ── Signal wiring ──────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._ctrl.diy_list_updated.connect(self._refresh_table)

    # ── Manual entry handlers ──────────────────────────────────────

    def _on_empno_lookup(self) -> None:
        """Auto-fill name/dept from _Employees if EmpNo matches."""
        emp_no = self._emp_no_edit.text().strip()
        if not emp_no:
            return
        emp = self._ctrl.lookup_employee(emp_no)
        if emp:
            self._emp_name_edit.setText(emp.emp_name)
            self._dept_edit.setText(emp.department)

    def _on_add_manual(self) -> None:
        emp_no = self._emp_no_edit.text().strip()
        emp_name = self._emp_name_edit.text().strip()
        dept = self._dept_edit.text().strip()

        if not emp_no or not emp_name or not dept:
            self._manual_error.setText("All fields are required.")
            return

        added = self._ctrl.add_diy_participant(emp_no, emp_name, dept)
        if not added:
            self._manual_error.setText(f"EmpNo '{emp_no}' already in list.")
            return

        self._manual_error.setText("")
        self._emp_no_edit.clear()
        self._emp_name_edit.clear()
        self._dept_edit.clear()
        self._emp_no_edit.setFocus()

    # ── CSV handlers ───────────────────────────────────────────────

    def _on_download_template(self) -> None:
        template = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "assets", "participant_template.csv",
        )
        template = os.path.abspath(template)
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save CSV Template", "participant_template.csv",
            "CSV Files (*.csv)",
        )
        if dest:
            try:
                shutil.copy2(template, dest)
                QMessageBox.information(self, "Saved", f"Template saved to:\n{dest}")
            except Exception as exc:
                QMessageBox.warning(self, "Error", str(exc))

    def _on_choose_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv)",
        )
        if not path:
            return

        self._csv_path = path
        self._csv_path_lbl.setText(f"✓ {os.path.basename(path)}")

        # Parse and preview
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                required = {"EmpNo", "EmpName", "Department"}
                if not reader.fieldnames or required - set(reader.fieldnames):
                    self._csv_preview_lbl.setText(
                        f"❌ Missing columns: {required - set(reader.fieldnames or [])}"
                    )
                    self._load_csv_btn.setEnabled(False)
                    return

                self._csv_rows = []
                for row in reader:
                    emp_no = row.get("EmpNo", "").strip()
                    emp_name = row.get("EmpName", "").strip()
                    dept = row.get("Department", "").strip()
                    if emp_no and emp_name and dept:
                        self._csv_rows.append({
                            "EmpNo": emp_no, "EmpName": emp_name, "Department": dept,
                        })

                self._csv_preview_lbl.setText(
                    f"Preview: {len(self._csv_rows)} valid participant(s)"
                )
                self._load_csv_btn.setEnabled(len(self._csv_rows) > 0)
        except Exception as exc:
            self._csv_preview_lbl.setText(f"❌ Error: {exc}")
            self._load_csv_btn.setEnabled(False)

    def _on_load_csv(self) -> None:
        """Load parsed CSV rows into the controller's DIY list."""
        added = 0
        skipped = 0
        for row in self._csv_rows:
            ok = self._ctrl.add_diy_participant(
                row["EmpNo"], row["EmpName"], row["Department"],
            )
            if ok:
                added += 1
            else:
                skipped += 1

        self._csv_preview_lbl.setText(
            f"✅ Loaded {added} participant(s)"
            + (f", {skipped} duplicate(s) skipped" if skipped else "")
        )
        self._csv_rows = []
        self._load_csv_btn.setEnabled(False)

    # ── Clear all ──────────────────────────────────────────────────

    def _on_clear_all(self) -> None:
        if not self._ctrl.get_diy_participants():
            return
        reply = QMessageBox.question(
            self, "Clear All",
            "Remove all participants from the DIY list?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._ctrl.clear_diy_participants()

    # ── Table refresh ──────────────────────────────────────────────

    def _refresh_table(self) -> None:
        participants = self._ctrl.get_diy_participants()
        self._count_lbl.setText(f"Current Participants ({len(participants)}):")
        self._proceed_btn.setEnabled(len(participants) > 0)

        self._table.setRowCount(0)
        for i, p in enumerate(participants):
            self._table.insertRow(i)

            empno = QTableWidgetItem(p["EmpNo"])
            empno.setForeground(QColor(COLORS['accent_blue']))
            empno.setFont(QFont("Consolas", 11, QFont.Bold))
            self._table.setItem(i, 0, empno)

            self._table.setItem(i, 1, QTableWidgetItem(p["EmpName"]))
            self._table.setItem(i, 2, QTableWidgetItem(p["Department"]))

            remove_btn = QPushButton("Remove")
            remove_btn.setCursor(Qt.PointingHandCursor)
            remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {COLORS['accent_red']};
                    border: none; font-size: 11px; font-weight: 600;
                }}
                QPushButton:hover {{ text-decoration: underline; }}
            """)
            emp_no = p["EmpNo"]
            remove_btn.clicked.connect(lambda _, eno=emp_no: self._ctrl.remove_diy_participant(eno))
            self._table.setCellWidget(i, 3, remove_btn)

    # ── Helpers ────────────────────────────────────────────────────

    def _input_style(self) -> str:
        return f"""
            background-color: {COLORS['bg_card2']}; border: 1px solid {COLORS['border']};
            border-radius: 6px; padding: 6px 10px; color: {COLORS['text_primary']};
        """
