"""
Dark-Army — Voice Changer Server Manager
Runs voice conversion using rvc-python (pure Python, no external server needed).
This replaces the w-okada server approach since their releases are not publicly available.

Architecture:
  - Uses rvc-python library for RVC voice conversion
  - Runs as an in-process thread (no subprocess, no port)
  - Input audio → RVC model → output audio
  - Falls back gracefully if rvc-python not installed
"""

import sys
import time
import threading
import numpy as np
from pathlib import Path
from typing import Optional, Callable
from utils.logger import get_logger

logger = get_logger(__name__)

IS_WINDOWS = sys.platform == "win32"
IS_LINUX   = sys.platform.startswith("linux")
IS_MAC     = sys.platform == "darwin"


class VCServerManager:
    """
    Manages voice conversion using rvc-python (in-process, no external server).
    Provides same interface as the old server-based approach.
    """

    def __init__(self, data_dir: str,
                 on_status: Optional[Callable[[str], None]] = None,
                 on_ready: Optional[Callable[[], None]] = None,
                 on_error: Optional[Callable[[str], None]] = None):
        self.data_dir = Path(data_dir)
        self.models_dir = self.data_dir / "voice_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.on_status = on_status or (lambda s: None)
        self.on_ready  = on_ready  or (lambda: None)
        self.on_error  = on_error  or (lambda e: None)

        self._rvc = None
        self._ready = False
        self._running = False
        self._current_model = ""

        # Voice conversion parameters
        self.pitch_shift = 0
        self.f0_method   = "rmvpe"
        self.index_rate  = 0.5

    # ── Public API ────────────────────────────────────────────────────────────

    def is_installed(self) -> bool:
        """Check if rvc-python is available."""
        try:
            import rvc_python  # noqa
            return True
        except ImportError:
            return False

    def is_running(self) -> bool:
        return self._running

    def is_ready(self) -> bool:
        return self._ready

    def start(self) -> bool:
        """Initialize the RVC engine."""
        if self._running:
            return True

        if not self.is_installed():
            self.on_error(
                "Voice changer requires rvc-python.\n"
                "Install it with:\n  pip install rvc-python\n\n"
                "Then restart Dark-Army."
            )
            return False

        self.on_status("starting")
        try:
            from rvc_python.infer import RVCInference
            self._rvc = RVCInference(device="cuda:0" if self._has_cuda() else "cpu")
            self._running = True
            self._ready = True
            logger.info("RVC engine initialized")
            self.on_status("ready")
            self.on_ready()
            return True
        except Exception as e:
            logger.error(f"RVC init failed: {e}")
            self.on_error(f"Voice changer failed to start: {e}\n\nMake sure rvc-python is installed.")
            return False

    def stop(self):
        """Stop the RVC engine."""
        self._running = False
        self._ready   = False
        self._rvc     = None
        self.on_status("stopped")
        logger.info("RVC engine stopped")

    def convert_audio(self, audio: np.ndarray, sample_rate: int = 48000) -> np.ndarray:
        """
        Convert audio chunk using the loaded RVC model.
        Returns original audio if model not loaded or conversion fails.
        """
        if not self._ready or self._rvc is None or not self._current_model:
            return audio
        try:
            result = self._rvc.infer_audio(
                audio,
                pitch=self.pitch_shift,
                f0method=self.f0_method,
                index_rate=self.index_rate,
            )
            return result
        except Exception as e:
            logger.debug(f"Audio conversion error: {e}")
            return audio

    def load_model(self, model_path: str) -> bool:
        """Load an RVC model file."""
        if not self._rvc:
            return False
        try:
            self._rvc.load_model(model_path)
            self._current_model = model_path
            logger.info(f"Loaded RVC model: {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            self.on_error(f"Could not load voice model: {Path(model_path).name}\n{e}")
            return False

    def download(self, progress_cb: Optional[Callable[[int, str], None]] = None) -> bool:
        """
        'Download' for rvc-python = pip install rvc-python.
        Guides the user since we can't pip install in a packaged app easily.
        """
        if self.is_installed():
            if progress_cb:
                progress_cb(100, "rvc-python already installed")
            return True

        # In packaged app, we can try pip install
        if progress_cb:
            progress_cb(10, "Installing rvc-python...")
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "rvc-python", "--quiet"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                if progress_cb:
                    progress_cb(100, "rvc-python installed successfully")
                return True
            else:
                if progress_cb:
                    progress_cb(0, f"Install failed: {result.stderr[:100]}")
                return False
        except Exception as e:
            if progress_cb:
                progress_cb(0, f"Install error: {e}")
            return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _has_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            pass
        try:
            import onnxruntime as ort
            return "CUDAExecutionProvider" in ort.get_available_providers()
        except Exception:
            pass
        return False
