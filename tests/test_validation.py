import pytest
from sqlalchemy.exc import IntegrityError
from app.models import User, Category, Email
from datetime import datetime

def test_invalid_email_format(db):
    """Test that invalid email formats are rejected"""
    invalid_emails = [
        "not_an_email",
        "missing@domain",
        "@nodomain.com",
        "spaces in@email.com",
        ""
    ]
    
    for email in invalid_emails:
        with pytest.raises(ValueError):
            user = User(email=email)
            db.add(user)
            db.commit()

def test_duplicate_email_rejected(db):
    """Test that duplicate email addresses are rejected"""
    email = "test@example.com"
    
    # Create first user
    user1 = User(email=email)
    db.add(user1)
    db.commit()
    
    # Try to create second user with same email
    with pytest.raises(IntegrityError):
        user2 = User(email=email)
        db.add(user2)
        db.commit()

def test_unique_category_names_per_user(db):
    """Test that category names must be unique per user"""
    # Create two users
    user1 = User(email="user1@example.com")
    user2 = User(email="user2@example.com")
    db.add_all([user1, user2])
    db.commit()
    
    # First user can create a category
    cat1 = Category(name="Work", user_id=user1.id)
    db.add(cat1)
    db.commit()
    
    # Same user can't create duplicate category name
    with pytest.raises(IntegrityError):
        cat2 = Category(name="Work", user_id=user1.id)
        db.add(cat2)
        db.commit()
    
    db.rollback()  # Reset after error
    
    # Different user can use same category name
    cat3 = Category(name="Work", user_id=user2.id)
    db.add(cat3)
    db.commit()

def test_email_timestamps(db, test_user):
    """Test that email timestamps are properly set"""
    received_time = datetime.utcnow()
    
    email = Email(
        gmail_id="test123",
        subject="Test Email",
        sender="sender@example.com",
        content="Test content",
        received_at=received_time,
        user_id=test_user.id,
        gmail_account_id=1
    )
    db.add(email)
    db.commit()
    
    # Verify created_at and updated_at are set
    assert email.created_at is not None
    assert email.updated_at is not None
    assert email.received_at == received_time

def test_category_description_optional(db, test_user):
    """Test that category description is optional"""
    # Create category without description
    cat1 = Category(
        name="No Description",
        user_id=test_user.id
    )
    db.add(cat1)
    db.commit()
    
    assert cat1.description is None
    
    # Create category with description
    cat2 = Category(
        name="With Description",
        description="Test description",
        user_id=test_user.id
    )
    db.add(cat2)
    db.commit()
    
    assert cat2.description == "Test description"