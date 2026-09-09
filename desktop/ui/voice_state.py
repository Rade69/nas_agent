"""VoiceState model — port iz src/lib/voiceState.ts (kanonski lifecycle).

Definiše 9 glasovnih stanja (idle→listening→thinking→speaking) i mapiranje u 7
grubijih vizuelnih orb stanja (port `mapVoiceStateToOrbState` iz RickyOrb.tsx).
Nezavisno od UI sloja — koriste ga orb (QM-2), glavni UI (QM-4) i glasovna
integracija (QM-3), pa je izdvojeno u zaseban modul bez Qt zavisnosti.
"""

from __future__ import annotations

from enum import Enum


class VoiceState(str, Enum):
    """Kanonska glasovna stanja (vrijednosti identične voiceState.ts)."""

    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    WAITING_CONFIRMATION = "waiting_confirmation"
    INTERRUPTED = "interrupted"
    MUTED = "muted"
    ERROR = "error"


# Vizuelna orb stanja (7) — grublje od VoiceState, isto kao RickyOrbState.
ORB_STATE_IDLE = "idle"
ORB_STATE_LISTENING = "listening"
ORB_STATE_THINKING = "thinking"
ORB_STATE_SPEAKING = "speaking"
ORB_STATE_WARNING = "warning"
ORB_STATE_ERROR = "error"
ORB_STATE_MUTED = "muted"

ORB_STATES = frozenset(
    {
        ORB_STATE_IDLE,
        ORB_STATE_LISTENING,
        ORB_STATE_THINKING,
        ORB_STATE_SPEAKING,
        ORB_STATE_WARNING,
        ORB_STATE_ERROR,
        ORB_STATE_MUTED,
    }
)


def is_valid_voice_state(value: str) -> bool:
    return value in {s.value for s in VoiceState}


def map_voice_state_to_orb_state(voice_state: str) -> str:
    """Port mapVoiceStateToOrbState (RickyOrb.tsx) — orb ne odlučuje sam o svom
    stanju, ovo je jedini izvor istine za mapiranje."""
    if voice_state in (VoiceState.LISTENING.value, VoiceState.TRANSCRIBING.value):
        return ORB_STATE_LISTENING
    if voice_state == VoiceState.THINKING.value:
        return ORB_STATE_THINKING
    if voice_state == VoiceState.SPEAKING.value:
        return ORB_STATE_SPEAKING
    if voice_state in (VoiceState.WAITING_CONFIRMATION.value, VoiceState.INTERRUPTED.value):
        return ORB_STATE_WARNING
    if voice_state == VoiceState.ERROR.value:
        return ORB_STATE_ERROR
    if voice_state == VoiceState.MUTED.value:
        return ORB_STATE_MUTED
    return ORB_STATE_IDLE
