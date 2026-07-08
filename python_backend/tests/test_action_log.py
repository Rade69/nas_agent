import json

from app.agent.tool_executor import ToolExecutor
from app.agent.tool_registry import create_default_registry
from app.schemas.tool import ToolExecutionRequest
from app.services.action_log import ActionLogService, redact_sensitive
from app.storage.db import initialize_database
from app.storage.repositories.tool_run_repo import ToolRunRepository
from app.core.config import Settings


def make_executor(tmp_path) -> tuple[ToolExecutor, ToolRunRepository]:
    settings = Settings(data_dir=tmp_path)
    initialize_database(settings)
    repo = ToolRunRepository(settings.database_path)
    action_log = ActionLogService(repo)
    return ToolExecutor(create_default_registry(), action_log=action_log), repo


def test_successful_tool_execution_creates_tool_run(tmp_path) -> None:
    executor, repo = make_executor(tmp_path)

    response = executor.execute(
        ToolExecutionRequest(tool_name="echo", arguments={"text": "hello"})
    )

    row = repo.get(response.action_log_id)
    assert response.ok is True
    assert row is not None
    assert row["tool_name"] == "echo"
    assert row["status"] == "success"
    assert row["risk_level"] == "low"
    assert row["requires_confirmation"] == 0
    assert row["computer_mode"] == 0
    # FAZA S-4 / audit O3: the free-text "text" value is redacted in the durable
    # audit log (structure/keys preserved) so plaintext content isn't stored.
    assert json.loads(row["input_json"])["arguments"] == {"text": "[REDACTED]"}
    assert json.loads(row["output_json"])["result"] == {"text": "[REDACTED]"}


def test_failed_tool_execution_creates_tool_run(tmp_path) -> None:
    executor, repo = make_executor(tmp_path)

    response = executor.execute(
        ToolExecutionRequest(tool_name="echo", arguments={})
    )

    row = repo.get(response.action_log_id)
    assert response.ok is False
    assert row is not None
    assert row["tool_name"] == "echo"
    assert row["status"] == "failed"
    assert row["error_code"] == "INVALID_ARGUMENTS"
    # FAZA S-1: the missing required "text" is now caught by runtime schema
    # validation (before the handler's own ValueError), so the message is the
    # schema-driven one rather than echo_tool's ad-hoc "echo requires ..." text.
    assert "text" in row["error_message"]


# --- FAZA S-4 / audit O3: sensitive payload redaction ---

def test_redact_sensitive_masks_free_text_and_credentials() -> None:
    payload = {
        "arguments": {"text": "my password is hunter2", "x": 10, "appName": "notepad"},
        "context": {"token": "abc123", "computer_mode": True},
        "nested": [{"body": "secret email", "keep": "ok"}],
    }
    redacted = redact_sensitive(payload)
    assert redacted["arguments"]["text"] == "[REDACTED]"
    assert redacted["context"]["token"] == "[REDACTED]"
    assert redacted["nested"][0]["body"] == "[REDACTED]"
    # Non-sensitive structural fields are preserved for auditability.
    assert redacted["arguments"]["x"] == 10
    assert redacted["arguments"]["appName"] == "notepad"
    assert redacted["context"]["computer_mode"] is True
    assert redacted["nested"][0]["keep"] == "ok"
    # Original payload is not mutated.
    assert payload["arguments"]["text"] == "my password is hunter2"


def test_type_text_argument_is_redacted_in_audit_log(tmp_path) -> None:
    executor, repo = make_executor(tmp_path)
    # echo carries a "text" arg through the real ActionLogService path.
    response = executor.execute(
        ToolExecutionRequest(tool_name="echo", arguments={"text": "sensitive typed content"})
    )
    row = repo.get(response.action_log_id)
    assert "sensitive typed content" not in row["input_json"]
    assert "[REDACTED]" in row["input_json"]