"""
Dark-Army — Real-time Audio Pipeline
Captures mic audio → streams to VC server → outputs converted audio.
Uses sounddevice for cross-platform audio I/O.
Target latency: <400ms on GPU, <800ms on CPU.
"""

import sys
import time
import queue
import threading
import numpy as np
import socketio
from typing import Optional, Callable
from utils.logger import get_logger

logger = get_logger(__name__)

VC_SERVER_URL = "http://127.0.0.1:18888"

# Audio settings
SAMPLE_RATE    = 48000   # Hz — standard for voice
CHUNK_SAMPLES  = 2048    # ~42ms chunks at 48kHz (good latency/quality tradeoff)
CHANNELS       = 1       # Mono mic input
DTYPE          = np.int16


class AudioPipeline:
    """
    Real-time audio pipeline:
    Mic → sounddevice capture → Socket.IO to VC server → processed audio → output device
    """

    def __init__(self,
                 input_device: Optional[int] = None,
                 output_device: Optional[int] = None,
                 on_latency: Optional[Callable[[float], None]] = None,
                 on_status: Optional[Callable[[str], None]] = None,
                 on_error: Optional[Callable[[str], None]] = None):
        self.input_device = input_device
        self.output_device = output_device
        self.on_latency = on_latency or (lambda l: None)
        self.on_status = on_status or (lambda s: None)
        self.on_error = on_error or (lambda e: None)

        self._sio: Optional[socketio.Client] = None
        self._running = False
        self._input_stream = None
        self._output_stream = None
        self._output_queue: queue.Queue = queue.Queue(maxsize=20)
        self._send_timestamps: dict = {}
        self._chunk_id = 0

        # VC settings (applied to server)
        self.pitch_shift = 0      # semitones
        self.voice_model = ""     # model name
        self.noise_suppression = True
        self.f0_method = "rmvpe"  # best quality F0 detection

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> bool:
        try:
            import sounddevice as sd
        except ImportError:
            self.on_error("sounddevice not installed. Run: pip install sounddevice")
            return False

        if self._running:
            return True

        try:
            self._running = True
            self._connect_socket()
            self._start_input_stream()
            self._start_output_stream()
            self.on_status("active")
            logger.info("Audio pipeline started")
            return True
        except Exception as e:
            logger.error(f"Audio pipeline start failed: {e}", exc_info=True)
            self.on_error(f"Audio pipeline error: {e}")
            self.stop()
            return False

    def stop(self):
        self._running = False
        if self._input_stream:
            try:
                self._input_stream.stop()
                self._input_stream.close()
            except Exception:
                pass
            self._input_stream = None
        if self._output_stream:
            try:
                self._output_stream.stop()
                self._output_stream.close()
            except Exception:
                pass
            self._output_stream = None
        if self._sio and self._sio.connected:
            try:
                self._sio.disconnect()
            except Exception:
                pass
        self._sio = None
        self.on_status("stopped")
        logger.info("Audio pipeline stopped")

    def set_pitch(self, semitones: int):
        self.pitch_shift = semitones
        self._update_server_settings()

    def set_model(self, model_name: str):
        self.voice_model = model_name
        self._update_server_settings()

    def set_noise_suppression(self, enabled: bool):
        self.noise_suppression = enabled
        self._update_server_settings()

    def list_audio_devices(self) -> dict:
        """Return dict of input/output audio devices."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            inputs = []
            outputs = []
            for i, d in enumerate(devices):
                if d["max_input_channels"] > 0:
                    inputs.append({"id": i, "name": d["name"]})
                if d["max_output_channels"] > 0:
                    outputs.append({"id": i, "name": d["name"]})
            return {"inputs": inputs, "outputs": outputs}
        except Exception as e:
            logger.error(f"Failed to list audio devices: {e}")
            return {"inputs": [], "outputs": []}

    # ── Internal ──────────────────────────────────────────────────────────────

    def _connect_socket(self):
        """Connect to VC server via Socket.IO."""
        self._sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=10,
            reconnection_delay=1,
        )

        @self._sio.on("response")
        def on_response(data):
            """Receive converted audio chunk from server."""
            try:
                chunk_id = data.get("id", -1)
                audio_bytes = data.get("audio", b"")
                if not audio_bytes:
                    return

                # Measure latency
                if chunk_id in self._send_timestamps:
                    latency_ms = (time.perf_counter() - self._send_timestamps.pop(chunk_id)) * 1000
                    self.on_latency(latency_ms)

                # Queue for playback
                audio = np.frombuffer(audio_bytes, dtype=DTYPE)
                try:
                    self._output_queue.put_nowait(audio)
                except queue.Full:
                    # Drop oldest frame to keep latency low
                    try:
                        self._output_queue.get_nowait()
                        self._output_queue.put_nowait(audio)
                    except queue.Empty:
                        pass
            except Exception as e:
                logger.warning(f"Audio response error: {e}")

        @self._sio.on("connect")
        def on_connect():
            logger.info("Socket.IO connected to VC server")
            self._update_server_settings()

        @self._sio.on("disconnect")
        def on_disconnect():
            logger.warning("Socket.IO disconnected from VC server")
            if self._running:
                self.on_status("reconnecting")

        self._sio.connect(VC_SERVER_URL, transports=["websocket"])

    def _start_input_stream(self):
        """Start mic capture with callback."""
        import sounddevice as sd

        def input_callback(indata, frames, time_info, status):
            if not self._running or self._sio is None:
                return
            audio = indata[:, 0].copy()  # mono
            audio_int16 = (audio * 32767).astype(DTYPE)
            self._send_chunk(audio_int16)

        self._input_stream = sd.InputStream(
            device=self.input_device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=CHUNK_SAMPLES,
            dtype="float32",
            callback=input_callback,
        )
        self._input_stream.start()

    def _start_output_stream(self):
        """Start audio output with callback."""
        import sounddevice as sd

        def output_callback(outdata, frames, time_info, status):
            try:
                audio = self._output_queue.get_nowait()
                # Resample if needed
                if len(audio) < frames:
                    audio = np.pad(audio, (0, frames - len(audio)))
                elif len(audio) > frames:
                    audio = audio[:frames]
                outdata[:, 0] = audio.astype("float32") / 32767.0
            except queue.Empty:
                outdata.fill(0)  # silence if no audio ready

        self._output_stream = sd.OutputStream(
            device=self.output_device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=CHUNK_SAMPLES,
            dtype="float32",
            callback=output_callback,
        )
        self._output_stream.start()

    def _send_chunk(self, audio: np.ndarray):
        """Send audio chunk to VC server."""
        if self._sio is None or not self._sio.connected:
            return
        try:
            chunk_id = self._chunk_id
            self._chunk_id += 1
            self._send_timestamps[chunk_id] = time.perf_counter()

            # Keep timestamp dict from growing unbounded
            if len(self._send_timestamps) > 100:
                oldest = min(self._send_timestamps.keys())
                del self._send_timestamps[oldest]

            self._sio.emit("request", {
                "id": chunk_id,
                "audio": audio.tobytes(),
                "sampleRate": SAMPLE_RATE,
                "channels": CHANNELS,
            })
        except Exception as e:
            logger.debug(f"Send chunk error: {e}")

    def _update_server_settings(self):
        """Push current settings to the VC server."""
        if self._sio is None or not self._sio.connected:
            return
        try:
            import requests as req
            req.post(f"{VC_SERVER_URL}/api/settings", json={
                "pitchShift": self.pitch_shift,
                "noiseSuppression": self.noise_suppression,
                "f0Method": self.f0_method,
            }, timeout=2)
        except Exception:
            pass
