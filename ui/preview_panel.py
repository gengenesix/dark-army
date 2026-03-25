import numpy as np
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QSizePolicy, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from ui.widgets import Card, SectionLabel, LiveBadge
from utils.frame_utils import frame_to_qpixmap

_TOGGLE_BASE = (
    "QPushButton { padding: 3px 10px; border: 1px solid #252632; "
    "border-radius: 6px; font-size: 11px; font-weight: 600; background: #1A1B24; color: #8B8CA8; } "
    "QPushButton:hover { color: #F0F0FA; border-color: #5C5FFF; } "
    "QPushButton:checked { background: #5C5FFF; color: #FFFFFF; border-color: #5C5FFF; }"
)


class PreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "split"  # "split" | "output" | "original"
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        card = Card()
        card.layout().setSpacing(6)
        outer.addWidget(card)

        # Mode toggle row
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(4)

        self._btn_split = QPushButton("Split View")
        self._btn_output = QPushButton("Output Only")
        self._btn_original = QPushButton("Original Only")

        for btn in (self._btn_split, self._btn_output, self._btn_original):
            btn.setCheckable(True)
            btn.setStyleSheet(_TOGGLE_BASE)
            toggle_row.addWidget(btn)

        toggle_row.addStretch()
        self._btn_split.setChecked(True)

        self._btn_split.clicked.connect(lambda: self._set_mode("split"))
        self._btn_output.clicked.connect(lambda: self._set_mode("output"))
        self._btn_original.clicked.connect(lambda: self._set_mode("original"))

        card.layout().addLayout(toggle_row)

        row = QHBoxLayout()
        row.setSpacing(12)
        card.layout().addLayout(row)

        self._orig_label = self._make_preview_label()
        self._swap_label = self._make_preview_label()

        orig_col = QVBoxLayout()
        orig_col.setSpacing(4)
        orig_col.addWidget(self._orig_label)
        cap1 = QLabel("CAMERA INPUT")
        cap1.setObjectName("sectionLabel")
        cap1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orig_col.addWidget(cap1)

        swap_col = QVBoxLayout()
        swap_col.setSpacing(4)
        swap_col.addWidget(self._swap_label)
        cap2_row = QHBoxLayout()
        cap2 = QLabel("ECHELON OUTPUT")
        cap2.setObjectName("sectionLabel")
        cap2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._live_badge = LiveBadge()
        cap2_row.addWidget(cap2)
        cap2_row.addWidget(self._live_badge)
        cap2_row.addStretch()
        swap_col.addLayout(cap2_row)

        self._orig_col_widget = QWidget()
        self._orig_col_widget.setLayout(orig_col)
        self._swap_col_widget = QWidget()
        self._swap_col_widget.setLayout(swap_col)

        row.addWidget(self._orig_col_widget)
        row.addWidget(self._swap_col_widget)

        self._set_placeholder()

    def _set_mode(self, mode: str):
        self._mode = mode
        self._btn_split.setChecked(mode == "split")
        self._btn_output.setChecked(mode == "output")
        self._btn_original.setChecked(mode == "original")
        self._orig_col_widget.setVisible(mode in ("split", "original"))
        self._swap_col_widget.setVisible(mode in ("split", "output"))

    def cycle_mode(self):
        modes = ["split", "output", "original"]
        idx = modes.index(self._mode)
        self._set_mode(modes[(idx + 1) % len(modes)])

    def _make_preview_label(self) -> QLabel:
        lbl = QLabel()
        lbl.setMinimumSize(400, 225)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("background-color: #111218; border-radius: 8px;")
        return lbl

    def _set_placeholder(self):
        for lbl in (self._orig_label, self._swap_label):
            lbl.setPixmap(QPixmap())
            lbl.setText("Start Dark-Army to see preview")
            lbl.setStyleSheet(
                "background-color: #111218; border-radius: 8px; "
                "color: #50516A; font-size: 13px;"
            )

    def update_frames(self, original: np.ndarray, swapped: np.ndarray):
        pairs = []
        if self._mode in ("split", "original"):
            pairs.append((original, self._orig_label))
        if self._mode in ("split", "output"):
            pairs.append((swapped, self._swap_label))
        for frame, lbl in pairs:
            if frame is None:
                continue
            pixmap = frame_to_qpixmap(frame)
            scaled = pixmap.scaled(
                lbl.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            lbl.setPixmap(scaled)
            lbl.setText("")

    def set_active(self, active: bool):
        self._live_badge.set_visible(active)
        if not active:
            self._set_placeholder()
            for lbl in (self._orig_label, self._swap_label):
                lbl.setStyleSheet(
                    "background-color: #111218; border-radius: 8px; "
                    "color: #50516A; font-size: 13px;"
                )
