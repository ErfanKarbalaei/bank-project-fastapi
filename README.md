# سامانه بانکی – Backend (FastAPI + asyncpg)

این مخزن شامل بک‌اند یک سیستم بانکی با FastAPI و پایگاه‌داده PostgreSQL (با درایور asyncpg) است. این راهنما به‌صورت کامل و قدم‌به‌قدم نحوه راه‌اندازی، پیکربندی، اجرا و تست APIها را توضیح می‌دهد.

## پیش‌نیازها
- Python 3.10 یا جدیدتر
- PostgreSQL 13+ (نصب و اجرا شده)
- pip و virtualenv (پیشنهادی)
- Alembic (داخل پروژه پیکربندی شده)
- Postman (برای تست APIها)

## راه‌اندازی سریع
1) ورود به پوشه پروژه:
```bash
cd bank-fastapi
```
2) ساخت و فعال‌سازی محیط مجازی (اختیاری اما توصیه‌شده)
- Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
- Linux/Mac:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
3) نصب وابستگی‌ها:
```bash
pip install -r requirements.txt
```
4) ایجاد/ویرایش فایل `.env` در ریشه پروژه:
```
# نمونه تنظیمات
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/bankdb
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```
> نکته: دیتابیس `bankdb` را در PostgreSQL بسازید یا نام دلخواه خود را جایگزین کنید.

5) اجرای مهاجرت‌های دیتابیس:
```bash
alembic upgrade head
```

6) (اختیاری) درج داده نمونه/انبوه برای تست:
```bash
python -m app.db.seed
```

7) اجرای سرور توسعه:
```bash
uvicorn app.main:app --reload
```
- مستندات Swagger: http://localhost:8000/docs
- مستندات ReDoc: http://localhost:8000/redoc

## تست با Postman
- فایل کالکشن: `postman_collectionBanking_API_v1.postman_collection.json`
1) فایل را در Postman ایمپورت کنید.
2) ابتدا Register و سپس Login را بزنید تا `access_token` دریافت شود.
3) برای درخواست‌های محافظت‌شده، هدر زیر را اضافه کنید:
```
Authorization: Bearer <access_token>
```

## جریان احراز هویت
- ثبت‌نام: `POST /api/v1/auth/register`
  ```json
  {
    "national_code": "1234567890",
    "full_name": "Ali Rezaei",
    "phone_number": "09123456789",
    "email": "ali@example.com",
    "password": "test1234"
  }
  ```
- ورود و دریافت توکن: `POST /api/v1/auth/token`
  ```json
  { "phone_number": "09123456789", "password": "test1234" }
  ```
- کاربر جاری: `GET /api/v1/auth/me` (نیازمند Bearer Token)

## فهرست اندپوینت‌ها
- Auth
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/token`
  - `GET  /api/v1/auth/me`
- Cards
  - `GET  /api/v1/cards/`
- Transactions
  - `POST /api/v1/transactions/withdraw`
  - `POST /api/v1/transactions/transfer`
  - `GET  /api/v1/transactions/recent?limit=10`
  - `GET  /api/v1/transactions/revenue?start_date=...&end_date=...`

> محدودیت‌های دامنه:
> - هر تراکنش باید زیر ۵ ثانیه تکمیل شود.
> - سقف تراکنش روزانه هر کارت: ۵۰,۰۰۰,۰۰۰ ریال.

## ساختار پروژه (خلاصه)
```
app/
  api/v1/
    endpoints/
      auth.py         # احراز هویت
      cards.py        # کارت‌ها
      transactions.py # تراکنش‌ها
    routers.py
  core/
    config.py        # تنظیمات/env
    security.py      # JWT و امنیت
  db/
    models/          # مدل‌ها
    session.py       # اتصال DB
    seed.py          # ایجاد داده نمونه
  repositories/      # دسترسی به داده
  schemas/           # Pydantic
  services/          # منطق کسب‌وکار
main.py              # شروع برنامه
alembic/             # مهاجرت‌ها
```

## دستورات مفید
- اجرای سرور:
```bash
uvicorn app.main:app --reload
```
- آخرین مهاجرت‌ها:
```bash
alembic upgrade head
```
- ایجاد مهاجرت جدید (برای توسعه):
```bash
alembic revision -m "message"
```
- درج داده نمونه:
```bash
python -m app.db.seed
```
- پسورد تمامی کاربران =bank123 
## خطاهای رایج
- اتصال به DB برقرار نمی‌شود:
  - مقدار `DATABASE_URL` را بررسی کنید و مطمئن شوید PostgreSQL اجراست و دیتابیس ساخته شده.
- خطای 401:
  - توکن را در هدر Authorization قرار دهید و از معتبر بودن آن مطمئن شوید.
- کندی درخواست‌ها:
  - منابع سیستم و ایندکس‌های دیتابیس را بررسی کنید.

## نکات امنیتی/عملکردی
- از `SECRET_KEY` قوی استفاده کنید.
- زمان انقضای معقول برای توکن‌ها تنظیم کنید.
- محدودیت‌های دامنه (سقف تراکنش/زمان اجرا) را در محیط واقعی مانیتور کنید.

## مشارکت
- برای مشارکت یک شاخه جدید بسازید و Pull Request ارسال کنید.

موفق باشید 🌱