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
        data_dir=data_dir if data_dir is not None else Path(__file__).resolve().parents[2] / "data",
    )