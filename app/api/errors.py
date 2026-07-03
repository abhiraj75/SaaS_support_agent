from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import ConversationNotFound, LLMEmptyResponse, LLMUnavailable, ToolLoopExceeded


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

    @app.exception_handler(LLMUnavailable)
    def _llm_unavailable(request: Request, exc: LLMUnavailable):
        if exc.retry_after is not None:
            message = "The language model is rate-limited right now. Please retry in a moment."
            headers = {"Retry-After": str(int(exc.retry_after))}
        else:
            message = "The language model is temporarily unavailable. Please retry shortly."
            headers = {}
        return JSONResponse(status_code=503, content={"error": message}, headers=headers)

    @app.exception_handler(LLMEmptyResponse)
    def _llm_empty_response(request: Request, exc: LLMEmptyResponse):
        return JSONResponse(
            status_code=502,
            content={"error": "The language model returned an unusable response. Please try again."},
        )
