"""desktop/core/process_bridge.py — Qt <-> Python backend procesni most (QM-1).

Pokreće python_backend/ kao zaseban proces (Opcija A, QT_MIGRATION_PLAN §2.1),
generiše short-lived session token (env, nikad komandna linija), čeka /health
prije nego što vrati kontrolu, i garantuje gašenje djeteta preko Windows Job
Object-a (KILL_ON_JOB_CLOSE) + atexit. Zamjena za electron/services/pythonProcess.cjs
u Qt shell-u; python_backend/ se ne mijenja ni jednom linijom.
"""

from __future__ import annotations

import atexit
import logging
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from desktop.core.win_job_object import assign_to_job_object, close_job_object

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

log = logging.getLogger("ricky.process_bridge")


class BackendProcessError(RuntimeError):
    """Backend se nije pokrenuo ili nije odgovorio na health check (fail-closed)."""


def generate_session_token() -> str:
    """Short-lived lokalni auth token (isti nivo entropije kao Electron-ov
    `randomBytes(32).toString("hex")`)."""
    return secrets.token_bytes(32).hex()


def find_free_port(host: str = DEFAULT_HOST) -> int:
    """Rezerviše i vraća slobodan TCP port na zadatom host-u."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


class BackendClient:
    """Tanki httpx klijent ka backend-u sa Bearer tokenom (parity sa
    electron/services/pythonClient.cjs `requestJson`)."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(
        self,
        path: str,
        method: str = "GET",
        json: Any | None = None,
        timeout: float = 5.0,
    ) -> httpx.Response:
        return httpx.request(
            method,
            self.base_url + path,
            headers={"Authorization": f"Bearer {self.token}"},
            json=json,
            timeout=timeout,
        )

    def health(self, timeout: float = 1.0) -> bool:
        """Fail-closed: vraća False na bilo koju HTTP/grešku veze (ne diže)."""
        try:
            resp = httpx.get(
                self.base_url + "/health",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=timeout,
            )
            if resp.status_code != 200:
                return False
            return resp.json().get("ok") is True
        except httpx.HTTPError:
            return False


class BackendProcess:
    """Upravlja lifecycle-om python_backend pod-procesa."""

    def __init__(
        self,
        repo_root: Path | str | None = None,
        data_dir: Path | str | None = None,
        port: int | None = None,
        host: str = DEFAULT_HOST,
    ):
        # process_bridge.py → parents[0]=core, [1]=desktop, [2]=repo root.
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
        self.data_dir = Path(data_dir) if data_dir else self.repo_root / "data"
        self.host = host
        self.port = port
        self.token = generate_session_token()
        self.process: subprocess.Popen[str] | None = None
        self.status = "stopped"
        self._job_handle: int | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def client(self) -> BackendClient:
        return BackendClient(self.base_url, self.token)

    def _build_command(self) -> list[str]:
        # Frozen-safe (FABLE-5 review 2026-07-20): nikad hardkodiran "python"
        # interpreter — isti exe se re-invocira sa `--backend`. U dev-u
        # sys.executable je interpreter pa se desktop paket pokreće sa -m.
        if getattr(sys, "frozen", False):
            return [sys.executable, "--backend"]
        return [sys.executable, "-m", "desktop", "--backend"]

    def _build_env(self) -> dict[str, str]:
        # Token ide kroz env (RICKY_LOCAL_TOKEN), NIKAD kroz komandnu liniju —
        # command line args su vidljivi u process listi.
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["RICKY_HOST"] = self.host
        env["RICKY_PORT"] = str(self.port)
        env["RICKY_LOCAL_TOKEN"] = self.token
        env["RICKY_DATA_DIR"] = str(self.data_dir)
        return env

    def start(self, timeout_s: float = 30.0) -> None:
        """Spawn-uje backend, čeka health, ili diže BackendProcessError (fail-closed)."""
        if self.status in ("starting", "running"):
            return
        if self.port is None:
            self.port = find_free_port(self.host)

        self.status = "starting"
        self.process = subprocess.Popen(
            self._build_command(),
            cwd=str(self.repo_root),
            env=self._build_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self._start_log_reader()
        self._job_handle = assign_to_job_object(self.process.pid)
        atexit.register(self.stop)

        try:
            self._wait_for_health(timeout_s)
        except Exception:
            self.stop()
            raise
        self.status = "running"
        log.info("Backend ready at %s", self.base_url)

    def _start_log_reader(self) -> None:
        """Drain stdout u background niti (izbjegava pipe-buffer deadlock)."""

        def _drain() -> None:
            assert self.process is not None and self.process.stdout is not None
            for raw in self.process.stdout:
                line = raw.decode(errors="replace").rstrip()
                if line:
                    log.info("[backend] %s", line)

        threading.Thread(target=_drain, daemon=True).start()

    def _wait_for_health(self, timeout_s: float) -> None:
        deadline = time.monotonic() + timeout_s
        client = self.client
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise BackendProcessError(
                    f"Backend exited early (code {self.process.returncode})"
                )
            if client.health(timeout=1.0):
                return
            time.sleep(0.3)
        raise BackendProcessError(
            f"Backend health check timed out after {timeout_s:.0f}s at {self.base_url}"
        )

    def stop(self) -> None:
        """Zaustavlja backend: Job Object close (primarni, Windows) + terminate/kill
        fallback (non-Windows ili kad Job Object nije dostupan). Idempotentno."""
        if self._job_handle is not None:
            close_job_object(self._job_handle)
            self._job_handle = None

        proc, self.process = self.process, None
        if proc is None:
            self.status = "stopped"
            return

        if proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        self.status = "stopped"
