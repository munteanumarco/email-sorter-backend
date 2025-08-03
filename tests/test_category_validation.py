import pytest
from sqlalchemy.exc import IntegrityError
from app.models import User, Category, Email
from datetime import datetime

def test_category_name_length(db, test_user):
    """Test category name length constraints"""
    # Test empty name
    with pytest.raises(ValueError):
        category = Category(
            name="",
            user_id=test_user.id
        )
        db.add(category)
        db.commit()
    
    # Test too long name (e.g., > 50 chars)
    with pytest.raises(ValueError):
        category = Category(
            name="a" * 51,  # 51 characters
            user_id=test_user.id
        )
        db.add(category)
        db.commit()
    
    # Test valid name
    category = Category(
        name="Valid Category Name",
        user_id=test_user.id
    )
    db.add(category)
    db.commit()
    assert category.id is not None

def test_category_special_characters(db, test_user):
    """Test handling of special characters in category names"""
    valid_names = [
        "Work & Personal",
        "Finance (2024)",
        "Project: Alpha",
        "Test-Category",
        "Category_Name"
    ]
    
    invalid_names = [
        "<script>alert(1)</script>",  # XSS attempt
        "Category\nName",  # Newline
        "Category\tName",  # Tab
        "////Category////",  # Excessive slashes
        "  "  # Only whitespace
    ]
    
    # Test valid names
    for name in valid_names:
        category = Category(
            name=name,
            user_id=test_user.id
        )
        db.add(category)
        db.commit()
        assert category.id is not None
        db.delete(category)
        db.commit()
    
    # Test invalid names
    for name in invalid_names:
        with pytest.raises(ValueError):
            category = Category(
                name=name,
                user_id=test_user.id
            )
            db.add(category)
            db.commit()

def test_category_email_reassignment(db, test_user):
    """Test reassigning emails between categories"""
    # Create two categories
    cat1 = Category(name="Category 1", user_id=test_user.id)
    cat2 = Category(name="Category 2", user_id=test_user.id)
    db.add_all([cat1, cat2])
    db.commit()
    
    # Create an email in first category
    email = Email(
        gmail_id="test123",
        subject="Test Email",
        sender="test@example.com",
        content="Test content",
        received_at=datetime.utcnow(),
        category_id=cat1.id,
        user_id=test_user.id,
        gmail_account_id=1
    )
    db.add(email)
    db.commit()
    
    # Verify initial category
    assert email.category_id == cat1.id
    
    # Move to second category
    email.category_id = cat2.id
    db.commit()
    db.refresh(email)
    
    # Verify new category
    assert email.category_id == cat2.id
    
    # Verify category relationships
    assert len(cat1.emails) == 0
    assert len(cat2.emails) == 1

def test_category_deletion_with_emails(db, test_user):
    """Test what happens to emails when a category is deleted"""
    # Create category
    category = Category(name="Test Category", user_id=test_user.id)
    db.add(category)
    db.commit()
    
    # Add some emails
    emails = [
        Email(
            gmail_id=f"msg{i}",
            subject=f"Test {i}",
            sender="test@example.com",
            content="Test content",
            received_at=datetime.utcnow(),
            category_id=category.id,
            user_id=test_user.id,
            gmail_account_id=1
        ) for i in range(3)
    ]
    db.add_all(emails)
    db.commit()
    
    # Delete category
    db.delete(category)
    db.commit()
    
    # Verify emails still exist but without category
    for email_id in [e.id for e in emails]:
        email = db.query(Email).get(email_id)
        assert email is not None  # Email still exists
        assert email.category_id is None  # But category_id is null