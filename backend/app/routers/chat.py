"""
AI Chat endpoints - Claude API integration
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_async_session, ChatSession, ChatMessage, MessageRole
from app.models.schemas import ChatMessageInput, ChatResponse, ChatMessageResponse
from app.services.ai_service import AIService

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def send_message(
    data: ChatMessageInput,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Verstuur een bericht naar de AI assistent.

    De AI kan:
    - Vragen beantwoorden over planning, omzet, beschikbaarheid
    - Acties uitvoeren: workshops aanmaken, wijzigen, toewijzingen maken
    - Scenario's doorrekenen

    Voorbeelden:
    - "Hoeveel omzet hebben we gepland voor Q1?"
    - "Kan Nienke volgende week dinsdag?"
    - "Plan een BWS in voor maart in Utrecht"
    - "Wat gebeurt er met de omzet als de BWS van 15 januari niet doorgaat?"
    """
    ai_service = AIService(session)

    # Get or create chat session
    if data.session_id:
        chat_session = await ai_service.get_session(data.session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat sessie niet gevonden")
    else:
        chat_session = await ai_service.create_session()

    # Save user message
    user_message = ChatMessage(
        session_id=chat_session.id,
        role=MessageRole.USER,
        content=data.content,
    )
    session.add(user_message)
    await session.flush()

    # Get AI response
    response = await ai_service.process_message(chat_session, data.content)

    # Save assistant message
    assistant_message = ChatMessage(
        session_id=chat_session.id,
        role=MessageRole.ASSISTANT,
        content=response["content"],
        function_call=response.get("function_call"),
        function_result=response.get("function_result"),
    )
    session.add(assistant_message)
    await session.commit()

    return ChatResponse(
        session_id=chat_session.id,
        message=ChatMessageResponse(
            id=assistant_message.id,
            role="assistant",
            content=response["content"],
            function_call=response.get("function_call"),
            created_at=assistant_message.created_at,
        ),
        requires_confirmation=response.get("requires_confirmation", False),
        pending_action=response.get("pending_action"),
    )


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    session: AsyncSession = Depends(get_async_session),
):
    """Haal chat geschiedenis op voor een sessie"""
    ai_service = AIService(session)
    messages = await ai_service.get_history(session_id, limit)

    return {
        "session_id": session_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role.value,
                "content": m.content,
                "function_call": m.function_call,
                "created_at": m.created_at,
            }
            for m in messages
        ],
    }


@router.post("/confirm/{session_id}")
async def confirm_action(
    session_id: str,
    action_id: str,
    confirmed: bool,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Bevestig of annuleer een actie die bevestiging vereist.

    Destructieve acties (verwijderen, annuleren) vereisen bevestiging.
    """
    ai_service = AIService(session)

    if confirmed:
        result = await ai_service.execute_pending_action(session_id, action_id)
        return {
            "status": "executed",
            "result": result,
        }
    else:
        await ai_service.cancel_pending_action(session_id, action_id)
        return {
            "status": "cancelled",
        }


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Verwijder een chat sessie en alle berichten"""
    ai_service = AIService(session)
    await ai_service.delete_session(session_id)

    return {"message": "Sessie verwijderd", "id": session_id}
