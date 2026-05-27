"""
app/views/screens/grand_loading_screen.py
------------------------------------------
Grand prize reveal screen.
Animates the winner's EmpNo as a slot machine:
one character per slot, revealed every SLOT_CHAR_INTERVAL_MS ms.

v2.0 changes:
    - Particle burst (confetti emoji rain) on final reveal
    - Gold shimmer pulse on winner card
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve
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
        self._confetti_labels: list[QLabel] = []
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

        # Winner card (hidden until all chars revealed) — with gold shimmer
        self._winner_card = QFrame()
        self._winner_card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(255,215,0,0.1), stop:0.5 rgba(255,215,0,0.05),
                    stop:1 rgba(255,215,0,0.1));
                border: 2px solid {COLORS['accent_gold']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        card_layout = QVBoxLayout(self._winner_card)
        card_layout.setSpacing(6)

        self._name_lbl = QLabel(self._winner.emp_name)
        self._name_lbl.setAlignment(Qt.AlignCenter)
        self._name_lbl.setFont(QFont("Segoe UI", 30, QFont.Bold))
        self._name_lbl.setStyleSheet(f"color: {COLORS['accent_gold']}; border: none; background: transparent;")
        card_layout.addWidget(self._name_lbl)

        self._dept_lbl = QLabel(self._winner.department)
        self._dept_lbl.setAlignment(Qt.AlignCenter)
        self._dept_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 14px; border: none; background: transparent;")
        card_layout.addWidget(self._dept_lbl)

        self._winner_card.hide()
        root.addWidget(self._winner_card)

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
            self._show_winner_reveal()

    def _show_winner_reveal(self) -> None:
        """Show winner card with gold shimmer pulse + confetti burst."""
        self._winner_card.show()
        self._confetti.show()

        # Gold shimmer pulse on winner card
        self._shimmer_pulse()

        # Confetti burst
        self._spawn_confetti()

    def _shimmer_pulse(self) -> None:
        """Pulsing opacity animation on the winner card."""
        opacity = QGraphicsOpacityEffect(self._winner_card)
        self._winner_card.setGraphicsEffect(opacity)

        pulse = QPropertyAnimation(opacity, b"opacity")
        pulse.setDuration(800)
        pulse.setStartValue(0.5)
        pulse.setEndValue(1.0)
        pulse.setEasingCurve(QEasingCurve.InOutSine)
        pulse.setLoopCount(3)
        pulse.start()
        self._pulse_anim = pulse

    def _spawn_confetti(self) -> None:
        """Create floating confetti emoji labels across the screen."""
        import random
        emojis = ["🎉", "✨", "🌟", "🎊", "💫", "⭐", "🏆"]
        for _ in range(12):
            emoji = random.choice(emojis)
            lbl = QLabel(emoji, self)
            lbl.setFont(QFont("Segoe UI", random.randint(16, 28)))
            lbl.setStyleSheet("background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignCenter)

            x = random.randint(20, max(self.width() - 60, 100))
            start_y = random.randint(-60, -20)
            end_y = self.height() + 40

            lbl.move(x, start_y)
            lbl.show()

            anim = QPropertyAnimation(lbl, b"pos")
            anim.setDuration(random.randint(2000, 4000))
            anim.setStartValue(lbl.pos())
            from PySide6.QtCore import QPoint
            anim.setEndValue(QPoint(x + random.randint(-30, 30), end_y))
            anim.setEasingCurve(QEasingCurve.Linear)
            anim.start()

            self._confetti_labels.append(lbl)
            # prevent GC
            if not hasattr(self, '_confetti_anims'):
                self._confetti_anims = []
            self._confetti_anims.append(anim)
