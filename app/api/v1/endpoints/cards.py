from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.api.v1.deps import get_db, get_current_user
from app.repositories.card_repo import CardRepository
from app.schemas.card_schema import CardOut
from app.db.models.user_model import User

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])

@router.get("/", response_model=List[CardOut])
async def list_user_cards(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    card_repo = CardRepository(db)
    cards = await card_repo.list_by_user(current_user.id)
    return cards
