"""Runtime validation of tool-call arguments against each tool's input_schema.

Security Gate 0 / FAZA S-1 (docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md). Every
ToolDefinition already carries a JSON Schema in `input_schema`, but until now
that schema was only *advertised* to the model (prompt_builder sends it as the
OpenAI function-calling `parameters`) and never *enforced* on the backend. A
model — or an injected instruction, or a malformed/hostile tool call — could
therefore pass extra fields, wrong types, or out-of-range enum values and the
handler would run anyway (relying on ad-hoc `.get()`/ValueError checks).

This module closes that gap: ToolExecutor validates arguments here before the
handler is ever invoked, so `additionalProperties: false`, `required`, `enum`,
and min/max declared in the schema become real backend-enforced constraints.
"""
from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


def validate_tool_arguments(input_schema: dict[str, Any], arguments: dict[str, Any]) -> str | None:
    """Validate `arguments` against `input_schema`.

    Returns None when the arguments are valid, or a human-readable error string
    describing the first violation (suitable for an INVALID_ARGUMENTS error).

    Fails closed: if the schema itself is malformed, that is reported as an
    error rather than silently skipping validation — a tool with an unusable
    schema must not run with unvalidated arguments. Some structural defects
    (e.g. an unknown `type`) only surface while validating, so any exception
    raised during checking is also treated as a validation failure, never
    swallowed into a "pass".
    """
    try:
        Draft202012Validator.check_schema(input_schema)
    except SchemaError as exc:
        return f"Tool input_schema is invalid: {exc.message}"

    try:
        errors = sorted(
            Draft202012Validator(input_schema).iter_errors(arguments),
            key=lambda e: list(e.path),
        )
    except Exception as exc:  # noqa: BLE001 — fail closed on any validation fault
        return f"Argument validation failed: {exc}"

    if not errors:
        return None

    first = errors[0]
    location = ".".join(str(part) for part in first.path)
    if location:
        return f"Argument '{location}' is invalid: {first.message}"
    return first.message
