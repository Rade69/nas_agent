import json

from app.agent.tool_executor import ToolExecutor
from app.agent.tool_registry import create_default_registry
from app.schemas.tool import ToolExecutionRequest
from app.services.action_log import ActionLogService
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
    assert json.loads(row["input_json"])["arguments"] == {"text": "hello"}
    assert json.loads(row["output_json"])["result"] == {"text": "hello"}


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