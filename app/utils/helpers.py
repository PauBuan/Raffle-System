"""
app/utils/helpers.py
--------------------
Small UI helper functions used across the presentation layer.
"""

from PySide6.QtWidgets import QMessageBox, QWidget

from config.settings import (
    COLORS, CATEGORY_MINOR, CATEGORY_MAJOR, CATEGORY_GRAND,
)


def show_error(parent: QWidget, message: str) -> None:
    """Display a styled error message box."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Error")
    box.setText(message)
    box.exec()


def confirm(parent: QWidget, message: str) -> bool:
    """Show a Yes/No confirmation dialog; return True if Yes."""
    reply = QMessageBox.question(
        parent,
        "Confirm",
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return reply == QMessageBox.Yes


def badge_color(category: str) -> str:
    """Return the accent colour for the given prize category."""
    return {
        CATEGORY_MINOR: COLORS["accent_green"],
        CATEGORY_MAJOR: COLORS["accent_blue"],
        CATEGORY_GRAND: COLORS["accent_gold"],
    }.get(category, COLORS["text_muted"])
