# -*- mode: python ; coding: utf-8 -*-
#
# FAZA 19: PyInstaller spec za Python backend sidecar (--onedir).
#
# Pokretanje:
#   cd python_backend
#   pyinstaller --clean --noconfirm ricky_backend.spec
#
# Rezultat: python_backend/dist/ricky_backend/ricky_backend.exe
# Ovaj folder se kopira kao extraFiles u electron-builder paket.
#
# Context: agent_reports/2026-07-06_faza19-packaging-plan.md
#          docs/PACKAGING_PLAN.md
#

import sys
from pathlib import Path

block_cipher = None

# Dodaj python_backend/ u sys.path da PyInstaller može naći sve app/* module.
_here = Path(SPECPATH).resolve()  # SPECPATH = dir gdje je .spec fajl = python_backend/
sys.path.insert(0, str(_here))

a = Analysis(
    ["app/main.py"],
    pathex=[str(_here)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "app.agent",
        "app.agent.tool_registry",
        "app.agent.tool_executor",
        "app.agent.permission_engine",
        "app.agent.cancellation",
        "app.agent.conversation_state",
        "app.agent.model_client",
        "app.agent.prompt_builder",
        "app.agent.runtime",
        "app.api",
        "app.api.health",
        "app.api.tools",
        "app.api.realtime",
        "app.api.confirmations",
        "app.api.plans",
        "app.api.events",
        "app.api.agent",
        "app.api.security",
        "app.core",
        "app.core.config",
        "app.core.errors",
        "app.core.logging",
        "app.core.auth",
        "app.core.payload_hash",
        "app.core.path_sandbox",
        "app.core.security_self_test",
        "app.schemas",
        "app.schemas.common",
        "app.schemas.tool",
        "app.schemas.realtime",
        "app.schemas.confirmation",
        "app.schemas.plan",
        "app.schemas.agent",
        "app.services",
        "app.services.action_log",
        "app.services.artifact_service",
        "app.services.confirmation_service",
        "app.services.event_bus",
        "app.services.notes_service",
        "app.services.plan_service",
        "app.services.records_service",
        "app.services.exa_client",
        "app.services.openai_image_client",
        "app.storage",
        "app.storage.db",
        "app.tools",
        "app.tools.artifacts",
        "app.tools.memory",
        "app.tools.memory.notes",
        "app.tools.memory.records",
        "app.tools.system",
        "app.tools.system.screenshot",
        "app.tools.system.ui_inspect",
        "app.tools.web",
        "app.tools.web.search",
        "app.tools.images",
        "app.tools.images.generate",
        # storage repos (lazy-loaded in main.py, must be explicit)
        "app.storage.repositories",
        "app.storage.repositories.tool_run_repo",
        "app.storage.repositories.confirmation_repo",
        "app.storage.repositories.plan_repo",
        "app.storage.repositories.notes_repo",
        "app.storage.repositories.records_repo",
        "app.storage.repositories.artifact_repo",
        "app.storage.repositories.event_repo",
        "app.storage.repositories.agent_repo",
        # third-party deps
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ricky_backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI app — no console window, logs go to file or stdout pipe
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# --onedir: keep the internal Python distribution in a folder so electron-builder
# can include the entire folder as extraFiles without bundling a single huge exe.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ricky_backend",
)
