from datetime import datetime
from app.models import Category, Email
from app.services.category import CategoryService

def test_create_category(test_user, db):
    """Test category creation through service"""
    category_service = CategoryService(db)
    category_data = {
        "name": "Work",
        "description": "Work related emails"
    }
    
    category = category_service.create_category(category_data, test_user.id)
    
    assert category.name == "Work"
    assert category.description == "Work related emails"
    assert category.user_id == test_user.id

def test_get_user_categories(test_user, test_category, db):
    """Test retrieving user's categories"""
    category_service = CategoryService(db)
    
    # Create another category
    category_service.create_category({
        "name": "Personal",
        "description": "Personal emails"
    }, test_user.id)
    
    categories = category_service.get_user_categories(test_user.id)
    
    assert len(categories) == 2
    assert any(c.name == "Test Category" for c in categories)
    assert any(c.name == "Personal" for c in categories)

def test_get_category_emails(test_user, test_category, db):
    """Test retrieving emails for a category"""
    category_service = CategoryService(db)
    
    # Create some test emails in the category
    emails = [
        Email(
            gmail_id=f"msg{i}",
            subject=f"Test Email {i}",
            sender="sender@example.com",
            content=f"Content {i}",
            received_at=datetime.utcnow(),
            category_id=test_category.id,
            user_id=test_user.id,
            gmail_account_id=1  # This is just for testing
        ) for i in range(3)
    ]
    
    for email in emails:
        db.add(email)
    db.commit()
    
    # Get emails for the category
    category_emails = category_service.get_category_emails(test_category.id, test_user.id)
    
    assert len(category_emails) == 3
    assert all(email.category_id == test_category.id for email in category_emails)