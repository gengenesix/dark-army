import collections
import cv2
import numpy as np
import time
from dataclasses import dataclass
from typing import List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class DetectedFace:
    bbox: np.ndarray
    landmarks: np.ndarray
    embedding: np.ndarray
    confidence: float
    age: int
    gender: str

class FaceDetector:
    def __init__(self, models_dir: str, providers: list):
        self.app = None
        self.models_dir = models_dir
        self.providers = providers
        self.is_loaded = False
        self._last_face = None
        self._detect_interval = 5
        self._frame_count_tracked = 0
        self._landmark_buffer = collections.deque(maxlen=3)
        self._last_faces = None
        self._frame_count_tracked_multi = 0

    def load(self) -> bool:
        try:
            import insightface
            from pathlib import Path
            t0 = time.time()

            # Ensure models dir exists
            models_path = Path(self.models_dir)
            models_path.mkdir(parents=True, exist_ok=True)
            buffalo_path = models_path / "models" / "buffalo_l"

            logger.info(f"FaceDetector: models_dir={self.models_dir}")
            logger.info(f"FaceDetector: buffalo_l path={buffalo_path}")
            logger.info(f"FaceDetector: buffalo_l exists={buffalo_path.exists()}")
            if buffalo_path.exists():
                onnx_files = list(buffalo_path.glob("*.onnx"))
                logger.info(f"FaceDetector: buffalo_l onnx files={[f.name for f in onnx_files]}")

            self.app = insightface.app.FaceAnalysis(
                name='buffalo_l',
                root=str(models_path),
                providers=self.providers
            )
            ctx_id = 0 if any("CUDA" in p for p in self.providers) else -1
            self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))
            self.is_loaded = True
            logger.info(f"FaceDetector loaded in {time.time()-t0:.2f}s")
            return True
        except Exception as e:
            logger.error(f"FaceDetector load failed: {e}", exc_info=True)
            return False

    def detect_faces(self, frame: np.ndarray) -> List[DetectedFace]:
        if not self.is_loaded or frame is None:
            return []
        try:
            faces = self.app.get(frame)
            result = []
            for f in faces:
                embedding = f.embedding if hasattr(f, 'embedding') and f.embedding is not None else np.zeros(512)
                det_score = float(f.det_score) if hasattr(f, 'det_score') else 0.0
                age = int(f.age) if hasattr(f, 'age') and f.age is not None else 0
                gender = "M" if hasattr(f, 'gender') and f.gender == 1 else "F"
                landmarks = f.kps if hasattr(f, 'kps') and f.kps is not None else np.zeros((5, 2))
                result.append(DetectedFace(
                    bbox=f.bbox,
                    landmarks=landmarks,
                    embedding=embedding,
                    confidence=det_score,
                    age=age,
                    gender=gender
                ))
            return sorted(result, key=lambda x: x.confidence, reverse=True)
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []

    def get_primary_face(self, frame: np.ndarray) -> Optional[DetectedFace]:
        faces = self.detect_faces(frame)
        if not faces:
            return None
        # Return largest face by bbox area
        def area(f):
            b = f.bbox
            return (b[2]-b[0]) * (b[3]-b[1])
        return max(faces, key=area)

    def get_tracked_face(self, frame: np.ndarray) -> Optional[DetectedFace]:
        """Cached face detection with landmark smoothing to reduce jitter."""
        self._frame_count_tracked += 1
        if self._frame_count_tracked % self._detect_interval == 0 or self._last_face is None:
            face = self.get_primary_face(frame)
            if face is not None:
                self._landmark_buffer.append(face.landmarks.copy())
                if len(self._landmark_buffer) > 1:
                    smoothed = np.mean(list(self._landmark_buffer), axis=0)
                    face = DetectedFace(
                        bbox=face.bbox,
                        landmarks=smoothed,
                        embedding=face.embedding,
                        confidence=face.confidence,
                        age=face.age,
                        gender=face.gender,
                    )
            self._last_face = face
        return self._last_face

    def get_tracked_faces(self, frame: np.ndarray) -> List[DetectedFace]:
        """Cached multi-face detection — only re-detects every _detect_interval frames."""
        self._frame_count_tracked_multi += 1
        if self._frame_count_tracked_multi % self._detect_interval == 0 or self._last_faces is None:
            self._last_faces = self.detect_faces(frame)
        return self._last_faces

    def reset_tracking(self):
        """Reset tracking state — call when scene changes dramatically."""
        self._last_face = None
        self._frame_count_tracked = 0
        self._landmark_buffer.clear()
        self._last_faces = None
        self._frame_count_tracked_multi = 0

    def extract_face_from_image(self, image_path: str) -> Optional[DetectedFace]:
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            return self.get_primary_face(img)
        except Exception as e:
            logger.error(f"extract_face_from_image error: {e}")
            return None
