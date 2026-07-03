import uuid

from sqlalchemy.orm import Session

from app.tools.base import Tool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_declarations(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.arg_model.model_json_schema(),
            }
            for tool in self._tools.values()
        ]

    def dispatch(self, tool_name: str, raw_args: dict, customer_id: uuid.UUID | None, db: Session) -> dict:
        tool = self._tools[tool_name]
        validated = tool.arg_model(**raw_args)
        return tool.execute(validated, customer_id, db)
