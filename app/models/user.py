from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import re
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    gmail_accounts = relationship("GmailAccount", back_populates="user")
    categories = relationship("Category", back_populates="user")
    emails = relationship("Email", back_populates="user")

    def __init__(self, **kwargs):
        if 'email' in kwargs:
            self.validate_email(kwargs['email'])
        super().__init__(**kwargs)

    @staticmethod
    def validate_email(email: str) -> None:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")