from fastapi import HTTPException
from core.ai_agent import AIAgent
from core.exceptions import GeminiAPIError

_ai_agent_instance = None

def get_ai_agent():
    global _ai_agent_instance
    if _ai_agent_instance is None:
        try:
            _ai_agent_instance = AIAgent()
        except GeminiAPIError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khởi tạo AI Agent: {e}")
    return _ai_agent_instance