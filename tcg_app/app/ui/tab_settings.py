"""
Tab: Configuración — exchange rate management and database statistics.
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel,
    QPushButton, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui import theme
from app.db import database as db
from app.api import exchange
from app.core import updater as upd
from version import __version__


class SettingsTab(QWidget):
    rate_updated = pyqtSignal()

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        title = QLabel("Configuración")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        # ── Exchange rate
        rate_box    = QGroupBox("Tipo de cambio  USD → CLP")
        rate_layout = QGridLayout(rate_box)
        rate_layout.setSpacing(10)
        rate_layout.setColumnStretch(1, 1)

        lbl_h = QLabel("Tasa actual:")
        lbl_h.setObjectName("mutedLabel")

        self._lbl_rate = QLabel("—")
        self._lbl_rate.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self._lbl_rate.setStyleSheet(f"color: {theme.ACCENT};")

        self._lbl_rate_ts = QLabel()
        self._lbl_rate_ts.setObjectName("mutedLabel")

        self._btn_rate = QPushButton(
            theme.icon("arrows-rotate", theme.TEXT), "  Actualizar tasa"
        )
        self._btn_rate.setFixedWidth(180)
        self._btn_rate.clicked.connect(self._update_rate)

        rate_layout.addWidget(lbl_h,            0, 0)
        rate_layout.addWidget(self._lbl_rate,   1, 0)
        rate_layout.addWidget(self._lbl_rate_ts,2, 0)
        rate_layout.addWidget(self._btn_rate,   1, 1, Qt.AlignmentFlag.AlignRight)
        root.addWidget(rate_box)

        # ── DB stats
        db_box    = QGroupBox("Base de datos")
        db_layout = QGridLayout(db_box)
        db_layout.setSpacing(8)
        db_layout.setColumnStretch(1, 1)

        self._lbl_products  = QLabel("—")
        self._lbl_prices    = QLabel("—")
        self._lbl_last_sync = QLabel("—")
        self._lbl_db_path   = QLabel()
        self._lbl_db_path.setObjectName("mutedLabel")
        self._lbl_db_path.setWordWrap(True)

        bold_font = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
        for lbl in (self._lbl_products, self._lbl_prices, self._lbl_last_sync):
            lbl.setFont(bold_font)

        for i, (label, widget) in enumerate([
            ("Productos:",           self._lbl_products),
            ("Precios:",             self._lbl_prices),
            ("Última sincronización:", self._lbl_last_sync),
            ("Archivo:",             self._lbl_db_path),
        ]):
            h = QLabel(label)
            h.setObjectName("mutedLabel")
            db_layout.addWidget(h,      i, 0)
            db_layout.addWidget(widget, i, 1)

        root.addWidget(db_box)

        # ── Dirs
        dirs_box    = QGroupBox("Directorios")
        dirs_layout = QGridLayout(dirs_box)
        dirs_layout.setSpacing(8)
        dirs_layout.setColumnStretch(1, 1)

        base = Path(__file__).resolve().parent.parent.parent.parent
        for i, (label, path) in enumerate([
            ("CSVs fuente:",           base / "output_pokemon_tcg"),
            ("Imágenes descargadas:",  base / "downloads"),
        ]):
            h = QLabel(label)
            h.setObjectName("mutedLabel")
            v = QLabel(str(path))
            v.setFont(QFont("Consolas", 9))
            v.setWordWrap(True)
            dirs_layout.addWidget(h, i, 0)
            dirs_layout.addWidget(v, i, 1)

        root.addWidget(dirs_box)

        # ── Updates box
        upd_box    = QGroupBox("Actualizaciones")
        upd_layout = QGridLayout(upd_box)
        upd_layout.setSpacing(10)
        upd_layout.setColumnStretch(1, 1)

        ver_lbl = QLabel("Versión instalada:")
        ver_lbl.setObjectName("mutedLabel")
        self._lbl_version = QLabel(__version__)
        self._lbl_version.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))

        self._lbl_upd_status = QLabel("—")
        self._lbl_upd_status.setObjectName("mutedLabel")
        self._lbl_upd_status.setWordWrap(True)

        self._btn_check_upd = QPushButton(
            theme.icon("arrows-rotate", theme.TEXT), "  Buscar actualizaciones"
        )
        self._btn_check_upd.setFixedWidth(210)
        self._btn_check_upd.clicked.connect(self._check_for_updates)

        self._btn_install_upd = QPushButton(
            theme.icon("download", "#ffffff"), "  Instalar actualización"
        )
        self._btn_install_upd.setObjectName("primaryBtn")
        self._btn_install_upd.setFixedWidth(210)
        self._btn_install_upd.setVisible(False)
        self._btn_install_upd.clicked.connect(self._install_update)
        self._pending_update: dict | None = None

        upd_layout.addWidget(ver_lbl,               0, 0)
        upd_layout.addWidget(self._lbl_version,     0, 1)
        upd_layout.addWidget(self._lbl_upd_status,  1, 0, 1, 2)
        upd_layout.addWidget(self._btn_check_upd,   2, 0)
        upd_layout.addWidget(self._btn_install_upd, 2, 1, Qt.AlignmentFlag.AlignLeft)
        root.addWidget(upd_box)

        root.addStretch()

    def _refresh(self):
        stats    = db.get_db_stats(self.conn)
        rate_str = db.get_setting(self.conn, "usd_clp_rate")
        rate_ts  = db.get_setting(self.conn, "usd_clp_updated_at")

        if rate_str:
            self._lbl_rate.setText(f"$ {float(rate_str):,.2f} CLP")
        if rate_ts:
            self._lbl_rate_ts.setText(
                f"Actualizado: {rate_ts[:16].replace('T', ' ')} UTC"
            )

        self._lbl_products.setText(f"{stats['products']:,}")
        self._lbl_prices.setText(f"{stats['prices']:,}")
        self._lbl_last_sync.setText(stats["last_sync"])
        self._lbl_db_path.setText(str(db.DB_PATH))

    def _update_rate(self):
        self._btn_rate.setEnabled(False)
        self._lbl_rate_ts.setText("Actualizando…")
        try:
            rate, ts = exchange.fetch_and_save(self.conn)
            self._lbl_rate.setText(f"$ {rate:,.2f} CLP")
            self._lbl_rate_ts.setText(f"Actualizado: {ts}")
            self.rate_updated.emit()
        except Exception as e:
            self._lbl_rate_ts.setText(f"Error: {e}")
        finally:
            self._btn_rate.setEnabled(True)

    def _check_for_updates(self):
        self._btn_check_upd.setEnabled(False)
        self._lbl_upd_status.setText("Consultando servidor…")
        self._btn_install_upd.setVisible(False)
        version_url = db.get_setting(self.conn, "update_url") or upd.DEFAULT_VERSION_URL
        try:
            info = upd.check_for_update(version_url)
            if info:
                self._pending_update = info
                notes = info.get("release_notes", "")
                self._lbl_upd_status.setText(
                    f"Nueva versión disponible: v{info['version']}\n{notes}"
                )
                self._lbl_upd_status.setStyleSheet(f"color: {theme.SUCCESS};")
                self._btn_install_upd.setVisible(True)
            elif info is None and not upd.is_frozen():
                self._lbl_upd_status.setText(
                    f"ℹ  Modo desarrollo (script) — usa git pull para actualizar."
                )
                self._lbl_upd_status.setStyleSheet(f"color: {theme.MUTED};")
            else:
                self._lbl_upd_status.setText(f"✔  Estás al día (v{__version__})")
                self._lbl_upd_status.setStyleSheet(f"color: {theme.SUCCESS};")
        except Exception as e:
            self._lbl_upd_status.setText(f"Sin conexión o error: {e}")
            self._lbl_upd_status.setStyleSheet(f"color: {theme.WARNING};")
        finally:
            self._btn_check_upd.setEnabled(True)

    def _install_update(self):
        if not self._pending_update:
            return
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        info = self._pending_update
        reply = QMessageBox.question(
            self, "Instalar actualización",
            f"Se instalará la versión {info['version']}.\n"
            "La aplicación se cerrará y volverá a abrirse.\n\n¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        dlg = QProgressDialog("Descargando actualización…", None, 0, 100, self)
        dlg.setWindowTitle("Actualizar")
        dlg.setModal(True)
        dlg.show()
        try:
            upd.download_and_install(
                info["download_url"],
                progress_cb=lambda c, t: dlg.setValue(int(c / t * 100)) if t else None,
            )
        except RuntimeError as e:
            dlg.close()
            QMessageBox.critical(self, "Error", str(e))
