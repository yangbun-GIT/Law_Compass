from __future__ import annotations

from fastapi import APIRouter, Header

from app.routers.internal_auth import check_internal_token
from app.services.chat.chat_orchestrator import handle_chat_message

router = APIRouter()


@router.post("/chat/message")
async def chat_message(payload: dict, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return handle_chat_message(payload)
