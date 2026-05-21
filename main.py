"""
main.py
-------
Application entry point for the Raffle System.

Usage
-----
    python main.py

Requirements
------------
    PySide6, pyodbc (optional — falls back to SQLite demo mode)
"""

import sys
import logging

from PySide6.QtWidgets import QApplication

from app.views   import MainWindow
from app.utils   import get_stylesheet
from config      import APP_NAME


def configure_logging() -> None:
    """Set up application-wide logging to stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    configure_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(get_stylesheet())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
