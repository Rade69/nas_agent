from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from app.storage.repositories.plan_repo import PlanRepository


class PlanService:
    """Application layer over PlanRepository (FAZA 9).

    Plans are the storage primitive that replaces Notepad-based planning: a plan
    is an ordered set of steps persisted in SQLite, optionally referenced by a
    confirmation (e.g. "approve this plan before running step 3"). This service
    owns ID generation and row→dict conversion for the API layer.
    """

    def __init__(self, repository: PlanRepository) -> None:
        self._repository = repository

    def create(
        self,
        *,
        title: str,
        summary: str | None = None,
        steps: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        plan_id = f"plan_{uuid4().hex[:12]}"
        row = self._repository.create(
            plan_id=plan_id,
            title=title,
            summary=summary,
            steps=steps,
        )
        return self._to_dict(row)

    def get(self, plan_id: str) -> dict[str, Any] | None:
        row = self._repository.get(plan_id)
        return self._to_dict(row) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._repository.list(limit=limit)
        return [self._to_dict(row) for row in rows]

    def update(
        self,
        plan_id: str,
        *,
        title: str | None = None,
        summary: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any] | None:
        row = self._repository.update(
            plan_id,
            title=title,
            summary=summary,
            status=status,
        )
        return self._to_dict(row) if row else None

    def update_step(
        self,
        plan_id: str,
        step_id: str,
        *,
        status: str | None = None,
        title: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        row = self._repository.update_step(
            plan_id,
            step_id,
            status=status,
            title=title,
            details=details,
        )
        return self._to_dict(row) if row else None

    def _to_dict(self, row: Any) -> dict[str, Any]:
        steps: list[dict[str, Any]] = []
        for step in row["steps"]:
            details_json = step["details_json"] if "details_json" in step.keys() else "{}"
            try:
                details = json.loads(details_json) if details_json else {}
            except (json.JSONDecodeError, TypeError):
                details = {}
            steps.append(
                {
                    "id": step["id"],
                    "plan_id": step["plan_id"],
                    "step_index": step["step_index"],
                    "title": step["title"],
                    "status": step["status"],
                    "details": details,
                }
            )
        return {
            "id": row["id"],
            "title": row["title"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "summary": row["summary"],
            "steps": steps,
        }
