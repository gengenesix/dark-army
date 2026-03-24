import sys
import cv2
import queue
import threading
import time
from typing import Optional, List, Dict
from utils.logger import get_logger

logger = get_logger(__name__)

IS_WINDOWS = sys.platform == "win32"


class CameraCapture:
    def __init__(self, device_id: int = 0, width: int = 1280, height: int = 720, fps: int = 30):
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        self._cap = None
        self._queue = queue.Queue(maxsize=1)
        self._running = False
        self._thread = None

    def start(self) -> bool:
        try:
            if IS_WINDOWS:
                # Use DirectShow backend on Windows for better camera compatibility
                self._cap = cv2.VideoCapture(self.device_id, cv2.CAP_DSHOW)
            else:
                self._cap = cv2.VideoCapture(self.device_id)
            if not self._cap.isOpened():
                logger.error(f"Cannot open camera {self.device_id}")
                return False
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cap.set(cv2.CAP_PROP_FPS, self.fps)
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            logger.info(f"Camera {self.device_id} started")
            return True
        except Exception as e:
            logger.error(f"Camera start error: {e}")
            return False

    def _capture_loop(self):
        while self._running:
            if self._cap is None:
                break
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(frame)
            except queue.Full:
                pass

    def get_frame(self) -> Optional[cv2.Mat]:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info("Camera stopped")

    def list_cameras(self) -> List[Dict]:
        """Enumerate available cameras — platform-aware."""
        cameras = []

        if IS_WINDOWS:
            # Use DirectShow on Windows — probe indices 0..7
            for i in range(8):
                try:
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        cameras.append({"id": i, "name": f"Camera {i}"})
                        cap.release()
                except Exception:
                    pass
            return cameras if cameras else [{"id": 0, "name": "Default Camera"}]

        # Linux/macOS: try fast path via /dev/video* first
        import glob
        video_devs = sorted(glob.glob("/dev/video*"))
        if video_devs:
            for dev in video_devs[:8]:
                try:
                    idx = int(dev.replace("/dev/video", ""))
                    cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
                    if cap.isOpened():
                        cameras.append({"id": idx, "name": f"Camera {idx} ({dev})"})
                        cap.release()
                except Exception:
                    pass
            return cameras if cameras else [{"id": 0, "name": "Default Camera"}]

        # Fallback: probe first 4 indices
        for i in range(4):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    cameras.append({"id": i, "name": f"Camera {i}"})
                    cap.release()
            except Exception:
                pass
        return cameras if cameras else [{"id": 0, "name": "Default Camera"}]
