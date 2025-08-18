from fastapi import APIRouter, Depends
from typing import Any, Dict, Optional
from pydantic import BaseModel

from core.ai_agent import AIAgent
from core.dependencies import get_ai_agent
from core.models.schema import Prompt
from core.notification import get_notification_manager

router = APIRouter(
    prefix="/schedules",
    tags=["schedules"]
)

class EmailSetupRequest(BaseModel):
    email: str

@router.post("/prompt", response_model=Dict[str, Any])
def consultant_schedules(body: Prompt, agent: AIAgent = Depends(get_ai_agent)):
    response = agent.process_user_input(body.content)
    return {"result": response}

@router.get("/notification-status")
def get_notification_status():
    """Lấy trạng thái hệ thống notification"""
    manager = get_notification_manager()
    return manager.get_system_status()

@router.post("/setup-email")
def setup_email(request: EmailSetupRequest):
    """Thiết lập email nhận thông báo"""
    manager = get_notification_manager()
    return manager.setup_email(request.email)

@router.post("/test-email")
def test_email(request: EmailSetupRequest):
    """Test gửi email để kiểm tra cấu hình SMTP"""
    manager = get_notification_manager()
    return manager.test_email_send(request.email)