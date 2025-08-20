from fastapi import APIRouter, Depends, Request, Header
from typing import Any, Dict, Optional
from pydantic import BaseModel

from core.ai_agent import AIAgent
from core.dependencies import get_ai_agent
from core.models.schema import Prompt
from core.notification import get_notification_manager
from core.services.google_calendar_service import GoogleCalendarService

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


@router.post("/google/watch/start")
def start_google_watch(request: Request):
    """Khởi tạo Google Calendar watch webhook và lưu channel vào DB."""
    base_url = str(request.base_url).rstrip('/')
    callback_url = f"{base_url}/schedules/google/webhook"
    svc = GoogleCalendarService()
    result = svc.start_watch(callback_url)
    return {"message": "Watch started", "data": result}


@router.post("/google/watch/stop")
def stop_google_watch():
    svc = GoogleCalendarService()
    ok = svc.stop_watch()
    return {"message": "Watch stopped" if ok else "Failed to stop"}


@router.post("/google/sync")
def manual_google_sync():
    """Kéo các thay đổi mới nhất từ Google về local (có dùng syncToken)."""
    svc = GoogleCalendarService()
    result = svc.sync_from_google()
    return {"message": "Synced", "result": result}


@router.post("/google/webhook")
async def google_webhook(
    request: Request,
    x_goog_channel_id: Optional[str] = Header(None, convert_underscores=False),
    x_goog_resource_id: Optional[str] = Header(None, convert_underscores=False),
    x_goog_resource_state: Optional[str] = Header(None, convert_underscores=False),
    x_goog_message_number: Optional[str] = Header(None, convert_underscores=False),
):
    """
    Nhận notification từ Google. Theo best practice, khi nhận webhook chỉ cần
    trigger incremental sync.
    """
    svc = GoogleCalendarService()
    state = svc.get_sync_state()
ư
    if state.get('channel_id') and state.get('channel_id') != x_goog_channel_id:
        return {"status": "ignored", "reason": "channel mismatch"}
    if state.get('resource_id') and state.get('resource_id') != x_goog_resource_id:
        return {"status": "ignored", "reason": "resource mismatch"}

    result = svc.sync_from_google()
    return {"status": "ok", "synced": result}