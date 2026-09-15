import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services.llm_service import LLMService

# Change this import to match your existing authentication
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/ai",
    tags=["AI"]
)


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user=Depends(get_current_user)
):

    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    messages = [
        {
            "role": "user",
            "content": request.message
        }
    ]

    async def generate():

        try:

            async for chunk in LLMService.generate_stream(
                messages
            ):

                data = {
                    "content": chunk
                }

                yield f"data: {json.dumps(data)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:

            error_data = {
                "error": str(e)
            }

            yield (
                f"data: {json.dumps(error_data)}\n\n"
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

