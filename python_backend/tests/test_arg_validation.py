"""FAZA S-1 — runtime tool-argument schema validation.

Covers both the pure validator (validate_tool_arguments) and its enforcement
inside ToolExecutor: an argument set that violates a tool's input_schema must
be rejected with INVALID_ARGUMENTS *before the handler runs*.
"""
from __future__ import annotations

from app.agent.arg_validation import validate_tool_arguments
from app.agent.tool_executor import ToolExecutor
from app.agent.tool_registry import ToolRegistry
from app.schemas.tool import ToolDefinition, ToolExecutionRequest

STRICT_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "mode": {"type": "string", "enum": ["a", "b"]},
        "count": {"type": "number", "minimum": 1, "maximum": 10},
    },
    "required": ["text"],
    "additionalProperties": False,
}


# --- Pure validator ---------------------------------------------------------

def test_valid_arguments_pass() -> None:
    assert validate_tool_arguments(STRICT_SCHEMA, {"text": "hi", "mode": "a", "count": 3}) is None


def test_missing_required_field_rejected() -> None:
    error = validate_tool_arguments(STRICT_SCHEMA, {"mode": "a"})
    assert error is not None
    assert "text" in error


def test_extra_field_rejected_when_additional_properties_false() -> None:
    error = validate_tool_arguments(STRICT_SCHEMA, {"text": "hi", "injected": "rm -rf"})
    assert error is not None


def test_wrong_type_rejected() -> None:
    error = validate_tool_arguments(STRICT_SCHEMA, {"text": 123})
    assert error is not None
    assert "text" in error


def test_enum_out_of_range_rejected() -> None:
    error = validate_tool_arguments(STRICT_SCHEMA, {"text": "hi", "mode": "z"})
    assert error is not None
    assert "mode" in error


def test_number_out_of_range_rejected() -> None:
    error = validate_tool_arguments(STRICT_SCHEMA, {"text": "hi", "count": 999})
    assert error is not None
    assert "count" in error


def test_malformed_schema_fails_closed() -> None:
    # A schema that is itself invalid must produce an error, not silently pass.
    error = validate_tool_arguments({"type": "not-a-real-type"}, {"anything": 1})
    assert error is not None


# --- Enforcement inside ToolExecutor ---------------------------------------

def _executor_with_spy():
    calls: list[dict] = []

    def handler(arguments: dict) -> dict:
        calls.append(arguments)
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="strict_tool",
            description="Tool with a strict input schema.",
            input_schema=STRICT_SCHEMA,
            risk="low",
            requires_confirmation=False,
            requires_computer_mode=False,
            allowed_in_background=True,
            timeout_ms=5000,
            implemented_by="python",
            enabled=True,
        ),
        handler,
    )
    return ToolExecutor(registry), calls


def test_executor_rejects_invalid_arguments_before_handler() -> None:
    executor, calls = _executor_with_spy()

    response = executor.execute(
        ToolExecutionRequest(tool_name="strict_tool", arguments={"text": "hi", "injected": "x"})
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "INVALID_ARGUMENTS"
    assert response.tool_state == "failed"
    # The handler must never see arguments that failed schema validation.
    assert calls == []


def test_executor_runs_handler_on_valid_arguments() -> None:
    executor, calls = _executor_with_spy()

    response = executor.execute(
        ToolExecutionRequest(tool_name="strict_tool", arguments={"text": "hi", "count": 2})
    )

    assert response.ok is True
    assert calls == [{"text": "hi", "count": 2}]
