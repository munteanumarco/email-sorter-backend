from datetime import datetime
from app.models import User, Category, Email, GmailAccount

def test_user_creation(db):
    """Test basic user creation"""
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    
    fetched_user = db.query(User).first()
    assert fetched_user.email == "test@example.com"
    assert fetched_user.created_at is not None
    assert fetched_user.updated_at is not None

def test_category_user_relationship(test_user, test_category, db):
    """Test relationship between user and categories"""
    # Test category was created with correct user
    assert test_category.user_id == test_user.id
    
    # Test relationship from user side
    assert len(test_user.categories) == 1
    assert test_user.categories[0].name == "Test Category"

def test_email_categorization(test_user, test_category, db):
    """Test assigning an email to a category"""
    # Create a Gmail account
    gmail_account = GmailAccount(
        email="test@gmail.com",
        google_id="123",
        is_primary=True,
        user_id=test_user.id
    )
    db.add(gmail_account)
    db.commit()
    
    # Create an email
    email = Email(
        gmail_id="msg123",
        subject="Test Email",
        sender="sender@example.com",
        content="Test content",
        received_at=datetime.utcnow(),
        category_id=test_category.id,
        user_id=test_user.id,
        gmail_account_id=gmail_account.id
    )
    db.add(email)
    db.commit()
    
    # Test relationships
    assert email.category_id == test_category.id
    assert email.user_id == test_user.id
    assert len(test_category.emails) == 1
    assert test_category.emails[0].subject == "Test Email"

def test_gmail_account_relationships(test_user, db):
    """Test Gmail account creation and relationships"""
    # Create Gmail account
    gmail_account = GmailAccount(
        email="test@gmail.com",
        google_id="123",
        is_primary=True,
        user_id=test_user.id
    )
    db.add(gmail_account)
    db.commit()
    
    # Test relationships
    assert len(test_user.gmail_accounts) == 1
    assert test_user.gmail_accounts[0].is_primary == True
    assert test_user.gmail_accounts[0].email == "test@gmail.com"