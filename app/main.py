from fastapi import FastAPI
from app.api.v1.endpoints import auth
from app.middleware.auth_middleware import AuthMiddleware

import logging

logging.basicConfig(level=logging.DEBUG)

app = FastAPI(
    title="Bank API",
    description="سیستم بانکی برای مدیریت کاربران، کارت‌ها و تراکنش‌ها",
    version="1.0.0",
)


app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.add_middleware(AuthMiddleware)


@app.get("/")
async def root():
    return {"message": "Welcome to Bank API 🚀"}
