# app/api/routers.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, cards, transactions

router = APIRouter()

router.include_router(auth.router)
router.include_router(cards.router)
router.include_router(transactions.router)