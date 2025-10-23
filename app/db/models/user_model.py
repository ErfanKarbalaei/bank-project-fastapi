from sqlalchemy import Column, Integer, String, Date, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    national_id = Column(String(10), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=True)
    birth_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    hashed_password = Column(String(255), nullable=False)

    cards = relationship("Card", back_populates="owner")
