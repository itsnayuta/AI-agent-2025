from fastapi import APIRouter, Depends, Request, Header, BackgroundTasks, HTTPException
from typing import Any, Dict, Optional
from pydantic import BaseModel

import os, sqlite3
from core.ai_agent import AIAgent
from core.dependencies import get_ai_agent
from core.models.schema import Prompt
from core.notification import get_notification_manager
from core.services.google_calendar_service import GoogleCalendarService
from core.config import Config
router = APIRouter(
    prefix="/schedules",
    tags=["schedules"]
)

class EmailSetupRequest(BaseModel):
    email: str

@router.post("/prompt", response_model=Dict[str, Any])
async def consultant_schedules(body: Prompt, session_id: str = "default"):
    """Xử lý yêu cầu từ người dùng với session support."""
    try:
        agent = get_ai_agent(session_id)
        response = await agent.process_user_input(body.content)
        return {
            "result": response,
            "session_id": session_id,
            "success": True
        }
    except Exception as e:
        return {
            "result": f"Lỗi: {str(e)}",
            "session_id": session_id,
            "success": False
        }

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


@router.post("/google/sync")
def manual_google_sync(background_tasks: BackgroundTasks):
    """Sync thủ công từ Google Calendar về local database."""
    def _do_manual_sync():
        try:
            svc = GoogleCalendarService()
            result = svc.sync_from_google()
            print(f"[Manual] {result}")
        except Exception as e:
            print(f"[Manual] Lỗi: {e}")
    
    background_tasks.add_task(_do_manual_sync)
    return {"message": "Sync queued"}

@router.post("/google/webhook")
def google_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_goog_channel_id: Optional[str] = Header(None, alias="x-goog-channel-id"),
    x_goog_resource_id: Optional[str] = Header(None, alias="x-goog-resource-id"),
    x_goog_resource_state: Optional[str] = Header(None, alias="x-goog-resource-state"),
    x_goog_message_number: Optional[str] = Header(None, alias="x-goog-message-number"),
):
    """Nhận webhook từ Google Calendar và trigger sync."""
    
    def _do_webhook_sync():
        try:
            svc = GoogleCalendarService()
            state = svc.get_sync_state()
            
            stored_channel = state.get('channel_id')
            stored_resource = state.get('resource_id')
            
            if not x_goog_channel_id and not x_goog_resource_id:
                pass  # Google test ping, cho phép sync
            elif stored_channel and stored_channel != x_goog_channel_id:
                print(f"[Webhook] Ignored: channel mismatch")
                return
            elif stored_resource and stored_resource != x_goog_resource_id:
                print(f"[Webhook] Ignored: resource mismatch")
                return

            result = svc.sync_from_google()
            if result.get('synced', 0) > 0:
                print(f"[Webhook] Synced {result['synced']} changes")
        except Exception as e:
            print(f"[Webhook] Error: {e}")

    background_tasks.add_task(_do_webhook_sync)
    return {"status": "ok"}

@router.get("/google/debug")
def debug_google_sync():
    """Kiểm tra trạng thái sync."""
    try:
        svc = GoogleCalendarService()
        state = svc.get_sync_state()
        
        conn = sqlite3.connect('database/schedule.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM schedules WHERE COALESCE(deleted, 0) = 0')
        active_schedules = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM schedules WHERE google_event_id IS NOT NULL AND COALESCE(deleted, 0) = 0')
        synced_schedules = cursor.fetchone()[0]
        conn.close()
        
        return {
            "sync_state": state,
            "files": {
                "credentials": os.path.exists('core/OAuth/credentials.json'),
                "token": os.path.exists('token.pickle')
            },
            "database": {
                "active_schedules": active_schedules,
                "synced_schedules": synced_schedules
            }
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/google/reset-webhook")
def reset_google_webhook():
    """Reset và tạo lại webhook."""
    try:
        svc = GoogleCalendarService()
        
        svc.stop_watch()
        
        public_base_url = Config.PUBLIC_BASE_URL
        if not public_base_url:
            return {"error": "Cần PUBLIC_BASE_URL"}
        
        webhook_url = f"{public_base_url}/schedules/google/webhook"
        watch_result = svc.start_watch(webhook_url)
        
        return {"message": "Reset webhook thành công", "watch": watch_result}
        
    except Exception as e:
        return {"error": str(e)}
class SessionRequest(BaseModel):
    session_id: str

class ConversationSearchRequest(BaseModel):
    query: str
    limit: int = 10

@router.get("/conversation/history")
def get_conversation_history(session_id: str = "default", limit: Optional[int] = None):
    """Lấy lịch sử conversation."""
    try:
        agent = AIAgent(session_id=session_id)
        history = agent.get_conversation_history(limit)
        return {
            "session_id": session_id,
            "history": history,
            "total": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversation/stats")
def get_conversation_stats(session_id: str = "default"):
    """Lấy thống kê conversation."""
    try:
        agent = AIAgent(session_id=session_id)
        stats = agent.get_conversation_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversation/clear")
def clear_conversation(session_id: str = "default"):
    """Xóa toàn bộ lịch sử conversation."""
    try:
        agent = AIAgent(session_id=session_id)
        deleted_count = agent.clear_conversation_history()
        return {
            "message": f"Đã xóa {deleted_count} tin nhắn",
            "session_id": session_id,
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversation/search")
def search_conversation(request: ConversationSearchRequest, session_id: str = "default"):
    """Tìm kiếm trong lịch sử conversation."""
    try:
        agent = AIAgent(session_id=session_id)
        results = agent.search_conversation(request.query, request.limit)
        return {
            "session_id": session_id,
            "query": request.query,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))