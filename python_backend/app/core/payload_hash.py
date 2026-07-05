from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_payload(payload: dict[str, Any]) -> str:
    """Deterministic hash used to bind a confirmation to an exact tool payload.

    Sorted keys + explicit separators so equivalent dicts always hash the same
    regardless of key order (see SECURITY_HARDENING_PLAN.md section 25.3:
    a confirmation must be tied to the exact payload, not just the tool name).
    """
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
