"""
Dark-Army — Voice Changer UI Panel
Controls: server status, model selector, pitch, noise suppression, device selection.
"""

import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QComboBox, QLabel, QSlider, QCheckBox,
                              QProgressBar, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from ui.widgets import SectionCard
from utils.logger import get_logger

logger = get_logger(__name__)


class ModelDownloadThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, manager, url: str, filename: str):
        super().__init__()
        self.manager = manager
        self.url = url
        self.filename = filename

    def run(self):
        ok = self.manager.download_model(
            self.url, self.filename,
            progress_cb=lambda p, s: self.progress.emit(p, s)
        )
        self.finished.emit(ok, self.filename)


class ServerDownloadThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool)

    def __init__(self, server_manager):
        super().__init__()
        self.server_manager = server_manager

    def run(self):
        ok = self.server_manager.download(
            progress_cb=lambda p, s: self.progress.emit(p, s)
        )
        self.finished.emit(ok)


class VoicePanel(QWidget):
    """Voice changer sidebar panel."""

    # Signals
    start_vc_requested = pyqtSignal()
    stop_vc_requested = pyqtSignal()
    pitch_changed = pyqtSignal(int)
    model_changed = pyqtSignal(str)
    input_device_changed = pyqtSignal(int)
    output_device_changed = pyqtSignal(int)

    def __init__(self, server_manager, model_manager, audio_pipeline, parent=None):
        super().__init__(parent)
        self.server_manager = server_manager
        self.model_manager = model_manager
        self.audio_pipeline = audio_pipeline
        self._dl_thread = None
        self._server_dl_thread = None
        self._setup_ui()
        self._refresh_devices()
        self._refresh_models()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Server Status ──────────────────────────────────────────────────
        server_card = SectionCard("Voice Server")

        self._server_status = QLabel("● Not installed")
        self._server_status.setStyleSheet("color: #FF4D7A; font-weight: 600; font-size: 12px;")
        server_card.add_widget(self._server_status)

        self._download_server_btn = QPushButton("⬇  Download Voice Server")
        self._download_server_btn.setMinimumHeight(32)
        self._download_server_btn.clicked.connect(self._on_download_server)
        server_card.add_widget(self._download_server_btn)

        self._server_progress = QProgressBar()
        self._server_progress.setFixedHeight(4)
        self._server_progress.setVisible(False)
        server_card.add_widget(self._server_progress)

        layout.addWidget(server_card)

        # ── Voice Toggle ───────────────────────────────────────────────────
        toggle_card = SectionCard("Voice Changer")

        self._vc_toggle = QPushButton("🎤  Enable Voice Changer")
        self._vc_toggle.setObjectName("startBtn")
        self._vc_toggle.setMinimumHeight(44)
        self._vc_toggle.setEnabled(False)
        self._vc_toggle.clicked.connect(self._on_vc_toggle)
        toggle_card.add_widget(self._vc_toggle)

        self._vc_latency = QLabel("Latency: —")
        self._vc_latency.setStyleSheet("color: #6B7094; font-size: 11px;")
        self._vc_latency.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toggle_card.add_widget(self._vc_latency)

        layout.addWidget(toggle_card)

        # ── Model ──────────────────────────────────────────────────────────
        model_card = SectionCard("Voice Model")

        self._model_combo = QComboBox()
        self._model_combo.setMinimumHeight(32)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        model_card.add_widget(self._model_combo)

        model_btns = QHBoxLayout()
        model_btns.setSpacing(6)
        self._load_model_btn = QPushButton("Load")
        self._load_model_btn.setMinimumHeight(30)
        self._load_model_btn.clicked.connect(self._on_load_model)
        self._dl_preset_btn = QPushButton("⬇ Preset")
        self._dl_preset_btn.setMinimumHeight(30)
        self._dl_preset_btn.clicked.connect(self._on_show_presets)
        model_btns.addWidget(self._load_model_btn)
        model_btns.addWidget(self._dl_preset_btn)
        model_card.add_layout(model_btns)

        self._model_progress = QProgressBar()
        self._model_progress.setFixedHeight(4)
        self._model_progress.setVisible(False)
        model_card.add_widget(self._model_progress)

        layout.addWidget(model_card)

        # ── Pitch ──────────────────────────────────────────────────────────
        pitch_card = SectionCard("Pitch Shift")

        pitch_row = QHBoxLayout()
        self._pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self._pitch_slider.setRange(-24, 24)
        self._pitch_slider.setValue(0)
        self._pitch_slider.setMinimumHeight(28)
        self._pitch_val = QLabel("0 st")
        self._pitch_val.setFixedWidth(40)
        self._pitch_val.setStyleSheet("color: #7B7EFF; font-weight: 600;")
        self._pitch_slider.valueChanged.connect(self._on_pitch_changed)
        pitch_row.addWidget(self._pitch_slider)
        pitch_row.addWidget(self._pitch_val)
        pitch_card.add_layout(pitch_row)

        # Preset pitch buttons
        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        for label, val in [("♀ +12", 12), ("♀ +6", 6), ("0", 0), ("♂ -6", -6), ("♂ -12", -12)]:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda _, v=val: self._pitch_slider.setValue(v))
            preset_row.addWidget(btn)
        pitch_card.add_layout(preset_row)
        layout.addWidget(pitch_card)

        # ── Audio Devices ──────────────────────────────────────────────────
        devices_card = SectionCard("Audio Devices")

        devices_card.add_widget(QLabel("Microphone Input:"))
        self._input_combo = QComboBox()
        self._input_combo.setMinimumHeight(30)
        self._input_combo.currentIndexChanged.connect(self._on_input_device_changed)
        devices_card.add_widget(self._input_combo)

        devices_card.add_widget(QLabel("Voice Output:"))
        self._output_combo = QComboBox()
        self._output_combo.setMinimumHeight(30)
        self._output_combo.currentIndexChanged.connect(self._on_output_device_changed)
        devices_card.add_widget(self._output_combo)

        self._noise_cb = QCheckBox("Noise suppression")
        self._noise_cb.setChecked(True)
        self._noise_cb.setMinimumHeight(28)
        self._noise_cb.toggled.connect(self._on_noise_toggled)
        devices_card.add_widget(self._noise_cb)

        # Virtual cable hint
        hint = QLabel("💡 Set output to VB-Cable / BlackHole\nfor use in Zoom, Discord, etc.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6B7094; font-size: 10px; padding: 4px 0;")
        devices_card.add_widget(hint)

        layout.addWidget(devices_card)

        # Update server status
        self._update_server_status()

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_vc_toggle(self):
        if self.audio_pipeline._running:
            self.stop_vc_requested.emit()
            self._vc_toggle.setText("🎤  Enable Voice Changer")
            self._vc_toggle.setObjectName("startBtn")
        else:
            self.start_vc_requested.emit()
            self._vc_toggle.setText("⏹  Disable Voice Changer")
            self._vc_toggle.setObjectName("stopBtn")
        self._vc_toggle.style().unpolish(self._vc_toggle)
        self._vc_toggle.style().polish(self._vc_toggle)

    def _on_pitch_changed(self, val: int):
        self._pitch_val.setText(f"{val:+d} st" if val != 0 else "0 st")
        self.pitch_changed.emit(val)

    def _on_model_changed(self, idx: int):
        data = self._model_combo.itemData(idx)
        if data:
            self.model_changed.emit(data)

    def _on_load_model(self):
        data = self._model_combo.currentData()
        if data and self.server_manager.is_ready():
            self.model_manager.load_model_on_server(data)

    def _on_show_presets(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Download Preset Voice")
        dlg.setFixedSize(380, 260)
        layout = QVBoxLayout(dlg)
        lst = QListWidget()
        for p in self.model_manager.list_preset_models():
            lst.addItem(f"{p['name']} — {p['description']}")
        layout.addWidget(lst)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if dlg.exec() and lst.currentRow() >= 0:
            preset = self.model_manager.list_preset_models()[lst.currentRow()]
            self._start_model_download(preset["url"], preset["filename"])

    def _start_model_download(self, url: str, filename: str):
        self._model_progress.setValue(0)
        self._model_progress.setVisible(True)
        self._dl_thread = ModelDownloadThread(self.model_manager, url, filename)
        self._dl_thread.progress.connect(lambda p, s: self._model_progress.setValue(p))
        self._dl_thread.finished.connect(self._on_model_dl_done)
        self._dl_thread.start()

    def _on_model_dl_done(self, ok: bool, filename: str):
        self._model_progress.setVisible(False)
        if ok:
            self._refresh_models()

    def _on_download_server(self):
        self._server_progress.setValue(0)
        self._server_progress.setVisible(True)
        self._download_server_btn.setEnabled(False)
        self._server_dl_thread = ServerDownloadThread(self.server_manager)
        self._server_dl_thread.progress.connect(
            lambda p, s: (self._server_progress.setValue(p),
                          self._server_status.setText(f"⬇ {s}"))
        )
        self._server_dl_thread.finished.connect(self._on_server_dl_done)
        self._server_dl_thread.start()

    def _on_server_dl_done(self, ok: bool):
        self._server_progress.setVisible(False)
        self._download_server_btn.setEnabled(True)
        self._update_server_status()

    def _on_input_device_changed(self, idx: int):
        data = self._input_combo.itemData(idx)
        if data is not None:
            self.input_device_changed.emit(data)

    def _on_output_device_changed(self, idx: int):
        data = self._output_combo.itemData(idx)
        if data is not None:
            self.output_device_changed.emit(data)

    def _on_noise_toggled(self, checked: bool):
        self.audio_pipeline.set_noise_suppression(checked)

    # ── Public update methods ──────────────────────────────────────────────

    def update_server_status(self, status: str):
        colors = {
            "ready":       ("#22D98F", "● Ready"),
            "starting":    ("#FFB547", "⏳ Starting..."),
            "crashed":     ("#FF4D7A", "● Crashed"),
            "stopped":     ("#6B7094", "● Stopped"),
            "reconnecting": ("#FFB547", "⟳ Reconnecting..."),
        }
        for key, (color, text) in colors.items():
            if key in status.lower():
                self._server_status.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 12px;")
                self._server_status.setText(text)
                self._vc_toggle.setEnabled(key == "ready")
                return
        self._server_status.setText(f"● {status}")

    def update_vc_latency(self, ms: float):
        color = "#22D98F" if ms < 400 else ("#FFB547" if ms < 800 else "#FF4D7A")
        self._vc_latency.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._vc_latency.setText(f"Latency: {ms:.0f} ms")

    def _refresh_devices(self):
        devices = self.audio_pipeline.list_audio_devices()
        self._input_combo.clear()
        for d in devices.get("inputs", []):
            self._input_combo.addItem(d["name"], d["id"])
        self._output_combo.clear()
        for d in devices.get("outputs", []):
            self._output_combo.addItem(d["name"], d["id"])

    def _refresh_models(self):
        self._model_combo.clear()
        self._model_combo.addItem("— select model —", None)
        for m in self.model_manager.list_local_models():
            self._model_combo.addItem(m["name"], m["path"])

    def _update_server_status(self):
        if self.server_manager.is_installed():
            self._download_server_btn.setVisible(False)
            self._server_status.setStyleSheet("color: #6B7094; font-weight: 600; font-size: 12px;")
            self._server_status.setText("● Installed — not running")
        else:
            self._server_status.setStyleSheet("color: #FF4D7A; font-weight: 600; font-size: 12px;")
            self._server_status.setText("● Not installed")
