"""Provider abstraction — AIProvider enum, capabilities, config (MM-1).

Odvaja provider (OpenAI/MiniMax/budući) od business logike. Kod NE smije
granati po imenu providera (`if provider == "minimax"`) — umjesto toga pita
`ProviderCapabilities` (šta provider može). Provider specifični protokoli
terminiraju u adapteru, ne cure u ToolExecutor/UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AIProvider(str, Enum):
    OPENAI = "openai"
    MINIMAX = "minimax"


@dataclass(frozen=True)
class ProviderCapabilities:
    """Šta provider STVARNO podržava — ne pretpostavlja se iz imena."""

    realtime_audio_input: bool      # mikrofon → provider, live
    realtime_audio_output: bool     # provider → zvučnik, live (jedan tok)
    streaming_text: bool            # tekst se emituje inkrementalno
    streaming_audio: bool           # TTS se emituje inkrementalno
    tool_calling: bool              # model može zatražiti alate
    interruption: bool              # barge-in / cancel odgovora
    native_vad: bool                # provider radi turn detection
    transcripts: bool               # vraća transkript korisnikovog govora


# OpenAI Realtime: pun speech-to-speech, native VAD, barge-in, transcripts.
OPENAI_CAPABILITIES = ProviderCapabilities(
    realtime_audio_input=True,
    realtime_audio_output=True,
    streaming_text=True,
    streaming_audio=True,
    tool_calling=True,
    interruption=True,
    native_vad=True,
    transcripts=True,
)

# MiniMax: NEMA native speech-to-speech (composite STT→M3→T2A, MM-0 finding).
# M3 daje streaming text + tool calling; Speech 2.8 daje streaming TTS.
MINIMAX_CAPABILITIES = ProviderCapabilities(
    realtime_audio_input=False,
    realtime_audio_output=False,
    streaming_text=True,
    streaming_audio=True,
    tool_calling=True,
    interruption=False,
    native_vad=False,
    transcripts=True,
)

CAPABILITIES: dict[AIProvider, ProviderCapabilities] = {
    AIProvider.OPENAI: OPENAI_CAPABILITIES,
    AIProvider.MINIMAX: MINIMAX_CAPABILITIES,
}


def capabilities_for(provider: AIProvider) -> ProviderCapabilities:
    return CAPABILITIES[provider]


@dataclass(frozen=True)
class ModelProviderConfig:
    """Konfiguracija jednog model/text providera (backend side)."""

    provider: AIProvider
    api_key: str | None
    model: str


def create_model_client(settings) -> "ModelClient":
    """Centralna tačka konstrukcije model clienta (MM-1/MM-3).

    Provider selection se čita iz `settings.ai_provider`; vraća
    OpenAIModelClient ili MiniMaxModelClient — pozivaoci (runtime/main) ne
    granaju po imenu providera.
    """
    from app.agent.model_client import MiniMaxModelClient, ModelClient, OpenAIModelClient

    try:
        provider = AIProvider(settings.ai_provider)
    except ValueError:
        provider = AIProvider.OPENAI

    if provider is AIProvider.MINIMAX:
        return MiniMaxModelClient(settings.minimax_api_key, settings.minimax_model)
    return OpenAIModelClient(settings.openai_api_key, settings.openai_model)
