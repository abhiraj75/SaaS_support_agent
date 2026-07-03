from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.errors import register_error_handlers

app = FastAPI(title="Support Agent")

register_error_handlers(app)
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok"}
