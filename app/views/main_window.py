"""
app/views/main_window.py
-------------------------
Application shell (Presentation Layer — View).

Routing
-------
MainWindow → DrawPanel / WinnersView → RaffleController → Services → Models → DB

The window owns the tab bar and the controller instance.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QStatusBar, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont

from app.controllers              import RaffleController
from app.views.components         import DrawPanel, WinnersView
from config.settings              import (
    APP_NAME, APP_VERSION,
    CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND, COLORS,
)


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self._ctrl = RaffleController(parent=self)
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        self._build_ui()
        self._ctrl.error_occurred.connect(self._on_error)

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        root.addWidget(self._build_header())

        # Tab area
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        tabs.addTab(
            DrawPanel(CATEGORY_MINOR, self._ctrl),
            "🎁  Minor",
        )
        tabs.addTab(
            DrawPanel(CATEGORY_MAJOR, self._ctrl),
            "🏆  Major",
        )
        tabs.addTab(
            DrawPanel(CATEGORY_GRAND, self._ctrl),
            "★  Grand",
        )
        tabs.addTab(
            WinnersView(self._ctrl),
            "📋  Winners",
        )
        root.addWidget(tabs)

        # Status bar
        self._status = QStatusBar()
        self._status.setStyleSheet(f"""
            QStatusBar {{
                background: {COLORS['bg_card']};
                color:      {COLORS['text_muted']};
                font-size:  11px;
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        self._status.showMessage("Ready — select a department and prize to begin.")
        self.setStatusBar(self._status)

        self._ctrl.draw_completed.connect(self._on_draw_done)
        self._ctrl.department_set.connect(
            lambda d: self._status.showMessage(f"Department: {d}")
        )

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #0D0D1A, stop:0.5 #16162A, stop:1 #0D0D1A);
            border-bottom: 1px solid {COLORS['border']};
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)

        icon = QLabel("🎰")
        icon.setFont(QFont("Segoe UI", 22))
        layout.addWidget(icon)

        title = QLabel(APP_NAME.upper())
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_gold']}; letter-spacing: 3px;")
        layout.addWidget(title)
        layout.addStretch()

        ver = QLabel(f"v{APP_VERSION}")
        ver.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(ver)

        return header

    # ── Signal handlers ────────────────────────────────────────────

    def _on_draw_done(self, result) -> None:
        count = len(result.winners)
        label = "redraw" if result.is_redraw else "draw"
        self._status.showMessage(
            f"{label.capitalize()} complete — {count} winner(s) for '{result.prize.prize_name}'."
        )

    def _on_error(self, message: str) -> None:
        self._status.showMessage(f"⚠  {message}", 5000)
