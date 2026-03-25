import os
import sys
import subprocess
import cv2
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QProgressBar, QWidget, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from config.manager import AppConfig
from models.downloader import ModelDownloader

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")


class OnboardingDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Welcome to Dark-Army")
        self.setFixedSize(540, 520)
        self.setModal(True)
        self._downloader = None
        self._setup_ui()
        self.run_all_checks()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Welcome to Dark-Army")
        title.setStyleSheet("color: #E8E9F0; font-size: 20px; font-weight: 700; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel("Let's verify your setup before we begin.")
        subtitle.setStyleSheet("color: #6B7094; font-size: 13px; background: transparent;")
        layout.addWidget(subtitle)

        layout.addSpacing(4)

        # Virtual camera row (Linux only — skip on Windows)
        if IS_LINUX:
            self._vcam_row = self._make_check_row(
                "Virtual Camera Driver",
                "Required for Zoom, Meet, Discord"
            )
            layout.addWidget(self._vcam_row["widget"])
        else:
            self._vcam_row = None

        # Model row
        self._model_row = self._make_check_row(
            "Face Swap Model",
            "inswapper_128.onnx (~554 MB, one-time download)"
        )
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFixedHeight(5)
        layout.addWidget(self._model_row["widget"])
        layout.addWidget(self._progress)

        # Webcam row
        self._cam_row = self._make_check_row(
            "Webcam",
            "Checking for connected camera..."
        )
        layout.addWidget(self._cam_row["widget"])

        layout.addStretch()

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #6B7094; font-size: 11px; background: transparent;")
        layout.addWidget(self._status_lbl)

        self._continue_btn = QPushButton("Continue →")
        self._continue_btn.setObjectName("primaryBtn")
        self._continue_btn.setFixedHeight(44)
        self._continue_btn.setEnabled(False)
        self._continue_btn.clicked.connect(self._on_continue)
        layout.addWidget(self._continue_btn)

        skip_btn = QPushButton("Skip setup (advanced)")
        skip_btn.setStyleSheet("color: #6B7094; background: transparent; border: none; font-size: 11px;")
        skip_btn.clicked.connect(self._on_skip)
        layout.addWidget(skip_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _make_check_row(self, title: str, desc: str) -> dict:
        widget = QFrame()
        widget.setObjectName("checkRow")
        row = QHBoxLayout(widget)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)

        icon = QLabel("○")
        icon.setFixedWidth(22)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 16px; color: #3A3B4E; background: transparent;")

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name_lbl = QLabel(title)
        name_lbl.setStyleSheet("font-weight: 600; color: #E8E9F0; background: transparent; font-size: 13px;")
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #6B7094; font-size: 11px; background: transparent;")
        text_col.addWidget(name_lbl)
        text_col.addWidget(desc_lbl)

        btn = QPushButton("Check")
        btn.setFixedWidth(130)
        btn.setFixedHeight(32)

        row.addWidget(icon)
        row.addLayout(text_col, 1)
        row.addWidget(btn)

        return {"widget": widget, "icon": icon, "desc": desc_lbl, "btn": btn}

    def run_all_checks(self):
        if IS_LINUX and self._vcam_row:
            self._check_vcam()
        self._check_model()
        self._check_camera()

    # ── Virtual Camera (Linux only) ──────────────────
    def _check_vcam(self):
        ok = os.path.exists('/dev/video10')
        row = self._vcam_row
        if ok:
            self._set_row_ok(row, "Dark-Army Camera device ready")
        else:
            self._set_row_fail(row, "Not found — click Fix to install")
            self._connect_btn(row["btn"], self._fix_vcam)
            row["btn"].setText("Fix Now")
        self._update_continue()

    def _fix_vcam(self):
        self._vcam_row["desc"].setText("Installing virtual camera...")
        self._vcam_row["btn"].setEnabled(False)
        try:
            subprocess.run(
                ['sudo', 'modprobe', 'v4l2loopback',
                 'devices=1', 'video_nr=10',
                 'card_label=Dark-Army Camera', 'exclusive_caps=1'],
                check=True, timeout=15
            )
        except Exception as e:
            self._vcam_row["desc"].setText(f"Error: {e}. Try: sudo modprobe v4l2loopback")
            self._vcam_row["btn"].setEnabled(True)
            return
        self._check_vcam()

    # ── Model ────────────────────────────────────────
    def _check_model(self):
        path = Path(self.config.models_dir) / "inswapper_128.onnx"
        row = self._model_row
        if path.exists():
            self._set_row_ok(row, "inswapper_128.onnx ready")
        else:
            self._set_row_fail(row, "Not downloaded yet (~554 MB)")
            self._connect_btn(row["btn"], self._download_model)
            row["btn"].setText("Download")
        self._update_continue()

    def _download_model(self):
        self._model_row["btn"].setEnabled(False)
        self._model_row["btn"].setText("Downloading...")
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._downloader = ModelDownloader(self.config.models_dir)
        self._downloader.progress_updated.connect(self._on_dl_progress)
        self._downloader.all_done.connect(self._on_dl_done)
        self._downloader.download_failed.connect(self._on_dl_failed)
        self._downloader.start()

    def _on_dl_progress(self, pct: int, msg: str):
        self._progress.setValue(pct)
        self._model_row["desc"].setText(msg)

    def _on_dl_done(self):
        self._progress.setVisible(False)
        self._check_model()

    def _on_dl_failed(self, name: str, error: str):
        self._progress.setVisible(False)
        self._model_row["desc"].setText(f"Failed: {error}")
        self._model_row["btn"].setEnabled(True)
        self._model_row["btn"].setText("Retry")

    # ── Webcam ───────────────────────────────────────
    def _check_camera(self):
        row = self._cam_row
        row["desc"].setText("Scanning for cameras...")
        cap = cv2.VideoCapture(0)
        ok = cap.isOpened()
        cap.release()
        if ok:
            self._set_row_ok(row, "Camera detected and ready")
        else:
            self._set_row_fail(row, "No camera found — connect a webcam and retry")
            self._connect_btn(row["btn"], self._check_camera)
            row["btn"].setText("Retry")
        self._update_continue()

    # ── Helpers ──────────────────────────────────────
    def _set_row_ok(self, row: dict, desc: str):
        row["icon"].setText("✅")
        row["icon"].setStyleSheet("font-size: 14px; background: transparent;")
        row["desc"].setText(desc)
        row["btn"].setText("OK")
        row["btn"].setEnabled(False)

    def _set_row_fail(self, row: dict, desc: str):
        row["icon"].setText("⚠️")
        row["icon"].setStyleSheet("font-size: 14px; background: transparent;")
        row["desc"].setText(desc)
        row["btn"].setEnabled(True)

    def _connect_btn(self, btn: QPushButton, slot):
        try:
            btn.clicked.disconnect()
        except Exception:
            pass
        btn.clicked.connect(slot)

    def _update_continue(self):
        model_ok = (Path(self.config.models_dir) / "inswapper_128.onnx").exists()
        cap = cv2.VideoCapture(0)
        cam_ok = cap.isOpened()
        cap.release()

        if IS_LINUX:
            vcam_ok = os.path.exists('/dev/video10')
            all_ok = vcam_ok and model_ok and cam_ok
        else:
            # Windows: virtual camera not required (use OBS or similar)
            all_ok = model_ok and cam_ok

        self._continue_btn.setEnabled(all_ok)
        if all_ok:
            self._status_lbl.setText("✅ Everything looks good — you're ready to go!")
            self._status_lbl.setStyleSheet("color: #22D98F; font-size: 11px; background: transparent;")
        else:
            missing = []
            if IS_LINUX and not os.path.exists('/dev/video10'):
                missing.append("virtual camera")
            if not model_ok:
                missing.append("AI model")
            if not cam_ok:
                missing.append("webcam")
            self._status_lbl.setText(f"Still needed: {', '.join(missing)}")
            self._status_lbl.setStyleSheet("color: #FFB547; font-size: 11px; background: transparent;")

    def _on_continue(self):
        self.config.first_launch = False
        from config.manager import ConfigManager
        ConfigManager().save(self.config)
        self.accept()

    def _on_skip(self):
        """Skip onboarding — let user proceed even if not fully configured."""
        self.config.first_launch = False
        from config.manager import ConfigManager
        ConfigManager().save(self.config)
        self.accept()
