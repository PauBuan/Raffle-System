"""
app/views/screens/grand_loading_screen.py
------------------------------------------
Grand prize reveal screen.
Animates the winner's EmpNo as a slot machine:
one character per slot, revealed every SLOT_CHAR_INTERVAL_MS ms.

e.g. EmpNo = "OJT26A02"
     tick 0 → "_ _ _ _ _ _ _ _"
     tick 1 → "O _ _ _ _ _ _ _"
     tick 2 → "O J _ _ _ _ _ _"
     ...
     tick 8 → "O J T 2 6 A 0 2"
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PySide6.QtCore    import Qt, QTimer
from PySide6.QtGui     import QFont
from app.models        import Winner
from config.settings   import COLORS, SLOT_CHAR_INTERVAL_MS


class _SlotCharLabel(QLabel):
    """Single character slot cell."""

    def __init__(self, parent=None) -> None:
        super().__init__("_", parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(60, 80)
        self.setFont(QFont("Consolas", 32, QFont.Bold))
        self.setStyleSheet(f"""
            background-color: {COLORS['bg_card2']};
            color:            {COLORS['text_muted']};
            border:           2px solid {COLORS['border']};
            border-radius:    8px;
        """)

    def reveal(self, char: str) -> None:
        """Display the revealed character with gold highlight."""
        self.setText(char)
        self.setStyleSheet(f"""
            background-color: {COLORS['bg_card2']};
            color:            {COLORS['accent_gold']};
            border:           2px solid {COLORS['accent_gold']};
            border-radius:    8px;
        """)


class GrandLoadingScreen(QWidget):
    """
    Full-screen Grand prize slot-machine reveal.
    Call start_reveal() to begin the animation.
    """

    def __init__(self, prize_name: str, winner: Winner, parent=None) -> None:
        super().__init__(parent)
        self._winner    = winner
        self._emp_no    = winner.emp_no
        self._slots: list[_SlotCharLabel] = []
        self._tick      = 0
        self._timer     = QTimer(self)
        self._timer.timeout.connect(self._reveal_next_char)
        self._build_ui(prize_name)

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self, prize_name: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(80, 60, 80, 60)
        root.setSpacing(30)
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")

        # Tag
        tag = QLabel("★  GRAND PRIZE DRAW  ★")
        tag.setAlignment(Qt.AlignCenter)
        tag.setStyleSheet(f"""
            color: {COLORS['accent_gold']};
            font-size: 14px; font-weight: 700; letter-spacing: 5px;
        """)
        root.addWidget(tag)

        # Prize name
        prize_lbl = QLabel(prize_name)
        prize_lbl.setAlignment(Qt.AlignCenter)
        prize_lbl.setFont(QFont("Segoe UI", 36, QFont.Bold))
        prize_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        root.addWidget(prize_lbl)

        # Gold divider
        div = QFrame()
        div.setFixedHeight(2)
        div.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 transparent, stop:0.5 {COLORS['accent_gold']}, stop:1 transparent);"
        )
        root.addWidget(div)

        root.addStretch()

        # Slot label
        slot_title = QLabel("EMPLOYEE NUMBER")
        slot_title.setAlignment(Qt.AlignCenter)
        slot_title.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 11px; letter-spacing: 3px; font-weight: 600;
        """)
        root.addWidget(slot_title)

        # Slot cells
        slot_row = QHBoxLayout()
        slot_row.setSpacing(8)
        slot_row.setAlignment(Qt.AlignCenter)
        for _ in self._emp_no:
            cell = _SlotCharLabel()
            slot_row.addWidget(cell)
            self._slots.append(cell)
        root.addLayout(slot_row)

        root.addSpacing(30)

        # Winner name (hidden until all chars revealed)
        self._name_lbl = QLabel(self._winner.emp_name)
        self._name_lbl.setAlignment(Qt.AlignCenter)
        self._name_lbl.setFont(QFont("Segoe UI", 30, QFont.Bold))
        self._name_lbl.setStyleSheet(f"color: {COLORS['accent_gold']};")
        self._name_lbl.hide()
        root.addWidget(self._name_lbl)

        self._dept_lbl = QLabel(self._winner.department)
        self._dept_lbl.setAlignment(Qt.AlignCenter)
        self._dept_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 14px;")
        self._dept_lbl.hide()
        root.addWidget(self._dept_lbl)

        root.addStretch()

        # Confetti hint
        self._confetti = QLabel("🎉  Congratulations!  🎉")
        self._confetti.setAlignment(Qt.AlignCenter)
        self._confetti.setFont(QFont("Segoe UI", 18))
        self._confetti.setStyleSheet(f"color: {COLORS['accent_gold']};")
        self._confetti.hide()
        root.addWidget(self._confetti)

    # ── Animation ──────────────────────────────────────────────────

    def start_reveal(self) -> None:
        """Start the slot-machine character reveal."""
        self._tick = 0
        self._timer.start(SLOT_CHAR_INTERVAL_MS)

    def _reveal_next_char(self) -> None:
        if self._tick < len(self._slots):
            self._slots[self._tick].reveal(self._emp_no[self._tick])
            self._tick += 1
        else:
            self._timer.stop()
            self._name_lbl.show()
            self._dept_lbl.show()
            self._confetti.show()
