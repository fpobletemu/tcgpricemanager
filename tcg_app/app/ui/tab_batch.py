"""
Tab: Búsqueda por lotes — fuzzy matching, confirmation flow, image download.
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QGroupBox,
    QHeaderView, QFileDialog, QProgressBar, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

import requests

from app.ui import theme
from app.ui.dialogs import FuzzyConfirmDialog
from app.db import database as db
from app.core import fuzzy, images, export
from app.api import exchange
import re as _re


def _is_separator(text: str) -> bool:
    """True for divider lines like '---   ---   ---'."""
    return bool(_re.match(r'^[-=_*#|\s]{4,}$', text.strip()))


# Keys that signal a metadata column (case-insensitive)
_META_KEYS = {"idioma", "rareza", "language", "rarity", "lang"}


def _merge_multiline_input(text: str) -> str:
    """
    When tabs are lost during paste, a single card entry like:
        Card Name 123/456  \\t  Idioma  \\t  EN  \\t  Rareza  \\t  Double Rare
    arrives as 5 separate lines.  This function detects that pattern and
    re-joins the groups back into one tab-separated line per card.

    Detection: if ≥ 15 % of non-empty lines are known metadata keys,
    we are in multi-line mode and group every 5 consecutive non-empty lines.
    """
    lines = [l.rstrip() for l in text.splitlines()]
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return text

    meta_key_count = sum(1 for l in non_empty if l.strip().lower() in _META_KEYS)
    if meta_key_count / len(non_empty) < 0.15:
        return text   # Already tab-separated (or plain list) – leave as-is

    # Multi-line mode: collect runs of non-empty lines separated by blanks,
    # OR group strictly by 5 consecutive non-blank lines per entry.
    result: list[str] = []
    group: list[str] = []

    def flush():
        if group:
            result.append("\t".join(group))
            group.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # A blank line always ends the current group
            flush()
            continue
        group.append(stripped)
        # A complete entry has 5 parts: name, key1, val1, key2, val2
        if len(group) == 5:
            flush()

    flush()
    return "\n".join(result)


# ── Worker threads ─────────────────────────────────────────────────────────

class _FuzzyWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, queries: list[str], candidates: list[dict]):
        super().__init__()
        self.queries    = queries
        self.candidates = candidates

    def run(self):
        try:
            results = fuzzy.batch_search(
                self.queries, self.candidates,
                progress_cb=lambda c, t, q: self.progress.emit(c, t, q),
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class _DownloadWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int, str)
    error    = pyqtSignal(str)

    def __init__(self, items: list[dict], dest_dir: Path):
        super().__init__()
        self.items    = items
        self.dest_dir = dest_dir

    def run(self):
        try:
            saved = images.download_batch(
                self.items, self.dest_dir,
                progress_cb=lambda c, t: self.progress.emit(c, t),
            )
            self.finished.emit(len(saved), str(self.dest_dir))
        except Exception as e:
            self.error.emit(str(e))


class _ThumbLoader(QThread):
    """Downloads one card thumbnail and emits (product_id, raw_bytes)."""
    loaded = pyqtSignal(int, bytes)

    def __init__(self, product_id: int, url: str):
        super().__init__()
        self.product_id = product_id
        self.url        = url

    def run(self):
        try:
            r = requests.get(
                self.url, timeout=8,
                headers={"User-Agent": "TCGPriceManager/1.0.0"},
            )
            r.raise_for_status()
            self.loaded.emit(self.product_id, r.content)
        except Exception:
            self.loaded.emit(self.product_id, b"")


# ── Column indices
COL_IMG      = 0
COL_INPUT    = 1
COL_META     = 2   # Idioma · Rareza (from input)
COL_MATCH    = 3
COL_CODE     = 4
COL_SET      = 5
COL_SCORE    = 6
COL_STATO    = 7
COL_BTN      = 8
COL_DEL      = 9

_THUMB_W = 44   # thumbnail cell width (px)
_THUMB_H = 48   # thumbnail image height (px)
_ROW_H   = 56   # row height (px)


class BatchTab(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn         = conn
        self._batch_items: list[fuzzy.BatchItem] = []
        self._worker      = None
        self._dl_worker   = None
        self._candidates: list[dict] = []
        self._pending_meta: list[dict] = []          # metadata per query line
        self._thumb_cache: dict[int, QPixmap] = {}
        self._thumb_loaders: list[_ThumbLoader] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Búsqueda por Lotes")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        # ── Input
        input_box    = QGroupBox("Lista de cartas  (una por línea)")
        input_layout = QVBoxLayout(input_box)

        self._txt_input = QTextEdit()
        self._txt_input.setPlaceholderText(
            "Lugia VSTAR\nCharizard ex\nPikachu VMAX\n..."
        )
        self._txt_input.setFont(QFont("Consolas", 10))
        self._txt_input.setMaximumHeight(140)
        input_layout.addWidget(self._txt_input)

        inp_btns = QHBoxLayout()
        self._btn_process = QPushButton(
            theme.icon("bolt", "#ffffff"), "  Procesar lista"
        )
        self._btn_process.setObjectName("primaryBtn")
        self._btn_process.clicked.connect(self._process)
        inp_btns.addWidget(self._btn_process)
        inp_btns.addStretch()
        input_layout.addLayout(inp_btns)
        root.addWidget(input_box)

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

        # ── Results table
        self._table = QTableWidget(0, 10)
        self._table.setHorizontalHeaderLabels(
            ["", "Entrada", "Info", "Match encontrado", "Código", "Set", "Score", "Estado", "", ""]
        )
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(COL_IMG,   QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_INPUT, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(COL_META,  QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(COL_MATCH, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(COL_CODE,  QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(COL_SET,   QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(COL_SCORE, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_STATO, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_BTN,   QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_DEL,   QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(COL_IMG,   _THUMB_W + 8)
        self._table.setColumnWidth(COL_INPUT, 150)
        self._table.setColumnWidth(COL_META,  120)
        self._table.setColumnWidth(COL_CODE,  90)
        self._table.setColumnWidth(COL_SET,   140)
        self._table.setColumnWidth(COL_SCORE, 70)
        self._table.setColumnWidth(COL_STATO, 90)
        self._table.setColumnWidth(COL_BTN,   82)
        self._table.setColumnWidth(COL_DEL,   40)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self._table, 1)

        # ── Footer
        footer = QVBoxLayout()

        # Review progress bar (hidden until review starts)
        review_prog_row = QHBoxLayout()
        self._lbl_review_prog = QLabel()
        self._lbl_review_prog.setObjectName("mutedLabel")
        self._bar_review = QProgressBar()
        self._bar_review.setTextVisible(False)
        self._bar_review.setFixedHeight(5)
        review_prog_row.addWidget(self._lbl_review_prog)
        review_prog_row.addWidget(self._bar_review, 1)
        self._review_prog_widget = QWidget()
        self._review_prog_widget.setLayout(review_prog_row)
        self._review_prog_widget.setVisible(False)
        footer.addWidget(self._review_prog_widget)

        # Action row
        action_row = QHBoxLayout()
        self._lbl_summary = QLabel("Sin resultados")
        self._lbl_summary.setObjectName("mutedLabel")

        self._btn_review = QPushButton(
            theme.icon("circle-exclamation", theme.WARNING), "  Revisar pendientes"
        )
        self._btn_review.setVisible(False)
        self._btn_review.clicked.connect(self._review_pending)

        self._btn_download = QPushButton(
            theme.icon("images", "#ffffff"), "  Descargar imágenes"
        )
        self._btn_download.setObjectName("primaryBtn")
        self._btn_download.setEnabled(False)
        self._btn_download.clicked.connect(self._download_images)

        self._btn_export = QPushButton(
            theme.icon("file-csv", "#ffffff"), "  Exportar CSV"
        )
        self._btn_export.setObjectName("primaryBtn")
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._export_csv)

        action_row.addWidget(self._lbl_summary)
        action_row.addStretch()
        action_row.addWidget(self._btn_review)
        action_row.addWidget(self._btn_download)
        action_row.addWidget(self._btn_export)
        footer.addLayout(action_row)

        root.addLayout(footer)

    # ── Processing ─────────────────────────────────────────────────────────

    def _process(self):
        text = self._txt_input.toPlainText().strip()
        if not text:
            return

        # Normalize: re-join lines if tabs were lost during paste
        text = _merge_multiline_input(text)
        parsed = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            card_query, meta = fuzzy.parse_batch_line(stripped)
            card_query = card_query.strip()
            if card_query and not _is_separator(card_query):
                parsed.append((card_query, meta))

        if not parsed:
            return

        queries               = [q for q, _ in parsed]
        self._pending_meta    = [m for _, m in parsed]

        self._btn_process.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setMaximum(len(queries))
        self._progress.setValue(0)
        self._prog_label.setVisible(True)

        if not self._candidates:
            self._candidates = db.load_all_for_fuzzy(self.conn)

        self._worker = _FuzzyWorker(queries, self._candidates)
        self._worker.progress.connect(self._on_fuzzy_progress)
        self._worker.finished.connect(self._on_fuzzy_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_fuzzy_progress(self, cur: int, total: int, query: str):
        self._progress.setValue(cur)
        self._prog_label.setText(f"[{cur}/{total}]  Buscando: {query}")

    def _on_fuzzy_done(self, batch_items):
        # Attach metadata parsed from input lines
        for i, item in enumerate(batch_items):
            if i < len(self._pending_meta):
                item.metadata = self._pending_meta[i]
        self._batch_items = batch_items
        self._progress.setVisible(False)
        self._prog_label.setVisible(False)
        self._btn_process.setEnabled(True)
        self._populate_table()
        self._update_footer()

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._prog_label.setVisible(False)
        self._btn_process.setEnabled(True)
        self._lbl_summary.setText(f"Error: {msg}")

    # ── Table ──────────────────────────────────────────────────────────────

    def _populate_table(self):
        self._table.setRowCount(0)
        self._thumb_loaders.clear()   # cancel pending loads (GC)
        for idx, item in enumerate(self._batch_items):
            self._table.insertRow(idx)
            self._fill_row(idx, item)
            self._table.setRowHeight(idx, _ROW_H)

    def _fill_row(self, idx: int, item: fuzzy.BatchItem):
        prod = item.matched_product or {}

        # ── COL_IMG: card thumbnail
        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(_THUMB_W, _THUMB_H)
        thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_lbl.setStyleSheet(
            f"background: {theme.SURFACE}; border-radius: 3px;"
            f" border: 1px solid {theme.BORDER}; color: {theme.MUTED}; font-size: 8pt;"
        )
        thumb_lbl.setText("…")

        img_url   = prod.get("imageUrl", "")
        prod_id   = prod.get("productId")
        if prod_id and img_url:
            if prod_id in self._thumb_cache:
                self._set_thumb(thumb_lbl, self._thumb_cache[prod_id])
            else:
                loader = _ThumbLoader(prod_id, img_url)
                loader.loaded.connect(
                    lambda pid, data, lbl=thumb_lbl: self._on_thumb_loaded(pid, data, lbl)
                )
                self._thumb_loaders.append(loader)
                loader.start()

        # Center the thumbnail label inside the cell using a wrapper widget
        wrapper = QWidget()
        wrap_layout = QHBoxLayout(wrapper)
        wrap_layout.setContentsMargins(4, 4, 4, 4)
        wrap_layout.addWidget(thumb_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        self._table.setCellWidget(idx, COL_IMG, wrapper)

        # ── Text columns
        self._table.setItem(idx, COL_INPUT, QTableWidgetItem(item.input_text))

        # ── COL_META: compact metadata from input (Idioma · Rareza)
        meta     = item.metadata
        parts    = [v for k, v in meta.items() if v]
        meta_str = "  ·  ".join(parts) if parts else ""
        meta_lbl = QLabel(meta_str or "—")
        meta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta_lbl.setObjectName("mutedLabel")
        meta_lbl.setFont(QFont("Segoe UI", 9))
        if meta_str:
            meta_lbl.setToolTip("  |  ".join(f"{k}: {v}" for k, v in meta.items()))
        self._table.setCellWidget(idx, COL_META, meta_lbl)

        self._table.setItem(idx, COL_MATCH, QTableWidgetItem(prod.get("name", "—")))
        self._table.setItem(idx, COL_CODE,  QTableWidgetItem(prod.get("extNumber") or "—"))
        self._table.setItem(idx, COL_SET,   QTableWidgetItem(prod.get("groupName") or "—"))

        for col in (COL_INPUT, COL_CODE, COL_SET):
            if self._table.item(idx, col):
                self._table.item(idx, col).setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )

        score_lbl = QLabel(str(item.score) if item.status != "not_found" else "—")
        score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_lbl.setStyleSheet(theme.badge_style(item.score))
        self._table.setCellWidget(idx, COL_SCORE, score_lbl)

        status_lbl = QLabel(self._status_text(item.status))
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lbl.setStyleSheet(self._status_style(item.status))
        self._table.setCellWidget(idx, COL_STATO, status_lbl)

        btn = QPushButton("Cambiar")
        btn.setFixedSize(74, 28)
        btn.setStyleSheet("font-size: 9pt; min-width: 0;")
        btn.clicked.connect(self._make_change_handler(idx))
        self._table.setCellWidget(idx, COL_BTN, btn)

        # Delete button — always present
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setToolTip("Eliminar este ítem de la lista")
        del_btn.setStyleSheet(
            f"color: {theme.DANGER}; font-weight: 700; font-size: 11pt; "
            "min-width: 0; border: none; background: transparent;"
            f"border-radius: 4px;"
        )
        del_btn.clicked.connect(self._make_delete_handler(idx))
        self._table.setCellWidget(idx, COL_DEL, del_btn)

    def _make_change_handler(self, idx: int):
        def handler():
            self._open_confirm_dialog(idx)
        return handler

    def _make_delete_handler(self, idx: int):
        def handler():
            self._delete_item(idx)
        return handler

    def _delete_item(self, idx: int):
        if 0 <= idx < len(self._batch_items):
            self._batch_items.pop(idx)
            self._populate_table()
            self._update_footer()

    # ── Thumbnails ────────────────────────────────────────────────────

    def _on_thumb_loaded(self, product_id: int, data: bytes, label: QLabel):
        if not data:
            return
        pix = QPixmap()
        pix.loadFromData(data)
        if not pix.isNull():
            self._thumb_cache[product_id] = pix
            self._set_thumb(label, pix)

    @staticmethod
    def _set_thumb(label: QLabel, pix: QPixmap):
        scaled = pix.scaled(
            _THUMB_W, _THUMB_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(scaled)
        label.setStyleSheet("background: transparent; border: none;")

    @staticmethod
    def _status_text(status: str) -> str:
        return {"confirmed": "✓  OK", "review": "⚠  Revisar", "not_found": "✗  No hallado"}.get(
            status, status
        )

    @staticmethod
    def _status_style(status: str) -> str:
        if status == "confirmed":
            return f"color: {theme.SUCCESS}; font-weight: 700;"
        if status == "review":
            return f"color: {theme.WARNING}; font-weight: 700;"
        return f"color: {theme.DANGER}; font-weight: 700;"

    # ── Review ─────────────────────────────────────────────────────────────

    def _review_pending(self):
        """Open dialogs for all pending items one by one with progress tracking."""
        pending = [
            (idx, item) for idx, item in enumerate(self._batch_items)
            if item.status in ("review", "not_found")
        ]
        total = len(pending)
        if not total:
            return

        self._bar_review.setRange(0, total)
        self._bar_review.setValue(0)
        self._review_prog_widget.setVisible(True)

        for current_num, (idx, _) in enumerate(pending, 1):
            self._bar_review.setValue(current_num - 1)
            self._lbl_review_prog.setText(
                f"Revisando  {current_num} de {total}  —  "
                f"{current_num - 1} completado{'s' if current_num - 1 != 1 else ''}"
            )
            self._open_confirm_dialog(idx, current=current_num, total=total)

        self._bar_review.setValue(total)
        self._lbl_review_prog.setText(
            f"Revisión completa  —  {total} ítem{'s' if total != 1 else ''} procesado{'s' if total != 1 else ''}"
        )
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._review_prog_widget.setVisible(False))
        self._update_footer()

    def _open_confirm_dialog(self, idx: int, current: int = 1, total: int = 1):
        item = self._batch_items[idx]
        dlg  = FuzzyConfirmDialog(
            item, self.conn, current=current, total=total, parent=self
        )
        if dlg.exec():
            selected = dlg.selected_product()
            if selected is None:
                self._batch_items[idx].status          = "not_found"
                self._batch_items[idx].matched_product = None
            else:
                self._batch_items[idx].status          = "confirmed"
                self._batch_items[idx].matched_product = selected
                self._batch_items[idx].score           = dlg.selected_score()
            self._fill_row(idx, self._batch_items[idx])
            self._update_footer()

    def _update_footer(self):
        confirmed = sum(1 for i in self._batch_items if i.status == "confirmed")
        review    = sum(1 for i in self._batch_items if i.status == "review")
        not_found = sum(1 for i in self._batch_items if i.status == "not_found")
        total     = len(self._batch_items)
        parts = [f"{confirmed}/{total} confirmados"]
        if review:
            parts.append(f"{review} pendiente{'s' if review != 1 else ''} ⚠")
        if not_found:
            parts.append(f"{not_found} omitido{'s' if not_found != 1 else ''}")
        self._lbl_summary.setText("  ·  ".join(parts))
        self._btn_review.setVisible(review > 0)
        btn_text = f"  Revisar pendientes ({review})" if review else "  Revisar pendientes"
        self._btn_review.setText(btn_text)
        self._btn_download.setEnabled(confirmed > 0 and review == 0)
        self._btn_export.setEnabled(confirmed > 0)

    # ── Download ───────────────────────────────────────────────────────────

    def _download_images(self):
        dest = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de destino", str(Path.home())
        )
        if not dest:
            return

        items_to_dl = [
            {
                "productId": item.matched_product["productId"],
                "imageUrl" : item.matched_product.get("imageUrl", ""),
                "cleanName": item.matched_product.get("cleanName", ""),
            }
            for item in self._batch_items
            if item.status == "confirmed" and item.matched_product
        ]

        self._btn_download.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setMaximum(len(items_to_dl))
        self._prog_label.setVisible(True)

        self._dl_worker = _DownloadWorker(items_to_dl, Path(dest))
        self._dl_worker.progress.connect(self._on_dl_progress)
        self._dl_worker.finished.connect(self._on_dl_done)
        self._dl_worker.error.connect(self._on_error)
        self._dl_worker.start()

    def _on_dl_progress(self, c: int, t: int):
        self._progress.setValue(c)
        self._prog_label.setText(f"Descargando imagen {c}/{t}…")

    def _on_dl_done(self, count: int, path: str):
        self._progress.setVisible(False)
        self._prog_label.setVisible(False)
        self._btn_download.setEnabled(True)
        self._lbl_summary.setText(f"✓  {count} imágenes guardadas en:  {path}")

    # ── Export CSV ─────────────────────────────────────────────────────────

    def _export_csv(self):
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar lista como CSV",
            str(Path.home() / "lista_cartas.csv"),
            "CSV (*.csv)",
        )
        if not dest:
            return
        try:
            rate  = exchange.get_rate(self.conn)
            rows  = export.export_batch_to_csv(
                self._batch_items, self.conn, Path(dest), rate
            )
            self._lbl_summary.setText(
                f"✓  CSV exportado — {rows} filas → {Path(dest).name}"
            )
        except Exception as e:
            self._lbl_summary.setText(f"Error al exportar: {e}")

