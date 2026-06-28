"""
FuzzyConfirmDialog – card match confirmation with manual search.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QRadioButton, QPushButton, QButtonGroup, QGroupBox,
    QFrame, QLineEdit, QScrollArea, QWidget, QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from app.ui import theme
from app.db import database as db
from app.core.fuzzy import normalize_for_sql


class FuzzyConfirmDialog(QDialog):
    """
    Shows fuzzy match suggestions for one batch item.
    Includes a live search box so the user can find any card manually.
    Accepts `current` and `total` to display review progress.
    """

    def __init__(self, batch_item, conn,
                 current: int = 1, total: int = 1, parent=None):
        super().__init__(parent)
        self.batch_item        = batch_item
        self.conn              = conn
        self.current           = current
        self.total             = total
        self._selected_product = None
        self._selected_score   = 0
        self._btn_group        = QButtonGroup(self)
        self._options: list[tuple[dict, int]] = []   # (product, score)
        self._search_timer     = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._run_search)

        self.setWindowTitle(f"Confirmar coincidencia  [{current} / {total}]")
        self.setMinimumWidth(640)
        self.setMinimumHeight(480)
        self.setModal(True)
        self._build_ui()

    # ── Build UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # ── Progress bar (review progress)
        if self.total > 1:
            prog_row = QHBoxLayout()
            prog_lbl = QLabel(f"Revisando  {self.current} de {self.total}")
            prog_lbl.setObjectName("mutedLabel")
            prog_bar = QProgressBar()
            prog_bar.setRange(0, self.total)
            prog_bar.setValue(self.current)
            prog_bar.setTextVisible(False)
            prog_bar.setFixedHeight(5)
            prog_row.addWidget(prog_lbl)
            prog_row.addWidget(prog_bar, 1)
            layout.addLayout(prog_row)

        # ── Query label
        query_lbl = QLabel(f'Buscando:  "{self.batch_item.input_text}"')
        query_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        layout.addWidget(query_lbl)

        # ── Manual search box
        search_box    = QGroupBox("Buscar carta manualmente")
        search_layout = QVBoxLayout(search_box)
        search_layout.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            "🔍  Escribe un nombre, código o set… (mínimo 2 caracteres)"
        )
        self._search_input.textChanged.connect(
            lambda: self._search_timer.start(300)   # 300 ms debounce
        )
        search_layout.addWidget(self._search_input)

        self._search_hint = QLabel("Las sugerencias automáticas se muestran abajo.")
        self._search_hint.setObjectName("mutedLabel")
        search_layout.addWidget(self._search_hint)
        layout.addWidget(search_box)

        # ── Suggestions scroll area
        opts_box    = QGroupBox("Opciones")
        opts_layout = QVBoxLayout(opts_box)
        opts_layout.setContentsMargins(0, 4, 0, 4)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setMinimumHeight(200)

        self._opts_container = QWidget()
        self._opts_inner     = QVBoxLayout(self._opts_container)
        self._opts_inner.setSpacing(8)
        self._opts_inner.setContentsMargins(8, 8, 8, 8)
        self._scroll.setWidget(self._opts_container)
        opts_layout.addWidget(self._scroll)
        layout.addWidget(opts_box, 1)

        # ── Footer
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)

        self._btn_ok = QPushButton("Confirmar")
        self._btn_ok.setObjectName("primaryBtn")
        self._btn_ok.setDefault(True)
        self._btn_ok.clicked.connect(self._confirm)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self._btn_ok)
        layout.addLayout(btn_row)

        # Populate with initial suggestions
        self._populate_options(self.batch_item.suggestions, mode="suggestions")

    # ── Options population ─────────────────────────────────────────────────

    def _populate_options(self, items: list[dict], mode: str = "suggestions"):
        """
        Rebuild the radio button list.
        `mode`='suggestions' → items are {product, score} dicts.
        `mode`='search'      → items are product dicts from DB search.
        """
        # Clear previous widgets and button group
        for btn in self._btn_group.buttons():
            self._btn_group.removeButton(btn)
        while self._opts_inner.count():
            child = self._opts_inner.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                # clear nested layout
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        self._options = []

        if not items:
            lbl = QLabel("Sin resultados.")
            lbl.setObjectName("mutedLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._opts_inner.addWidget(lbl)
            self._opts_inner.addStretch()
            return

        for i, item in enumerate(items):
            if mode == "suggestions":
                prod  = item["product"]
                score = item["score"]
            else:
                prod  = item
                score = 0   # manual search: no score

            self._options.append((prod, score))

            rb = QRadioButton()
            rb.setChecked(i == 0)
            self._btn_group.addButton(rb, i)

            row = QHBoxLayout()
            row.setSpacing(10)
            row.addWidget(rb)

            name_lbl = QLabel(prod.get("name", "—"))
            name_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))

            code_lbl = QLabel(prod.get("extNumber") or "")
            code_lbl.setObjectName("mutedLabel")
            code_lbl.setFixedWidth(80)
            code_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            set_lbl = QLabel(prod.get("groupName") or prod.get("groupAbbr") or "")
            set_lbl.setObjectName("mutedLabel")
            set_lbl.setFixedWidth(190)

            if mode == "suggestions" and score > 0:
                score_lbl = QLabel(str(score))
                score_lbl.setFixedWidth(44)
                score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                score_lbl.setStyleSheet(theme.badge_style(score))
            else:
                score_lbl = QLabel("")
                score_lbl.setFixedWidth(44)

            row_widget = QWidget()
            row_widget.setLayout(row)
            row.addWidget(name_lbl, 1)
            row.addWidget(code_lbl)
            row.addWidget(set_lbl)
            row.addWidget(score_lbl)
            self._opts_inner.addWidget(row_widget)

        # ── "None" option
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        self._opts_inner.addWidget(sep)

        skip_rb = QRadioButton("Ninguna de las anteriores  (omitir este ítem)")
        skip_rb.setObjectName("mutedLabel")
        self._btn_group.addButton(skip_rb, len(self._options))
        self._opts_inner.addWidget(skip_rb)
        self._opts_inner.addStretch()

    # ── Manual search ──────────────────────────────────────────────────────

    def _run_search(self):
        raw   = self._search_input.text().strip()
        if len(raw) < 2:
            # Restore original suggestions
            self._search_hint.setText(
                "Las sugerencias automáticas se muestran abajo."
            )
            self._populate_options(self.batch_item.suggestions, mode="suggestions")
            return

        # Normalize: strip apostrophes, trailing numbers, punctuation
        query   = normalize_for_sql(raw)
        results = db.search_products(self.conn, name=query, limit=15)

        # If normalized query returns nothing, try the raw string as fallback
        if not results and query != raw.lower():
            results = db.search_products(self.conn, name=raw, limit=15)

        count = len(results)
        self._search_hint.setText(
            f"{count} resultado{'s' if count != 1 else ''} encontrado{'s' if count != 1 else ''}"
            + ("  (máx. 15)" if count == 15 else "")
        )
        self._populate_options(results, mode="search")

    # ── Confirm ────────────────────────────────────────────────────────────

    def _confirm(self):
        cid = self._btn_group.checkedId()
        if 0 <= cid < len(self._options):
            self._selected_product = self._options[cid][0]
            self._selected_score   = self._options[cid][1] or 99
        else:
            self._selected_product = None
            self._selected_score   = 0
        self.accept()

    def selected_product(self) -> dict | None:
        return self._selected_product

    def selected_score(self) -> int:
        return self._selected_score
