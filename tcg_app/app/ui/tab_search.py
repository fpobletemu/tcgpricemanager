"""
Tab: Búsqueda individual de cartas.
Filters by name, card number, or set. Shows a detail panel with prices in USD & CLP.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QTableView, QLabel, QGroupBox, QSplitter,
    QFrame, QScrollArea, QGridLayout, QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QFont, QPixmap
from pathlib import Path
import requests

from app.ui import theme
from app.db import database as db
from app.api import exchange
from app.core import export


class _ImageLoader(QThread):
    loaded = pyqtSignal(bytes)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            r = requests.get(self.url, timeout=10,
                             headers={"User-Agent": "TCGPriceManager/1.0.0"})
            r.raise_for_status()
            self.loaded.emit(r.content)
        except Exception:
            self.loaded.emit(b"")


class SearchTab(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn           = conn
        self._rate          = 900.0
        self._all_groups: list[dict] = []
        self._last_results: list[dict] = []   # for CSV export
        self._build_ui()
        self._load_groups()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Búsqueda de Cartas")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        # ── Filter bar
        filter_box  = QGroupBox("Filtros")
        filter_row  = QHBoxLayout(filter_box)
        filter_row.setSpacing(10)

        self._inp_name = QLineEdit()
        self._inp_name.setPlaceholderText("🔍  Nombre de la carta…")
        self._inp_name.returnPressed.connect(self._search)

        self._inp_number = QLineEdit()
        self._inp_number.setPlaceholderText("#  Código  (ej: 139/195)")
        self._inp_number.setFixedWidth(160)
        self._inp_number.returnPressed.connect(self._search)

        self._cmb_set = QComboBox()
        self._cmb_set.setFixedWidth(270)
        self._cmb_set.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )

        self._btn_search = QPushButton(
            theme.icon("magnifying-glass", "#ffffff"), "  Buscar"
        )
        self._btn_search.setObjectName("primaryBtn")
        self._btn_search.clicked.connect(self._search)

        self._btn_clear = QPushButton("Limpiar")
        self._btn_clear.clicked.connect(self._clear)

        filter_row.addWidget(self._inp_name, 2)
        filter_row.addWidget(self._inp_number)
        filter_row.addWidget(QLabel("Set:"))
        filter_row.addWidget(self._cmb_set)
        filter_row.addWidget(self._btn_search)
        filter_row.addWidget(self._btn_clear)
        root.addWidget(filter_box)

        # ── Splitter: table | detail
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Left: results table
        table_panel  = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(6)

        self._result_count = QLabel("—")
        self._result_count.setObjectName("mutedLabel")

        self._btn_export_search = QPushButton(
            theme.icon("file-csv", theme.MUTED), "  Exportar CSV"
        )
        self._btn_export_search.setEnabled(False)
        self._btn_export_search.clicked.connect(self._export_results)

        count_row = QHBoxLayout()
        count_row.addWidget(self._result_count)
        count_row.addStretch()
        count_row.addWidget(self._btn_export_search)
        table_layout.addLayout(count_row)

        self._model = QStandardItemModel(0, 6)
        self._model.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Código", "Set", "Rareza", "Tipo"]
        )
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnWidth(0, 65)
        self._table.setColumnWidth(1, 200)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(3, 175)
        self._table.setColumnWidth(4, 115)
        self._table.selectionModel().selectionChanged.connect(self._on_row_selected)

        table_layout.addWidget(self._table)
        splitter.addWidget(table_panel)

        # Right: detail panel
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail_scroll.setMinimumWidth(320)
        self._detail = _DetailPanel()
        detail_scroll.setWidget(self._detail)
        splitter.addWidget(detail_scroll)

        splitter.setSizes([650, 370])
        root.addWidget(splitter, 1)

    def _load_groups(self):
        self._all_groups = db.get_all_groups(self.conn)
        self._cmb_set.clear()
        self._cmb_set.addItem("Todos los sets", None)
        for g in self._all_groups:
            label = f"{g['categoryName']} – {g['name']}"
            self._cmb_set.addItem(label, g["groupId"])

    def _search(self):
        name   = self._inp_name.text().strip()
        number = self._inp_number.text().strip()
        gid    = self._cmb_set.currentData()

        if not name and not number and gid is None:
            return

        results = db.search_products(self.conn, name=name, number=number, group_id=gid)
        self._last_results = results
        self._populate_table(results)

    def _clear(self):
        self._inp_name.clear()
        self._inp_number.clear()
        self._cmb_set.setCurrentIndex(0)
        self._model.removeRows(0, self._model.rowCount())
        self._result_count.setText("—")
        self._detail.clear()
        self._last_results = []
        self._btn_export_search.setEnabled(False)

    def _populate_table(self, rows: list[dict]):
        self._model.removeRows(0, self._model.rowCount())
        for r in rows:
            items = [
                QStandardItem(str(r.get("productId", ""))),
                QStandardItem(r.get("name", "")),
                QStandardItem(r.get("extNumber") or "—"),
                QStandardItem(r.get("groupName", "")),
                QStandardItem(r.get("extRarity") or "—"),
                QStandardItem(r.get("extCardType") or "—"),
            ]
            items[0].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items[2].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items[0].setData(r, Qt.ItemDataRole.UserRole)
            self._model.appendRow(items)

        n = len(rows)
        self._result_count.setText(
            f"{n:,} resultado{'s' if n != 1 else ''}"
            + (" — mostrando primeros 300" if n == 300 else "")
        )
        self._btn_export_search.setEnabled(n > 0)

    def _on_row_selected(self):
        indexes = self._table.selectedIndexes()
        if not indexes:
            return
        row_data = self._model.item(indexes[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        if not row_data:
            return
        prices = db.get_prices_for_product(self.conn, row_data["productId"])
        try:
            self._rate = exchange.get_rate(self.conn)
        except Exception:
            pass
        self._detail.show_product(row_data, prices, self._rate)

    def refresh_groups(self):
        self._load_groups()

    def _export_results(self):
        if not self._last_results:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "Exportar resultados como CSV",
            str(Path.home() / "resultados_busqueda.csv"),
            "CSV (*.csv)",
        )
        if not dest:
            return
        try:
            rate = exchange.get_rate(self.conn)
            rows = export.export_search_to_csv(
                self._last_results, self.conn, Path(dest), rate
            )
            self._result_count.setText(
                f"{len(self._last_results):,} resultados  —  ✓ CSV exportado ({rows} filas)"
            )
        except Exception as e:
            self._result_count.setText(f"Error al exportar: {e}")


# ── Detail panel ───────────────────────────────────────────────────────────

class _DetailPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._img_loader = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(12)

        # Image placeholder
        self._img_label = QLabel("Sin imagen")
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setFixedHeight(170)
        self._img_label.setStyleSheet(
            f"border: 1px solid {theme.BORDER}; border-radius: 8px; "
            f"background: {theme.SURFACE}; color: {theme.MUTED}; font-size: 9pt;"
        )
        layout.addWidget(self._img_label)

        # Name & meta
        self._lbl_name = QLabel()
        self._lbl_name.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self._lbl_name.setWordWrap(True)

        self._lbl_meta = QLabel()
        self._lbl_meta.setObjectName("mutedLabel")
        self._lbl_meta.setWordWrap(True)

        layout.addWidget(self._lbl_name)
        layout.addWidget(self._lbl_meta)

        # Prices container
        self._prices_box    = QGroupBox("Precios de mercado")
        self._prices_layout = QVBoxLayout(self._prices_box)
        self._prices_layout.setSpacing(4)
        layout.addWidget(self._prices_box)

        layout.addStretch()

    def clear(self):
        self._lbl_name.clear()
        self._lbl_meta.clear()
        self._img_label.clear()
        self._img_label.setText("Sin imagen")
        while self._prices_layout.count():
            child = self._prices_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def show_product(self, product: dict, prices: list[dict], rate: float):
        self.clear()
        self._lbl_name.setText(product.get("name", ""))

        parts = [x for x in [
            product.get("extNumber"), product.get("extRarity"), product.get("groupName")
        ] if x]
        self._lbl_meta.setText("  ·  ".join(parts))

        img_url = product.get("imageUrl", "")
        if img_url:
            self._img_loader = _ImageLoader(img_url)
            self._img_loader.loaded.connect(self._set_image)
            self._img_loader.start()

        if prices:
            for p in prices:
                self._prices_layout.addWidget(_PriceRow(p, rate))
        else:
            lbl = QLabel("Sin datos de precio")
            lbl.setObjectName("mutedLabel")
            self._prices_layout.addWidget(lbl)

    def _set_image(self, data: bytes):
        if not data:
            return
        pix = QPixmap()
        pix.loadFromData(data)
        if not pix.isNull():
            scaled = pix.scaledToHeight(160, Qt.TransformationMode.SmoothTransformation)
            self._img_label.setPixmap(scaled)


class _PriceRow(QFrame):
    """One price variant row: subTypeName header + Low / Mid / Market prices."""

    def __init__(self, price: dict, rate: float):
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(4)

        sub = price.get("subTypeName", "Normal")
        lbl_sub = QLabel(sub)
        lbl_sub.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        lbl_sub.setStyleSheet(f"color: {theme.ACCENT};")
        layout.addWidget(lbl_sub, 0, 0, 1, 6)

        for col, (header, field) in enumerate(
            [("Low", "lowPrice"), ("Mid", "midPrice"), ("Market", "marketPrice")]
        ):
            val = price.get(field)
            usd = f"${float(val):.2f}" if val else "—"
            clp = exchange.to_clp(val, rate)

            h_lbl = QLabel(header)
            h_lbl.setObjectName("mutedLabel")
            h_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            u_lbl = QLabel(usd)
            u_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            u_lbl.setFont(QFont("Consolas", 9))

            c_lbl = QLabel(clp)
            c_lbl.setObjectName("mutedLabel")
            c_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_lbl.setFont(QFont("Segoe UI", 8))

            layout.addWidget(h_lbl, 1, col * 2)
            layout.addWidget(u_lbl, 2, col * 2)
            layout.addWidget(c_lbl, 3, col * 2)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep, 4, 0, 1, 6)
