"""Confirmation state-machine service (FAZA 9).

Enforces the pending→approved/rejected/expired/cancelled transition
rules. Does NOT decide WHEN to issue a confirmation — the permission
engine (FAZA 10) owns that decision.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.core.payload_hash import hash_payload
from app.schemas.tool import RiskLevel
from app.storage.repositories.confirmation_repo import ConfirmationRepository


class ConfirmationService:
    """Application layer over ConfirmationRepository (FAZA 9).

    Owns confirmation lifecycle transitions and ID generation. The permission/
    risk layer that *creates* confirmations from tool execution is FAZA 10 —
    this service is the storage + state machine, callable both by the agent
    runtime (later) and directly from the UI/API for manual proposals.
    """

    def __init__(self, repository: ConfirmationRepository) -> None:
        self._repository = repository

    def propose(
        self,
        *,
        action_name: str,
        payload: dict[str, Any],
        risk_level: RiskLevel,
        plan_id: str | None = None,
        summary: str | None = None,
        tool_name: str | None = None,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        confirmation_id = f"confirm_{uuid4().hex[:12]}"
        expires_at = (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat()
        row = self._repository.create(
            confirmation_id=confirmation_id,
            action_name=action_name,
            payload=payload,
            risk_level=risk_level,
            plan_id=plan_id,
            summary=summary,
            tool_name=tool_name,
            payload_hash=hash_payload(payload),
            expires_at=expires_at,
        )
        return self._to_dict(row)

    def is_expired(self, confirmation: dict[str, Any]) -> bool:
        expires_at = confirmation.get("expires_at")
        if not expires_at:
            return False
        try:
            expiry = datetime.fromisoformat(expires_at)
        except ValueError:
            return False
        return datetime.now(UTC) > expiry

    def get(self, confirmation_id: str) -> dict[str, Any] | None:
        row = self._repository.get(confirmation_id)
        return self._to_dict(row) if row else None

    def list(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._repository.list(status=status, limit=limit)
        return [self._to_dict(row) for row in rows]

    def list_pending(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.list(status="pending", limit=limit)

    def approve(self, confirmation_id: str) -> dict[str, Any] | None:
        return self._resolve(confirmation_id, "approved")

    def reject(self, confirmation_id: str) -> dict[str, Any] | None:
        return self._resolve(confirmation_id, "rejected")

    def cancel(self, confirmation_id: str) -> dict[str, Any] | None:
        return self._resolve(confirmation_id, "cancelled")

    def _resolve(self, confirmation_id: str, status: str) -> dict[str, Any] | None:
        row = self._repository.resolve(confirmation_id, status)
        return self._to_dict(row) if row else None

    def _to_dict(self, row: Any) -> dict[str, Any]:
        import json

        payload_json = row["payload_json"] if "payload_json" in row.keys() else "{}"
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except (json.JSONDecodeError, TypeError):
            payload = {}

        return {
            "id": row["id"],
            "status": row["status"],
            "action_name": row["action_name"],
            "payload": payload,
            "risk_level": row["risk_level"],
            "plan_id": row["plan_id"] if "plan_id" in row.keys() else None,
            "summary": row["summary"] if "summary" in row.keys() else None,
            "tool_name": row["tool_name"] if "tool_name" in row.keys() else None,
            "payload_hash": row["payload_hash"] if "payload_hash" in row.keys() else None,
            "expires_at": row["expires_at"] if "expires_at" in row.keys() else None,
            "created_at": row["created_at"],
            "resolved_at": row["resolved_at"],
        }
