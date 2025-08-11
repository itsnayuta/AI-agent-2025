from fastapi import FastAPI
from core.routers.schedule_router import router as schedule_router_router

app = FastAPI()

app.include_router(schedule_router_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the scheduling API!"}