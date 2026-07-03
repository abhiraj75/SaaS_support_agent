class ConversationNotFound(Exception):
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        super().__init__(f"Conversation {conversation_id} not found")


class ToolLoopExceeded(Exception):
    pass


class LLMUnavailable(Exception):
    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__("LLM provider unavailable")


class LLMEmptyResponse(Exception):
    pass
