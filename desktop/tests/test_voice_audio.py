"""Testovi za audio level iz PCM-a (OA-3 priprema)."""

import array
import math

from desktop.voice.audio import AudioLevelTracker, rms_level


def _pcm(samples):
    a = array.array("h", samples)
    return a.tobytes()


def test_rms_silence_is_zero():
    assert rms_level(_pcm([0] * 480)) == 0.0


def test_rms_empty_is_zero():
    assert rms_level(b"") == 0.0


def test_rms_normal_speech_is_positive():
    level = rms_level(_pcm([8000] * 480))
    assert 0.0 < level <= 1.0


def test_rms_clipping_capped_at_one():
    level = rms_level(_pcm([32767] * 480))
    assert level <= 1.0
    assert level > 0.9


def test_audio_level_tracker_fast_attack_slow_release():
    tracker = AudioLevelTracker(attack=0.5, release=0.06)
    # brz skok na govor
    up = tracker.update(0.8)
    assert up > 0.3
    # spor pad na tišinu
    down = tracker.update(0.0)
    assert down > 0.0  # ne pada odmah na nulu
    assert down < 0.8
