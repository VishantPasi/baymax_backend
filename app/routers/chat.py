# import json

# from fastapi import APIRouter, Depends, HTTPException
# from fastapi.responses import StreamingResponse

# from app.schemas.chat import ChatRequest
# from app.services.llm_service import LLMService

# # Change this import to match your existing authentication
# from app.core.dependencies import get_current_user


# router = APIRouter(
#     prefix="/ai",
#     tags=["AI"]
# )


# @router.post("/chat")
# async def chat(
#     request: ChatRequest,
#     current_user=Depends(get_current_user)
# ):

#     if not request.message.strip():
#         raise HTTPException(
#             status_code=400,
#             detail="Message cannot be empty"
#         )

#     messages = [
#         {
#             "role": "user",
#             "content": request.message
#         }
#     ]

#     async def generate():

#         try:

#             async for chunk in LLMService.generate_stream(
#                 messages
#             ):

#                 data = {
#                     "content": chunk
#                 }

#                 yield f"data: {json.dumps(data)}\n\n"

#             yield "data: [DONE]\n\n"

#         except Exception as e:

#             error_data = {
#                 "error": str(e)
#             }

#             yield (
#                 f"data: {json.dumps(error_data)}\n\n"
#             )

#     return StreamingResponse(
#         generate(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "X-Accel-Buffering": "no"
#         }
#     )



import json

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ChatSession, ChatMessage, User
from app.schemas.chat import (ChatCreate, ChatResponse, ChatDetailResponse, PaginatedChatMessagesResponse, PaginatedChatsResponse,)
from sqlalchemy.orm import selectinload
from app.schemas.message import MessageCreate
from app.core.dependencies import get_current_user
from app.services.llm_service import LLMService


router = APIRouter(
    prefix="/chats",
    tags=["Chats"],
)

@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat(
    chat: ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_chat = ChatSession(
        user_id=current_user.id,
        title=chat.title,
    )

    db.add(new_chat)

    await db.commit()
    await db.refresh(new_chat)

    return new_chat


@router.get(
    "",
    response_model=PaginatedChatsResponse,
)
async def get_chats(
    page: int = Query(
        1,
        ge=1,
        description="Page number"
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of chats per page"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * page_size

    # ---------------------------------------------
    # Total number of chats
    # ---------------------------------------------

    total_result = await db.execute(
        select(func.count())
        .select_from(ChatSession)
        .where(
            ChatSession.user_id == current_user.id
        )
    )

    total = total_result.scalar_one()

    # ---------------------------------------------
    # Get current page
    # ---------------------------------------------

    result = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.user_id == current_user.id
        )
        .order_by(
            ChatSession.updated_at.desc()
        )
        .offset(offset)
        .limit(page_size)
    )

    chats = result.scalars().all()

    # ---------------------------------------------
    # Check if another page exists
    # ---------------------------------------------

    has_next = offset + len(chats) < total

    return PaginatedChatsResponse(
        items=chats,
        page=page,
        page_size=page_size,
        total=total,
        has_next=has_next,
    )


@router.get(
    "/{chat_id}",
    response_model=PaginatedChatMessagesResponse,
)
async def get_chat(
    chat_id: int,
    page: int = Query(
        1,
        ge=1,
        description="Page number"
    ),
    page_size: int = Query(
        50,
        ge=1,
        le=100,
        description="Number of messages per page"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ---------------------------------------------
    # Get chat
    # ---------------------------------------------

    chat_result = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.id == chat_id,
            ChatSession.user_id == current_user.id,
        )
    )

    chat = chat_result.scalar_one_or_none()

    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # ---------------------------------------------
    # Total messages
    # ---------------------------------------------

    total_result = await db.execute(
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.chat_id == chat_id
        )
    )

    total = total_result.scalar_one()

    # ---------------------------------------------
    # Get messages
    # ---------------------------------------------

    offset = (page - 1) * page_size

    messages_result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.chat_id == chat_id
        )
        .order_by(
            ChatMessage.created_at.asc()
        )
        .offset(offset)
        .limit(page_size)
    )

    messages = messages_result.scalars().all()

    # ---------------------------------------------
    # Pagination information
    # ---------------------------------------------

    has_next = offset + len(messages) < total

    return PaginatedChatMessagesResponse(
        chat_id=chat.id,
        title=chat.title,
        messages=messages,
        page=page,
        page_size=page_size,
        total=total,
        has_next=has_next,
    )


@router.post(
    "/{chat_id}/messages",
)
async def send_message(
    chat_id: int,
    message: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # --------------------------------------------------
    # 1. Validate message
    # --------------------------------------------------

    if not message.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    # --------------------------------------------------
    # 2. Find chat and verify ownership
    # --------------------------------------------------

    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(
            ChatSession.id == chat_id,
            ChatSession.user_id == current_user.id,
        )
    )

    chat = result.scalar_one_or_none()

    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # --------------------------------------------------
    # 3. Save user's message
    # --------------------------------------------------

    user_message = ChatMessage(
        chat_id=chat.id,
        role="user",
        content=message.message,
    )

    db.add(user_message)

    await db.commit()
    await db.refresh(user_message)

    # --------------------------------------------------
    # 4. Build conversation history
    # --------------------------------------------------

    messages = []

    for msg in chat.messages:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })

    # Add the newly-created message because
    # chat.messages was loaded before we inserted it.
    messages.append({
        "role": "user",
        "content": message.message,
    })

    # --------------------------------------------------
    # 5. Stream response from LLM
    # --------------------------------------------------

    async def generate():

        full_response = ""

        try:

            async for chunk in LLMService.generate_stream(
                messages
            ):

                full_response += chunk

                data = {
                    "content": chunk
                }

                yield f"data: {json.dumps(data)}\n\n"

            # --------------------------------------------------
            # 6. Save complete AI response
            # --------------------------------------------------

            assistant_message = ChatMessage(
                chat_id=chat.id,
                role="assistant",
                content=full_response,
            )

            db.add(assistant_message)

            await db.commit()

            # --------------------------------------------------
            # 7. Tell Flutter streaming is finished
            # --------------------------------------------------

            yield "data: [DONE]\n\n"

        except Exception as e:

            await db.rollback()

            error_data = {
                "error": str(e)
            }

            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )