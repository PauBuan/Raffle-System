"""
app/views/dialogs/admin_login_dialog.py
----------------------------------------
Admin / Dev mode login dialog.
Triggered by Ctrl+Shift+X global shortcut.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QColor

from config.settings import COLORS


class AdminLoginDialog(QDialog):
    """
    Login dialog for entering admin dev mode.
    Access .admin_name and .password after exec().
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.admin_name: str = ""
        self.password:   str = ""

        self.setWindowTitle("Admin Access")
        self.setFixedSize(420, 340)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("login_card")
        card.setStyleSheet(f"""
            QFrame#login_card {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['accent_red']};
                border-radius: 14px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 140))
        card.setGraphicsEffect(shadow)

        root = QVBoxLayout(card)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("🔐  Admin Access")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_red']}; background: transparent;")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("X")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['text_muted']};
                border: none; font-size: 16px; font-weight: 700; border-radius: 16px;
            }}
            QPushButton:hover {{ background: {COLORS['accent_red']}; color: #fff; }}
        """)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        root.addLayout(header)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {COLORS['border']};")
        root.addWidget(div)
        root.addSpacing(12)

        # Admin Name
        name_lbl = QLabel("ADMIN NAME")
        name_lbl.setStyleSheet(self._label_style())
        root.addWidget(name_lbl)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Your name (for audit log)")
        self._name_edit.setStyleSheet(self._input_style())
        root.addWidget(self._name_edit)
        root.addSpacing(6)

        # Password
        pw_lbl = QLabel("PASSWORD")
        pw_lbl.setStyleSheet(self._label_style())
        root.addWidget(pw_lbl)

        self._pw_edit = QLineEdit()
        self._pw_edit.setEchoMode(QLineEdit.Password)
        self._pw_edit.setPlaceholderText("Enter admin password")
        self._pw_edit.setStyleSheet(self._input_style())
        self._pw_edit.returnPressed.connect(self._on_login)
        root.addWidget(self._pw_edit)

        # Error
        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(f"color: {COLORS['accent_red']}; font-size: 11px; background: transparent;")
        self._error_lbl.hide()
        root.addWidget(self._error_lbl)

        root.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']}; border-radius: 8px;
                padding: 0 24px; font-weight: 600; font-size: 13px;
            }}
            QPushButton:hover {{ border-color: {COLORS['text_primary']}; color: {COLORS['text_primary']}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        login_btn = QPushButton("Enter Dev Mode")
        login_btn.setFixedHeight(40)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_red']}; color: #fff; border: none;
                border-radius: 8px; padding: 0 28px; font-weight: 700; font-size: 13px;
            }}
            QPushButton:hover {{ background: #ff7070; }}
        """)
        login_btn.clicked.connect(self._on_login)
        btn_row.addWidget(login_btn)

        root.addLayout(btn_row)
        outer.addWidget(card)

    def _on_login(self) -> None:
        name = self._name_edit.text().strip()
        pw = self._pw_edit.text()

        if not name:
            self._error_lbl.setText("Admin name is required.")
            self._error_lbl.show()
            return

        self.admin_name = name
        self.password = pw
        self.accept()

    @staticmethod
    def _label_style() -> str:
        return f"""
            color: {COLORS['text_muted']}; font-size: 11px;
            font-weight: 600; letter-spacing: 1px; background: transparent;
        """

    @staticmethod
    def _input_style() -> str:
        return f"""
            background-color: {COLORS['bg_card2']}; border: 1px solid {COLORS['border']};
            border-radius: 8px; padding: 8px 12px; color: {COLORS['text_primary']}; font-size: 13px;
        """

    # Dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
