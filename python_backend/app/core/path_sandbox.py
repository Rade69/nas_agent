"""File system sandbox primitives (Security Gate 0 —
docs/SECURITY_HARDENING_PLAN.md section 10 "File system sandbox").

No tool registers arbitrary file paths yet (screenshots/artifacts write to a
backend-controlled path, not a user/model-supplied one), so nothing calls
these functions in production today. They exist so the *first* tool that
does accept a path (a future Document Engine tool, or FAZA 13's
computer_open_app) has a single, already-tested place to validate against
instead of each tool re-implementing path safety ad hoc.
"""
from __future__ import annotations

from pathlib import Path

from app.core.errors import AppError

BLOCKED_EXECUTION_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".ps1",
    ".vbs",
    ".js",
    ".msi",
    ".scr",
    ".reg",
}

DEFAULT_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB, MVP default


def resolve_within_roots(path: str | Path, allowed_roots: list[Path]) -> Path:
    """Canonicalize `path` and confirm it resolves inside one of `allowed_roots`.

    Resolving symlinks and `..` segments before the containment check (rather
    than string-matching for "..") means a symlink that points outside every
    allowed root is caught the same way plain traversal is — both end up as a
    resolved path that fails every `relative_to` check below.
    """
    candidate = Path(path)
    if _is_unc_or_network_path(candidate):
        raise AppError(
            "PATH_NOT_ALLOWED",
            f"Network/UNC paths are not allowed: {path}",
            status_code=403,
        )

    resolved = candidate.resolve()
    for root in allowed_roots:
        resolved_root = root.resolve()
        try:
            resolved.relative_to(resolved_root)
            return resolved
        except ValueError:
            continue
    raise AppError(
        "PATH_NOT_ALLOWED",
        f"Path is outside the allowed workspace: {path}",
        status_code=403,
    )


def _is_unc_or_network_path(path: Path) -> bool:
    text = str(path)
    return text.startswith("\\\\") or text.startswith("//")


def ensure_extension_allowed(path: Path, *, allow_execution: bool = False) -> None:
    """Block execution of known dangerous script/binary extensions.

    `allow_execution=True` is an explicit admin/developer override escape
    hatch per SECURITY_HARDENING_PLAN.md section 10 ("Osim ako postoji
    poseban admin/developer allowlist") — no caller sets it yet.
    """
    if allow_execution:
        return
    if path.suffix.lower() in BLOCKED_EXECUTION_EXTENSIONS:
        raise AppError(
            "EXTENSION_BLOCKED",
            f"Files with extension '{path.suffix}' cannot be executed: {path}",
            status_code=403,
        )


def ensure_file_size_allowed(path: Path, *, max_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES) -> None:
    if not path.exists():
        return
    size = path.stat().st_size
    if size > max_bytes:
        raise AppError(
            "FILE_TOO_LARGE",
            f"File exceeds max allowed size ({max_bytes} bytes): {path} is {size} bytes",
            status_code=403,
        )
