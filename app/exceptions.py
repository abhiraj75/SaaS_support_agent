class ConversationNotFound(Exception):
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        super().__init__(f"Conversation {conversation_id} not found")


class ToolLoopExceeded(Exception):
    pass
