"""
app/utils/helpers.py
--------------------
Small UI helper functions used across the presentation layer.
"""

import csv
import os
from typing import List, Dict, Optional

from PySide6.QtWidgets import QMessageBox, QWidget, QLabel, QFileDialog
from PySide6.QtCore import Qt, QTimer

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


def show_toast(parent: QWidget, message: str, duration_ms: int = 3000) -> None:
    """
    Show a non-blocking toast notification at the bottom of the parent widget.
    Auto-hides after duration_ms milliseconds.
    """
    toast = QLabel(message, parent)
    toast.setAlignment(Qt.AlignCenter)
    toast.setStyleSheet(f"""
        QLabel {{
            background-color: {COLORS['accent_gold']};
            color: #000;
            font-weight: 600;
            font-size: 12px;
            padding: 10px 24px;
            border-radius: 8px;
        }}
    """)
    toast.setFixedHeight(40)
    toast.adjustSize()

    # Position at bottom center
    x = max(0, (parent.width() - toast.width()) // 2)
    y = parent.height() - 60
    toast.move(x, y)
    toast.show()
    toast.raise_()

    QTimer.singleShot(duration_ms, toast.deleteLater)


def export_csv(
    parent: QWidget,
    rows: List[Dict[str, str]],
    default_filename: str = "raffle_export.csv",
    title: str = "Export to CSV",
) -> Optional[str]:
    """
    Export a list of dicts to a CSV file via a Save dialog.

    Parameters
    ----------
    parent : QWidget
        Parent widget for the file dialog.
    rows : list[dict]
        Each dict is one row; keys become column headers.
    default_filename : str
        Suggested filename in the Save dialog.
    title : str
        Dialog window title.

    Returns
    -------
    str | None
        The path where the file was saved, or ``None`` if the user cancelled.
    """
    if not rows:
        show_error(parent, "Nothing to export — the list is empty.")
        return None

    filepath, _ = QFileDialog.getSaveFileName(
        parent,
        title,
        default_filename,
        "CSV Files (*.csv);;All Files (*)",
    )
    if not filepath:
        return None

    # Ensure .csv extension
    if not filepath.lower().endswith(".csv"):
        filepath += ".csv"

    fieldnames = list(rows[0].keys())

    try:
        with open(filepath, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except OSError as exc:
        show_error(parent, f"Failed to save file:\n{exc}")
        return None

    show_toast(parent, f"Exported {len(rows)} rows → {os.path.basename(filepath)}")
    return filepath
