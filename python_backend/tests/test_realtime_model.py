"""Testovi za OpenAI Realtime model konfiguraciju (RTM-1/RTM-2)."""

import pytest

from app.core.config import (
    OPENAI_REALTIME_MODEL_DEFAULT,
    resolve_effective_realtime_model,
    resolve_openai_realtime_model,
)


def test_default_is_gpt_realtime_2_1():
    assert OPENAI_REALTIME_MODEL_DEFAULT == "gpt-realtime-2.1"


def test_resolve_newer():
    assert resolve_openai_realtime_model("gpt-realtime-2.1") == "gpt-realtime-2.1"


def test_resolve_older():
    assert resolve_openai_realtime_model("gpt-realtime-2") == "gpt-realtime-2"


def test_invalid_model_fails_closed():
    with pytest.raises(ValueError, match="not allowed"):
        resolve_openai_realtime_model("nepostojeci-model")


def test_invalid_model_no_silent_fallback():
    # Fail-closed: ne smije tiho vratiti default. Stari/nepostojeći ID-jevi
    # (gpt-realtime-2.1-mini, gpt-realtime) više nisu dozvoljeni.
    with pytest.raises(ValueError):
        resolve_openai_realtime_model("gpt-realtime-2.1-mini")

    with pytest.raises(ValueError):
        resolve_openai_realtime_model("gpt-realtime")

    with pytest.raises(ValueError):
        resolve_openai_realtime_model("")


# --- resolve_effective_realtime_model (in-app selector precedence) ---

def test_effective_default_when_no_choice_and_default_env():
    assert resolve_effective_realtime_model(None, "gpt-realtime-2.1") == "gpt-realtime-2.1"


def test_effective_uses_env_fallback_when_no_choice():
    assert resolve_effective_realtime_model(None, "gpt-realtime-2") == "gpt-realtime-2"


def test_effective_user_choice_overrides_env():
    # T-B4: env 2, korisnik izabrao 2.1 → 2.1.
    assert resolve_effective_realtime_model("gpt-realtime-2.1", "gpt-realtime-2") == "gpt-realtime-2.1"


def test_effective_reverse_override():
    # T-B5: env 2.1, korisnik izabrao 2 → 2.
    assert (
        resolve_effective_realtime_model("gpt-realtime-2", "gpt-realtime-2.1")
        == "gpt-realtime-2"
    )


def test_effective_invalid_user_choice_fails_closed():
    # T-B6: invalid persisted value — nema silent fallbacka.
    with pytest.raises(ValueError):
        resolve_effective_realtime_model("nepostojeci-model", "gpt-realtime-2.1")
