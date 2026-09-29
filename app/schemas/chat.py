from datetime import datetime
from pydantic import BaseModel


class ChatCreate(BaseModel):
    title: str


class ChatResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedChatsResponse(BaseModel):
    items: list[ChatResponse]
    page: int
    page_size: int
    total: int
    has_next: bool


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    class Config:
        from_attributes = True


class PaginatedChatMessagesResponse(BaseModel):
    chat_id: int
    title: str
    messages: list[MessageResponse]
    page: int
    page_size: int
    total: int
    has_next: bool