"""Audio validation. The browser sends 16 kHz mono PCM WAV (converted client-side from MediaRecorder).
Anything else is converted with ffmpeg only if it is installed; otherwise it is rejected clearly."""
from __future__ import annotations

import array
import io
import shutil
import subprocess
import wave
from dataclasses import dataclass


class AudioError(Exception):
    """Raised with a message that is safe to show to the user."""

    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class AudioInfo:
    wav: bytes
    duration_s: float
    sample_rate: int
    rms: float


def _is_wav(data: bytes) -> bool:
    return len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def _convert_with_ffmpeg(data: bytes) -> bytes:
    if not shutil.which("ffmpeg"):
        raise AudioError("Unsupported audio format. Send 16 kHz mono WAV audio.", 415)
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"],
        input=data, capture_output=True, timeout=30,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise AudioError("The audio could not be decoded. Please record again.", 422)
    return proc.stdout


def validate_audio(data: bytes, max_seconds: int, max_bytes: int = 4 * 1024 * 1024) -> AudioInfo:
    if not data:
        raise AudioError("No audio received. Please record again.")
    if len(data) > max_bytes:
        raise AudioError("The audio file is too large.", 413)
    if not _is_wav(data):
        data = _convert_with_ffmpeg(data)
    try:
        with wave.open(io.BytesIO(data)) as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            pcm = w.readframes(frames)
    except (wave.Error, EOFError):
        raise AudioError("The audio could not be read. Please record again.")
    if width != 2 or channels != 1:
        raise AudioError("Audio must be 16-bit mono WAV.", 415)
    if rate < 8000:
        raise AudioError("Audio sample rate is too low.", 415)
    duration = frames / rate if rate else 0.0
    if duration < 0.3:
        raise AudioError("That recording was too short. Hold the button and speak.")
    if duration > max_seconds + 0.5:
        raise AudioError(f"Recordings can be at most {max_seconds} seconds.")
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) - (len(pcm) % 2)])
    rms = (sum(s * s for s in samples) / max(1, len(samples))) ** 0.5
    return AudioInfo(wav=data, duration_s=duration, sample_rate=rate, rms=rms)


SILENCE_RMS = 40.0  # int16 scale; below this the recording is effectively silent
