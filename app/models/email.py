from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    gmail_id = Column(String, unique=True, index=True)
    subject = Column(String)
    sender = Column(String)
    content = Column(Text)
    summary = Column(Text, nullable=True)
    unsubscribe_link = Column(Text, nullable=True)  # Added this field
    received_at = Column(DateTime)
    is_archived = Column(Boolean, default=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    gmail_account_id = Column(Integer, ForeignKey("gmail_accounts.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="emails")
    user = relationship("User", back_populates="emails")
    gmail_account = relationship("GmailAccount", back_populates="emails")