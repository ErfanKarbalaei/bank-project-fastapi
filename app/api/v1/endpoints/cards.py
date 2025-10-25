from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any  # اضافه کردن Dict و Any
from app.api.v1.deps import get_db_connection, get_current_user  # تغییر get_db به get_db_connection
from app.repositories.card_repo import CardRepository
from app.schemas.card_schema import CardOut
from asyncpg import Connection  # استفاده از Connection

# ❌ حذف ایمپورت AsyncSession
# ❌ حذف ایمپورت مدل User


router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


@router.get("/", response_model=List[CardOut])
async def list_user_cards(
        # ⚠️ تغییر type hint به dict برای current_user و get_db به get_db_connection
        current_user: Dict[str, Any] = Depends(get_current_user),
        conn: Connection = Depends(get_db_connection)
):
    """
    لیست کارت‌های متعلق به کاربر جاری را برمی‌گرداند.
    """
    card_repo = CardRepository(conn)  # استفاده از conn
    # ⚠️ دسترسی به ID کاربر از دیکشنری
    cards = await card_repo.list_by_user(current_user['id'])

    # cards لیستی از dictها است که مستقیماً به List[CardOut] مپ می‌شود.
    return cards
