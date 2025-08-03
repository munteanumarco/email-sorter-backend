from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import re
from app.core.database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)  # Max length 50
    description = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="categories")
    emails = relationship("Email", back_populates="category")

    # Make category names unique per user
    __table_args__ = (
        UniqueConstraint('name', 'user_id', name='uix_category_name_user'),
    )

    def __init__(self, **kwargs):
        if 'name' in kwargs:
            self.validate_name(kwargs['name'])
        super().__init__(**kwargs)

    @staticmethod
    def validate_name(name: str) -> None:
        """Validate category name"""
        if not name or len(name.strip()) == 0:
            raise ValueError("Category name cannot be empty")
        
        if len(name) > 50:
            raise ValueError("Category name cannot be longer than 50 characters")
        
        # Check for invalid characters/patterns
        invalid_patterns = [
            r'<[^>]*>',  # HTML tags
            r'[\n\r\t]',  # Newlines and tabs
            r'^[\s/]*$',  # Only whitespace or slashes
            r'^\s+|\s+$',  # Leading/trailing whitespace
            r'/{2,}',  # Multiple consecutive slashes
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, name):
                raise ValueError(f"Category name contains invalid characters or format")
        
        # Ensure name isn't just whitespace after stripping
        if not name.strip():
            raise ValueError("Category name cannot be empty or just whitespace")