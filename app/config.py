import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://agent:agent@localhost:5432/support_agent")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
