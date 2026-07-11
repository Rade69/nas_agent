from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# Dictation Mode "Doradi" menu — full-text rewrite operations, not a chat/agent
# turn (no conversation state, no tools). Context: agent_reports/2026-07-11_dictation-rewrite-menu.md
TextRewriteOperation = Literal["formalize", "shorten", "proofread", "translate_en"]


class TextRewriteRequest(BaseModel):
    text: str
    operation: TextRewriteOperation


class TextRewriteResponse(BaseModel):
    text: str
