from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from asyncpg import Connection

from app.api.v1.deps import get_db_connection, get_current_user
from app.repositories.card_repo import CardRepository
from app.schemas.card_schema import CardOut

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


@router.get("/", response_model=List[CardOut])
async def list_user_cards(
    current_user: Dict[str, Any] = Depends(get_current_user),
    conn: Connection = Depends(get_db_connection),
):

    card_repo = CardRepository(conn)
    cards = await card_repo.list_by_user(current_user['id'])
    return [CardOut(**card) for card in cards]  # explicit mapping
