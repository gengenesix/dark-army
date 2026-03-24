from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QComboBox)
from PyQt6.QtCore import pyqtSignal
from ui.widgets import SectionCard


class ControlsPanel(QWidget):
    mode_changed = pyqtSignal(str)
    camera_changed = pyqtSignal(int)
    target_face_changed = pyqtSignal(str)
    bg_blur_changed = pyqtSignal(str)
    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    _TARGET_FACE_MODES = ["largest", "smallest", "all", "face_1", "face_2", "face_3"]
    _BG_BLUR_MODES = ["off", "light", "heavy"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "balanced"
        self._mode_btns = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Performance Section ──
        perf_card = SectionCard("Performance")
        mode_row = QHBoxLayout()
        mode_row.setSpacing(4)
        for label, mode in [("⚡ Speed", "speed"), ("⚖ Balanced", "balanced"), ("✨ Quality", "quality")]:
            btn = QPushButton(label)
            btn.setObjectName("modeBtn")
            btn.setProperty("selected", mode == "balanced")
            btn.clicked.connect(lambda checked, m=mode: self._on_mode(m))
            self._mode_btns[mode] = btn
            mode_row.addWidget(btn)
        perf_card.add_layout(mode_row)
        layout.addWidget(perf_card)

        # ── Camera Section ──
        cam_card = SectionCard("Camera")
        self._cam_combo = QComboBox()
        self._cam_combo.currentIndexChanged.connect(self._on_camera_changed)
        cam_card.add_widget(self._cam_combo)
        layout.addWidget(cam_card)

        # ── Target Face Section ──
        target_card = SectionCard("Target Face")
        self._target_face_combo = QComboBox()
        self._target_face_combo.addItems(["Largest", "Smallest", "All", "Face 1", "Face 2", "Face 3"])
        self._target_face_combo.currentIndexChanged.connect(self._on_target_face_changed)
        target_card.add_widget(self._target_face_combo)
        layout.addWidget(target_card)

        # ── Background Blur Section ──
        blur_card = SectionCard("Background Blur")
        self._bg_blur_combo = QComboBox()
        self._bg_blur_combo.addItems(["Off", "Light", "Heavy"])
        self._bg_blur_combo.currentIndexChanged.connect(self._on_bg_blur_changed)
        blur_card.add_widget(self._bg_blur_combo)
        layout.addWidget(blur_card)

    def _on_mode(self, mode: str):
        self._mode = mode
        for m, btn in self._mode_btns.items():
            btn.setProperty("selected", m == mode)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.mode_changed.emit(mode)

    def _on_camera_changed(self, idx: int):
        data = self._cam_combo.itemData(idx)
        if data is not None:
            self.camera_changed.emit(data)

    def _on_target_face_changed(self, idx: int):
        mode = self._TARGET_FACE_MODES[idx] if idx < len(self._TARGET_FACE_MODES) else "largest"
        self.target_face_changed.emit(mode)

    def _on_bg_blur_changed(self, idx: int):
        mode = self._BG_BLUR_MODES[idx] if idx < len(self._BG_BLUR_MODES) else "off"
        self.bg_blur_changed.emit(mode)

    def set_target_face_mode(self, mode: str):
        if mode in self._TARGET_FACE_MODES:
            self._target_face_combo.blockSignals(True)
            self._target_face_combo.setCurrentIndex(self._TARGET_FACE_MODES.index(mode))
            self._target_face_combo.blockSignals(False)

    def set_bg_blur(self, strength: str):
        if strength in self._BG_BLUR_MODES:
            self._bg_blur_combo.blockSignals(True)
            self._bg_blur_combo.setCurrentIndex(self._BG_BLUR_MODES.index(strength))
            self._bg_blur_combo.blockSignals(False)

    def populate_cameras(self, cameras: list):
        self._cam_combo.blockSignals(True)
        self._cam_combo.clear()
        if not cameras:
            self._cam_combo.addItem("No cameras found")
        else:
            for c in cameras:
                self._cam_combo.addItem(c["name"], c["id"])
        self._cam_combo.blockSignals(False)

    def set_mode(self, mode: str):
        self._on_mode(mode)
