from sqlalchemy import Column, Integer, Numeric, ForeignKey, DateTime, String, func, Enum
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class TransactionStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    source_card_id = Column(Integer, ForeignKey("cards.id"))
    dest_card_id = Column(Integer, ForeignKey("cards.id"))
    amount = Column(Numeric(15, 2), nullable=False)
    fee = Column(Numeric(15, 2), nullable=False)
    status = Column(
        Enum(TransactionStatus, name="transactionstatus", create_type=True),
        default=TransactionStatus.SUCCESS,
        nullable=False,
    )
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source_card = relationship("Card", foreign_keys=[source_card_id], back_populates="transactions_from")
    dest_card = relationship("Card", foreign_keys=[dest_card_id], back_populates="transactions_to")
