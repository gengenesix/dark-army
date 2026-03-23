import os
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                              QLabel, QPushButton, QMessageBox, QSizePolicy,
                              QFrame, QApplication, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QPixmap, QIcon, QColor
import cv2

from config.manager import AppConfig, ConfigManager
from core.hardware import HardwareInfo
from core.face_detector import FaceDetector, DetectedFace
from core.capture import CameraCapture
from core.pipeline import EchelonPipeline
from core.face_gallery import FaceGallery
from ui.widgets import Card, SectionLabel, Divider
from ui.face_panel import FacePanel
from ui.preview_panel import PreviewPanel
from ui.controls_panel import ControlsPanel
from ui.status_bar import StatusBar
from ui.settings_dialog import SettingsDialog
from ui.tutorial import TutorialOverlay
from utils.logger import get_logger

logger = get_logger(__name__)


class FaceLoadThread(QThread):
    face_loaded = pyqtSignal(object, str)  # DetectedFace, path
    face_failed = pyqtSignal(str)

    def __init__(self, image_path: str, models_dir: str, providers: list, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.models_dir = models_dir
        self.providers = providers

    def run(self):
        try:
            detector = FaceDetector(self.models_dir, self.providers)
            if not detector.load():
                self.face_failed.emit("Could not load face detector")
                return
            face = detector.extract_face_from_image(self.image_path)
            if face is None:
                self.face_failed.emit("No face detected in this photo")
            else:
                self.face_loaded.emit(face, self.image_path)
        except Exception as e:
            self.face_failed.emit(str(e))


def _make_card_frame() -> QFrame:
    """Helper: returns a QFrame styled as a card (sidebar)."""
    f = QFrame()
    f.setObjectName("card")
    return f


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, hw_info: HardwareInfo):
        super().__init__()
        self.config = config
        self.hw_info = hw_info
        self.pipeline = None
        self._face_thread = None
        self._source_face = None
        self._pending_gallery_save_name = None
        self.tray = None
        self.face_gallery = FaceGallery(config.data_dir)
        self._setup_window()
        self._setup_ui()
        self._setup_connections()
        self._setup_hotkeys()
        # Delay camera scan until AFTER window is visible — speeds up startup
        QTimer.singleShot(500, self._load_cameras)
        self._refresh_gallery()
        self._refresh_presets()

    def _setup_window(self):
        self.setWindowTitle("Echelon")
        # Set window icon
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "icon_256.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(900, 620)
        self.resize(self.config.window_width, self.config.window_height)
        self.move(self.config.window_x, self.config.window_y)

    def _build_header(self):
        header = QFrame()
        header.setObjectName("echelonHeader")
        header.setFixedHeight(56)
        header.setStyleSheet("""
            QFrame#echelonHeader {
                background: #0B0C14;
                border-bottom: 1px solid #1A1B24;
            }
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        logo_path = Path(__file__).parent.parent / "assets" / "icons" / "icon_32.png"
        if logo_path.exists():
            logo_lbl = QLabel()
            logo_lbl.setPixmap(QPixmap(str(logo_path)).scaled(
                28, 28,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
            layout.addWidget(logo_lbl)
            layout.addSpacing(10)

        name_lbl = QLabel("ECHELON")
        name_lbl.setStyleSheet(
            "color: #5C5FFF; font-size: 18px; font-weight: 800; "
            "letter-spacing: 4px; background: transparent;"
        )
        layout.addWidget(name_lbl)

        layout.addSpacing(8)
        ver_lbl = QLabel("v2.0")
        ver_lbl.setStyleSheet(
            "color: #50516A; font-size: 11px; background: transparent; padding-top: 4px;"
        )
        layout.addWidget(ver_lbl)

        layout.addStretch()

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(36, 36)
        settings_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #1A1B24;
                border-radius: 8px;
                color: #8B8CA8;
                font-size: 16px;
                padding: 0;
            }
            QPushButton:hover {
                background: #1A1B24;
                color: #F0F0FA;
                border-color: #5C5FFF;
            }
        """)
        settings_btn.clicked.connect(self._show_settings)
        layout.addWidget(settings_btn)

        return header

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        outer_layout.addWidget(self._build_header())

        content = QWidget()
        main_layout = QHBoxLayout(content)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        outer_layout.addWidget(content)

        # Left sidebar
        sidebar = _make_card_frame()
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 12)
        sidebar_layout.setSpacing(12)

        self.face_panel = FacePanel()
        sidebar_layout.addWidget(self.face_panel)

        sidebar_layout.addWidget(Divider())

        self.controls_panel = ControlsPanel()
        self.controls_panel.set_mode(self.config.performance_mode)
        sidebar_layout.addWidget(self.controls_panel)

        sidebar_layout.addStretch()

        sidebar_layout.addWidget(Divider())
        sidebar_layout.addWidget(SectionLabel("PRESETS"))
        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(80)
        self._load_preset_btn = QPushButton("Load")
        self._load_preset_btn.setFixedWidth(46)
        self._load_preset_btn.setStyleSheet("font-size: 11px; padding: 3px 6px;")
        self._load_preset_btn.clicked.connect(self._on_load_preset)
        preset_row.addWidget(self._preset_combo)
        preset_row.addWidget(self._load_preset_btn)
        sidebar_layout.addLayout(preset_row)

        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setObjectName("settingsBtn")
        settings_btn.setStyleSheet("color: #8888A0; background: transparent; border: none; text-align: left; padding: 4px 0;")
        settings_btn.clicked.connect(self._show_settings)
        sidebar_layout.addWidget(settings_btn)

        # Right area
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        self.preview_panel = PreviewPanel()
        right_layout.addWidget(self.preview_panel)

        self.status_bar_widget = StatusBar()
        right_layout.addWidget(self.status_bar_widget)

        main_layout.addWidget(sidebar)
        main_layout.addLayout(right_layout)

        # GPU mode label
        gpu_mode = "CUDA" if self.hw_info.has_cuda else "CPU"
        self.status_bar_widget.update_gpu_mode(gpu_mode)

        # Hotkeys are configured in _setup_hotkeys()

    def _setup_connections(self):
        self.face_panel.face_selected.connect(self._on_face_selected)
        self.face_panel.gallery_save_requested.connect(self._on_gallery_save)
        self.face_panel.gallery_load_requested.connect(self._on_gallery_load)
        self.face_panel.gallery_delete_requested.connect(self._on_gallery_delete)
        self.controls_panel.start_clicked.connect(self.on_start)
        self.controls_panel.stop_clicked.connect(self.on_stop)
        self.controls_panel.mode_changed.connect(self._on_mode_changed)
        self.controls_panel.camera_changed.connect(self._on_camera_changed)
        self.controls_panel.target_face_changed.connect(self._on_target_face_changed)
        self.controls_panel.bg_blur_changed.connect(self._on_bg_blur_changed)

    def _setup_hotkeys(self):
        QShortcut(QKeySequence("Space"), self, self._toggle_pipeline)
        QShortcut(QKeySequence("F1"), self, self._cycle_mode)
        QShortcut(QKeySequence("F2"), self, self._toggle_vcam)
        QShortcut(QKeySequence("Escape"), self, self.hide)
        QShortcut(QKeySequence("Ctrl+Q"), self, self._quit_app)

    def _refresh_gallery(self):
        faces = self.face_gallery.list_faces()
        self.face_panel.update_gallery_list(faces)

    def _load_cameras(self):
        cap = CameraCapture()
        cameras = cap.list_cameras()
        self.controls_panel.populate_cameras(cameras)

    def _on_face_selected(self, path: str):
        if self._face_thread and self._face_thread.isRunning():
            return
        self._face_thread = FaceLoadThread(path, self.config.models_dir, self.hw_info.onnx_providers)
        self._face_thread.face_loaded.connect(self._on_face_loaded)
        self._face_thread.face_failed.connect(self._on_face_failed)
        self._face_thread.start()
        self.face_panel._status_label.setText("Detecting face...")
        self.face_panel._status_label.setStyleSheet("color: #FFB547; font-size: 12px;")

    def _on_face_loaded(self, face: DetectedFace, path: str):
        self._source_face = face
        self.face_panel.show_face_preview(path)
        self.config.active_source_face_path = path
        if self.pipeline:
            self.pipeline.set_source_face(face)
        # Complete a pending gallery save if one was queued
        if self._pending_gallery_save_name:
            ok = self.face_gallery.save_face(self._pending_gallery_save_name, path, face)
            if ok:
                self._refresh_gallery()
            else:
                QMessageBox.warning(self, "Gallery Full",
                    f"Could not save '{self._pending_gallery_save_name}' — gallery full (max 5).")
            self._pending_gallery_save_name = None

    def _on_face_failed(self, msg: str):
        self.face_panel.show_error(msg)
        self._pending_gallery_save_name = None

    # ── Gallery operations ───────────────────────────────────────────────────

    def _on_gallery_save(self, name: str):
        """Save the currently loaded face to gallery under the given name."""
        if self._source_face is None:
            QMessageBox.warning(self, "No Face Loaded",
                "Upload and detect a face photo first before saving to gallery.")
            return
        ok = self.face_gallery.save_face(name, self.config.active_source_face_path, self._source_face)
        if ok:
            self._refresh_gallery()
        else:
            QMessageBox.warning(self, "Gallery Full",
                f"Could not save '{name}' — gallery full (max 5).")

    def _on_gallery_load(self, name: str):
        """Load cached face embedding instantly (no detection needed)."""
        face = self.face_gallery.load_face(name)
        if face is None:
            QMessageBox.warning(self, "Load Failed", f"Could not load '{name}' from gallery.")
            return
        self._source_face = face
        preview = str(self.face_gallery.faces_dir / name / "preview.jpg")
        if os.path.exists(preview):
            self.face_panel.show_face_preview(preview)
        else:
            self.face_panel._status_label.setText(f"✓ Loaded: {name}")
            self.face_panel._status_label.setStyleSheet("color: #22D98F; font-size: 12px;")
        if self.pipeline:
            self.pipeline.set_source_face(face)

    def _on_gallery_delete(self, name: str):
        self.face_gallery.delete_face(name)
        self._refresh_gallery()

    # ── Pipeline control ─────────────────────────────────────────────────────

    def on_start(self):
        if self._source_face is None:
            QMessageBox.warning(self, "No Source Face",
                "Please upload a face photo before starting.")
            return
        self.controls_panel.start_btn.set_state("loading")
        self.config.camera_device_id = self.controls_panel._cam_combo.currentData() or 0
        self.pipeline = EchelonPipeline(self.config, self.hw_info)
        self.pipeline.set_source_face(self._source_face)
        self.pipeline.frames_ready.connect(self._on_frames_ready)
        self.pipeline.fps_updated.connect(self.status_bar_widget.update_fps)
        self.pipeline.latency_updated.connect(self.status_bar_widget.update_latency)
        self.pipeline.status_changed.connect(self._on_status_changed)
        self.pipeline.error_occurred.connect(self._on_error)
        self.pipeline.virtual_cam_status.connect(self.status_bar_widget.update_vcam)
        self.pipeline.frame_skip_changed.connect(self.status_bar_widget.update_frame_skip)
        self.status_bar_widget.update_frame_skip(self.config.frame_skip)
        if self.config.auto_tune:
            self.pipeline.enable_auto_tune(True)
        self.pipeline.start()

    def on_stop(self):
        if self.pipeline:
            self.pipeline.stop()
            self.pipeline = None
        self.controls_panel.start_btn.set_state("idle")
        self.preview_panel.set_active(False)
        self.status_bar_widget.update_status("Idle")
        self.status_bar_widget.update_frame_skip(0)
        if self.tray:
            self.tray.set_active(False)

    def _toggle_pipeline(self):
        if self.pipeline and self.pipeline.isRunning():
            self.on_stop()
        else:
            self.on_start()

    def _on_frames_ready(self, orig, swapped):
        self.preview_panel.update_frames(orig, swapped)

    def _on_status_changed(self, status: str):
        self.status_bar_widget.update_status(status)
        if status == "Live":
            self.controls_panel.start_btn.set_state("live")
            self.preview_panel.set_active(True)
            if self.tray:
                self.tray.set_active(True)
                self.tray.show_notification("Echelon Active",
                    "Select 'Echelon Camera' in your video call app")
        elif status == "Stopped":
            self.controls_panel.start_btn.set_state("idle")
            self.preview_panel.set_active(False)
            if self.tray:
                self.tray.set_active(False)

    def _on_error(self, msg: str):
        QMessageBox.warning(self, "Echelon Error", msg)
        self.controls_panel.start_btn.set_state("idle")

    def _cycle_mode(self):
        """F1 — cycle quality → balanced → speed → quality."""
        modes = ["quality", "balanced", "speed"]
        current = self.config.performance_mode
        idx = modes.index(current) if current in modes else 0
        new_mode = modes[(idx + 1) % len(modes)]
        self.controls_panel.set_mode(new_mode)
        self._on_mode_changed(new_mode)

    def _toggle_vcam(self):
        """F2 — toggle virtual camera on/off while pipeline is live."""
        if self.pipeline and self.pipeline.isRunning():
            self.pipeline.toggle_virtual_cam()

    def _quit_app(self):
        """Ctrl+Q — actually quit (not just minimise)."""
        self._save_geometry()
        self.on_stop()
        QApplication.quit()

    def _on_mode_changed(self, mode: str):
        self.config.performance_mode = mode
        if self.pipeline:
            self.pipeline.set_performance_mode(mode)
            self.status_bar_widget.update_frame_skip(self.pipeline.frame_skip)

    def _on_camera_changed(self, device_id: int):
        self.config.camera_device_id = device_id

    def _show_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            # Apply updated perf settings to running pipeline immediately
            if self.pipeline:
                self.pipeline.frame_skip = self.config.frame_skip
                self.pipeline.face_detector._detect_interval = self.config.face_detect_interval
                self.pipeline.set_performance_mode(self.config.performance_mode)
                if self.config.auto_tune:
                    self.pipeline.enable_auto_tune(True)
                self.status_bar_widget.update_frame_skip(self.pipeline.frame_skip)

    def _on_target_face_changed(self, mode: str):
        self.config.target_face_mode = mode
        if self.pipeline:
            self.pipeline.set_target_face_mode(mode)

    def _on_bg_blur_changed(self, strength: str):
        self.config.bg_blur = strength
        if self.pipeline:
            self.pipeline.set_bg_blur(strength)

    def _refresh_presets(self):
        self._preset_combo.clear()
        for p in (self.config.presets or []):
            self._preset_combo.addItem(p.get("name", "Unnamed"))

    def _on_load_preset(self):
        idx = self._preset_combo.currentIndex()
        if idx < 0 or not self.config.presets:
            return
        preset = self.config.presets[idx]
        mode = preset.get("performance_mode", "balanced")
        self.controls_panel.set_mode(mode)
        self._on_mode_changed(mode)
        bg_blur = preset.get("bg_blur", "off")
        self.controls_panel.set_bg_blur(bg_blur)
        self._on_bg_blur_changed(bg_blur)
        target_face_mode = preset.get("target_face_mode", "largest")
        self.controls_panel.set_target_face_mode(target_face_mode)
        self._on_target_face_changed(target_face_mode)

    def show_tutorial(self):
        """Show the first-launch tutorial overlay."""
        overlay = TutorialOverlay(self)
        overlay.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if self.tray:
            self.tray.show_notification("Echelon", "Running in background")

    def _save_geometry(self):
        pos = self.pos()
        size = self.size()
        self.config.window_x = pos.x()
        self.config.window_y = pos.y()
        self.config.window_width = size.width()
        self.config.window_height = size.height()
