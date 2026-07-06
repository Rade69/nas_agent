import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseModel):
    app_name: str = "RileyJarvis Python Backend"
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    openai_api_key: str | None = None
    # Security PR-1 / SECURITY_HARDENING_PLAN.md section 6: local session token.
    # Electron generates this and passes it via RICKY_LOCAL_TOKEN when it spawns
    # the backend (see electron/services/pythonProcess.cjs). When unset (tests,
    # or `uvicorn app.main:app` run directly per README without Electron), the
    # auth dependency in app/core/auth.py fails open rather than locking out
    # local dev/test runs — the real Electron-launched path always sets it.
    local_token: str | None = None
    # FAZA 16: Exa web search API key (env: EXA_API_KEY). Held only on the
    # Python backend side, same pattern as OPENAI_API_KEY.
    exa_api_key: str | None = None

    @property
    def database_path(self) -> Path:
        return self.data_dir / "ricky.sqlite"


def get_settings() -> Settings:
    # Electron already injects OPENAI_API_KEY into this process's env when it
    # spawns the backend (see electron/services/pythonProcess.cjs). This load
    # is a fallback for running the backend directly (per README), so it never
    # overrides an already-set value.
    load_dotenv(dotenv_path=REPO_ROOT / ".env.local", override=False)
    data_dir_env = os.environ.get("RICKY_DATA_DIR")
    data_dir = Path(data_dir_env) if data_dir_env else None
    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
        local_token=os.environ.get("RICKY_LOCAL_TOKEN") or None,
        exa_api_key=os.environ.get("EXA_API_KEY") or None,
        data_dir=data_dir if data_dir is not None else Path(__file__).resolve().parents[2] / "data",
        # FAZA 19: PyInstaller sidecar receives host/port from Electron's env.
        # Defaults are fine for dev (uvicorn --host/--port CLI args take
        # precedence), but in a packaged build the .exe has no CLI args, so
        # these env vars are the only way to configure the listen address.
        host=os.environ.get("RICKY_HOST") or "127.0.0.1",
        port=int(os.environ["RICKY_PORT"]) if os.environ.get("RICKY_PORT") else 8765,
    )