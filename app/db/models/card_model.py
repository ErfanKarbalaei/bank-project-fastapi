from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    card_number = Column(String(16), unique=True, nullable=False, index=True)
    cvv2 = Column(String(4), nullable=False)
    expire_date = Column(String(5), nullable=False, doc="MM/YY format")
    balance = Column(Numeric(18, 0), default=0, nullable=False, doc="Balance in Rials")  # ✅ ریال
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="cards")
    transactions_from = relationship(
        "Transaction",
        foreign_keys="[Transaction.source_card_id]",
        back_populates="source_card",
    )
    transactions_to = relationship(
        "Transaction",
        foreign_keys="[Transaction.dest_card_id]",
        back_populates="dest_card",
    )

    def __repr__(self):
        return f"<Card(number={self.card_number}, balance={self.balance} ریال)>"
