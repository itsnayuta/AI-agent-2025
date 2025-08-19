from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request

from core.routers import schedule_router
from contextlib import asynccontextmanager
from core.notification import get_notification_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Khởi động hệ thống notification
    notification_manager = get_notification_manager()
    init_result = notification_manager.initialize()
    
    if init_result['success']:
        print("Ứng dụng đã khởi động hoàn tất!")
    else:
        print(f"Lỗi khởi tạo notification: {init_result.get('message', 'Unknown error')}")
    
    yield
    
    # Shutdown: Tắt hệ thống notification
    shutdown_result = notification_manager.shutdown()
    if shutdown_result['success']:
        print("Ứng dụng đã tắt!")
    

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
