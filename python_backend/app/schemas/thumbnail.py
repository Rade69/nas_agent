"""Pydantic models for thumbnail reference images (S-03, docs/
SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md).
"""
from __future__ import annotations

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
