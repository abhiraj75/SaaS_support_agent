import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.exceptions import LLMEmptyResponse, LLMUnavailable

_client = None

# google-genai does not retry 429s, and the free tier's per-minute cap is easy to hit.
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 0.5


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _build_contents(messages: list[dict]) -> list[types.Content]:
    contents = []
    for msg in messages:
        role = msg["role"]
        if role in ("user", "assistant"):
            # Gemini uses "model" for assistant turns
            gemini_role = "model" if role == "assistant" else "user"
            contents.append(types.Content(role=gemini_role, parts=[types.Part(text=msg["content"])]))
        elif role == "tool_call":
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part(function_call=types.FunctionCall(name=msg["name"], args=msg["args"]))],
                )
            )
        elif role == "tool_response":
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part(function_response=types.FunctionResponse(name=msg["name"], response=msg["result"]))],
                )
            )
    return contents


def _build_tools(declarations: list[dict]) -> list[types.Tool] | None:
    if not declarations:
        return None
    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=d["name"],
                    description=d["description"],
                    parameters=d["parameters"],
                )
                for d in declarations
            ]
        )
    ]


def _suggested_retry_after(exc: genai_errors.APIError) -> float | None:
    details = getattr(exc, "details", None)
    if not isinstance(details, dict):
        return None
    for item in details.get("error", {}).get("details", []):
        if str(item.get("@type", "")).endswith("RetryInfo"):
            raw = item.get("retryDelay", "")
            if isinstance(raw, str) and raw.endswith("s"):
                try:
                    return float(raw[:-1])
                except ValueError:
                    return None
    return None


def _generate_with_retry(contents, config):
    client = _get_client()
    delay = _BACKOFF_BASE_SECONDS
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
        except genai_errors.APIError as exc:
            retryable = isinstance(exc, genai_errors.ServerError) or exc.code == 429
            if not retryable or attempt == _MAX_RETRIES:
                raise LLMUnavailable(_suggested_retry_after(exc)) from exc
            time.sleep(delay)
            delay *= 2


def _parse_response(response) -> dict:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise LLMEmptyResponse("Gemini returned no candidates")

    candidate = candidates[0]
    parts = (candidate.content.parts if candidate.content else None) or []

    # a tool call is the action, so it wins over any leading commentary text
    for part in parts:
        if part.function_call:
            fc = part.function_call
            return {
                "type": "tool_call",
                "tool_name": fc.name,
                "arguments": dict(fc.args) if fc.args else {},
            }

    text = "".join(part.text for part in parts if part.text)
    if not text:
        raise LLMEmptyResponse(
            f"Gemini returned no usable content (finish_reason={candidate.finish_reason})"
        )
    return {"type": "text", "content": text}


def generate(messages: list[dict], tool_declarations: list[dict], system_prompt: str) -> dict:
    """Send messages to Gemini, return normalized {type, ...} response.

    Returns either:
        {"type": "tool_call", "tool_name": str, "arguments": dict}
        {"type": "text", "content": str}
    """
    contents = _build_contents(messages)
    tools = _build_tools(tool_declarations)

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.1,
    )
    if tools:
        config.tools = tools

    response = _generate_with_retry(contents, config)
    return _parse_response(response)
