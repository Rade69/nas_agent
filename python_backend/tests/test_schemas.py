"""Edge-case schema validation tests (FAZA 18).

Validira Pydantic modele za potvrde i planove — min/max dužine, required
polja, enum vrijednosti, nepoznata polja. Ovo pokriva slučajeve koje
endpoint testovi ne pogađaju direktno (client-side payload greške).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.confirmation import ConfirmationCreateRequest
from app.schemas.plan import (
    PlanCreateRequest,
    PlanStepCreateRequest,
    PlanUpdateRequest,
)
from app.schemas.tool import ToolExecutionContext, ToolExecutionRequest


def test_confirmation_create_requires_action_name() -> None:
    # Pydantic min_length=1 ne odbija whitespace ("   " ima dužinu 3).
    # Testiramo da prazan string "" je odbijen.
    with pytest.raises(ValidationError) as exc:
        ConfirmationCreateRequest(action_name="")
    errors = exc.value.errors()
    assert any("action_name" in e["loc"] for e in errors)
    assert any("min_length" in e["type"] or "string_too_short" in e["type"] for e in errors)


def test_confirmation_create_rejects_unknown_risk() -> None:
    with pytest.raises(ValidationError) as exc:
        ConfirmationCreateRequest(action_name="test", risk_level="extreme")
    errors = exc.value.errors()
    assert any("risk_level" in e["loc"] for e in errors)


def test_plan_create_requires_title() -> None:
    with pytest.raises(ValidationError) as exc:
        PlanCreateRequest(title="")
    assert any("title" in e["loc"] for e in exc.value.errors())


def test_plan_step_requires_title() -> None:
    with pytest.raises(ValidationError) as exc:
        PlanStepCreateRequest(title="")
    assert any("title" in e["loc"] for e in exc.value.errors())


def test_plan_update_allows_partial_fields() -> None:
    # Samo status — ostalo treba da ostane None (nije obavezno).
    update = PlanUpdateRequest(status="approved")
    assert update.status == "approved"
    assert update.title is None
    assert update.summary is None


def test_tool_execution_context_defaults() -> None:
    ctx = ToolExecutionContext()
    assert ctx.computer_mode is False
    assert ctx.conversation_id is None
    assert ctx.confirmation_id is None


def test_tool_execution_request_default_arguments() -> None:
    req = ToolExecutionRequest(tool_name="echo")
    assert req.arguments == {}
    assert req.context.computer_mode is False


def test_tool_execution_accepts_confirmation_id() -> None:
    req = ToolExecutionRequest(
        tool_name="records_delete",
        arguments={"id": "rec_123", "confirmed": True},
        context=ToolExecutionContext(confirmation_id="confirm_abc123"),
    )
    assert req.context.confirmation_id == "confirm_abc123"
