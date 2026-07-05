"""Records tool handlers (FAZA 11).

Structured local-database records migrated from the Electron JSON `db.records`
array. A record is a titled item in a named collection with arbitrary fields.
records_delete requires confirmation (destructive = critical) — confirmation
enforcement is FAZA 10; here we expose the tool with the right risk flag.
"""
from __future__ import annotations

import json
from typing import Any

from app.services.records_service import RecordsService


def make_handlers(service: RecordsService) -> dict[str, Any]:
    def records_create(arguments: dict[str, Any]) -> dict[str, Any]:
        collection = str(arguments.get("collection") or "default")
        title = arguments.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("records_create requires a 'title' string argument.")
        fields = arguments.get("fields")
        if fields is not None and not isinstance(fields, dict):
            raise ValueError("'fields' must be an object.")
        fields_dict = fields if isinstance(fields, dict) else {}
        record = service.create(
            collection=collection,
            title=title,
            fields=fields_dict,
        )
        return {
            "record": record,
            "artifact": _records_artifact(service.list_in_collection(collection), collection),
        }

    def records_search(arguments: dict[str, Any]) -> dict[str, Any]:
        collection = str(arguments.get("collection") or "default")
        query = str(arguments.get("query") or "")
        records = service.search(collection=collection, query=query)
        return {
            "records": records,
            "artifact": _records_artifact(records, collection),
        }

    def records_update(arguments: dict[str, Any]) -> dict[str, Any]:
        record_id = str(arguments.get("id") or "")
        if not record_id:
            raise ValueError("records_update requires an 'id' string argument.")
        title = arguments.get("title")
        if title is not None and not isinstance(title, str):
            raise ValueError("'title' must be a string.")
        fields_merge = arguments.get("fields")
        if fields_merge is not None and not isinstance(fields_merge, dict):
            raise ValueError("'fields' must be an object.")
        record = service.update(
            record_id=record_id,
            title=title if isinstance(title, str) else None,
            fields_merge=fields_merge if isinstance(fields_merge, dict) else None,
        )
        if record is None:
            raise ValueError(f"Record '{record_id}' not found.")
        return {
            "record": record,
            "artifact": _records_artifact(service.list_in_collection(record["collection"]), record["collection"]),
        }

    def records_delete(arguments: dict[str, Any]) -> dict[str, Any]:
        # Confirmation is enforced by the permission/risk layer (FAZA 10). The
        # tool definition carries requires_confirmation=True; until FAZA 10 lands,
        # we honor an explicit `confirmed: true` argument (legacy-compatible with
        # the existing Electron handler).
        if arguments.get("confirmed") is not True:
            raise ValueError("records_delete requires explicit confirmation (confirmed=true).")
        record_id = str(arguments.get("id") or "")
        if not record_id:
            raise ValueError("records_delete requires an 'id' string argument.")
        deleted = service.delete(record_id)
        return {"deleted": deleted}

    return {
        "records_create": records_create,
        "records_search": records_search,
        "records_update": records_update,
        "records_delete": records_delete,
    }


def _records_artifact(records: list[dict[str, Any]], collection: str) -> dict[str, Any]:
    if not records:
        return {"title": f"Records: {collection}", "kind": "text", "content": "No records in this collection."}
    content = json.dumps(records, indent=2, ensure_ascii=False)
    return {"title": f"Records: {collection}", "kind": "notes", "content": content}
