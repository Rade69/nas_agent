"""Artifact tool handlers (FAZA 11).

Tools for creating, fetching, and listing structured artifacts in the Python
backend. The `artifact_show` flow is also supported as a thin passthrough that
simply stores whatever the model provided and returns it for the artifact panel.
"""
from __future__ import annotations

import json
from typing import Any

from app.services.artifact_service import ArtifactService


def make_handlers(service: ArtifactService) -> dict[str, Any]:
    def artifact_create(arguments: dict[str, Any]) -> dict[str, Any]:
        title = arguments.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("artifact_create requires a 'title' string argument.")
        kind = str(arguments.get("kind") or "text")
        content = arguments.get("content")
        if content is None:
            raise ValueError("artifact_create requires a 'content' argument.")
        artifact = service.create(
            type=kind,
            title=title,
            content=content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
        )
        return {
            "artifact": artifact,
            "artifact_id": artifact["id"],
        }

    def artifact_get(arguments: dict[str, Any]) -> dict[str, Any]:
        artifact_id = str(arguments.get("id") or "")
        if not artifact_id:
            raise ValueError("artifact_get requires an 'id' string argument.")
        artifact = service.get(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact '{artifact_id}' not found.")
        return {"artifact": artifact}

    def artifact_list(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 20)
        type_filter = arguments.get("type")
        artifacts = service.list(limit=limit, type=type_filter if isinstance(type_filter, str) else None)
        return {"artifacts": artifacts}

    def artifact_show(arguments: dict[str, Any]) -> dict[str, Any]:
        # Thin passthrough: model already provided a full artifact payload; store
        # it so the event bridge can surface it to the UI artifact panel.
        title = str(arguments.get("title") or "Artifact")
        kind = str(arguments.get("kind") or "text")
        content = arguments.get("content")
        if content is None:
            content = json.dumps(arguments, ensure_ascii=False)
        artifact = service.create(
            type=kind,
            title=title,
            content=content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
        )
        return {"artifact": artifact, "artifact_id": artifact["id"]}

    return {
        "artifact_create": artifact_create,
        "artifact_get": artifact_get,
        "artifact_list": artifact_list,
        "artifact_show": artifact_show,
    }
