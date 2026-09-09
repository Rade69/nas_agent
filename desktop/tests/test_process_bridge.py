"""Testovi za QM-1 process bridge (desktop/core/process_bridge.py).

Jedinični testovi pokrivaju token/port/command/env invarijante (token nikad u
cmdline, fail-closed health). Integracioni testovi (marker `integration`)
spawn-uju stvarni proces — pokrenuti sa `python -m pytest desktop/tests`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from desktop.core.process_bridge import (
    BackendClient,
    BackendProcess,
    BackendProcessError,
    find_free_port,
    generate_session_token,
)
from desktop.core.win_job_object import assign_to_job_object, close_job_object

ROOT = Path(__file__).resolve().parents[2]


# --- token ---

def test_token_is_64_hex_chars():
    t = generate_session_token()
    assert len(t) == 64
    assert all(c in "0123456789abcdef" for c in t)


def test_token_is_unique_per_call():
    assert generate_session_token() != generate_session_token()


# --- port ---

def test_find_free_port_returns_valid_port():
    port = find_free_port()
    assert 1024 <= port <= 65535


# --- command line invarijante ---

def test_command_contains_backend_flag():
    bp = BackendProcess()
    assert "--backend" in bp._build_command()


def test_token_never_in_command_line():
    bp = BackendProcess()
    cmd = bp._build_command()
    assert bp.token not in " ".join(cmd)


def test_env_contains_token_host_port_data_dir():
    bp = BackendProcess()
    bp.port = 12345
    env = bp._build_env()
    assert env["RICKY_LOCAL_TOKEN"] == bp.token
    assert env["RICKY_PORT"] == "12345"
    assert env["RICKY_HOST"] == "127.0.0.1"
    assert env["PYTHONUNBUFFERED"] == "1"
    assert env["RICKY_DATA_DIR"] == str(bp.data_dir)


# --- health fail-closed ---

def test_client_health_fail_closed_on_dead_port():
    client = BackendClient("http://127.0.0.1:1", "irrelevant-token")
    assert client.health(timeout=0.5) is False


def test_health_check_timeout_raises_backend_process_error(tmp_path):
    bp = BackendProcess(repo_root=ROOT, data_dir=tmp_path, port=1)
    with pytest.raises(BackendProcessError):
        bp.start(timeout_s=1.0)


# --- Windows Job Object (integracija) ---

@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object je Windows-only")
def test_job_object_kills_child_on_handle_close():
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    handle = assign_to_job_object(proc.pid)
    assert handle is not None

    # Zatvaranje handle-a simulira smrt roditelja — KILL_ON_JOB_CLOSE mora
    # natjerati kernel da ubije dijete bez eksplicitnog terminate().
    close_job_object(handle)
    proc.wait(timeout=10)
    assert proc.returncode is not None


# --- stvarni backend lifecycle (integracija) ---

@pytest.mark.integration
def test_backend_start_and_stop(tmp_path):
    import psutil

    bp = BackendProcess(repo_root=ROOT, data_dir=tmp_path)
    bp.start(timeout_s=90)
    try:
        assert bp.status == "running"
        assert bp.process is not None and bp.process.poll() is None
        pid = bp.process.pid
    finally:
        bp.stop()

    assert bp.status == "stopped"
    assert bp.process is None
    time.sleep(0.5)
    assert not psutil.pid_exists(pid)
