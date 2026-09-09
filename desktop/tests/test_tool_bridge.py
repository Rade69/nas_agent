"""Testovi za ToolBridge (QM-3): tool execution, confirmation flow, idempotency."""

from desktop.ui.tool_bridge import ToolBridge, to_realtime_tool


class FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class FakeClient:
    def __init__(self):
        self.calls: list[tuple[str, str, dict]] = []
        self.handlers: dict[str, callable] = {}

    def request(self, path, method="GET", json=None, timeout=5.0):
        self.calls.append((path, method, json))
        handler = self.handlers.get(path)
        if handler:
            status, body = handler(json)
            return FakeResponse(status, body)
        return FakeResponse(200, {})


def _tool_response(ok, **extra):
    body = {"ok": ok, "tool_name": "test_tool", "result": extra.pop("result", {}),
            "action_log_id": "log1", "duration_ms": 5}
    body.update(extra)
    return body


def test_to_realtime_tool_shape():
    spec = {
        "name": "web_search",
        "description": "traži web",
        "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]},
    }
    tool = to_realtime_tool(spec)
    assert tool["type"] == "function"
    assert tool["name"] == "web_search"
    assert tool["parameters"]["required"] == ["q"]


def test_execute_tool_normalizes_success():
    client = FakeClient()
    client.handlers["/tools/execute"] = lambda j: (
        200,
        _tool_response(True, result={"vrijeme": "10:00"}),
    )
    bridge = ToolBridge(client)
    result = bridge.execute_tool("test_tool", {"x": 1})
    assert result["ok"] is True
    assert result["result"] == {"vrijeme": "10:00"}
    assert result["error_code"] is None


def test_execute_tool_normalizes_confirmation_required():
    client = FakeClient()
    client.handlers["/tools/execute"] = lambda j: (
        200,
        _tool_response(False, error={"code": "CONFIRMATION_REQUIRED", "message": "treba potvrda"}),
    )
    bridge = ToolBridge(client)
    result = bridge.execute_tool("test_tool", {})
    assert result["ok"] is False
    assert result["error_code"] == "CONFIRMATION_REQUIRED"


def test_run_tool_call_marks_completed():
    client = FakeClient()
    client.handlers["/tools/execute"] = lambda j: (200, _tool_response(True, result={}))
    bridge = ToolBridge(client)
    bridge.run_tool_call("call-1", "test_tool", {})
    assert "call-1" in bridge.completed_call_ids


def test_run_tool_call_idempotency():
    client = FakeClient()
    client.handlers["/tools/execute"] = lambda j: (200, _tool_response(True, result={}))
    bridge = ToolBridge(client)
    bridge.run_tool_call("call-1", "test_tool", {})
    duplicate = bridge.run_tool_call("call-1", "test_tool", {})
    assert duplicate.get("duplicate") is True
    # samo jedan stvarni execute poziv
    executes = [c for c in client.calls if c[0] == "/tools/execute"]
    assert len(executes) == 1


def test_run_tool_call_confirmation_required_creates_confirmation_and_emits():
    client = FakeClient()
    client.handlers["/tools/execute"] = lambda j: (
        200,
        _tool_response(False, error={"code": "CONFIRMATION_REQUIRED", "message": "treba potvrda"}),
    )
    client.handlers["/confirmations"] = lambda j: (200, {"id": "conf-123", "status": "pending"})
    bridge = ToolBridge(client)
    emitted = []
    bridge.confirmation_required.connect(emitted.append)

    result = bridge.run_tool_call("call-2", "risky_tool", {"x": 1}, risk="high")

    assert result.get("waiting_confirmation") is True
    assert len(emitted) == 1
    assert emitted[0]["confirmation_id"] == "conf-123"
    assert emitted[0]["tool_name"] == "risky_tool"
    assert "call-2" not in bridge.completed_call_ids


def test_retry_with_confirmation_uses_confirmation_id():
    client = FakeClient()
    client.handlers["/tools/execute"] = lambda j: (200, _tool_response(True, result={"obrisano": True}))
    bridge = ToolBridge(client)

    result = bridge.retry_with_confirmation("call-3", "risky_tool", {"x": 1}, "conf-123")

    assert result["ok"] is True
    execute_call = [c for c in client.calls if c[0] == "/tools/execute"][0]
    assert execute_call[2]["context"]["confirmation_id"] == "conf-123"
    assert "call-3" in bridge.completed_call_ids


def test_build_realtime_tools_fetches_and_converts():
    client = FakeClient()
    client.handlers["/tools"] = lambda j: (
        200,
        {"tools": [{"name": "a", "description": "d", "input_schema": {"type": "object"}}]},
    )
    bridge = ToolBridge(client)
    tools = bridge.build_realtime_tools()
    assert tools[0]["name"] == "a"
    assert tools[0]["type"] == "function"
