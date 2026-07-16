"""create_plan tool — allows the agent to propose multi-step plans (P2).

Creates a plan via the existing PlanService. The plan starts in 'proposed'
status and appears in the Predloženi tab. The user must approve it before
any action steps are executed.
"""
from __future__ import annotations

from typing import Any

from app.core.errors import AppError


def _handle_create_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    from app.main import app
    plan_service = app.state.plan_service
    if plan_service is None:
        raise AppError("PLANS_UNAVAILABLE", "Plan service is not initialized.")

    title = str(arguments.get("title", "")).strip()
    if not title:
        raise ValueError("title is required.")

    summary = str(arguments.get("summary", "")).strip() or None

    raw_steps = arguments.get("steps", [])
    if not isinstance(raw_steps, list):
        raw_steps = []

    step_dicts: list[dict[str, Any]] = []
    for s in raw_steps:
        if isinstance(s, dict) and s.get("title"):
            step_dicts.append({"title": str(s["title"]).strip()})
        elif isinstance(s, str):
            step_dicts.append({"title": s.strip()})

    plan = plan_service.create(
        title=title,
        summary=summary,
        steps=step_dicts if step_dicts else None,
    )
    return {
        "ok": True,
        "plan_id": plan["id"],
        "title": plan["title"],
        "status": plan["status"],
        "steps_count": len(plan.get("steps", [])),
        "message": (
            f"Plan '{title}' created with {len(step_dicts)} steps. "
            f"It is in Predloženi tab — approve it to start."
        ),
    }


def make_handler():
    return _handle_create_plan
