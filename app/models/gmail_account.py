from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class GmailAccount(Base):
    __tablename__ = "gmail_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    google_id = Column(String, unique=True, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    last_sync_time = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="gmail_accounts")
    emails = relationship("Email", back_populates="gmail_account", cascade="all, delete-orphan")

    # Ensure only one primary account per user
    __table_args__ = (
        UniqueConstraint('user_id', 'is_primary', name='uix_user_primary_account',
                        sqlite_on_conflict='FAIL'),  # For SQLite
    )