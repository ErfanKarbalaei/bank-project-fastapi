from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.v1 import routers
import logging
from app.db.session import connect_db_pool, close_db_pool

logging.basicConfig(level=logging.DEBUG)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db_pool()
    yield
    await close_db_pool()

app = FastAPI(
    title="Bank API",
    description="سیستم بانکی برای مدیریت کاربران، کارت‌ها و تراکنش‌ها",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(routers.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Bank API 🚀"}
