from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import ConversationNotFound, ToolLoopExceeded


def register_error_handlers(app):
    @app.exception_handler(ConversationNotFound)
    def _conversation_not_found(request: Request, exc: ConversationNotFound):
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @app.exception_handler(ToolLoopExceeded)
    def _tool_loop_exceeded(request: Request, exc: ToolLoopExceeded):
        return JSONResponse(
            status_code=422,
            content={"error": "Agent exceeded maximum tool iterations without producing a response"},
        )
