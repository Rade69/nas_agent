from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import AppError
from app.core.path_sandbox import (
    ensure_extension_allowed,
    ensure_file_size_allowed,
    resolve_within_roots,
)


def test_resolve_within_roots_allows_path_inside_root(tmp_path: Path) -> None:
    allowed = tmp_path / "workspace"
    allowed.mkdir()
    target = allowed / "notes.txt"
    target.write_text("hi")

    resolved = resolve_within_roots(target, [allowed])
    assert resolved == target.resolve()


def test_resolve_within_roots_blocks_traversal_outside_root(tmp_path: Path) -> None:
    allowed = tmp_path / "workspace"
    allowed.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("nope")

    traversal_path = allowed / ".." / "secret.txt"

    with pytest.raises(AppError) as excinfo:
        resolve_within_roots(traversal_path, [allowed])
    assert excinfo.value.code == "PATH_NOT_ALLOWED"


def test_resolve_within_roots_blocks_unrelated_absolute_path(tmp_path: Path) -> None:
    allowed = tmp_path / "workspace"
    allowed.mkdir()

    with pytest.raises(AppError) as excinfo:
        resolve_within_roots(Path("C:/Windows/System32/drivers/etc/hosts"), [allowed])
    assert excinfo.value.code == "PATH_NOT_ALLOWED"


def test_resolve_within_roots_blocks_unc_path(tmp_path: Path) -> None:
    allowed = tmp_path / "workspace"
    allowed.mkdir()

    with pytest.raises(AppError) as excinfo:
        resolve_within_roots("\\\\fileserver\\share\\doc.txt", [allowed])
    assert excinfo.value.code == "PATH_NOT_ALLOWED"


def test_resolve_within_roots_allows_second_root_when_first_does_not_match(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    target = root_b / "file.txt"
    target.write_text("x")

    resolved = resolve_within_roots(target, [root_a, root_b])
    assert resolved == target.resolve()


def test_ensure_extension_allowed_blocks_dangerous_extensions() -> None:
    with pytest.raises(AppError) as excinfo:
        ensure_extension_allowed(Path("payload.exe"))
    assert excinfo.value.code == "EXTENSION_BLOCKED"


def test_ensure_extension_allowed_permits_safe_extensions() -> None:
    ensure_extension_allowed(Path("notes.txt"))  # must not raise


def test_ensure_extension_allowed_override_permits_execution() -> None:
    ensure_extension_allowed(Path("tool.ps1"), allow_execution=True)  # must not raise


def test_ensure_file_size_allowed_blocks_oversized_file(tmp_path: Path) -> None:
    big_file = tmp_path / "big.bin"
    big_file.write_bytes(b"0" * 1024)

    with pytest.raises(AppError) as excinfo:
        ensure_file_size_allowed(big_file, max_bytes=100)
    assert excinfo.value.code == "FILE_TOO_LARGE"


def test_ensure_file_size_allowed_permits_small_file(tmp_path: Path) -> None:
    small_file = tmp_path / "small.txt"
    small_file.write_text("hi")

    ensure_file_size_allowed(small_file, max_bytes=100)  # must not raise


def test_ensure_file_size_allowed_ignores_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.txt"
    ensure_file_size_allowed(missing, max_bytes=1)  # must not raise
