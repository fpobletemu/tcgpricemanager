"""
Tab: Sincronización — import local CSVs or sync fresh data from the TCGCSV API.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QProgressBar, QTextEdit, QLabel, QGroupBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui import theme
from app.db import database as db
from app.core import sync


class _SyncWorker(QThread):
    progress = pyqtSignal(int, int, str)   # current, total, group_name
    finished = pyqtSignal(int, int)        # groups_done, rows_processed
    error    = pyqtSignal(str)

    def __init__(self, conn, mode: str):   # mode: 'local' | 'api'
        super().__init__()
        self.conn = conn
        self.mode = mode

    def run(self):
        try:
            def cb(cur, tot, name):
                self.progress.emit(cur, tot, name)

            if self.mode == "local":
                groups, rows = sync.import_local_csvs(self.conn, cb)
            else:
                groups, rows = sync.sync_from_api(self.conn, cb)

            self.finished.emit(groups, rows)
        except Exception as e:
            self.error.emit(str(e))


class SyncTab(QWidget):
    sync_done = pyqtSignal()

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn   = conn
        self.worker = None
        self._build_ui()
        self._refresh_info()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Sincronización de Datos")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        # ── Status info
        info_box    = QGroupBox("Estado actual")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(6)

        self._lbl_server = QLabel()
        self._lbl_last   = QLabel()
        self._lbl_db     = QLabel()
        for lbl in (self._lbl_server, self._lbl_last, self._lbl_db):
            lbl.setObjectName("mutedLabel")
            info_layout.addWidget(lbl)
        root.addWidget(info_box)

        # ── Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_local = QPushButton(
            theme.icon("hard-drive", theme.TEXT), "  Importar CSVs locales"
        )
        self.btn_local.setObjectName("primaryBtn")
        self.btn_local.setMinimumWidth(210)
        self.btn_local.setToolTip("Importa los CSVs ya descargados en output_pokemon_tcg/")

        self.btn_api = QPushButton(
            theme.icon("cloud-arrow-down", theme.TEXT), "  Sync desde API"
        )
        self.btn_api.setMinimumWidth(180)
        self.btn_api.setToolTip("Descarga datos actualizados desde TCGCSV y los importa")

        btn_row.addWidget(self.btn_local)
        btn_row.addWidget(self.btn_api)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ── Progress
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        root.addWidget(self._progress)

        self._prog_label = QLabel()
        self._prog_label.setObjectName("mutedLabel")
        self._prog_label.setVisible(False)
        root.addWidget(self._prog_label)

        # ── Log
        log_box    = QGroupBox("Log")
        log_layout = QVBoxLayout(log_box)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 9))
        self._log.setMinimumHeight(240)
        log_layout.addWidget(self._log)
        root.addWidget(log_box, 1)

        self.btn_local.clicked.connect(lambda: self._start("local"))
        self.btn_api.clicked.connect(lambda: self._start("api"))

    def _refresh_info(self):
        stats    = db.get_db_stats(self.conn)
        last_srv = db.get_setting(self.conn, "last_sync_at") or "—"
        self._lbl_server.setText(f"Última build del servidor :  {last_srv}")
        self._lbl_last.setText(  f"Última sincronización local :  {stats['last_sync']}")
        self._lbl_db.setText(
            f"Base de datos :  {stats['products']:,} productos  ·  {stats['prices']:,} precios"
        )

    def _log_msg(self, msg: str):
        self._log.append(msg)
        self._log.verticalScrollBar().setValue(
            self._log.verticalScrollBar().maximum()
        )

    def _set_busy(self, busy: bool):
        self.btn_local.setEnabled(not busy)
        self.btn_api.setEnabled(not busy)
        self._progress.setVisible(busy)
        self._prog_label.setVisible(busy)

    def _start(self, mode: str):
        self._set_busy(True)
        label = "CSVs locales" if mode == "local" else "API de TCGCSV"
        self._log_msg(f"\n──── Iniciando sync desde {label} ────")
        self._progress.setValue(0)
        self.worker = _SyncWorker(self.conn, mode)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, cur: int, total: int, name: str):
        self._progress.setMaximum(total)
        self._progress.setValue(cur)
        self._prog_label.setText(f"[{cur}/{total}]  {name}")
        if cur % 20 == 0 or cur == total:
            self._log_msg(f"  [{cur:>3}/{total}]  {name}")

    def _on_finished(self, groups: int, rows: int):
        self._set_busy(False)
        self._log_msg(
            f"\n✓  Sync completo —  {groups} grupos  ·  {rows:,} filas procesadas\n"
        )
        self._refresh_info()
        self.sync_done.emit()

    def _on_error(self, msg: str):
        self._set_busy(False)
        self._log_msg(f"\n✗  Error: {msg}\n")
