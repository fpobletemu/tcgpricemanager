"""
TCG Price Manager — entry point.
"""
import sys
import os
import traceback
from pathlib import Path

# Fix SSL cert path before any import that might use requests (frozen EXE only).
# PyInstaller bundles certifi but doesn't set the env vars — without this,
# every HTTPS call fails on machines without Python installed.
if getattr(sys, "frozen", False):
    _cert = os.path.join(sys._MEIPASS, "certifi", "cacert.pem")
    os.environ.setdefault("SSL_CERT_FILE", _cert)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _cert)

# Ensure 'app' package is importable when running as: python tcg_app/main.py
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from app.db import database as db
from app.ui.main_window import MainWindow
from app.ui import theme


def _global_exception_handler(exc_type, exc_value, exc_tb):
    """Show unhandled exceptions in a dialog instead of silently crashing."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(msg, file=sys.stderr)
    try:
        box = QMessageBox()
        box.setWindowTitle("Error inesperado")
        box.setIcon(QMessageBox.Icon.Critical)
        box.setText(f"<b>{exc_type.__name__}:</b> {exc_value}")
        box.setDetailedText(msg)
        box.exec()
    except Exception:
        pass


def main():
    sys.excepthook = _global_exception_handler

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("TCG Price Manager")
    app.setOrganizationName("TCGPriceManager")
    app.setStyleSheet(theme.STYLESHEET)

    conn = db.initialize_db()

    window = MainWindow(conn)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
