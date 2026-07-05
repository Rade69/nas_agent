"""Notes tool handlers (FAZA 11).

Low-risk memory tool migrated from the Electron JSON `db.notes` array. Notes
are short text items with optional tags. No confirmation or computer_mode
required (risk=low per SECURITY_MODEL.md).
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.services.notes_service import NotesService


def make_handlers(service: NotesService) -> dict[str, Any]:
    def note_add(arguments: dict[str, Any]) -> dict[str, Any]:
        text = arguments.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("note_add requires a non-empty 'text' string argument.")
        tags = arguments.get("tags")
        if tags is not None and not isinstance(tags, list):
            raise ValueError("'tags' must be an array of strings.")
        tags_list = [str(t) for t in tags] if isinstance(tags, list) else []
        note = service.create(text=text, tags=tags_list)
        return {
            "note": note,
            "artifact": {
                "title": "Fun Notes",
                "kind": "notes",
                "content": _render_notes(service.list(limit=20)),
            },
        }

    def note_search(arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query") or "")
        notes = service.search(query=query) if query else service.list(limit=20)
        return {
            "notes": notes,
            "artifact": {
                "title": f"Notes search: {query or 'all'}",
                "kind": "notes",
                "content": _render_notes(notes),
            },
        }

    def note_list(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 20)
        notes = service.list(limit=limit)
        return {
            "notes": notes,
            "artifact": {
                "title": "Fun Notes",
                "kind": "notes",
                "content": _render_notes(notes),
            },
        }

    return {"note_add": note_add, "note_search": note_search, "note_list": note_list}


def _render_notes(notes: list[dict[str, Any]]) -> str:
    if not notes:
        return "No notes yet."
    lines = []
    for note in notes:
        tags = note.get("tags") or []
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        lines.append(f"- {note['text']}{tag_str}")
    return "\n".join(lines)
