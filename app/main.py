from fastapi import FastAPI

from app.routers.auth import router as auth_router


app = FastAPI(
    title="BayMax API",
)


app.include_router(auth_router)


@app.get("/")
async def root():
    return {
        "message": "BayMax API is running"
    }