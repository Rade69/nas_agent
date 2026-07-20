"""Pydantic models for thumbnail reference images (S-03, docs/
SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ThumbnailReferenceCreateRequest(BaseModel):
    path: str
    label: str | None = None


class ThumbnailReferenceResponse(BaseModel):
    # Deliberately no canonical_path field — the opaque id is the only
    # identifier this response ever exposes.
    id: str
    label: str | None = None
    preview_data_url: str


class ThumbnailReferenceResolveResponse(BaseModel):
    canonical_path: str


# ---------------------------------------------------------------------------
# QM-6T1: Thumbnail board models (docs/PI_TASK_QM6_THUMBNAIL_PYTHON_DOMAIN.md)
# ---------------------------------------------------------------------------


class ThumbnailBoardImage(BaseModel):
    id: str
    number: int
    type: str
    status: str
    path: str | None = None
    prompt: str
    size: str
    parent_id: str | None = None
    run_id: str | None = None
    created_at: str
    updated_at: str


class ThumbnailBoardState(BaseModel):
    selected_id: str | None = None
    view: str = "grid"
    page: int = 1
    page_size: int = 9


class ThumbnailBoardPageMeta(BaseModel):
    page: int
    page_size: int
    total_images: int
    total_pages: int
    next_number: int


class ThumbnailBoardSummary(BaseModel):
    view: str
    selected_number: int | None = None
    references: int = 0
    page: ThumbnailBoardPageMeta
    images: list[dict[str, Any]] = []


class ThumbnailBoardArtifact(BaseModel):
    title: str
    kind: str = "thumbnailBoard"
    fullscreen: bool = False
    content: str


# --- Request / Response models ---


class ThumbnailBoardResponse(BaseModel):
    ok: bool = True
    board: dict | None = None
    artifact: dict | None = None
    silent: bool = False
    thumbnail_ready: bool = False
    error: str | None = None


class ThumbnailLoadingPrepareRequest(BaseModel):
    prompt: str
    mode: str = "generate"
    number: int | None = None
    target_id: str | None = None


class ThumbnailGenerateRequest(BaseModel):
    prompt: str
    run_id: str | None = None
    references: list[str] = []


class ThumbnailEditRequest(BaseModel):
    prompt: str
    number: int | None = None
    target_id: str | None = None
    run_id: str | None = None
    references: list[str] = []


class ThumbnailSelectRequest(BaseModel):
    number: int


class ThumbnailGridRequest(BaseModel):
    page: int = 1


class ThumbnailBoardViewResponse(BaseModel):
    ok: bool = True
    board: dict | None = None
    artifact: dict | None = None


# Pydantic forward-reference fix: with `from __future__ import annotations`,
# models using complex forward references need explicit rebuild.
ThumbnailBoardResponse.model_rebuild()
ThumbnailBoardViewResponse.model_rebuild()
