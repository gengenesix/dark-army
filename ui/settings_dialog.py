import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QCheckBox, QComboBox, QLineEdit,
                              QGroupBox, QFormLayout, QSlider, QMessageBox,
                              QInputDialog, QScrollArea, QWidget, QSizePolicy,
                              QFrame)
from PyQt6.QtCore import Qt
from config.manager import AppConfig, BASE_DIR


def _grp_style():
    return (
        "QGroupBox { color: #8888A0; font-weight: 600; border: 1px solid #2A2A35; "
        "border-radius: 8px; margin-top: 8px; padding-top: 8px; } "
        "QGroupBox::title { subcontrol-origin: margin; left: 12px; }"
    )


def _make_slider_row(mn, mx, default):
    """Returns (layout, slider, value_label)."""
    row = QHBoxLayout()
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(mn, mx)
    slider.setValue(default)
    slider.setFixedWidth(120)
    val_lbl = QLabel(str(default))
    slider.valueChanged.connect(lambda v: val_lbl.setText(str(v)))
    row.addWidget(slider)
    row.addWidget(val_lbl)
    row.addStretch()
    return row, slider, val_lbl


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumSize(520, 600)
        self.resize(520, 740)
        self._setup_ui()
        self.load_from_config(config)

    def _setup_ui(self):
        # Outer layout: scroll area + fixed button row
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scroll area for all settings content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_widget = QWidget()
        scroll_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(24, 24, 24, 12)
        layout.setSpacing(16)

        scroll.setWidget(scroll_widget)
        outer.addWidget(scroll, 1)

        # ── General ─────────────────────────────────────────────────────────
        gen = QGroupBox("General")
        gen.setStyleSheet(_grp_style())
        gen_layout = QFormLayout(gen)
        gen_layout.setSpacing(10)
        self._login_cb = QCheckBox()
        self._minimized_cb = QCheckBox()
        self._perf_combo = QComboBox()
        self._perf_combo.addItems(["quality", "balanced", "speed"])
        gen_layout.addRow("Launch on login:", self._login_cb)
        gen_layout.addRow("Start minimized:", self._minimized_cb)
        gen_layout.addRow("Default mode:", self._perf_combo)
        layout.addWidget(gen)

        # ── Performance ──────────────────────────────────────────────────────
        perf = QGroupBox("Performance")
        perf.setStyleSheet(_grp_style())
        perf_layout = QFormLayout(perf)
        perf_layout.setSpacing(12)
        perf_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        skip_row, self._skip_slider, self._skip_val_lbl = _make_slider_row(0, 3, 1)
        perf_layout.addRow("Frame skip (0 = off):", skip_row)

        det_row, self._det_slider, self._det_val_lbl = _make_slider_row(1, 10, 5)
        perf_layout.addRow("Detect every N frames:", det_row)

        self._res_combo = QComboBox()
        self._res_combo.setMinimumHeight(32)
        self._res_combo.addItems(["480p (Speed)", "640p (Balanced)", "720p (Quality)"])
        perf_layout.addRow("Processing resolution:", self._res_combo)

        self._autotune_cb = QCheckBox("Auto-tune to maintain ~15 FPS")
        self._autotune_cb.setMinimumHeight(28)
        perf_layout.addRow("", self._autotune_cb)

        opt_btn = QPushButton("⚡  Optimize for My Hardware")
        opt_btn.setMinimumHeight(34)
        opt_btn.clicked.connect(self._on_optimize)
        perf_layout.addRow("", opt_btn)

        layout.addWidget(perf)

        # ── Advanced ────────────────────────────────────────────────────────
        adv = QGroupBox("Advanced")
        adv.setStyleSheet(_grp_style())
        adv_layout = QFormLayout(adv)
        adv_layout.setSpacing(10)
        self._vcam_edit = QLineEdit()
        self._loglevel_combo = QComboBox()
        self._loglevel_combo.addItems(["INFO", "DEBUG", "WARNING"])
        open_log_btn = QPushButton("Open Log File")
        open_log_btn.clicked.connect(self._open_log)
        adv_layout.addRow("Virtual camera:", self._vcam_edit)
        adv_layout.addRow("Log level:", self._loglevel_combo)
        adv_layout.addRow("", open_log_btn)
        layout.addWidget(adv)

        # ── Presets ───────────────────────────────────────────────────────────
        presets_grp = QGroupBox("Presets")
        presets_grp.setStyleSheet(_grp_style())
        presets_layout = QVBoxLayout(presets_grp)
        presets_layout.setSpacing(8)
        self._presets_combo = QComboBox()
        presets_layout.addWidget(self._presets_combo)
        preset_btn_row = QHBoxLayout()
        save_preset_btn = QPushButton("Save Current")
        save_preset_btn.clicked.connect(self._on_save_preset)
        load_preset_btn = QPushButton("Load")
        load_preset_btn.clicked.connect(self._on_load_preset)
        del_preset_btn = QPushButton("Delete")
        del_preset_btn.clicked.connect(self._on_delete_preset)
        preset_btn_row.addWidget(save_preset_btn)
        preset_btn_row.addWidget(load_preset_btn)
        preset_btn_row.addWidget(del_preset_btn)
        presets_layout.addLayout(preset_btn_row)
        layout.addWidget(presets_grp)

        # ── About ────────────────────────────────────────────────────────────
        about = QGroupBox("About")
        about.setStyleSheet(_grp_style())
        about_layout = QVBoxLayout(about)
        about_layout.addWidget(QLabel("Dark-Army v1.0"))
        about_layout.addWidget(QLabel("Created by Zero"))
        about_layout.addWidget(QLabel("Face Swap + Voice Changer by Zero"))
        about_layout.addWidget(QLabel("© 2026 Zero. All rights reserved."))
        update_btn = QPushButton("Check for Updates")
        update_btn.clicked.connect(self._on_check_updates)
        about_layout.addWidget(update_btn)
        layout.addWidget(about)

        layout.addStretch()

        # Fixed button row OUTSIDE scroll area (always visible at bottom)
        btn_frame = QFrame()
        btn_frame.setStyleSheet(
            "QFrame { background: #0D0E14; border-top: 1px solid #1E1F2E; }"
        )
        btn_row = QHBoxLayout(btn_frame)
        btn_row.setContentsMargins(24, 12, 24, 16)
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(90)
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumWidth(90)
        save_btn.setMinimumHeight(36)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        outer.addWidget(btn_frame)

    # ── Resolution index helpers ──────────────────────────────────────────
    _MODE_TO_RES = {"speed": 0, "balanced": 1, "quality": 2}

    def load_from_config(self, config: AppConfig):
        self._login_cb.setChecked(config.launch_on_login)
        self._minimized_cb.setChecked(config.start_minimized)
        idx = self._perf_combo.findText(config.performance_mode)
        if idx >= 0:
            self._perf_combo.setCurrentIndex(idx)
        self._vcam_edit.setText(config.virtual_camera_device)
        idx2 = self._loglevel_combo.findText(config.log_level)
        if idx2 >= 0:
            self._loglevel_combo.setCurrentIndex(idx2)
        self._skip_slider.setValue(config.frame_skip)
        self._skip_val_lbl.setText(str(config.frame_skip))
        self._det_slider.setValue(config.face_detect_interval)
        self._det_val_lbl.setText(str(config.face_detect_interval))
        self._res_combo.setCurrentIndex(self._MODE_TO_RES.get(config.performance_mode, 1))
        self._autotune_cb.setChecked(config.auto_tune)
        self._update_preset_list()

    def save_to_config(self, config: AppConfig):
        config.launch_on_login = self._login_cb.isChecked()
        config.start_minimized = self._minimized_cb.isChecked()
        config.performance_mode = self._perf_combo.currentText()
        config.virtual_camera_device = self._vcam_edit.text()
        config.log_level = self._loglevel_combo.currentText()
        config.frame_skip = self._skip_slider.value()
        config.face_detect_interval = self._det_slider.value()
        config.auto_tune = self._autotune_cb.isChecked()

    def _on_optimize(self):
        """Preset tuned for 8 GB RAM / no GPU."""
        self._skip_slider.setValue(2)
        self._det_slider.setValue(5)
        self._res_combo.setCurrentIndex(0)
        self._perf_combo.setCurrentText("speed")
        self._autotune_cb.setChecked(True)
        QMessageBox.information(
            self, "Optimized",
            "Settings tuned for CPU-only / 8 GB RAM:\n"
            "  Frame skip: 2  •  Detect every 5 frames  •  480p"
        )

    def _on_save(self):
        self.save_to_config(self.config)
        from config.manager import ConfigManager
        ConfigManager().save(self.config)
        self.accept()

    def _open_log(self):
        log_path = BASE_DIR / "logs" / "echelon.log"
        try:
            if sys.platform == "win32":
                subprocess.Popen(["notepad.exe", str(log_path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(log_path)])
            else:
                subprocess.Popen(["xdg-open", str(log_path)])
        except Exception:
            pass

    # ── Preset helpers ────────────────────────────────────────────────────

    def _update_preset_list(self):
        self._presets_combo.clear()
        for p in (self.config.presets or []):
            self._presets_combo.addItem(p.get("name", "Unnamed"))

    def _on_save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        preset = {
            "name": name,
            "performance_mode": self._perf_combo.currentText(),
            "bg_blur": "off",
            "target_face_mode": "largest",
        }
        if self.config.presets is None:
            self.config.presets = []
        self.config.presets = [p for p in self.config.presets if p.get("name") != name]
        self.config.presets.append(preset)
        self._update_preset_list()
        self._presets_combo.setCurrentText(name)

    def _on_load_preset(self):
        idx = self._presets_combo.currentIndex()
        if idx < 0 or not self.config.presets:
            return
        preset = self.config.presets[idx]
        mode = preset.get("performance_mode", "balanced")
        i = self._perf_combo.findText(mode)
        if i >= 0:
            self._perf_combo.setCurrentIndex(i)

    def _on_delete_preset(self):
        idx = self._presets_combo.currentIndex()
        if idx < 0 or not self.config.presets:
            return
        self.config.presets.pop(idx)
        self._update_preset_list()

    def _on_check_updates(self):
        QMessageBox.information(
            self, "Check for Updates",
            "Dark-Army v1.0 \u2014 You\u2019re up to date!"
        )
