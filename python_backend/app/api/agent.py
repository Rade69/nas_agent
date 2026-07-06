from fastapi import APIRouter, Path, Request

from app.agent.runtime import LocalDesktopAssistant
from app.core.errors import AppError
from app.schemas.agent import AgentConversationResponse, AgentSendMessageRequest, AgentSendMessageResponse

router = APIRouter(tags=["agent"])


def _assistant(request: Request) -> LocalDesktopAssistant:
    assistant = getattr(request.app.state, "agent_runtime", None)
    if assistant is None:
        raise AppError("AGENT_RUNTIME_UNAVAILABLE", "Agent runtime is not initialized.", status_code=500)
    return assistant


@router.post("/agent/message", response_model=AgentSendMessageResponse)
def send_agent_message(request_body: AgentSendMessageRequest, request: Request) -> AgentSendMessageResponse:
    result = _assistant(request).handle_message(
        conversation_id=request_body.conversation_id,
        message=request_body.message,
        computer_mode=request_body.computer_mode,
    )
    return AgentSendMessageResponse(**result)


@router.get("/agent/conversations/{conversation_id}", response_model=AgentConversationResponse)
def get_agent_conversation(
    request: Request,
    conversation_id: str = Path(..., min_length=1),
) -> AgentConversationResponse:
    conversations = getattr(request.app.state, "conversation_state_service", None)
    if conversations is None:
        raise AppError("AGENT_RUNTIME_UNAVAILABLE", "Conversation state service is not initialized.", status_code=500)
    conversation = conversations.get_conversation(conversation_id)
    if conversation is None:
        raise AppError("CONVERSATION_NOT_FOUND", f"Conversation '{conversation_id}' not found.", status_code=404)
    return conversation
