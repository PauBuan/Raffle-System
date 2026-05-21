"""
app/views/components/winners_view.py
-------------------------------------
"View Winners" tab.
Displays all winners grouped by Minor → Major → Grand,
with a name-sort option and a Recent Winners (Top 30) section.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QFrame, QTabWidget,
    QComboBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QColor

from app.controllers import RaffleController
from app.models      import Winner
from app.utils       import badge_color
from config.settings import COLORS, CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND, RECENT_WINNERS_LIMIT


class WinnersView(QWidget):
    """Full winners display with grouped tabs and recent section."""

    def __init__(self, controller: RaffleController, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = controller
        self._build_ui()
        self.refresh()

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Top controls
        top = QHBoxLayout()
        title = QLabel("Winners Board")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch()

        sort_lbl = QLabel("Sort by:")
        sort_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
        top.addWidget(sort_lbl)

        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["Draw Order", "Name A–Z", "Name Z–A"])
        self._sort_combo.currentIndexChanged.connect(self.refresh)
        top.addWidget(self._sort_combo)

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)

        root.addLayout(top)

        # Splitter: grouped tabs (top) + recent (bottom)
        splitter = QSplitter(Qt.Vertical)

        # Grouped winner tabs
        self._tabs = QTabWidget()
        for cat, color in [
            (CATEGORY_MINOR, badge_color(CATEGORY_MINOR)),
            (CATEGORY_MAJOR, badge_color(CATEGORY_MAJOR)),
            (CATEGORY_GRAND, badge_color(CATEGORY_GRAND)),
        ]:
            tbl = self._make_table()
            self._tabs.addTab(tbl, cat)
        splitter.addWidget(self._tabs)

        # Recent winners panel
        recent_frame = QFrame()
        recent_frame.setObjectName("card")
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(14, 12, 14, 12)
        recent_layout.setSpacing(8)

        rec_hdr = QLabel(f"⏱  Recent Winners  (Top {RECENT_WINNERS_LIMIT})")
        rec_hdr.setObjectName("section_header")
        recent_layout.addWidget(rec_hdr)

        self._recent_table = self._make_table()
        recent_layout.addWidget(self._recent_table)
        splitter.addWidget(recent_frame)

        splitter.setSizes([500, 240])
        root.addWidget(splitter)

    @staticmethod
    def _make_table() -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(["Emp No", "Name", "Department", "Prize", "Drawn At"])
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.verticalHeader().hide()
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(f"QTableWidget {{ alternate-background-color: {COLORS['bg_card2']}; }}")
        return tbl

    # ── Data ────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload and redisplay all winner data."""
        sort_idx = self._sort_combo.currentIndex()

        for tab_idx, cat in enumerate([CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND]):
            winners = self._ctrl.load_winners_by_category(cat)
            winners = self._sort_winners(winners, sort_idx)
            tbl: QTableWidget = self._tabs.widget(tab_idx)
            self._populate_table(tbl, winners, badge_color(cat))

        recent = self._ctrl.load_recent_winners(RECENT_WINNERS_LIMIT)
        self._populate_table(self._recent_table, recent, COLORS["accent_blue"])

    @staticmethod
    def _sort_winners(winners: list[Winner], sort_idx: int) -> list[Winner]:
        if sort_idx == 1:
            return sorted(winners, key=lambda w: w.emp_name)
        if sort_idx == 2:
            return sorted(winners, key=lambda w: w.emp_name, reverse=True)
        return winners  # draw order (default)

    @staticmethod
    def _populate_table(tbl: QTableWidget, winners: list[Winner], accent: str) -> None:
        tbl.setRowCount(0)
        for row_i, w in enumerate(winners):
            tbl.insertRow(row_i)
            cells = [w.emp_no, w.emp_name, w.department, w.prize_name, w.drawn_at[:19]]
            for col_i, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col_i == 0:
                    item.setForeground(QColor(accent))
                    item.setFont(QFont("Consolas", 11, QFont.Bold))
                tbl.setItem(row_i, col_i, item)
