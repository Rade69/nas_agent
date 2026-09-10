"""desktop/voice/audio.py — audio level iz PCM streama (OA-3, priprema u OA-1).

Računa glasnoću (RMS 0..1) iz ISTOG PCM16 input chunk-a koji ide OpenAI-ju —
bez drugog microphone capture-a (INV-6). Smoothing: brz attack, spor release,
da orb ne pada mehanički na nulu između slogova.
"""

from __future__ import annotations

import array
import math


def rms_level(pcm: bytes) -> float:
    """RMS nivo PCM16 mono chunka, normalizovan 0..1."""
    if not pcm or len(pcm) < 2:
        return 0.0
    samples = array.array("h")
    samples.frombytes(pcm[: (len(pcm) // 2) * 2])
    n = len(samples)
    if n == 0:
        return 0.0
    sum_sq = sum(s * s for s in samples)
    rms = math.sqrt(sum_sq / n)
    # Perceptual shaping: korijen tlači male nivoe, ali zadržava raspon 0..1.
    return max(0.0, min(1.0, math.sqrt(rms / 32768.0)))


class AudioLevelTracker:
    """Attack/release smoothing nad uzastopnim RMS nivoima."""

    def __init__(self, attack: float = 0.5, release: float = 0.06) -> None:
        self.attack = attack
        self.release = release
        self._level = 0.0

    def update(self, level: float) -> float:
        alpha = self.attack if level > self._level else self.release
        self._level = alpha * level + (1.0 - alpha) * self._level
        return self._level

    def reset(self) -> None:
        self._level = 0.0

    @property
    def level(self) -> float:
        return self._level
