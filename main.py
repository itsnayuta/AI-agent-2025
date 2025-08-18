from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.routers.schedule_router import router as schedule_router_router
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

app.include_router(schedule_router_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the scheduling API!"}