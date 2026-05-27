"""
app/views/screens/minor_loading_screen.py
------------------------------------------
Loading / reveal screen for Minor prize draws.
Displays winners as an animated, staggered list with slide-in + fade effects.

v2.0 changes:
    - Slide-in from left per row + subtle fade
    - Uses MINOR_ROW_INTERVAL_MS from settings
"""

from PySide6.QtWidgets  import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore     import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui      import QFont, QColor
from app.models         import Winner
from config.settings    import COLORS, MINOR_ROW_INTERVAL_MS


class _WinnerRow(QFrame):
    """Single animated winner row for the Minor list."""

    def __init__(self, index: int, winner: Winner, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedHeight(72)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['bg_card2']}, stop:1 {COLORS['bg_card']});
                border-left: 4px solid {COLORS['accent_green']};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Rank badge
        rank_lbl = QLabel(f"#{index + 1:02d}")
        rank_lbl.setFont(QFont("Consolas", 18, QFont.Bold))
        rank_lbl.setStyleSheet(f"color: {COLORS['accent_green']}; letter-spacing: 1px;")
        rank_lbl.setFixedWidth(54)
        layout.addWidget(rank_lbl)

        # Name + EmpNo
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(winner.emp_name)
        name_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        name_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")

        empno_lbl = QLabel(winner.emp_no)
        empno_lbl.setFont(QFont("Consolas", 11))
        empno_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")

        info.addWidget(name_lbl)
        info.addWidget(empno_lbl)
        layout.addLayout(info)
        layout.addStretch()

        dept_lbl = QLabel(winner.department)
        dept_lbl.setStyleSheet(f"""
            color: {COLORS['accent_green']};
            background: rgba(105,240,174,0.1);
            border: 1px solid {COLORS['accent_green']};
            border-radius: 4px;
            padding: 3px 10px;
            font-weight: 600;
            font-size: 11px;
        """)
        layout.addWidget(dept_lbl)

        self.setGraphicsEffect(None)
        self.hide()

    def animate_in(self) -> None:
        """Slide in from left + fade in."""
        self.show()

        # Slide animation
        start_pos = self.pos() + QPoint(-80, 0)
        end_pos = self.pos()
        self.move(start_pos)

        slide = QPropertyAnimation(self, b"pos")
        slide.setDuration(300)
        slide.setStartValue(start_pos)
        slide.setEndValue(end_pos)
        slide.setEasingCurve(QEasingCurve.OutCubic)
        slide.start()
        self._slide_anim = slide

        # Fade animation
        opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(opacity)
        fade = QPropertyAnimation(opacity, b"opacity")
        fade.setDuration(300)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.start()
        self._fade_anim = fade


class MinorLoadingScreen(QWidget):
    """
    Full-screen overlay for Minor prize reveals.
    Winners appear one-by-one with a staggered delay + slide-in animation.
    """

    def __init__(self, prize_name: str, winners: list[Winner], parent=None) -> None:
        super().__init__(parent)
        self._winners = winners
        self._rows: list[_WinnerRow] = []
        self._reveal_index = 0

        self._build_ui(prize_name)

    # ── UI construction ────────────────────────────────────────────

    def _build_ui(self, prize_name: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 40, 60, 40)
        root.setSpacing(20)
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")

        # Header
        header = QVBoxLayout()
        header.setSpacing(4)

        tag = QLabel("✦  MINOR PRIZE DRAW  ✦")
        tag.setAlignment(Qt.AlignCenter)
        tag.setStyleSheet(f"""
            color: {COLORS['accent_green']};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 4px;
        """)
        header.addWidget(tag)

        prize_lbl = QLabel(prize_name)
        prize_lbl.setAlignment(Qt.AlignCenter)
        prize_lbl.setFont(QFont("Segoe UI", 28, QFont.Bold))
        prize_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(prize_lbl)

        sub = QLabel(f"{len(self._winners)} winner{'s' if len(self._winners) != 1 else ''}")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        header.addWidget(sub)

        root.addLayout(header)

        # Divider
        div = QFrame()
        div.setFixedHeight(2)
        div.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                          f"stop:0 transparent, stop:0.5 {COLORS['accent_green']}, stop:1 transparent);")
        root.addWidget(div)

        # Scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(container)
        self._list_layout.setSpacing(10)
        self._list_layout.setContentsMargins(0, 10, 0, 10)

        for i, w in enumerate(self._winners):
            row = _WinnerRow(i, w)
            self._list_layout.addWidget(row)
            self._rows.append(row)

        self._list_layout.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll)

    # ── Animation ──────────────────────────────────────────────────

    def start_reveal(self) -> None:
        """Begin staggered reveal of winner rows with slide-in animation."""
        self._reveal_index = 0
        self._reveal_next()

    def _reveal_next(self) -> None:
        if self._reveal_index >= len(self._rows):
            return
        row = self._rows[self._reveal_index]
        row.animate_in()
        self._reveal_index += 1
        QTimer.singleShot(MINOR_ROW_INTERVAL_MS, self._reveal_next)
