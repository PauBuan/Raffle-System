"""
app/views/components/draw_panel.py
-----------------------------------
Reusable draw panel component used inside each prize-category tab.
Displays the prize list, draw / redraw buttons, and triggers
the appropriate loading screen.

v2.0 changes:
    - Winner count spinbox (user-defined draw count)
    - "All Employees (Whole Tip)" in department combo
    - Button pulse animation on draw
    - Grand confirm/redraw flow integration
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QStackedWidget, QSizePolicy, QSpinBox,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui  import QFont, QColor

from app.controllers          import RaffleController
from app.models               import Prize
from app.views.screens        import MinorLoadingScreen, MajorLoadingScreen, GrandLoadingScreen
from app.views.dialogs        import AddPrizeDialog
from app.views.grand_confirm_panel import GrandConfirmPanel
from app.utils                import show_error, badge_color, confirm
from config.settings          import COLORS, CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND


class DrawPanel(QWidget):
    """
    Self-contained draw panel for one prize category tab.
    Contains: prize selector, winner count spinbox, draw button,
    optional redraw button, and a stacked area that switches between
    the panel and the appropriate loading screen.
    """

    def __init__(
        self,
        category:    str,
        controller:  RaffleController,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._category   = category
        self._ctrl       = controller
        self._prizes:    list[Prize] = []
        self._stack      = QStackedWidget(self)

        self._build_ui()
        self._connect_signals()
        self.refresh_prizes()

    # ── UI construction ────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._stack)

        # ── Main panel (index 0) ───────────────────────────────────
        main_panel = QWidget()
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Top bar
        top_bar = QHBoxLayout()
        cat_lbl = QLabel(self._category.upper() + "  PRIZES")
        cat_lbl.setObjectName("section_header")
        cat_lbl.setStyleSheet(f"color: {badge_color(self._category)}; font-weight: 700; font-size: 15px; letter-spacing: 2px;")
        top_bar.addWidget(cat_lbl)
        top_bar.addStretch()

        add_btn = QPushButton("＋  Add Prize")
        add_btn.setObjectName("btn_add")
        add_btn.clicked.connect(self._on_add_prize)
        top_bar.addWidget(add_btn)

        del_btn = QPushButton("✕  Remove")
        del_btn.setObjectName("btn_danger")
        del_btn.clicked.connect(self._on_delete_prize)
        top_bar.addWidget(del_btn)

        main_layout.addLayout(top_bar)

        # Prize table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Prize Name", "Category", "Winners", "Prize ID"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.verticalHeader().hide()
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"""
            QTableWidget {{ alternate-background-color: {COLORS['bg_card2']}; }}
        """)
        main_layout.addWidget(self._table)

        # Draw controls
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)

        self._dept_lbl = QLabel("Department:")
        self._dept_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
        ctrl_row.addWidget(self._dept_lbl)

        self._dept_combo = QComboBox()
        self._dept_combo.setMinimumWidth(180)
        self._populate_dept_combo()
        self._dept_combo.currentTextChanged.connect(self._on_department_changed)
        if self._dept_combo.count():
            self._on_department_changed(self._dept_combo.currentText())
        ctrl_row.addWidget(self._dept_combo)

        ctrl_row.addStretch()

        # Winner count spinbox
        wc_lbl = QLabel("Winners to draw:")
        wc_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
        ctrl_row.addWidget(wc_lbl)

        self._winner_count_spin = QSpinBox()
        self._winner_count_spin.setMinimum(1)
        self._winner_count_spin.setMaximum(999)
        self._winner_count_spin.setValue(1)
        self._winner_count_spin.setFixedWidth(80)
        ctrl_row.addWidget(self._winner_count_spin)

        ctrl_row.addStretch()

        if self._category in (CATEGORY_MAJOR, CATEGORY_GRAND):
            self._redraw_btn = QPushButton("↺  Redraw")
            self._redraw_btn.setObjectName("btn_redraw")
            self._redraw_btn.clicked.connect(self._on_redraw)
            ctrl_row.addWidget(self._redraw_btn)

        self._draw_btn = QPushButton(f"🎲  Draw  {self._category}")
        self._draw_btn.setObjectName("btn_draw")
        self._draw_btn.clicked.connect(self._on_draw)
        ctrl_row.addWidget(self._draw_btn)

        main_layout.addLayout(ctrl_row)
        self._stack.addWidget(main_panel)   # index 0

    def _connect_signals(self) -> None:
        self._ctrl.draw_completed.connect(self._on_draw_completed)
        self._ctrl.grand_pending.connect(self._on_grand_pending)
        self._ctrl.prizes_updated.connect(self.refresh_prizes)
        self._ctrl.error_occurred.connect(lambda msg: show_error(self, msg))
        self._ctrl.mode_changed.connect(self._on_mode_changed)

    # ── Data helpers ───────────────────────────────────────────────

    def refresh_prizes(self) -> None:
        """Reload prize list for this category from the database."""
        self._prizes = self._ctrl.load_prizes(self._category)
        self._table.setRowCount(0)
        for row_idx, prize in enumerate(self._prizes):
            self._table.insertRow(row_idx)

            # Prize Name
            self._table.setItem(row_idx, 0, QTableWidgetItem(prize.prize_name))

            # Category badge
            cat_item = QTableWidgetItem(prize.category_name)
            cat_item.setTextAlignment(Qt.AlignCenter)
            cat_item.setForeground(QColor(badge_color(prize.category_name)))
            cat_item.setFont(QFont("Segoe UI", 11, QFont.Bold))
            self._table.setItem(row_idx, 1, cat_item)

            # Winners (WinnerCount)
            qty_item = QTableWidgetItem(str(prize.winner_count))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row_idx, 2, qty_item)

            # Prize ID
            id_item = QTableWidgetItem(str(prize.prize_id))
            id_item.setTextAlignment(Qt.AlignCenter)
            id_item.setForeground(QColor(COLORS['text_muted']))
            self._table.setItem(row_idx, 3, id_item)

    def _selected_prize(self) -> Prize | None:
        rows = self._table.selectedItems()
        if not rows:
            return None
        row = self._table.currentRow()
        return self._prizes[row] if row < len(self._prizes) else None

    def _populate_dept_combo(self) -> None:
        """Fill the department combo based on current mode."""
        self._dept_combo.blockSignals(True)
        self._dept_combo.clear()

        if self._ctrl.get_mode() == "event":
            # Event mode: building assignment (LTI / CIP)
            self._dept_lbl.setText("Assignment:")
            self._dept_combo.addItem("🏢 LTI")
            self._dept_combo.addItem("🏢 CIP")
        else:
            # Department mode: standard department list
            self._dept_lbl.setText("Department:")
            self._dept_combo.addItem("🏢 All Employees (Whole Tip)")
            for dept in self._ctrl.load_departments():
                self._dept_combo.addItem(dept)

        self._dept_combo.blockSignals(False)
        if self._dept_combo.count():
            self._on_department_changed(self._dept_combo.currentText())

    def _on_mode_changed(self, mode: str) -> None:
        """React to mode switch — repopulate department/assignment combo."""
        self._populate_dept_combo()

    def _on_department_changed(self, text: str) -> None:
        """Map display text to controller value."""
        if "All Employees" in text:
            self._ctrl.set_department("ALL")
        elif "LTI" in text:
            self._ctrl.set_department("LTI")
        elif "CIP" in text:
            self._ctrl.set_department("CIP")
        else:
            self._ctrl.set_department(text)

    # ── Slot handlers ──────────────────────────────────────────────

    def _on_add_prize(self) -> None:
        dlg = AddPrizeDialog(default_category=self._category, parent=self)
        if dlg.exec():
            result = self._ctrl.add_prize(dlg.category, dlg.prize_name, dlg.winner_count)
            if result and result.was_deduplicated:
                from app.utils import show_toast
                show_toast(
                    self,
                    f"Added to existing prize '{result.prize.prize_name}' "
                    f"— total winners: {result.new_total}",
                )

    def _on_delete_prize(self) -> None:
        prize = self._selected_prize()
        if not prize:
            show_error(self, "Select a prize to remove.")
            return
        if confirm(self, f"Remove '{prize.prize_name}'?"):
            self._ctrl.delete_prize(prize.prize_id)

    def _on_draw(self) -> None:
        prize = self._selected_prize()
        if not prize:
            show_error(self, "Select a prize to draw.")
            return

        # Button pulse animation
        self._pulse_button(self._draw_btn)

        winner_count = self._winner_count_spin.value()

        if self._category == CATEGORY_GRAND:
            # Grand draws use the confirm/redraw flow
            self._ctrl.start_grand_draw(prize.prize_id, lti_count=winner_count)
        else:
            self._ctrl.start_draw(prize.prize_id, winner_count)

    def _on_redraw(self) -> None:
        prize = self._selected_prize()
        if not prize:
            show_error(self, "Select a prize to redraw.")
            return
        winner_count = self._winner_count_spin.value()

        if self._category == CATEGORY_GRAND:
            self._ctrl.redraw_grand()
        else:
            self._ctrl.start_redraw(prize.prize_id, winner_count)

    def _on_draw_completed(self, result) -> None:
        """Only handle results that belong to this panel's category."""
        if result.prize.category_name != self._category:
            return
        self._show_loading_screen(result)

    def _on_grand_pending(self, result) -> None:
        """Handle Grand draw pending result — show slot machine then confirm panel."""
        if self._category != CATEGORY_GRAND:
            return
        if not result.pending_employees:
            show_error(self, "No eligible employees for Grand draw.")
            return

        # Show slot machine for first pending employee
        from app.models import Winner
        emp = result.pending_employees[0]
        fake_winner = Winner(
            winner_id=0, prize_id=result.prize.prize_id,
            prize_name=result.prize.prize_name,
            category_name=CATEGORY_GRAND,
            emp_no=emp.emp_no, emp_name=emp.emp_name,
            department=emp.department, drawn_at="", is_redraw=False,
        )
        screen = GrandLoadingScreen(result.prize.prize_name, fake_winner, self)

        # Push onto stack
        while self._stack.count() > 1:
            old = self._stack.widget(1)
            self._stack.removeWidget(old)
            old.deleteLater()

        self._stack.addWidget(screen)
        self._stack.setCurrentIndex(1)
        screen.start_reveal()

        # After reveal completes, show confirm/redraw panel
        total_chars = len(emp.emp_no)
        from config.settings import SLOT_CHAR_INTERVAL_MS
        reveal_duration = total_chars * SLOT_CHAR_INTERVAL_MS + 500

        QTimer.singleShot(reveal_duration, lambda: self._show_grand_confirm(result, screen))

    def _show_grand_confirm(self, result, parent_screen) -> None:
        """Show the confirm/redraw overlay after Grand reveal."""
        if not result.pending_employees:
            return
        emp = result.pending_employees[0]

        panel = GrandConfirmPanel(
            emp_name=emp.emp_name,
            emp_no=emp.emp_no,
            department=emp.department,
            parent=parent_screen,
        )
        panel.confirmed.connect(lambda: self._on_grand_confirmed(emp))
        panel.redrawn.connect(self._on_grand_redrawn)
        panel.show()
        panel.animate_in()

    def _on_grand_confirmed(self, emp) -> None:
        """User confirmed Grand winner."""
        self._ctrl.confirm_grand_winner(emp)
        self._stack.setCurrentIndex(0)

    def _on_grand_redrawn(self) -> None:
        """User chose to redraw Grand."""
        self._stack.setCurrentIndex(0)
        self._ctrl.redraw_grand()

    def _show_loading_screen(self, result) -> None:
        """Build and display the appropriate loading screen, then auto-close."""
        cat = self._category
        if cat == CATEGORY_MINOR:
            screen = MinorLoadingScreen(result.prize.prize_name, result.winners, self)
        elif cat == CATEGORY_MAJOR:
            screen = MajorLoadingScreen(result.prize.prize_name, result.winners, self)
        else:
            # Grand standard draw (non-grouped) — shouldn't reach here in v2
            if not result.winners:
                show_error(self, "No eligible employees for Grand draw.")
                return
            screen = GrandLoadingScreen(result.prize.prize_name, result.winners[0], self)

        # Push onto stack
        while self._stack.count() > 1:
            old = self._stack.widget(1)
            self._stack.removeWidget(old)
            old.deleteLater()

        self._stack.addWidget(screen)
        self._stack.setCurrentIndex(1)
        screen.start_reveal()

        # "Back" button overlaid on the screen
        back_btn = QPushButton("← Back to Draw", screen)
        back_btn.setFixedSize(160, 36)
        back_btn.move(20, 20)
        back_btn.show()
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))

    def _pulse_button(self, btn: QPushButton) -> None:
        """Brief scale-like pulse animation on draw button click."""
        original_style = btn.styleSheet()
        btn.setStyleSheet(original_style + "border: 2px solid #FFE94D;")
        QTimer.singleShot(150, lambda: btn.setStyleSheet(original_style))
