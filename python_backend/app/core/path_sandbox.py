"""File system sandbox primitives (Security Gate 0 —
docs/SECURITY_HARDENING_PLAN.md section 10 "File system sandbox").

First real caller: app/services/thumbnail_reference_service.py (S-03, docs/
SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md) — validating a user-picked
reference image path before it's persisted and later uploaded to OpenAI.
Kept as a shared module (not inlined into that one caller) so the next tool
that accepts a user/model-supplied path has the same tested primitives to
validate against instead of re-implementing path safety ad hoc.
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

# S-03 (docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md): first real caller
# of this module, for thumbnail_reference registration. This is an ALLOWLIST
# (opposite polarity from BLOCKED_EXECUTION_EXTENSIONS above) — a reference
# image must match one of these, not merely avoid the executable blocklist.
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

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


def ensure_image_extension_allowed(path: Path) -> None:
    """Allowlist check for reference images (S-03) — the inverse of
    ensure_extension_allowed above. A path must match ALLOWED_IMAGE_EXTENSIONS
    exactly; anything else is rejected, including extensions that aren't on
    the dangerous-execution blocklist either (e.g. a .txt or .pdf renamed to
    look like an image is still not an image)."""
    if path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise AppError(
            "EXTENSION_NOT_ALLOWED",
            f"'{path.suffix}' is not an allowed image type: {path}",
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
