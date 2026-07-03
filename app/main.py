from fastapi import FastAPI

from app.api.articles import router as articles_router
from app.api.chat import router as chat_router
from app.api.errors import register_error_handlers
from app.api.feedback import router as feedback_router

app = FastAPI(title="Support Agent")

register_error_handlers(app)
app.include_router(chat_router)
app.include_router(feedback_router)
app.include_router(articles_router)


@app.get("/health")
def health():
    return {"status": "ok"}

