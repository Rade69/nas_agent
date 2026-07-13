"""POST /text/rewrite — Dictation Mode "Doradi" menu backend.

Plain text-in/text-out model call for formalize/shorten/proofread/
translate_en operations. Deliberately NOT routed through the agent
runtime (which would persist conversation state — wrong semantics).
"""
from fastapi import APIRouter, Request

from app.agent.model_client import ModelClient
from app.core.errors import AppError
from app.schemas.text import TextRewriteOperation, TextRewriteRequest, TextRewriteResponse

router = APIRouter(tags=["text"])

# One-line instruction per "Doradi" menu action. Each must return ONLY the
# rewritten text — no preamble, no explanation — since the response replaces
# dictationText verbatim in the editor.
_OPERATION_PROMPTS: dict[TextRewriteOperation, str] = {
    "formalize": (
        "Preformuliši sljedeći tekst na formalniji, poslovni ton. Zadrži isti "
        "jezik i značenje. Vrati SAMO prerađeni tekst, bez objašnjenja i bez navodnika."
    ),
    "shorten": (
        "Skrati sljedeći tekst zadržavajući ključne informacije i isti jezik. "
        "Vrati SAMO skraćenu verziju, bez objašnjenja i bez navodnika."
    ),
    "proofread": (
        "Ispravi pravopisne i gramatičke greške u sljedećem tekstu. Ne mijenjaj "
        "stil niti značenje. Vrati SAMO ispravljen tekst, bez objašnjenja i bez navodnika."
    ),
    "translate_en": (
        "Prevedi sljedeći tekst na engleski jezik. Vrati SAMO prevod, bez "
        "objašnjenja i bez navodnika."
    ),
}


def _model_client(request: Request) -> ModelClient:
    client = getattr(request.app.state, "text_model_client", None)
    if client is None:
        raise AppError("TEXT_MODEL_UNAVAILABLE", "Text rewrite model client is not initialized.", status_code=500)
    return client


@router.post("/text/rewrite", response_model=TextRewriteResponse)
def rewrite_text(request_body: TextRewriteRequest, request: Request) -> TextRewriteResponse:
    text = request_body.text.strip()
    if not text:
        raise AppError("EMPTY_TEXT", "Text must not be empty.", status_code=400)

    client = _model_client(request)
    prompt = _OPERATION_PROMPTS[request_body.operation]
    response = client.complete(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        tools=[],
    )
    # Never let an empty/failed model reply wipe out the user's dictated text.
    return TextRewriteResponse(text=response.content or request_body.text)
