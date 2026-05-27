"""
app/views/screens/major_loading_screen.py
------------------------------------------
Loading / reveal screen for Major prize draws.
Fewer winners → larger cards with card flip + dramatic entrance.

v2.0 changes:
    - Card flip (Y-axis transform simulation) before showing winner name
    - Uses MAJOR_CARD_INTERVAL_MS from settings
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui     import QFont
from app.models        import Winner
from config.settings   import COLORS, MAJOR_CARD_INTERVAL_MS


class _MajorWinnerCard(QFrame):
    """Large winner card used in the Major draw screen."""

    def __init__(self, index: int, winner: Winner, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedHeight(100)
        self._winner = winner

        # Start with "back" style (hidden content)
        self._back_style = f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {COLORS['accent_blue']}, stop:1 #1a1a3a);
                border: 1px solid {COLORS['accent_blue']};
                border-left: 5px solid {COLORS['accent_blue']};
                border-radius: 10px;
            }}
        """
        self._front_style = f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #1a1a3a, stop:1 {COLORS['bg_card']});
                border: 1px solid {COLORS['accent_blue']};
                border-left: 5px solid {COLORS['accent_blue']};
                border-radius: 10px;
            }}
        """

        self.setStyleSheet(self._back_style)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(20)

        # Number badge
        num_frame = QFrame()
        num_frame.setFixedSize(56, 56)
        num_frame.setStyleSheet(f"""
            background-color: {COLORS['accent_blue']};
            border-radius: 28px;
        """)
        num_layout = QVBoxLayout(num_frame)
        num_layout.setContentsMargins(0, 0, 0, 0)
        num_lbl = QLabel(str(index + 1))
        num_lbl.setAlignment(Qt.AlignCenter)
        num_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        num_lbl.setStyleSheet("color: #000; background: transparent; border: none;")
        num_layout.addWidget(num_lbl)
        layout.addWidget(num_frame)

        # Name block (hidden initially for flip effect)
        self._info_widget = QWidget()
        self._info_widget.setStyleSheet("background: transparent; border: none;")
        info = QVBoxLayout(self._info_widget)
        info.setSpacing(4)
        info.setContentsMargins(0, 0, 0, 0)
        name = QLabel(winner.emp_name)
        name.setFont(QFont("Segoe UI", 17, QFont.Bold))
        name.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")

        detail = QLabel(f"{winner.emp_no}  ·  {winner.department}")
        detail.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; background: transparent; border: none;")

        info.addStretch()
        info.addWidget(name)
        info.addWidget(detail)
        info.addStretch()
        layout.addLayout(info)
        layout.addStretch()

        # Trophy icon
        trophy = QLabel("🏆")
        trophy.setFont(QFont("Segoe UI", 28))
        trophy.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(trophy)

        # Initially hide content
        self._info_widget.setVisible(False)
        self.hide()

    def flip_reveal(self) -> None:
        """Simulate a card flip by fading out, switching content, fading in."""
        self.show()

        # Phase 1: Show card back with fade-in
        opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(opacity)

        fade_in = QPropertyAnimation(opacity, b"opacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.start()
        self._fade_in = fade_in

        # Phase 2: After brief pause, "flip" to front
        QTimer.singleShot(350, self._show_front)

    def _show_front(self) -> None:
        """Transition from card back to front — reveal winner info."""
        self.setStyleSheet(self._front_style)
        self._info_widget.setVisible(True)

        # Brief opacity pulse for the flip effect
        opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(opacity)
        pulse = QPropertyAnimation(opacity, b"opacity")
        pulse.setDuration(250)
        pulse.setStartValue(0.6)
        pulse.setEndValue(1.0)
        pulse.setEasingCurve(QEasingCurve.OutCubic)
        pulse.start()
        self._pulse = pulse


class MajorLoadingScreen(QWidget):
    """Full-screen overlay for Major prize reveals with card flip animation."""

    def __init__(self, prize_name: str, winners: list[Winner], parent=None) -> None:
        super().__init__(parent)
        self._winners = winners
        self._cards: list[_MajorWinnerCard] = []
        self._reveal_index = 0
        self._build_ui(prize_name)

    def _build_ui(self, prize_name: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(100, 50, 100, 50)
        root.setSpacing(20)
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")

        # Tag
        tag = QLabel("◈  MAJOR PRIZE DRAW  ◈")
        tag.setAlignment(Qt.AlignCenter)
        tag.setStyleSheet(f"""
            color: {COLORS['accent_blue']};
            font-size: 13px; font-weight: 700; letter-spacing: 4px;
        """)
        root.addWidget(tag)

        # Prize name
        prize_lbl = QLabel(prize_name)
        prize_lbl.setAlignment(Qt.AlignCenter)
        prize_lbl.setFont(QFont("Segoe UI", 32, QFont.Bold))
        prize_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        root.addWidget(prize_lbl)

        # Divider
        div = QFrame()
        div.setFixedHeight(2)
        div.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 transparent, stop:0.5 {COLORS['accent_blue']}, stop:1 transparent);"
        )
        root.addWidget(div)

        root.addStretch()

        for i, w in enumerate(self._winners):
            card = _MajorWinnerCard(i, w, parent=self)
            root.addWidget(card)
            self._cards.append(card)

        root.addStretch()

    def start_reveal(self) -> None:
        self._reveal_index = 0
        self._reveal_next()

    def _reveal_next(self) -> None:
        if self._reveal_index >= len(self._cards):
            return
        self._cards[self._reveal_index].flip_reveal()
        self._reveal_index += 1
        QTimer.singleShot(MAJOR_CARD_INTERVAL_MS, self._reveal_next)
