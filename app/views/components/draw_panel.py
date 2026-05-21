"""
app/views/components/draw_panel.py
-----------------------------------
Reusable draw panel component used inside each prize-category tab.
Displays the prize list, draw / redraw buttons, and triggers
the appropriate loading screen.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui  import QFont, QColor

from app.controllers          import RaffleController
from app.models               import Prize
from app.views.screens        import MinorLoadingScreen, MajorLoadingScreen, GrandLoadingScreen
from app.views.dialogs        import AddPrizeDialog
from app.utils                import show_error, badge_color, confirm
from config.settings          import COLORS, CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND


class DrawPanel(QWidget):
    """
    Self-contained draw panel for one prize category tab.
    Contains: prize selector, draw button, optional redraw button,
    and a stacked area that switches between the panel and the
    appropriate loading screen.
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

        dept_lbl = QLabel("Department:")
        dept_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
        ctrl_row.addWidget(dept_lbl)

        self._dept_combo = QComboBox()
        self._dept_combo.setMinimumWidth(180)
        for dept in self._ctrl.load_departments():
            self._dept_combo.addItem(dept)
        self._dept_combo.currentTextChanged.connect(self._ctrl.set_department)
        if self._dept_combo.count():
            self._ctrl.set_department(self._dept_combo.currentText())
        ctrl_row.addWidget(self._dept_combo)

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
        self._ctrl.prizes_updated.connect(self.refresh_prizes)
        self._ctrl.error_occurred.connect(lambda msg: show_error(self, msg))

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

            # Winners (Quantity)
            qty_item = QTableWidgetItem(str(prize.quantity))
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

    # ── Slot handlers ──────────────────────────────────────────────

    def _on_add_prize(self) -> None:
        dlg = AddPrizeDialog(default_category=self._category, parent=self)
        if dlg.exec():
            self._ctrl.add_prize(dlg.category, dlg.prize_name, dlg.quantity)

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
        self._ctrl.start_draw(prize.prize_id)

    def _on_redraw(self) -> None:
        prize = self._selected_prize()
        if not prize:
            show_error(self, "Select a prize to redraw.")
            return
        self._ctrl.start_redraw(prize.prize_id)

    def _on_draw_completed(self, result) -> None:
        """Only handle results that belong to this panel's category."""
        if result.prize.category_name != self._category:
            return
        self._show_loading_screen(result)

    def _show_loading_screen(self, result) -> None:
        """Build and display the appropriate loading screen, then auto-close."""
        cat = self._category
        if cat == CATEGORY_MINOR:
            screen = MinorLoadingScreen(result.prize.prize_name, result.winners, self)
        elif cat == CATEGORY_MAJOR:
            screen = MajorLoadingScreen(result.prize.prize_name, result.winners, self)
        else:
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
