from fastapi import FastAPI
from contextlib import asynccontextmanager # ایمپورت contextmanager
from app.api.v1.endpoints import auth, transactions, cards

import logging
# ایمپورت توابع مدیریت Pool جدید
from app.db.session import connect_db_pool, close_db_pool

logging.basicConfig(level=logging.DEBUG)


# 1. تعریف تابع lifespan برای مدیریت چرخه عمر Pool
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🌟 در زمان شروع برنامه (Startup)
    await connect_db_pool()
    yield
    # 💥 در زمان خاموش شدن برنامه (Shutdown)
    await close_db_pool()


app = FastAPI(
    title="Bank API",
    description="سیستم بانکی برای مدیریت کاربران، کارت‌ها و تراکنش‌ها",
    version="1.0.0",
    lifespan=lifespan # اتصال تابع lifespan به برنامه
)

# 2. اضافه کردن روترها (بدون تغییر)
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(cards.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Bank API 🚀"}