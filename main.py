from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request

from core.routers import schedule_router
from contextlib import asynccontextmanager
import threading
import time
from core.notification import get_notification_manager
from core.config import Config
from core.services.google_calendar_service import GoogleCalendarService
from pyngrok import ngrok as _ngrok

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Khởi động hệ thống notification
    notification_manager = get_notification_manager()
    init_result = notification_manager.initialize()
    
    if init_result['success']:
        print("Ứng dụng đã khởi động hoàn tất!")

        if Config.AUTO_GOOGLE_SYNC:
            try:
                svc = GoogleCalendarService()
                
                svc.stop_watch()
                
                public_base_url = Config.PUBLIC_BASE_URL
                if not public_base_url:
                    try:
                        if _ngrok is None:
                            raise RuntimeError("pyngrok chưa được cài hoặc import thất bại")
                        if Config.NGROK_AUTHTOKEN:
                            _ngrok.set_auth_token(Config.NGROK_AUTHTOKEN)
                        tunnel = _ngrok.connect("http://127.0.0.1:8000", bind_tls=True)
                        public_base_url = tunnel.public_url
                        app.state._ngrok_tunnel = tunnel
                        print(f"[Dev] ngrok started at: {public_base_url}")
                    except Exception as ngrok_err:
                        print(f"[Dev] Không thể khởi động ngrok: {ngrok_err}")

                def _deferred_start_watch_and_sync(url: str):
                    time.sleep(2)
                    try:
                        cb = url.rstrip('/') + "/schedules/google/webhook"
                        info = svc.start_watch(cb)
                        print(f"[Google] Watch started: {info}")
                    except Exception as e:
                        print(f"[Google] Watch start error: {e}")
                    try:
                        backfill = svc.backfill_upcoming_days(days=30)
                        print(f"[Google] Backfill upcoming 30d: {backfill}")
                        sync_info = svc.sync_from_google()
                        print(f"[Google] Initial sync: {sync_info}")
                    except Exception as e:
                        print(f"[Google] Initial sync error: {e}")

                if public_base_url:
                    threading.Thread(target=_deferred_start_watch_and_sync, args=(public_base_url,), daemon=True).start()
                else:
                    print("[Google] Bỏ qua watch vì thiếu PUBLIC_BASE_URL")
            except Exception as e:
                print(f"[Google] Lỗi khởi động đồng bộ 2 chiều: {e}")
    else:
        print(f"Lỗi khởi tạo notification: {init_result.get('message', 'Unknown error')}")
    
    yield
    shutdown_result = notification_manager.shutdown()
    if shutdown_result['success']:
        print("Ứng dụng đã tắt!")
    try:
        tunnel = getattr(app.state, '_ngrok_tunnel', None)
        if tunnel is not None and _ngrok is not None:
            _ngrok.disconnect(tunnel.public_url)
    except Exception:
        pass
    

app = FastAPI(lifespan=lifespan)

# Mount static files (CSS, JS...)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include API router
app.include_router(schedule_router.router)

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
