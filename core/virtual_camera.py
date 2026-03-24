import sys
import cv2
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")


class VirtualCameraOutput:
    def __init__(self, device: str = '', width: int = 1280, height: int = 720, fps: int = 30):
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.available = False
        self._camera = None

    def start(self) -> bool:
        try:
            import pyvirtualcam

            if IS_WINDOWS:
                # On Windows, pyvirtualcam uses OBS Virtual Camera — no device path needed
                self._camera = pyvirtualcam.Camera(
                    width=self.width,
                    height=self.height,
                    fps=self.fps,
                    fmt=pyvirtualcam.PixelFormat.RGB,
                )
            elif IS_LINUX and self.device:
                # On Linux, use v4l2loopback with explicit device path
                self._camera = pyvirtualcam.Camera(
                    width=self.width,
                    height=self.height,
                    fps=self.fps,
                    device=self.device,
                    fmt=pyvirtualcam.PixelFormat.RGB,
                )
            else:
                # macOS or Linux without device — let pyvirtualcam pick default
                self._camera = pyvirtualcam.Camera(
                    width=self.width,
                    height=self.height,
                    fps=self.fps,
                    fmt=pyvirtualcam.PixelFormat.RGB,
                )

            self.available = True
            logger.info(f"Virtual camera started: {self.width}x{self.height}@{self.fps}")
            return True

        except ModuleNotFoundError:
            logger.warning("pyvirtualcam not installed. Virtual camera disabled.")
            self.available = False
            return False
        except Exception as e:
            err_msg = str(e)
            if IS_WINDOWS and ("obs" in err_msg.lower() or "virtual" in err_msg.lower() or "device" in err_msg.lower()):
                logger.warning(
                    "Virtual camera unavailable on Windows. "
                    "Install OBS Studio with Virtual Camera enabled to use this feature."
                )
            elif IS_LINUX and "v4l2loopback" in err_msg.lower():
                logger.warning(
                    "Virtual camera unavailable on Linux. "
                    "Run: sudo apt install v4l2loopback-dkms && sudo modprobe v4l2loopback"
                )
            else:
                logger.warning(f"Virtual camera not available: {e}. Continuing without it.")
            self.available = False
            return False

    def send_frame(self, frame: np.ndarray):
        if not self.available or self._camera is None:
            return
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if rgb.shape[1] != self.width or rgb.shape[0] != self.height:
                rgb = cv2.resize(rgb, (self.width, self.height))
            self._camera.send(rgb)
            self._camera.sleep_until_next_frame()
        except Exception as e:
            logger.warning(f"Virtual camera send error: {e}")

    def stop(self):
        if self._camera:
            try:
                self._camera.__exit__(None, None, None)
            except Exception:
                pass
            self._camera = None
        self.available = False

    def is_active(self) -> bool:
        return self.available and self._camera is not None
