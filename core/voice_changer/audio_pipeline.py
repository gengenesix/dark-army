"""
Dark-Army — Real-time Audio Pipeline
Captures mic audio → converts via RVC → outputs to virtual mic device.
Uses sounddevice for cross-platform audio I/O.
"""

import sys
import queue
import threading
import numpy as np
from typing import Optional, Callable
from utils.logger import get_logger

logger = get_logger(__name__)

SAMPLE_RATE   = 48000
CHUNK_SAMPLES = 4096   # ~85ms at 48kHz — good balance of latency vs quality
CHANNELS      = 1
DTYPE_NP      = np.int16
DTYPE_SD      = "float32"


class AudioPipeline:
    """
    Real-time audio pipeline:
      sounddevice mic input → RVC conversion → sounddevice output
    """

    def __init__(self,
                 vc_server=None,
                 input_device:  Optional[int] = None,
                 output_device: Optional[int] = None,
                 on_latency: Optional[Callable[[float], None]] = None,
                 on_status:  Optional[Callable[[str],  None]] = None,
                 on_error:   Optional[Callable[[str],  None]] = None):
        self.vc_server      = vc_server
        self.input_device   = input_device
        self.output_device  = output_device
        self.on_latency     = on_latency or (lambda l: None)
        self.on_status      = on_status  or (lambda s: None)
        self.on_error       = on_error   or (lambda e: None)

        self._running       = False
        self._input_stream  = None
        self._output_stream = None
        self._out_queue: queue.Queue = queue.Queue(maxsize=16)

        # Settings
        self.pitch_shift        = 0
        self.noise_suppression  = True
        self.enabled            = True   # if False, pass audio through unchanged

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> bool:
        try:
            import sounddevice as sd
        except ImportError:
            self.on_error(
                "sounddevice not installed.\n"
                "Run: pip install sounddevice\nThen restart Dark-Army."
            )
            return False

        if self._running:
            return True

        try:
            self._running = True
            self._start_input_stream()
            self._start_output_stream()
            self.on_status("active")
            logger.info("Audio pipeline started")
            return True
        except Exception as e:
            logger.error(f"Audio pipeline start failed: {e}", exc_info=True)
            self.on_error(f"Audio error: {e}")
            self.stop()
            return False

    def stop(self):
        self._running = False
        for stream in [self._input_stream, self._output_stream]:
            if stream:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass
        self._input_stream  = None
        self._output_stream = None
        # drain queue
        while not self._out_queue.empty():
            try: self._out_queue.get_nowait()
            except queue.Empty: break
        self.on_status("stopped")
        logger.info("Audio pipeline stopped")

    def set_pitch(self, semitones: int):
        self.pitch_shift = semitones
        if self.vc_server:
            self.vc_server.pitch_shift = semitones

    def set_noise_suppression(self, enabled: bool):
        self.noise_suppression = enabled

    def list_audio_devices(self) -> dict:
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            inputs, outputs = [], []
            for i, d in enumerate(devices):
                if d["max_input_channels"]  > 0: inputs.append( {"id": i, "name": d["name"]})
                if d["max_output_channels"] > 0: outputs.append({"id": i, "name": d["name"]})
            return {"inputs": inputs, "outputs": outputs}
        except Exception as e:
            logger.error(f"list_audio_devices: {e}")
            return {"inputs": [], "outputs": []}

    # ── Internal ──────────────────────────────────────────────────────────────

    def _start_input_stream(self):
        import sounddevice as sd
        import time

        def callback(indata, frames, time_info, status):
            if not self._running:
                return
            raw = indata[:, 0].copy()  # mono float32 [-1, 1]

            t0 = time.perf_counter()

            # Optional noise gate (simple RMS threshold)
            if self.noise_suppression:
                rms = float(np.sqrt(np.mean(raw ** 2)))
                if rms < 0.003:  # silence threshold
                    raw = np.zeros_like(raw)

            # Voice conversion
            if self.enabled and self.vc_server and self.vc_server.is_ready():
                int16 = (raw * 32767).astype(DTYPE_NP)
                converted = self.vc_server.convert_audio(int16, SAMPLE_RATE)
                raw = converted.astype("float32") / 32767.0

            latency_ms = (time.perf_counter() - t0) * 1000
            self.on_latency(latency_ms)

            try:
                self._out_queue.put_nowait(raw.copy())
            except queue.Full:
                try:
                    self._out_queue.get_nowait()
                    self._out_queue.put_nowait(raw.copy())
                except queue.Empty:
                    pass

        self._input_stream = sd.InputStream(
            device=self.input_device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=CHUNK_SAMPLES,
            dtype=DTYPE_SD,
            callback=callback,
            latency="low",
        )
        self._input_stream.start()

    def _start_output_stream(self):
        import sounddevice as sd

        def callback(outdata, frames, time_info, status):
            try:
                audio = self._out_queue.get_nowait()
                if len(audio) < frames:
                    audio = np.pad(audio, (0, frames - len(audio)))
                elif len(audio) > frames:
                    audio = audio[:frames]
                outdata[:, 0] = audio
            except queue.Empty:
                outdata.fill(0)

        self._output_stream = sd.OutputStream(
            device=self.output_device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=CHUNK_SAMPLES,
            dtype=DTYPE_SD,
            callback=callback,
            latency="low",
        )
        self._output_stream.start()
