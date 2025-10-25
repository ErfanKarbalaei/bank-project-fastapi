from fastapi import FastAPI
from app.api.v1.endpoints import auth, transactions, cards
# ⚠️ AuthMiddleware حذف شد - اعتبارسنجی باید توسط Depends(get_current_user) انجام شود
# from app.middleware.auth_middleware import AuthMiddleware

import logging

logging.basicConfig(level=logging.DEBUG)

app = FastAPI(
    title="Bank API",
    description="سیستم بانکی برای مدیریت کاربران، کارت‌ها و تراکنش‌ها",
    version="1.0.0",
)

# 1. حذف Middleware: به سیستم Dependency Injection اعتماد می‌کنیم.
# app.add_middleware(AuthMiddleware)

# 2. اضافه کردن روترها: Prefixها را از اینجا حذف می‌کنیم و اجازه می‌دهیم از Prefixهای داخلی (مثلاً /api/v1/...) استفاده شود.
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(cards.router)

# ⚠️ نیازی نیست که روترها را با prefixهای اضافی مثل prefix="/auth" یا prefix="" دوباره بپوشانید.

@app.get("/")
async def root():
    return {"message": "Welcome to Bank API 🚀"}