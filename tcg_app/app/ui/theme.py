"""
TCG Price Manager — dark theme stylesheet and icon helpers.
Single source of truth for all visual design decisions.
"""
import qtawesome as qta
from PyQt6.QtGui import QIcon

# ── Color palette ──────────────────────────────────────────────────────────
BG      = "#0d1117"
SURFACE = "#161b22"
BORDER  = "#30363d"
ACCENT  = "#58a6ff"
SUCCESS = "#3fb950"
WARNING = "#d29922"
DANGER  = "#f85149"
TEXT    = "#e6edf3"
MUTED   = "#7d8590"
HOVER   = "#1f2937"

# ── Global QSS ────────────────────────────────────────────────────────────
STYLESHEET = f"""
/* ── Base ─────────────────────────────────────────────── */
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
}}

QMainWindow, QDialog {{
    background-color: {BG};
}}

/* ── Tab bar ────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {SURFACE};
    margin-top: -1px;
}}

QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 10px 22px;
    border: none;
    font-size: 10pt;
    min-width: 120px;
}}

QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    color: {TEXT};
    background: {HOVER};
    border-radius: 4px 4px 0 0;
}}

/* ── Buttons ────────────────────────────────────────────── */
QPushButton {{
    background-color: #21262d;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 10pt;
    min-width: 90px;
}}

QPushButton:hover {{
    background-color: #30363d;
    border-color: #8b949e;
}}

QPushButton:pressed {{
    background-color: {HOVER};
}}

QPushButton:disabled {{
    color: {MUTED};
    border-color: #21262d;
    background-color: #161b22;
}}

QPushButton#primaryBtn {{
    background-color: #1f6feb;
    border-color: #388bfd;
    color: #ffffff;
}}

QPushButton#primaryBtn:hover {{
    background-color: #388bfd;
    border-color: #58a6ff;
}}

QPushButton#primaryBtn:pressed {{
    background-color: #1158c7;
}}

QPushButton#primaryBtn:disabled {{
    background-color: #1a2433;
    border-color: {BORDER};
    color: {MUTED};
}}

/* ── Inputs ─────────────────────────────────────────────── */
QLineEdit, QTextEdit, QComboBox {{
    background-color: #0d1117;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 10pt;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}}

QLineEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
    padding-right: 4px;
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    selection-background-color: {HOVER};
    color: {TEXT};
    padding: 4px;
    outline: none;
}}

/* ── Tables ─────────────────────────────────────────────── */
QTableView, QTableWidget {{
    background-color: {BG};
    color: {TEXT};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 6px;
    alternate-background-color: {SURFACE};
    selection-background-color: #1a2d4a;
    selection-color: {TEXT};
    font-size: 9.5pt;
    outline: none;
}}

QTableView::item, QTableWidget::item {{
    padding: 6px 8px;
    border: none;
}}

QHeaderView::section {{
    background-color: {SURFACE};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    padding: 8px 10px;
    font-weight: 600;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}

QHeaderView::section:last {{
    border-right: none;
}}

/* ── Progress bar ───────────────────────────────────────── */
QProgressBar {{
    background-color: {SURFACE};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}

/* ── Labels ─────────────────────────────────────────────── */
QLabel#sectionTitle {{
    font-size: 14pt;
    font-weight: 700;
    color: {TEXT};
    padding-bottom: 4px;
}}

QLabel#mutedLabel {{
    color: {MUTED};
    font-size: 9pt;
}}

QLabel#accentLabel {{
    color: {ACCENT};
    font-weight: 600;
}}

/* ── Scroll bars ────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: #484f58;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Group boxes ────────────────────────────────────────── */
QGroupBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 14px 12px 14px;
    font-weight: 600;
    font-size: 9pt;
    color: {MUTED};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {MUTED};
    background-color: {SURFACE};
}}

/* ── Status bar ─────────────────────────────────────────── */
QStatusBar {{
    background-color: {SURFACE};
    border-top: 1px solid {BORDER};
    color: {MUTED};
    font-size: 9pt;
    padding: 2px 8px;
}}

QStatusBar::item {{
    border: none;
}}

/* ── Splitter ───────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

/* ── Tooltips ───────────────────────────────────────────── */
QToolTip {{
    background-color: #1b2030;
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 5px 8px;
    border-radius: 4px;
    font-size: 9pt;
}}

/* ── Dialog ─────────────────────────────────────────────── */
QDialog {{
    background-color: {SURFACE};
}}

QDialog QGroupBox {{
    background-color: #1a1f27;
}}

/* ── Radio buttons ──────────────────────────────────────── */
QRadioButton {{
    spacing: 8px;
    color: {TEXT};
    font-size: 10pt;
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {BORDER};
    border-radius: 8px;
    background: {BG};
}}

QRadioButton::indicator:checked {{
    border-color: {ACCENT};
    background-color: {ACCENT};
}}

QRadioButton::indicator:hover {{
    border-color: {ACCENT};
}}

/* ── Frame separator ────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {BORDER};
    background-color: {BORDER};
    border: none;
    max-height: 1px;
}}
"""


# ── Helpers ────────────────────────────────────────────────────────────────
def icon(fa_name: str, color: str = MUTED) -> QIcon:
    """Return a qtawesome Font Awesome 6 Solid icon, or empty QIcon on failure."""
    try:
        return qta.icon(f"fa6s.{fa_name}", color=color)
    except Exception:
        try:
            return qta.icon(f"fa6r.{fa_name}", color=color)
        except Exception:
            return QIcon()


def badge_style(score: int) -> str:
    """Return inline QSS for a score badge label."""
    if score >= 90:
        return (
            f"background-color: #1a3a2a; color: {SUCCESS}; "
            "border-radius: 10px; padding: 2px 10px; "
            "font-size: 9pt; font-weight: 700;"
        )
    elif score >= 70:
        return (
            f"background-color: #3a2e0a; color: {WARNING}; "
            "border-radius: 10px; padding: 2px 10px; "
            "font-size: 9pt; font-weight: 700;"
        )
    return (
        f"background-color: #3a1010; color: {DANGER}; "
        "border-radius: 10px; padding: 2px 10px; "
        "font-size: 9pt; font-weight: 700;"
    )
