from fastapi import FastAPI
from app.core import firebase

from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router



app = FastAPI(
    title="BayMax Server",
)


app.include_router(auth_router)
app.include_router(chat_router)




@app.get("/")
async def root():
    return {
        "message": "BayMax Server is running"
    }