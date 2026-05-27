"""
app/views/dialogs/add_prize_dialog.py
--------------------------------------
Modal dialog for adding a new prize to any category.

Routing
-------
    DrawPanel._on_add_prize()  →  AddPrizeDialog.exec()
        → user fills form → dialog.accept()
    DrawPanel  →  RaffleController.add_prize(category, name, qty)
        → RaffleService.add_prize()
        → PrizeRepository.add_prize()  →  INSERT INTO Prizes
        → controller.prizes_updated signal  →  DrawPanel.refresh_prizes()
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QComboBox, QPushButton, QFrame,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QColor
from config.settings import COLORS, CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND


class AddPrizeDialog(QDialog):
    """
    Collects prize details from the user.
    Access results via .category, .prize_name, .quantity after exec().
    """

    def __init__(self, default_category: str = CATEGORY_MINOR, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add New Prize")
        self.setFixedSize(460, 400)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.category:      str = default_category
        self.prize_name:    str = ""
        self.winner_count:  int = 1

        self._build_ui(default_category)

    def _build_ui(self, default_category: str) -> None:
        # Outer layout (transparent) — holds the styled card
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        # Card container with shadow
        card = QFrame()
        card.setObjectName("dialog_card")
        card.setStyleSheet(f"""
            QFrame#dialog_card {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        card.setGraphicsEffect(shadow)

        root = QVBoxLayout(card)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(6)

        # ── Header ─────────────────────────────────────────────────
        header_row = QHBoxLayout()
        title = QLabel("Add New Prize")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_gold']}; background: transparent;")
        header_row.addWidget(title)
        header_row.addStretch()

        close_btn = QPushButton("X")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_muted']};
                border: none;
                font-size: 16px;
                font-weight: 700;
                border-radius: 16px;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_red']};
                color: #fff;
            }}
        """)
        close_btn.clicked.connect(self.reject)
        header_row.addWidget(close_btn)
        root.addLayout(header_row)

        # Subtle divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {COLORS['border']};")
        root.addWidget(div)
        root.addSpacing(10)

        # ── Category ───────────────────────────────────────────────
        root.addWidget(self._make_label("CATEGORY"))
        self._cat_combo = QComboBox()
        self._cat_combo.setStyleSheet(self._input_style())
        for cat in [CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND]:
            self._cat_combo.addItem(cat)
        self._cat_combo.setCurrentText(default_category)
        root.addWidget(self._cat_combo)
        root.addSpacing(6)

        # ── Prize Name ─────────────────────────────────────────────
        root.addWidget(self._make_label("PRIZE NAME"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Gift Card P500")
        self._name_edit.setStyleSheet(self._input_style())
        root.addWidget(self._name_edit)

        # Error hint (hidden by default)
        self._error_lbl = QLabel("Prize name is required.")
        self._error_lbl.setStyleSheet(f"""
            color: {COLORS['accent_red']};
            font-size: 11px;
            background: transparent;
            padding-left: 4px;
        """)
        self._error_lbl.hide()
        root.addWidget(self._error_lbl)
        root.addSpacing(6)

        # ── Quantity ───────────────────────────────────────────────
        root.addWidget(self._make_label("NUMBER OF WINNERS"))
        self._qty_spin = QSpinBox()
        self._qty_spin.setMinimum(1)
        self._qty_spin.setMaximum(100)
        self._qty_spin.setValue(1)
        self._qty_spin.setStyleSheet(self._input_style())
        root.addWidget(self._qty_spin)

        root.addStretch()

        # ── Action buttons ─────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 0 24px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['text_primary']};
                color: {COLORS['text_primary']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        add_btn = QPushButton("Add Prize")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(40)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_gold']};
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 0 32px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: #ffe94d;
            }}
            QPushButton:pressed {{
                background: #e6c200;
            }}
        """)
        add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(add_btn)

        root.addLayout(btn_row)
        outer.addWidget(card)

    # ── Helpers ────────────────────────────────────────────────────

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            background: transparent;
            padding-left: 2px;
            margin-bottom: 0px;
        """)
        return lbl

    @staticmethod
    def _input_style() -> str:
        return f"""
            background-color: {COLORS['bg_card2']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 8px 12px;
            color: {COLORS['text_primary']};
            font-size: 13px;
        """

    def _on_add(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._error_lbl.show()
            self._name_edit.setStyleSheet(f"""
                background-color: {COLORS['bg_card2']};
                border: 1px solid {COLORS['accent_red']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            """)
            self._name_edit.setFocus()
            return

        self._error_lbl.hide()
        self.category     = self._cat_combo.currentText()
        self.prize_name   = name
        self.winner_count = self._qty_spin.value()
        self.accept()

    # Allow dragging the frameless dialog
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
