from fastapi import APIRouter, Depends
from typing import Any, Dict

from core.ai_agent import AIAgent
from core.dependencies import get_ai_agent
from core.models.schema import Prompt

router = APIRouter(
    prefix="/schedules",
    tags=["schedules"]
)

@router.post("/prompt", response_model=Dict[str, Any])
def consultant_schedules(body: Prompt, agent: AIAgent = Depends(get_ai_agent)):
    response = agent.process_user_input(body.content)
    return {"result": response}