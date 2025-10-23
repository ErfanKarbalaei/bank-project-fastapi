from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.db.session import Base

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    card_number = Column(String(16), unique=True, nullable=False)
    balance = Column(Numeric(15, 2), default=0)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    owner = relationship("User", back_populates="cards")
    transactions_from = relationship("Transaction", foreign_keys="[Transaction.source_card_id]", back_populates="source_card")
    transactions_to = relationship("Transaction", foreign_keys="[Transaction.dest_card_id]", back_populates="dest_card")
