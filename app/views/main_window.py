"""
app/views/main_window.py
-------------------------
Application shell (Presentation Layer — View).

Routing
-------
MainWindow → ModeSelectScreen → DrawPanel / WinnersView → RaffleController → Services → Models → DB

v2.0 changes:
    - Mode selection screen on launch
    - Ctrl+Shift+X secret admin dev mode
    - Participants tab in Event mode
    - Window title changes for dev mode
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QStatusBar, QFrame, QStackedWidget,
    QMessageBox, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QShortcut, QKeySequence

from app.controllers              import RaffleController, AdminController
from app.views.components         import DrawPanel, WinnersView
from app.views.components.participants_panel import ParticipantsPanel
from app.views.screens.mode_select_screen    import ModeSelectScreen
from app.views.dialogs.admin_login_dialog    import AdminLoginDialog
from app.views.dialogs.admin_panel           import AdminPanel
from app.views.dialogs.session_setup_dialog  import SessionSetupDialog
from config.settings              import (
    APP_NAME, APP_VERSION,
    CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND, COLORS,
)


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self._ctrl       = RaffleController(parent=self)
        self._admin_ctrl = AdminController(parent=self)
        self._dev_mode   = False

        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        self._build_ui()
        self._ctrl.error_occurred.connect(self._on_error)

        # Secret admin shortcut
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+X"), self)
        shortcut.activated.connect(self._on_admin_shortcut)

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        root.addWidget(self._build_header())

        # Main stacked widget: mode select (0) vs app content (1)
        self._main_stack = QStackedWidget()

        # Mode selection screen
        self._mode_screen = ModeSelectScreen()
        self._mode_screen.mode_selected.connect(self._on_mode_selected)
        self._main_stack.addWidget(self._mode_screen)   # index 0

        # App content (tabs)
        self._app_widget = QWidget()
        app_layout = QVBoxLayout(self._app_widget)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._tabs.addTab(
            DrawPanel(CATEGORY_MINOR, self._ctrl),
            "🎁  Minor",
        )
        self._tabs.addTab(
            DrawPanel(CATEGORY_MAJOR, self._ctrl),
            "🏆  Major",
        )
        self._tabs.addTab(
            DrawPanel(CATEGORY_GRAND, self._ctrl),
            "★  Grand",
        )
        self._tabs.addTab(
            WinnersView(self._ctrl),
            "📋  Winners",
        )

        # Participants tab (hidden initially, shown in event mode)
        self._participants_panel = ParticipantsPanel(self._ctrl)
        self._participants_tab_idx = self._tabs.addTab(
            self._participants_panel,
            "👥  Participants",
        )
        self._tabs.setTabVisible(self._participants_tab_idx, False)

        app_layout.addWidget(self._tabs)
        self._main_stack.addWidget(self._app_widget)   # index 1

        root.addWidget(self._main_stack)

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
        self._status.showMessage("Ready — select a drawing mode to begin.")
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
        self._header_title = title
        layout.addStretch()

        # ← Change Mode button (hidden until a mode is selected)
        self._change_mode_btn = QPushButton("← Change Mode")
        self._change_mode_btn.setCursor(Qt.PointingHandCursor)
        self._change_mode_btn.setFixedHeight(32)
        self._change_mode_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                color: {COLORS['accent_blue']};
                border-color: {COLORS['accent_blue']};
            }}
        """)
        self._change_mode_btn.clicked.connect(self._go_back_to_mode_select)
        self._change_mode_btn.hide()
        layout.addWidget(self._change_mode_btn)

        layout.addSpacing(12)

        ver = QLabel(f"v{APP_VERSION}")
        ver.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(ver)

        return header

    # ── Mode selection ─────────────────────────────────────────────

    def _on_mode_selected(self, mode: str) -> None:
        """Handle mode selection from the mode screen."""
        if mode == "department":
            # Show session setup dialog (name + CSV upload)
            dlg = SessionSetupDialog(parent=self)
            if not dlg.exec():
                # User cancelled — stay on mode select
                return
            # Import CSV employees into the database
            if dlg.csv_path:
                self._admin_ctrl.import_employees_csv(dlg.csv_path)

            # Extract EmpNos from parsed CSV rows → session whitelist
            csv_emp_nos = {
                row.get("EmpNo", "").strip()
                for row in dlg.preview_rows
                if row.get("EmpNo", "").strip()
            }

            self._session_name = dlg.session_name
            self.setWindowTitle(
                f"{APP_NAME}  v{APP_VERSION}  —  {dlg.session_name}"
            )
            self._status.showMessage(
                f"Department Mode — Session: {dlg.session_name}  "
                f"({len(csv_emp_nos)} participants)"
            )
            self._tabs.setTabVisible(self._participants_tab_idx, True)

            # Set mode first, then push the whitelist (triggers refresh)
            self._ctrl.set_mode(mode)
            self._ctrl.set_session_participants(csv_emp_nos)
        else:
            self._status.showMessage(
                "Event Mode — select an event or create a new one."
            )
            self._tabs.setTabVisible(self._participants_tab_idx, True)
            self._ctrl.set_mode(mode)

        self._main_stack.setCurrentIndex(1)   # Show app content
        self._change_mode_btn.show()

    def _go_back_to_mode_select(self) -> None:
        """Return to the mode selection screen."""
        self._main_stack.setCurrentIndex(0)   # Show mode select
        self._change_mode_btn.hide()
        self._tabs.setTabVisible(self._participants_tab_idx, False)
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self._status.showMessage("Ready — select a drawing mode to begin.")

    # ── Admin dev mode ─────────────────────────────────────────────

    def _on_admin_shortcut(self) -> None:
        """Handle Ctrl+Shift+X — open admin login dialog."""
        dlg = AdminLoginDialog(parent=self)
        if dlg.exec():
            # Verify password
            if self._admin_ctrl.authenticate(dlg.password):
                self._admin_ctrl.set_admin_name(dlg.admin_name)
                self._dev_mode = True
                self.setWindowTitle(f"{APP_NAME} — ⚠ DEV MODE")
                self._header_title.setText(f"{APP_NAME.upper()}  ⚠ DEV MODE")
                self._header_title.setStyleSheet(
                    f"color: {COLORS['accent_red']}; letter-spacing: 3px;"
                )
                self._status.showMessage(f"⚠ Dev Mode active — Admin: {dlg.admin_name}")

                # Open admin panel
                panel = AdminPanel(self._admin_ctrl, parent=self)
                panel.exec()
            else:
                QMessageBox.warning(self, "Access Denied", "Incorrect admin password.")

    # ── Signal handlers ────────────────────────────────────────────

    def _on_draw_done(self, result) -> None:
        count = len(result.winners)
        label = "redraw" if result.is_redraw else "draw"
        self._status.showMessage(
            f"{label.capitalize()} complete — {count} winner(s) for '{result.prize.prize_name}'."
        )

    def _on_error(self, message: str) -> None:
        self._status.showMessage(f"⚠  {message}", 5000)
