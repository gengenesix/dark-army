"""
Dark-Army — Voice Changer Server Manager
Manages the w-okada voice-changer server as a background subprocess.
Handles download, start, stop, health monitoring, and auto-restart.
"""

import sys
import os
import time
import json
import shutil
import zipfile
import tarfile
import subprocess
import threading
import requests
import platform
from pathlib import Path
from typing import Optional, Callable
from utils.logger import get_logger

logger = get_logger(__name__)

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
IS_MAC = sys.platform == "darwin"

# w-okada server release URLs
VC_SERVER_VERSION = "v.2.0.73-fix"
VC_SERVER_URLS = {
    "windows": f"https://github.com/w-okada/voice-changer/releases/download/{VC_SERVER_VERSION}/MMVCServerSIO_win_x86_64_cuda_14.1.zip",
    "linux":   f"https://github.com/w-okada/voice-changer/releases/download/{VC_SERVER_VERSION}/MMVCServerSIO_linux_x86_64_cuda_14.1.tar.gz",
    "mac":     f"https://github.com/w-okada/voice-changer/releases/download/{VC_SERVER_VERSION}/MMVCServerSIO_mac_arm64.tar.gz",
}

VC_SERVER_PORT = 18888
VC_SERVER_HOST = "127.0.0.1"
VC_SERVER_URL  = f"http://{VC_SERVER_HOST}:{VC_SERVER_PORT}"


class VCServerManager:
    """
    Manages the w-okada voice-changer server lifecycle.
    - Downloads and extracts the server binary on first run
    - Starts/stops the server as a subprocess
    - Monitors health and auto-restarts on crash
    - Emits status callbacks for the UI
    """

    def __init__(self, data_dir: str,
                 on_status: Optional[Callable[[str], None]] = None,
                 on_ready: Optional[Callable[[], None]] = None,
                 on_error: Optional[Callable[[str], None]] = None):
        self.data_dir = Path(data_dir)
        self.server_dir = self.data_dir / "vc_server"
        self.on_status = on_status or (lambda s: None)
        self.on_ready = on_ready or (lambda: None)
        self.on_error = on_error or (lambda e: None)

        self._process: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._ready = False
        self._restart_count = 0
        self.MAX_RESTARTS = 5

    # ── Public API ────────────────────────────────────────────────────────────

    def is_installed(self) -> bool:
        return self._get_server_executable() is not None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def is_ready(self) -> bool:
        return self._ready

    def start(self) -> bool:
        """Start the VC server. Returns True if started successfully."""
        if self.is_running():
            return True
        if not self.is_installed():
            self.on_error("Voice changer server not installed. Please download it first.")
            return False
        self._running = True
        self._ready = False
        self._restart_count = 0
        return self._launch_server()

    def stop(self):
        """Stop the VC server and monitoring thread."""
        self._running = False
        self._ready = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        logger.info("VC server stopped")
        self.on_status("stopped")

    def download(self, progress_cb: Optional[Callable[[int, str], None]] = None) -> bool:
        """Download and extract the VC server for the current platform."""
        platform_key = "windows" if IS_WINDOWS else ("mac" if IS_MAC else "linux")
        url = VC_SERVER_URLS.get(platform_key)
        if not url:
            self.on_error(f"No VC server available for platform: {platform_key}")
            return False

        self.server_dir.mkdir(parents=True, exist_ok=True)
        archive_name = url.split("/")[-1]
        archive_path = self.server_dir / archive_name

        try:
            logger.info(f"Downloading VC server from: {url}")
            if progress_cb:
                progress_cb(0, "Downloading voice changer server...")

            resp = requests.get(url, stream=True, timeout=60,
                                headers={"User-Agent": "DarkArmy/1.0"})
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(archive_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0 and progress_cb:
                        pct = int(downloaded * 80 / total)
                        mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        progress_cb(pct, f"Downloading: {mb:.0f} / {total_mb:.0f} MB")

            if progress_cb:
                progress_cb(82, "Extracting server...")

            # Extract
            extract_dir = self.server_dir / "bin"
            extract_dir.mkdir(exist_ok=True)

            if archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(extract_dir)
            else:
                with tarfile.open(archive_path, "r:gz") as tf:
                    tf.extractall(extract_dir)

            archive_path.unlink()  # clean up archive

            if progress_cb:
                progress_cb(100, "Voice changer server ready")

            logger.info(f"VC server extracted to: {extract_dir}")
            return True

        except Exception as e:
            logger.error(f"VC server download failed: {e}")
            self.on_error(f"Download failed: {e}")
            return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_server_executable(self) -> Optional[Path]:
        """Find the server executable in the extracted directory."""
        bin_dir = self.server_dir / "bin"
        if not bin_dir.exists():
            return None

        if IS_WINDOWS:
            patterns = ["**/*SIO*.exe", "**/*server*.exe", "**/MMVCServerSIO.exe"]
        else:
            patterns = ["**/*SIO*", "**/*server*", "**/MMVCServerSIO"]

        for pattern in patterns:
            matches = list(bin_dir.glob(pattern))
            for m in matches:
                if m.is_file() and (IS_WINDOWS or os.access(m, os.X_OK)):
                    return m

        # Make any .sh or binary executable on Linux/Mac
        if not IS_WINDOWS:
            for f in bin_dir.rglob("*"):
                if f.is_file() and not f.suffix:
                    os.chmod(f, 0o755)

        return None

    def _launch_server(self) -> bool:
        exe = self._get_server_executable()
        if not exe:
            self.on_error("VC server executable not found. Please reinstall.")
            return False

        try:
            self.on_status("starting")
            env = os.environ.copy()
            env["PORT"] = str(VC_SERVER_PORT)

            self._process = subprocess.Popen(
                [str(exe), "--port", str(VC_SERVER_PORT)],
                cwd=str(exe.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
            )
            logger.info(f"VC server started (pid={self._process.pid})")

            # Start monitor thread
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self._monitor_thread.start()

            # Wait for server to be ready (up to 30s)
            return self._wait_for_ready(timeout=30)

        except Exception as e:
            logger.error(f"Failed to launch VC server: {e}")
            self.on_error(f"Could not start voice changer server: {e}")
            return False

    def _wait_for_ready(self, timeout: int = 30) -> bool:
        """Poll the server health endpoint until it responds."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.is_running():
                self.on_error("VC server exited unexpectedly during startup")
                return False
            try:
                resp = requests.get(f"{VC_SERVER_URL}/api/hello", timeout=2)
                if resp.status_code == 200:
                    self._ready = True
                    logger.info("VC server is ready")
                    self.on_status("ready")
                    self.on_ready()
                    return True
            except Exception:
                pass
            time.sleep(1)
        self.on_error("VC server did not start within 30 seconds")
        return False

    def _monitor_loop(self):
        """Watch the server process; auto-restart on unexpected exit."""
        while self._running:
            if self._process and self._process.poll() is not None:
                exit_code = self._process.returncode
                logger.warning(f"VC server exited with code {exit_code}")
                self._ready = False
                self.on_status("crashed")

                if self._restart_count < self.MAX_RESTARTS and self._running:
                    self._restart_count += 1
                    logger.info(f"Restarting VC server (attempt {self._restart_count})")
                    self.on_status(f"restarting ({self._restart_count}/{self.MAX_RESTARTS})")
                    time.sleep(2)
                    self._launch_server()
                else:
                    self._running = False
                    self.on_error(
                        "Voice changer server crashed too many times. "
                        "Check logs and try restarting manually."
                    )
                    return
            time.sleep(2)
