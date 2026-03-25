"""
Dark-Army — Voice Model Manager
Handles downloading, listing, loading, and switching RVC/Beatrice voice models.
"""

import json
import requests
from pathlib import Path
from typing import List, Dict, Optional, Callable
from utils.logger import get_logger

logger = get_logger(__name__)

VC_SERVER_URL = "http://127.0.0.1:18888"

# Built-in preset models (publicly available RVC models)
PRESET_MODELS = [
    {
        "name": "Female (Anime)",
        "description": "Bright anime-style female voice",
        "url": "https://huggingface.co/datasets/voice-changer-models/rvc-models/resolve/main/anime_female_v2.pth",
        "filename": "anime_female_v2.pth",
    },
    {
        "name": "Female (Natural)",
        "description": "Natural-sounding female voice",
        "url": "https://huggingface.co/datasets/voice-changer-models/rvc-models/resolve/main/natural_female_v2.pth",
        "filename": "natural_female_v2.pth",
    },
    {
        "name": "Deep Male",
        "description": "Deep, resonant male voice",
        "url": "https://huggingface.co/datasets/voice-changer-models/rvc-models/resolve/main/deep_male_v2.pth",
        "filename": "deep_male_v2.pth",
    },
]


class ModelManager:
    def __init__(self, models_dir: str):
        self.models_dir = Path(models_dir) / "voice_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def list_local_models(self) -> List[Dict]:
        """Return list of locally available voice models."""
        models = []
        for f in self.models_dir.glob("*.pth"):
            models.append({"name": f.stem, "path": str(f), "size_mb": f.stat().st_size // (1024*1024)})
        for f in self.models_dir.glob("*.onnx"):
            models.append({"name": f.stem, "path": str(f), "size_mb": f.stat().st_size // (1024*1024)})
        return models

    def list_preset_models(self) -> List[Dict]:
        return PRESET_MODELS

    def download_model(self, url: str, filename: str,
                       progress_cb: Optional[Callable[[int, str], None]] = None) -> bool:
        dest = self.models_dir / filename
        if dest.exists():
            logger.info(f"Model already exists: {filename}")
            return True
        try:
            resp = requests.get(url, stream=True, timeout=60,
                                headers={"User-Agent": "DarkArmy/1.0"})
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0 and progress_cb:
                        pct = int(downloaded * 100 / total)
                        mb = downloaded / (1024*1024)
                        progress_cb(pct, f"Downloading {filename}: {mb:.0f}MB")
            logger.info(f"Model downloaded: {filename}")
            return True
        except Exception as e:
            logger.error(f"Model download failed: {e}")
            if dest.exists():
                dest.unlink()
            return False

    def load_model_on_server(self, model_path: str) -> bool:
        """Tell the VC server to load a specific model."""
        try:
            resp = requests.post(f"{VC_SERVER_URL}/api/upload_model",
                                 json={"path": model_path}, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to load model on server: {e}")
            return False

    def get_server_models(self) -> List[str]:
        """Get list of models loaded on the VC server."""
        try:
            resp = requests.get(f"{VC_SERVER_URL}/api/models", timeout=5)
            if resp.status_code == 200:
                return resp.json().get("models", [])
        except Exception:
            pass
        return []

    def delete_model(self, filename: str) -> bool:
        target = self.models_dir / filename
        if target.exists():
            target.unlink()
            return True
        return False
