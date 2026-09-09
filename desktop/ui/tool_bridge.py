"""desktop/ui/tool_bridge.py — ToolBridge (QM-3).

Tanki most između glasovne sesije (voice.py) i Python backend tool sistema.
Svaki tool call ide kroz stvarni `POST /tools/execute` (permission/cancellation
gate) — NEMA lokalnog izvršavanja kao u spike-u. Confirmation Bridge je port
obrasca iz src/lib/realtime.ts: kad tool vrati CONFIRMATION_REQUIRED, bridge
kreira confirmation i emituje `confirmation_required`; retry sa confirmation_id
radi pozivalac (voice.py). Idempotency (completed_call_ids) port iz realtime.ts
R3 — isti call_id se nikad ne izvršava dvaput.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"


def to_realtime_tool(spec: dict[str, Any]) -> dict[str, Any]:
    """Konvertuje ToolDefinition (backend) u OpenAI Realtime function oblik."""
    return {
        "type": "function",
        "name": spec["name"],
        "description": spec.get("description", ""),
        "parameters": spec.get("input_schema")
        or {"type": "object", "properties": {}, "required": []},
    }


class ToolBridge(QObject):
    """Izvršava tool call-ove preko backend-a, uz confirmation + idempotency."""

    confirmation_required = Signal(dict)  # {tool_name, arguments, risk, confirmation_id}
    activity = Signal(str)

    def __init__(self, client) -> None:
        super().__init__()
        self._client = client
        self.completed_call_ids: set[str] = set()

    def fetch_tool_specs(self) -> list[dict[str, Any]]:
        resp = self._client.request("/tools", timeout=5.0)
        return resp.json().get("tools", [])

    def build_realtime_tools(self) -> list[dict[str, Any]]:
        return [to_realtime_tool(spec) for spec in self.fetch_tool_specs()]

    def risk_for(self, tool_name: str) -> str:
        for spec in self.fetch_tool_specs():
            if spec.get("name") == tool_name:
                return spec.get("risk") or "high"
        return "high"

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST /tools/execute → normalizovan rezultat (ok, error_code, result)."""
        resp = self._client.request(
            "/tools/execute",
            method="POST",
            json={
                "tool_name": tool_name,
                "arguments": arguments,
                "context": context or {},
            },
            timeout=30.0,
        )
        body = resp.json() if resp.status_code < 500 else {}
        error = body.get("error")
        return {
            "ok": bool(body.get("ok")),
            "error_code": (error or {}).get("code"),
            "error_message": (error or {}).get("message"),
            "result": body.get("result"),
            "tool_state": body.get("tool_state"),
        }

    def create_confirmation(
        self,
        tool_name: str,
        payload: dict[str, Any],
        risk_level: str,
    ) -> dict[str, Any]:
        resp = self._client.request(
            "/confirmations",
            method="POST",
            json={
                "action_name": tool_name,
                "payload": payload,
                "risk_level": risk_level,
                "tool_name": tool_name,
            },
            timeout=10.0,
        )
        return resp.json()

    def approve_confirmation(self, confirmation_id: str) -> dict[str, Any]:
        resp = self._client.request(
            f"/confirmations/{confirmation_id}/approve",
            method="POST",
            json={},
            timeout=10.0,
        )
        return resp.json()

    def reject_confirmation(self, confirmation_id: str) -> dict[str, Any]:
        resp = self._client.request(
            f"/confirmations/{confirmation_id}/reject",
            method="POST",
            json={},
            timeout=10.0,
        )
        return resp.json()

    def run_tool_call(
        self,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        risk: str | None = None,
    ) -> dict[str, Any]:
        """Idempotency + execute + auto-create-confirmation on REQUIRED.

        Vraća rezultat za model. Za CONFIRMATION_REQUIRED vraća
        `waiting_confirmation` rezultat i emituje `confirmation_required` —
        retry (sa confirmation_id) radi pozivalac kroz `retry_with_confirmation`.
        """
        if call_id in self.completed_call_ids:
            return {"ok": False, "duplicate": True, "message": "Alat je već izvršen."}

        self.activity.emit(f"Izvršavam {tool_name}")
        result = self.execute_tool(tool_name, arguments)

        if result.get("error_code") == CONFIRMATION_REQUIRED:
            risk_level = risk or self.risk_for(tool_name)
            confirmation = self.create_confirmation(tool_name, arguments, risk_level)
            self.confirmation_required.emit(
                {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "risk": risk_level,
                    "confirmation_id": confirmation.get("id"),
                }
            )
            return {
                "ok": False,
                "waiting_confirmation": True,
                "message": "Potrebna je tvoja potvrda prije izvršenja. Potvrdi u dijalogu.",
            }

        self.completed_call_ids.add(call_id)
        return result

    def retry_with_confirmation(
        self,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        confirmation_id: str,
    ) -> dict[str, Any]:
        """Ponovi tool call nakon odobrenja — isti tool_name/arguments, sada sa
        context.confirmation_id (potroši single-use confirmation)."""
        result = self.execute_tool(
            tool_name,
            arguments,
            context={"confirmation_id": confirmation_id},
        )
        self.completed_call_ids.add(call_id)
        return result
