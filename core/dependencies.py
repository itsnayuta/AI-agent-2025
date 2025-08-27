from fastapi import HTTPException
from core.ai_agent import AIAgent
from core.exceptions import GeminiAPIError

_ai_agent_instances = {}

def get_ai_agent(session_id: str = "default"):
    """Lấy hoặc tạo một instance của AIAgent cho session_id cụ thể."""
    global _ai_agent_instances
    
    if session_id not in _ai_agent_instances:
        try:
            _ai_agent_instances[session_id] = AIAgent(session_id=session_id)
        except GeminiAPIError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khởi tạo AI Agent: {e}")
    
    return _ai_agent_instances[session_id]

def clear_ai_agent_cache():
    """Xóa cache của tất cả AI Agent instances."""
    global _ai_agent_instances
    count = len(_ai_agent_instances)
    _ai_agent_instances.clear()
    return count