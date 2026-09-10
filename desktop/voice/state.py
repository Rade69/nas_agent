"""desktop/voice/state.py — reconnect state mašina i politika (OA-1).

Čista logika bez I/O: klasifikacija grešaka, exponential backoff, i tranzicije
stanja konekcije. Odvojena od WebSocket-a da se može jedinično testirati.
Razlikuje user-requested shutdown od network/auth/fatal failure — auth se NE
retry-uje kao Wi-Fi prekid.
"""

from __future__ import annotations

from enum import Enum


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    STOPPING = "stopping"
    FAILED = "failed"


class ErrorClass(str, Enum):
    """Klasa greške — određuje da li se i kako retry-uje."""

    MANUAL_DISCONNECT = "manual_disconnect"
    AUTH = "auth"          # invalid key / 401 / InvalidStatus — ne retry-ovati
    FATAL = "fatal"        # nepopravljiv protokol/konfiguracioni problem
    NETWORK = "network"    # socket drop / DNS / timeout — retry-able
    RATE_LIMIT = "rate_limit"  # retry-able sa server delay-om
    UNKNOWN = "unknown"


DEFAULT_BACKOFF = (2.0, 4.0, 8.0)
DEFAULT_MAX_ATTEMPTS = 3

# Websocket/httpx klasifikacija — ključ po tipu izuzetka ili substringu poruke.
_AUTH_MARKERS = ("InvalidStatus", "401", "auth", "api key", "credential")
_FATAL_MARKERS = ("protocol", "bad request", "400", "404")
_NETWORK_MARKERS = (
    "ConnectionClosed",
    "ConnectionError",
    "TimeoutError",
    "timeout",
    "getaddrinfo",
    "Errno 11001",
    "ENOTFOUND",
    "EAI_AGAIN",
    "fetch failed",
    "ConnectError",
    "ConnectionResetError",
    "OSError",
)


def classify_error(error_code: str, manual_disconnect: bool = False) -> ErrorClass:
    """Mapira naziv tipa izuzetka (ili poruku) u ErrorClass."""
    if manual_disconnect:
        return ErrorClass.MANUAL_DISCONNECT
    lowered = str(error_code).lower()
    if "ratelimit" in lowered or "rate limit" in lowered or "429" in lowered:
        return ErrorClass.RATE_LIMIT
    if any(m in str(error_code) for m in _AUTH_MARKERS):
        return ErrorClass.AUTH
    if any(m in str(error_code) for m in _FATAL_MARKERS):
        return ErrorClass.FATAL
    if any(m in str(error_code) for m in _NETWORK_MARKERS):
        return ErrorClass.NETWORK
    return ErrorClass.UNKNOWN


def backoff_seconds(attempt: int) -> float:
    """Exponential backoff: 2s, 4s, 8s, … capped na posljednju vrijednost."""
    if attempt < 1:
        attempt = 1
    idx = min(attempt - 1, len(DEFAULT_BACKOFF) - 1)
    return DEFAULT_BACKOFF[idx]


def should_reconnect(
    error_class: ErrorClass,
    attempt: int,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> bool:
    """Retry-uj samo network/rate-limit (bounded); auth/fatal/manual nikad."""
    if error_class not in (ErrorClass.NETWORK, ErrorClass.RATE_LIMIT):
        return False
    return attempt < max_attempts


class ReconnectPolicy:
    """Objedinjen API za worker — čista, testabilna."""

    def __init__(self, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> None:
        self.max_attempts = max_attempts
        self.attempt = 0

    def reset(self) -> None:
        self.attempt = 0

    def on_disconnect(self, error_code: str, manual: bool = False) -> tuple[bool, float]:
        """Vraća (should_reconnect, delay_seconds)."""
        error_class = classify_error(error_code, manual_disconnect=manual)
        if not should_reconnect(error_class, self.attempt, self.max_attempts):
            return False, 0.0
        self.attempt += 1
        return True, backoff_seconds(self.attempt)
