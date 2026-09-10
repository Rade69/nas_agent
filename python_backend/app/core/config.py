"""Backend configuration from environment variables.

Settings model (process/environment config — host, port, API keys) kept
deliberately separate from UserSettings (user-facing preferences in
schemas/settings.py) to avoid confusion between the two.
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]

# RTM-2 (OPENAI_REALTIME_21_MINI_AB_TEST): allowlist za OpenAI Realtime modele.
# Fail-closed — nepoznat model je konfiguraciona greška, NIKAD silent fallback
# na gpt-realtime (to bi pokvarilo A/B test).
OPENAI_REALTIME_MODELS = frozenset({"gpt-realtime", "gpt-realtime-2.1-mini"})
OPENAI_REALTIME_MODEL_DEFAULT = "gpt-realtime"


def resolve_openai_realtime_model(raw: str) -> str:
    """Vrati dozvoljeni model ili raise ValueError (centralna validacija)."""
    if raw not in OPENAI_REALTIME_MODELS:
        raise ValueError(
            f"OPENAI_REALTIME_MODEL '{raw}' is not allowed. "
            f"Allowed values: {sorted(OPENAI_REALTIME_MODELS)}"
        )
    return raw


class Settings(BaseModel):
    app_name: str = "RileyJarvis Python Backend"
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    openai_api_key: str | None = None
    # Security PR-1 / SECURITY_HARDENING_PLAN.md section 6: local session token.
    # Electron generates this and passes it via RICKY_LOCAL_TOKEN when it spawns
    # the backend (see electron/services/pythonProcess.cjs). get_settings()
    # below always resolves this to a real value — auto-generating one when
    # RICKY_LOCAL_TOKEN is unset — so app/core/auth.py can enforce it
    # unconditionally instead of failing open for the dev-without-Electron path.
    local_token: str | None = None
    # FAZA 16: Exa web search API key (env: EXA_API_KEY). Held only on the
    # Python backend side, same pattern as OPENAI_API_KEY.
    exa_api_key: str | None = None
    # MM-1 (docs/MINIMAX_PROVIDER_FINDING.md): provider selection + MiniMax
    # credentials. Held only on the backend side (Security Gate 0). Provider
    # selection is RICKY_AI_PROVIDER (openai|minimax), default openai.
    ai_provider: str = "openai"
    minimax_api_key: str | None = None
    minimax_model: str = "MiniMax-M3"
    openai_model: str = "gpt-4o-mini"
    # RTM-1 (OPENAI_REALTIME_21_MINI_AB_TEST): the OpenAI Realtime (voice)
    # model. Distinct from `openai_model` (text). Backend-owned source of truth
    # for the Realtime model — the desktop must not choose its own.
    openai_realtime_model: str = "gpt-realtime"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "ricky.sqlite"


def _resolve_local_token(data_dir: Path) -> str:
    """Security Gate 1 fix (2026-07-12, docs/PROJECT_OVERVIEW.md section 4.7):
    the backend used to fail open when RICKY_LOCAL_TOKEN was unset (dev
    `uvicorn app.main:app` run without Electron per README) — any local
    process, including a malicious webpage's fetch() to 127.0.0.1, could call
    tools unauthenticated. Electron's own launch path always sets the env var
    and is unaffected by this function. When it's absent, generate a
    per-process token and persist it to a gitignored file under data_dir so a
    developer running the frontend or curl separately can still authenticate.
    """
    env_token = os.environ.get("RICKY_LOCAL_TOKEN")
    if env_token:
        return env_token
    token = secrets.token_urlsafe(32)
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "dev_local_token.txt").write_text(token, encoding="utf-8")
    except OSError:
        pass
    return token


def get_settings() -> Settings:
    # Electron already injects OPENAI_API_KEY into this process's env when it
    # spawns the backend (see electron/services/pythonProcess.cjs). This load
    # is a fallback for running the backend directly (per README), so it never
    # overrides an already-set value.
    load_dotenv(dotenv_path=REPO_ROOT / ".env.local", override=False)
    data_dir_env = os.environ.get("RICKY_DATA_DIR")
    data_dir = Path(data_dir_env) if data_dir_env else Path(__file__).resolve().parents[2] / "data"
    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
        local_token=_resolve_local_token(data_dir),
        exa_api_key=os.environ.get("EXA_API_KEY") or None,
        ai_provider=os.environ.get("RICKY_AI_PROVIDER") or "openai",
        minimax_api_key=os.environ.get("MINIMAX_API_KEY") or None,
        minimax_model=os.environ.get("MINIMAX_MODEL") or "MiniMax-M3",
        openai_model=os.environ.get("OPENAI_MODEL") or "gpt-4o-mini",
        openai_realtime_model=resolve_openai_realtime_model(
            os.environ.get("OPENAI_REALTIME_MODEL") or OPENAI_REALTIME_MODEL_DEFAULT
        ),
        data_dir=data_dir,
        # FAZA 19: PyInstaller sidecar receives host/port from Electron's env.
        # Defaults are fine for dev (uvicorn --host/--port CLI args take
        # precedence), but in a packaged build the .exe has no CLI args, so
        # these env vars are the only way to configure the listen address.
        host=os.environ.get("RICKY_HOST") or "127.0.0.1",
        port=int(os.environ["RICKY_PORT"]) if os.environ.get("RICKY_PORT") else 8765,
    )