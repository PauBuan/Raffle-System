"""
app/views/grand_confirm_panel.py
---------------------------------
Confirm/Redraw overlay panel for Grand prize winners.
Shown after the Grand slot machine reveal finishes.
Animates in from bottom with a slide-up + fade.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui  import QFont

from config.settings import COLORS


class GrandConfirmPanel(QWidget):
    """
    Overlay panel shown after Grand prize reveal.
    Emits confirmed() or redrawn() signals.
    """

    confirmed = Signal()
    redrawn   = Signal()

    def __init__(
        self,
        emp_name:   str,
        emp_no:     str,
        department: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._build_ui(emp_name, emp_no, department)
        self.setFixedSize(500, 200)

        # Position at bottom center of parent
        if parent:
            px = (parent.width() - self.width()) // 2
            py = parent.height() - self.height() - 30
            self.move(px, py)

    def _build_ui(self, emp_name: str, emp_no: str, department: str) -> None:
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 rgba(22,22,42,240), stop:1 rgba(13,13,26,250));
                border: 2px solid {COLORS['accent_gold']};
                border-radius: 16px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(12)

        # Title
        title = QLabel("🏆  GRAND PRIZE WINNER")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_gold']}; letter-spacing: 2px; border: none; background: transparent;")
        root.addWidget(title)

        # Winner info
        info = QLabel(f"{emp_name}  —  {department}  —  {emp_no}")
        info.setAlignment(Qt.AlignCenter)
        info.setFont(QFont("Segoe UI", 16, QFont.Bold))
        info.setStyleSheet(f"color: {COLORS['text_primary']}; border: none; background: transparent;")
        root.addWidget(info)

        root.addSpacing(8)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)
        btn_row.addStretch()

        redraw_btn = QPushButton("↻  Re-draw")
        redraw_btn.setFixedHeight(42)
        redraw_btn.setCursor(Qt.PointingHandCursor)
        redraw_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['accent_red']};
                border: 2px solid {COLORS['accent_red']};
                border-radius: 8px;
                padding: 0 28px;
                font-weight: 700;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_red']};
                color: #fff;
            }}
        """)
        redraw_btn.clicked.connect(self.redrawn.emit)
        btn_row.addWidget(redraw_btn)

        confirm_btn = QPushButton("✓  Confirm Win")
        confirm_btn.setFixedHeight(42)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_gold']};
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 0 32px;
                font-weight: 700;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: #ffe94d;
            }}
        """)
        confirm_btn.clicked.connect(self.confirmed.emit)
        btn_row.addWidget(confirm_btn)

        btn_row.addStretch()
        root.addLayout(btn_row)

    def animate_in(self) -> None:
        """Slide up + fade in animation."""
        # Slide up
        start_pos = self.pos() + QPoint(0, 60)
        end_pos = self.pos()

        self.move(start_pos)

        slide_anim = QPropertyAnimation(self, b"pos")
        slide_anim.setDuration(400)
        slide_anim.setStartValue(start_pos)
        slide_anim.setEndValue(end_pos)
        slide_anim.setEasingCurve(QEasingCurve.OutCubic)
        slide_anim.start()

        # Keep reference to prevent GC
        self._slide_anim = slide_anim

        # Fade in
        opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(opacity)
        fade_anim = QPropertyAnimation(opacity, b"opacity")
        fade_anim.setDuration(400)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.start()
        self._fade_anim = fade_anim
