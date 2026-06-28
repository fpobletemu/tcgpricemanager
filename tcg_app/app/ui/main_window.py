"""
Main application window — QTabWidget with 4 tabs and a status bar.
"""
from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QStatusBar, QLabel
from PyQt6.QtGui import QIcon

from app.ui import theme
from app.ui.tab_sync     import SyncTab
from app.ui.tab_search   import SearchTab
from app.ui.tab_batch    import BatchTab
from app.ui.tab_settings import SettingsTab
from app.db import database as db


class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self._build_ui()
        self._update_status()

    def _build_ui(self):
        self.setWindowTitle("TCG Price Manager")
        self.setMinimumSize(1120, 740)
        self.resize(1280, 820)

        # Window icon
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # ── Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tab_sync     = SyncTab(self.conn, self)
        self.tab_search   = SearchTab(self.conn)
        self.tab_batch    = BatchTab(self.conn)
        self.tab_settings = SettingsTab(self.conn)

        self.tabs.addTab(self.tab_sync,     theme.icon("rotate"),           "  Sincronización")
        self.tabs.addTab(self.tab_search,   theme.icon("magnifying-glass"), "  Búsqueda")
        self.tabs.addTab(self.tab_batch,    theme.icon("list-check"),       "  Por Lotes")
        self.tabs.addTab(self.tab_settings, theme.icon("gear"),             "  Configuración")

        self.setCentralWidget(self.tabs)

        # ── Status bar
        self._status_msg   = QLabel("Listo")
        self._status_rate  = QLabel()
        self._status_count = QLabel()
        sep1 = QLabel("  |  ")
        sep2 = QLabel("  |  ")
        for w in (self._status_msg, self._status_rate, self._status_count, sep1, sep2):
            w.setObjectName("mutedLabel")

        sb = QStatusBar()
        sb.addWidget(self._status_msg, 1)
        sb.addPermanentWidget(self._status_rate)
        sb.addPermanentWidget(sep1)
        sb.addPermanentWidget(self._status_count)
        self.setStatusBar(sb)

        # ── Signal connections
        self.tab_sync.sync_done.connect(self._on_sync_done)
        self.tab_settings.rate_updated.connect(self._update_status)

    def _update_status(self):
        stats = db.get_db_stats(self.conn)
        rate  = db.get_setting(self.conn, "usd_clp_rate")
        self._status_count.setText(f"🃏  {stats['products']:,} productos")
        if rate:
            self._status_rate.setText(f"💱  1 USD = ${float(rate):,.0f} CLP")
        else:
            self._status_rate.setText("💱  Sin tasa  —  ve a Configuración")

    def _on_sync_done(self):
        self._update_status()
        self.tab_search.refresh_groups()
        self.set_status("Sincronización completada")

    def set_status(self, msg: str):
        self._status_msg.setText(msg)
