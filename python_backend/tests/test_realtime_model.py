"""Testovi za OpenAI Realtime model konfiguraciju (RTM-1/RTM-2)."""

import pytest

from app.core.config import (
    OPENAI_REALTIME_MODEL_DEFAULT,
    resolve_openai_realtime_model,
)


def test_default_is_gpt_realtime():
    assert OPENAI_REALTIME_MODEL_DEFAULT == "gpt-realtime"


def test_resolve_default():
    assert resolve_openai_realtime_model("gpt-realtime") == "gpt-realtime"


def test_resolve_mini():
    assert resolve_openai_realtime_model("gpt-realtime-2.1-mini") == "gpt-realtime-2.1-mini"


def test_invalid_model_fails_closed():
    with pytest.raises(ValueError, match="not allowed"):
        resolve_openai_realtime_model("nepostojeci-model")


def test_invalid_model_no_silent_fallback():
    # Fail-closed: ne smije tiho vratiti default.
    with pytest.raises(ValueError):
        resolve_openai_realtime_model("gpt-realtime-2.1-mini ")

    with pytest.raises(ValueError):
        resolve_openai_realtime_model("")
