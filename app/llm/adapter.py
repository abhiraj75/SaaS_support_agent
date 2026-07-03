from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)


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

    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=config,
    )

    part = response.candidates[0].content.parts[0]

    if part.function_call:
        fc = part.function_call
        return {
            "type": "tool_call",
            "tool_name": fc.name,
            "arguments": dict(fc.args) if fc.args else {},
        }

    return {"type": "text", "content": part.text}
