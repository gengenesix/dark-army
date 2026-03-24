import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ── Platform-appropriate data directory ──
def _get_base_dir() -> Path:
    if sys.platform == "win32":
        # Use %APPDATA%\Echelon on Windows (e.g. C:\Users\username\AppData\Roaming\Echelon)
        appdata = os.environ.get("APPDATA", str(Path.home()))
        return Path(appdata) / "Echelon"
    else:
        # Use ~/.echelon on Linux/macOS
        return Path.home() / ".echelon"

BASE_DIR = _get_base_dir()
CONFIG_PATH = BASE_DIR / "data" / "config.json"

def _default_virtual_camera_device() -> str:
    """Default virtual camera device path — platform-aware."""
    if sys.platform == "win32":
        return ""  # OBS Virtual Camera on Windows, no device path needed
    return "/dev/video10"  # v4l2loopback on Linux

@dataclass
class AppConfig:
    performance_mode: str = "balanced"
    camera_device_id: int = 0
    virtual_camera_device: str = field(default_factory=_default_virtual_camera_device)
    output_width: int = 1280
    output_height: int = 720
    output_fps: int = 30
    active_source_face_path: str = ""
    window_x: int = 100
    window_y: int = 100
    window_width: int = 1100
    window_height: int = 700
    launch_on_login: bool = False
    start_minimized: bool = False
    log_level: str = "INFO"
    first_launch: bool = True
    models_dir: str = ""
    data_dir: str = ""
    frame_skip: int = 1
    face_detect_interval: int = 5
    auto_tune: bool = False
    bg_blur: str = "off"
    target_face_mode: str = "largest"
    presets: list = field(default_factory=list)

class ConfigManager:
    def __init__(self):
        self.config_path = CONFIG_PATH
        self._ensure_dirs()

    def _ensure_dirs(self):
        dirs = [
            BASE_DIR / "data",
            BASE_DIR / "data" / "faces",
            BASE_DIR / "models",
            BASE_DIR / "logs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppConfig:
        self._ensure_dirs()
        config = AppConfig()
        config.models_dir = str(BASE_DIR / "models")
        config.data_dir = str(BASE_DIR / "data")
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            except Exception:
                pass
        if not config.models_dir:
            config.models_dir = str(BASE_DIR / "models")
        if not config.data_dir:
            config.data_dir = str(BASE_DIR / "data")
        return config

    def save(self, config: AppConfig):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=2)

    def reset(self) -> AppConfig:
        if self.config_path.exists():
            self.config_path.unlink()
        return self.load()
