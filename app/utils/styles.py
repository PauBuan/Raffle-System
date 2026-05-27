"""
app/utils/styles.py
--------------------
Central Qt stylesheet and font helpers.
Import get_stylesheet() and apply to QApplication.
"""

from config.settings import COLORS

_C = COLORS


def get_stylesheet() -> str:
    """Return the global dark-theme Qt stylesheet for the application."""
    return f"""
    /* ── Global ──────────────────────────────────────────── */
    QWidget {{
        background-color: {_C['bg_dark']};
        color:            {_C['text_primary']};
        font-family:      'Segoe UI', 'Arial', sans-serif;
        font-size:        13px;
    }}

    /* ── Cards / panels ──────────────────────────────────── */
    QFrame#card {{
        background-color: {_C['bg_card']};
        border:           1px solid {_C['border']};
        border-radius:    10px;
    }}

    /* ── Buttons ─────────────────────────────────────────── */
    QPushButton {{
        background-color: {_C['bg_card2']};
        color:            {_C['text_primary']};
        border:           1px solid {_C['border']};
        border-radius:    6px;
        padding:          8px 18px;
        font-weight:      600;
    }}
    QPushButton:hover {{
        background-color: {_C['accent_blue']};
        color:            #000000;
        border-color:     {_C['accent_blue']};
    }}
    QPushButton:pressed {{
        background-color: #2979a0;
    }}
    QPushButton#btn_draw {{
        background-color: {_C['accent_gold']};
        color:            #000000;
        font-size:        15px;
        font-weight:      700;
        padding:          12px 30px;
        border-radius:    8px;
        border:           none;
    }}
    QPushButton#btn_draw:hover {{
        background-color: #ffe94d;
    }}
    QPushButton#btn_redraw {{
        background-color: {_C['accent_red']};
        color:            #ffffff;
        font-weight:      700;
    }}
    QPushButton#btn_redraw:hover {{
        background-color: #ff7070;
    }}
    QPushButton#btn_danger {{
        background-color: transparent;
        color:            {_C['accent_red']};
        border:           1px solid {_C['accent_red']};
    }}

    /* ── ComboBox ────────────────────────────────────────── */
    QComboBox {{
        background-color: {_C['bg_card2']};
        border:           1px solid {_C['border']};
        border-radius:    6px;
        padding:          6px 10px;
        color:            {_C['text_primary']};
        min-width:        160px;
    }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox QAbstractItemView {{
        background-color: {_C['bg_card']};
        border:           1px solid {_C['border']};
        selection-background-color: {_C['accent_blue']};
        color: {_C['text_primary']};
    }}

    /* ── LineEdit / SpinBox ──────────────────────────────── */
    QLineEdit, QSpinBox {{
        background-color: {_C['bg_card2']};
        border:           1px solid {_C['border']};
        border-radius:    6px;
        padding:          6px 10px;
        color:            {_C['text_primary']};
    }}
    QLineEdit:focus, QSpinBox:focus {{
        border-color: {_C['accent_blue']};
    }}

    /* ── TableWidget ─────────────────────────────────────── */
    QTableWidget {{
        background-color: {_C['bg_card']};
        border:           1px solid {_C['border']};
        gridline-color:   {_C['border']};
        border-radius:    8px;
        outline:          none;
    }}
    QTableWidget::item {{
        padding: 6px 10px;
    }}
    QTableWidget::item:selected {{
        background-color: {_C['accent_blue']};
        color:            #000000;
    }}
    QHeaderView::section {{
        background-color: {_C['bg_card2']};
        color:            {_C['accent_gold']};
        border:           none;
        border-bottom:    1px solid {_C['border']};
        padding:          8px 10px;
        font-weight:      700;
        font-size:        12px;
        letter-spacing:   1px;
        text-transform:   uppercase;
    }}

    /* ── ScrollBar ───────────────────────────────────────── */
    QScrollBar:vertical {{
        background: {_C['bg_dark']};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {_C['border']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {_C['accent_blue']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

    /* ── Labels ──────────────────────────────────────────── */
    QLabel#title {{
        font-size:   22px;
        font-weight: 700;
        color:       {_C['accent_gold']};
        letter-spacing: 2px;
    }}
    QLabel#subtitle {{
        font-size:  14px;
        color:      {_C['text_muted']};
    }}
    QLabel#section_header {{
        font-size:   15px;
        font-weight: 700;
        color:       {_C['accent_blue']};
        letter-spacing: 1px;
        text-transform: uppercase;
    }}

    /* ── Tab widget ──────────────────────────────────────── */
    QTabWidget::pane {{
        border:           1px solid {_C['border']};
        background-color: {_C['bg_dark']};
        border-radius:    8px;
    }}
    QTabBar::tab {{
        background-color: {_C['bg_card']};
        color:            {_C['text_muted']};
        padding:          10px 22px;
        border:           none;
        font-weight:      600;
    }}
    QTabBar::tab:selected {{
        color:            {_C['accent_gold']};
        border-bottom:    2px solid {_C['accent_gold']};
        background-color: {_C['bg_card2']};
    }}

    /* ── Splitter ────────────────────────────────────────── */
    QSplitter::handle {{
        background: {_C['border']};
    }}

    /* ── Dialog / Wizard cards ───────────────────────────── */
    QFrame#dialog_card, QFrame#wizard_card {{
        background-color: {_C['bg_card']};
        border:           1px solid {_C['border']};
        border-radius:    14px;
        padding:          20px;
    }}

    QFrame#login_card {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
            stop:0 {_C['bg_card2']}, stop:1 {_C['bg_card']});
        border:           2px solid {_C['accent_gold']};
        border-radius:    16px;
        padding:          30px;
    }}

    /* ── Action buttons ─────────────────────────────────── */
    QPushButton#btn_add {{
        background-color: {_C['accent_green']};
        color:            #000000;
        font-weight:      700;
        border:           none;
        border-radius:    6px;
        padding:          8px 18px;
    }}
    QPushButton#btn_add:hover {{
        background-color: #6bffb8;
    }}

    QPushButton#btn_confirm {{
        background-color: {_C['accent_gold']};
        color:            #000000;
        font-weight:      700;
        border:           none;
        border-radius:    8px;
        padding:          10px 28px;
        font-size:        14px;
    }}
    QPushButton#btn_confirm:hover {{
        background-color: #ffe94d;
    }}

    QPushButton#btn_mode {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
            stop:0 {_C['bg_card2']}, stop:1 {_C['bg_card']});
        border:           2px solid {_C['border']};
        border-radius:    16px;
    }}
    QPushButton#btn_mode:hover {{
        border-color: {_C['accent_blue']};
    }}

    /* ── Progress bar (wizard steps) ────────────────────── */
    QProgressBar {{
        background-color: {_C['bg_card2']};
        border:           1px solid {_C['border']};
        border-radius:    6px;
        text-align:       center;
        color:            {_C['text_primary']};
        font-weight:      600;
        height:           18px;
    }}
    QProgressBar::chunk {{
        background-color: {_C['accent_blue']};
        border-radius:    5px;
    }}

    /* ── Dialog styling ─────────────────────────────────── */
    QDialog {{
        background-color: {_C['bg_dark']};
        border:           1px solid {_C['border']};
        border-radius:    12px;
    }}

    /* ── GroupBox (admin panel sections) ─────────────────── */
    QGroupBox {{
        background-color: {_C['bg_card']};
        border:           1px solid {_C['border']};
        border-radius:    10px;
        margin-top:       16px;
        padding-top:      20px;
        font-weight:      700;
        color:            {_C['accent_blue']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding:          4px 12px;
        background-color: {_C['bg_card2']};
        border:           1px solid {_C['border']};
        border-radius:    6px;
        color:            {_C['accent_gold']};
        font-size:        12px;
        letter-spacing:   1px;
    }}
    """

