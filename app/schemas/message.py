from pydantic import BaseModel


class MessageCreate(BaseModel):
    message: str