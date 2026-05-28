"""
app/views/screens/mode_select_screen.py
----------------------------------------
Mode selection screen shown on app launch.
User chooses between Department Mode, Event Mode, and DIY Mode.

v3.0 changes:
    - Three-button layout (Department | Event | DIY)
    - Updated descriptions per UPDATE_3.md Section 3.8
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui  import QFont

from config.settings import COLORS


class ModeSelectScreen(QWidget):
    """
    Full-screen mode selection.
    Emits mode_selected('department'), mode_selected('event'), or mode_selected('diy').
    """

    mode_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(60, 60, 60, 60)
        root.setSpacing(24)

        root.addStretch()

        # Title
        title = QLabel("SELECT DRAWING MODE")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_gold']}; letter-spacing: 4px;")
        root.addWidget(title)

        sub = QLabel("Choose how participants will be selected for the raffle draw")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 14px;")
        root.addWidget(sub)

        root.addSpacing(30)

        # Mode buttons — 3 columns
        btn_row = QHBoxLayout()
        btn_row.setSpacing(30)
        btn_row.addStretch()

        # Department Mode
        dept_btn = self._make_mode_button(
            icon="🏢",
            title="Department Mode",
            description=(
                "Draw within a single\n"
                "department.\n\n"
                "No group bias."
            ),
            accent=COLORS["accent_blue"],
        )
        dept_btn.clicked.connect(lambda: self.mode_selected.emit("department"))
        btn_row.addWidget(dept_btn)

        # Event Mode
        event_btn = self._make_mode_button(
            icon="🎉",
            title="Event Mode",
            description=(
                "Company-wide draw\n"
                "using all employees,\n"
                "split by building\n"
                "& group bias."
            ),
            accent=COLORS["accent_gold"],
        )
        event_btn.clicked.connect(lambda: self.mode_selected.emit("event"))
        btn_row.addWidget(event_btn)

        # DIY Mode
        diy_btn = self._make_mode_button(
            icon="✏",
            title="DIY Mode",
            description=(
                "Build your own list.\n"
                "Manual entry or\n"
                "CSV upload.\n\n"
                "No group bias."
            ),
            accent=COLORS["accent_green"],
        )
        diy_btn.clicked.connect(lambda: self.mode_selected.emit("diy"))
        btn_row.addWidget(diy_btn)

        btn_row.addStretch()
        root.addLayout(btn_row)

        # Event mode note
        note = QLabel("Event Mode note: Requires admin group setup to be READY.")
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-style: italic;"
        )
        root.addWidget(note)

        root.addStretch()

    def _make_mode_button(
        self, icon: str, title: str, description: str, accent: str,
    ) -> QPushButton:
        """Create a large styled mode selection button."""
        btn = QPushButton()
        btn.setFixedSize(280, 240)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {COLORS['bg_card2']}, stop:1 {COLORS['bg_card']});
                border: 2px solid {COLORS['border']};
                border-radius: 16px;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                border-color: {accent};
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {COLORS['bg_card2']}, stop:1 rgba(255,255,255,0.03));
            }}
        """)

        layout = QVBoxLayout(btn)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI", 36))
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title_lbl.setStyleSheet(
            f"color: {accent}; background: transparent; border: none;"
        )
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(desc_lbl)

        return btn
