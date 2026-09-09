"""Testovi za VoiceState model i mapiranje u vizuelna orb stanja (QM-2)."""

from desktop.ui.voice_state import (
    ORB_STATE_ERROR,
    ORB_STATE_IDLE,
    ORB_STATE_LISTENING,
    ORB_STATE_MUTED,
    ORB_STATE_SPEAKING,
    ORB_STATE_THINKING,
    ORB_STATE_WARNING,
    is_valid_voice_state,
    map_voice_state_to_orb_state,
)


def test_listening_and_transcribing_map_to_listening():
    assert map_voice_state_to_orb_state("listening") == ORB_STATE_LISTENING
    assert map_voice_state_to_orb_state("transcribing") == ORB_STATE_LISTENING


def test_confirmation_and_interrupted_map_to_warning():
    assert map_voice_state_to_orb_state("waiting_confirmation") == ORB_STATE_WARNING
    assert map_voice_state_to_orb_state("interrupted") == ORB_STATE_WARNING


def test_single_states_map_one_to_one():
    assert map_voice_state_to_orb_state("thinking") == ORB_STATE_THINKING
    assert map_voice_state_to_orb_state("speaking") == ORB_STATE_SPEAKING
    assert map_voice_state_to_orb_state("error") == ORB_STATE_ERROR
    assert map_voice_state_to_orb_state("muted") == ORB_STATE_MUTED


def test_unknown_defaults_to_idle():
    assert map_voice_state_to_orb_state("idle") == ORB_STATE_IDLE
    assert map_voice_state_to_orb_state("garbage") == ORB_STATE_IDLE


def test_is_valid_voice_state():
    assert is_valid_voice_state("idle")
    assert is_valid_voice_state("transcribing")
    assert not is_valid_voice_state("garbage")
    assert not is_valid_voice_state("")
