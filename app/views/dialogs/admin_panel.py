"""
app/views/dialogs/admin_panel.py
---------------------------------
Admin Panel dialog — opened from Dev Mode login.
Features: Department Grouping, Win Chance Weighting, Grand building allocation.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSpinBox, QLineEdit, QListWidget, QListWidgetItem,
    QGraphicsDropShadowEffect, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QColor

from app.controllers.admin_controller import AdminController
from config.settings import COLORS


class AdminPanel(QDialog):
    """Modal admin panel for group management and win chance boosts."""

    def __init__(self, admin_ctrl: AdminController, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = admin_ctrl

        self.setWindowTitle("Admin Panel — ⚠ DEV MODE")
        self.setMinimumSize(750, 550)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text_primary']};
            }}
        """)

        self._build_ui()
        self._refresh_groups()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("⚙  Admin Panel")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_red']};")
        header.addWidget(title)
        header.addStretch()

        admin_lbl = QLabel(f"Admin: {self._ctrl.get_admin_name()}")
        admin_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        header.addWidget(admin_lbl)
        root.addLayout(header)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {COLORS['border']};")
        root.addWidget(div)

        # Tabs
        tabs = QTabWidget()

        tabs.addTab(self._build_group_tab(), "📁  Group Management")
        tabs.addTab(self._build_boost_tab(), "🎯  Win Chance Boost")
        root.addWidget(tabs)

        # Close button
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close Admin Panel")
        close_btn.setFixedHeight(40)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']}; border-radius: 8px;
                padding: 0 28px; font-weight: 600;
            }}
            QPushButton:hover {{ border-color: {COLORS['text_primary']}; color: {COLORS['text_primary']}; }}
        """)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

    # ── Group Management Tab ───────────────────────────────────────

    def _build_group_tab(self) -> QTabWidget:
        page = QTabWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # Group list table
        self._group_table = QTableWidget()
        self._group_table.setColumnCount(4)
        self._group_table.setHorizontalHeaderLabels(["Group Name", "Building Tag", "Allocated Prizes", "Departments"])
        self._group_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._group_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._group_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._group_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._group_table.verticalHeader().hide()
        self._group_table.setAlternatingRowColors(True)
        self._group_table.setStyleSheet(f"QTableWidget {{ alternate-background-color: {COLORS['bg_card2']}; }}")
        layout.addWidget(self._group_table)

        # Group controls
        ctrl_row = QHBoxLayout()

        self._group_name_edit = QLineEdit()
        self._group_name_edit.setPlaceholderText("Group name")
        self._group_name_edit.setStyleSheet(f"""
            background-color: {COLORS['bg_card2']}; border: 1px solid {COLORS['border']};
            border-radius: 6px; padding: 6px 10px; color: {COLORS['text_primary']};
        """)
        ctrl_row.addWidget(self._group_name_edit)

        self._building_tag_combo = QComboBox()
        self._building_tag_combo.addItems(["(None)", "LTI", "CIP"])
        ctrl_row.addWidget(self._building_tag_combo)

        self._alloc_spin = QSpinBox()
        self._alloc_spin.setMinimum(0)
        self._alloc_spin.setMaximum(100)
        self._alloc_spin.setPrefix("Allocated: ")
        ctrl_row.addWidget(self._alloc_spin)

        add_group_btn = QPushButton("+ Add Group")
        add_group_btn.setCursor(Qt.PointingHandCursor)
        add_group_btn.clicked.connect(self._on_add_group)
        ctrl_row.addWidget(add_group_btn)

        del_group_btn = QPushButton("🗑 Delete")
        del_group_btn.setObjectName("btn_danger")
        del_group_btn.setCursor(Qt.PointingHandCursor)
        del_group_btn.clicked.connect(self._on_delete_group)
        ctrl_row.addWidget(del_group_btn)

        layout.addLayout(ctrl_row)

        # Department assignment
        dept_row = QHBoxLayout()
        dept_lbl = QLabel("Add dept to selected group:")
        dept_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
        dept_row.addWidget(dept_lbl)

        self._dept_combo = QComboBox()
        for d in self._ctrl.get_all_departments():
            self._dept_combo.addItem(d)
        dept_row.addWidget(self._dept_combo)

        add_dept_btn = QPushButton("+ Assign")
        add_dept_btn.setCursor(Qt.PointingHandCursor)
        add_dept_btn.clicked.connect(self._on_assign_dept)
        dept_row.addWidget(add_dept_btn)

        layout.addLayout(dept_row)

        return page

    # ── Win Chance Boost Tab ───────────────────────────────────────

    def _build_boost_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # Employee boost
        emp_frame = QFrame()
        emp_frame.setObjectName("card")
        emp_layout = QVBoxLayout(emp_frame)
        emp_layout.setContentsMargins(16, 12, 16, 12)

        emp_title = QLabel("Employee Boost")
        emp_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        emp_title.setStyleSheet(f"color: {COLORS['accent_gold']}; border: none;")
        emp_layout.addWidget(emp_title)

        emp_row = QHBoxLayout()
        emp_search_lbl = QLabel("Employee No:")
        emp_search_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
        emp_row.addWidget(emp_search_lbl)

        self._emp_boost_edit = QLineEdit()
        self._emp_boost_edit.setPlaceholderText("e.g. OJT26A01")
        self._emp_boost_edit.setStyleSheet(f"""
            background-color: {COLORS['bg_card2']}; border: 1px solid {COLORS['border']};
            border-radius: 6px; padding: 6px 10px; color: {COLORS['text_primary']};
        """)
        emp_row.addWidget(self._emp_boost_edit)

        emp_boost_lbl = QLabel("Boost:")
        emp_boost_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
        emp_row.addWidget(emp_boost_lbl)

        self._emp_boost_spin = QSpinBox()
        self._emp_boost_spin.setMinimum(1)
        self._emp_boost_spin.setMaximum(10)
        self._emp_boost_spin.setValue(1)
        emp_row.addWidget(self._emp_boost_spin)

        emp_save = QPushButton("Save Boost")
        emp_save.setCursor(Qt.PointingHandCursor)
        emp_save.clicked.connect(self._on_save_emp_boost)
        emp_row.addWidget(emp_save)

        emp_layout.addLayout(emp_row)
        layout.addWidget(emp_frame)

        # Department boost
        dept_frame = QFrame()
        dept_frame.setObjectName("card")
        dept_layout = QVBoxLayout(dept_frame)
        dept_layout.setContentsMargins(16, 12, 16, 12)

        dept_title = QLabel("Department Boost")
        dept_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        dept_title.setStyleSheet(f"color: {COLORS['accent_blue']}; border: none;")
        dept_layout.addWidget(dept_title)

        self._dept_boost_table = QTableWidget()
        self._dept_boost_table.setColumnCount(2)
        self._dept_boost_table.setHorizontalHeaderLabels(["Department", "Boost Multiplier"])
        self._dept_boost_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._dept_boost_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._dept_boost_table.verticalHeader().hide()
        self._dept_boost_table.setMaximumHeight(180)
        dept_layout.addWidget(self._dept_boost_table)

        dept_ctrl = QHBoxLayout()
        self._dept_boost_combo = QComboBox()
        for d in self._ctrl.get_all_departments():
            self._dept_boost_combo.addItem(d)
        dept_ctrl.addWidget(self._dept_boost_combo)

        self._dept_boost_spin = QSpinBox()
        self._dept_boost_spin.setMinimum(1)
        self._dept_boost_spin.setMaximum(10)
        self._dept_boost_spin.setValue(1)
        dept_ctrl.addWidget(self._dept_boost_spin)

        dept_save = QPushButton("Save Department Boost")
        dept_save.setCursor(Qt.PointingHandCursor)
        dept_save.clicked.connect(self._on_save_dept_boost)
        dept_ctrl.addWidget(dept_save)

        dept_layout.addLayout(dept_ctrl)
        layout.addWidget(dept_frame)

        layout.addStretch()

        # Refresh boosts
        self._refresh_dept_boosts()

        return page

    # ── Group Actions ──────────────────────────────────────────────

    def _refresh_groups(self) -> None:
        groups = self._ctrl.get_all_groups()
        self._group_table.setRowCount(0)
        for i, g in enumerate(groups):
            self._group_table.insertRow(i)
            self._group_table.setItem(i, 0, QTableWidgetItem(g.group_name))
            self._group_table.setItem(i, 1, QTableWidgetItem(g.building_tag or "—"))
            self._group_table.setItem(i, 2, QTableWidgetItem(str(g.allocated_prizes)))
            self._group_table.setItem(i, 3, QTableWidgetItem(", ".join(g.departments)))

    def _on_add_group(self) -> None:
        name = self._group_name_edit.text().strip()
        if not name:
            return
        tag = self._building_tag_combo.currentText()
        if tag == "(None)":
            tag = None
        alloc = self._alloc_spin.value()

        self._ctrl.save_groups([{
            "group_id": None,
            "group_name": name,
            "building_tag": tag,
            "allocated_prizes": alloc,
            "departments": [],
        }])
        self._group_name_edit.clear()
        self._refresh_groups()

    def _on_delete_group(self) -> None:
        row = self._group_table.currentRow()
        if row < 0:
            return
        groups = self._ctrl.get_all_groups()
        if row < len(groups):
            g = groups[row]
            self._ctrl.delete_group(g.group_id, g.group_name)
            self._refresh_groups()

    def _on_assign_dept(self) -> None:
        row = self._group_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select a group first.")
            return
        dept = self._dept_combo.currentText()
        groups = self._ctrl.get_all_groups()
        if row < len(groups):
            g = groups[row]
            if dept not in g.departments:
                g.departments.append(dept)
                self._ctrl.save_groups([{
                    "group_id": g.group_id,
                    "group_name": g.group_name,
                    "building_tag": g.building_tag,
                    "allocated_prizes": g.allocated_prizes,
                    "departments": g.departments,
                }])
                self._refresh_groups()

    # ── Boost Actions ──────────────────────────────────────────────

    def _on_save_emp_boost(self) -> None:
        emp_no = self._emp_boost_edit.text().strip()
        if not emp_no:
            return
        mult = self._emp_boost_spin.value()
        self._ctrl.set_employee_boost(emp_no, mult)
        self._emp_boost_edit.clear()

    def _on_save_dept_boost(self) -> None:
        dept = self._dept_boost_combo.currentText()
        mult = self._dept_boost_spin.value()
        self._ctrl.set_department_boost(dept, mult)
        self._refresh_dept_boosts()

    def _refresh_dept_boosts(self) -> None:
        boosts = self._ctrl.get_department_boosts()
        self._dept_boost_table.setRowCount(0)
        for i, (dept, mult) in enumerate(boosts.items()):
            self._dept_boost_table.insertRow(i)
            self._dept_boost_table.setItem(i, 0, QTableWidgetItem(dept))
            item = QTableWidgetItem(f"{mult}x")
            item.setTextAlignment(Qt.AlignCenter)
            self._dept_boost_table.setItem(i, 1, item)
