import pytest
from sqlalchemy.exc import IntegrityError
from app.models import User, GmailAccount
from datetime import datetime, timedelta

def test_gmail_account_requires_google_id(db, test_user):
    """Test that Gmail accounts require a Google ID"""
    # Try to create account without google_id
    with pytest.raises(IntegrityError):
        account = GmailAccount(
            email="test@gmail.com",
            user_id=test_user.id,
            is_primary=True
        )
        db.add(account)
        db.commit()

def test_primary_account_uniqueness(db, test_user):
    """Test that a user can only have one primary account"""
    # Create first primary account
    account1 = GmailAccount(
        email="primary@gmail.com",
        google_id="123",
        user_id=test_user.id,
        is_primary=True
    )
    db.add(account1)
    db.commit()
    
    # Try to create second primary account
    with pytest.raises(IntegrityError):
        account2 = GmailAccount(
            email="another@gmail.com",
            google_id="456",
            user_id=test_user.id,
            is_primary=True
        )
        db.add(account2)
        db.commit()

def test_token_expiry_validation(db, test_user):
    """Test token expiry handling"""
    # Create account with expired token
    past_time = datetime.utcnow() - timedelta(hours=2)
    account = GmailAccount(
        email="test@gmail.com",
        google_id="123",
        user_id=test_user.id,
        is_primary=True,
        access_token="expired_token",
        token_expiry=past_time
    )
    db.add(account)
    db.commit()
    
    assert account.token_expiry < datetime.utcnow()
    
    # Update with new token
    future_time = datetime.utcnow() + timedelta(hours=1)
    account.access_token = "new_token"
    account.token_expiry = future_time
    db.commit()
    
    assert account.token_expiry > datetime.utcnow()

def test_sync_time_tracking(db, test_user):
    """Test last sync time tracking"""
    account = GmailAccount(
        email="test@gmail.com",
        google_id="123",
        user_id=test_user.id,
        is_primary=True
    )
    db.add(account)
    db.commit()
    
    # Initially null
    assert account.last_sync_time is None
    
    # Update sync time
    sync_time = datetime.utcnow()
    account.last_sync_time = sync_time
    db.commit()
    
    db.refresh(account)
    assert account.last_sync_time is not None
    assert (datetime.utcnow() - account.last_sync_time).total_seconds() < 5  # Within 5 seconds

def test_cascade_delete_emails(db, test_user):
    """Test that deleting a Gmail account cascades to its emails"""
    # Create account
    account = GmailAccount(
        email="test@gmail.com",
        google_id="123",
        user_id=test_user.id,
        is_primary=True
    )
    db.add(account)
    db.commit()
    
    # Add some emails
    from app.models import Email
    emails = [
        Email(
            gmail_id=f"msg{i}",
            subject=f"Test {i}",
            sender="test@example.com",
            content="Test content",
            received_at=datetime.utcnow(),
            user_id=test_user.id,
            gmail_account_id=account.id
        ) for i in range(3)
    ]
    db.add_all(emails)
    db.commit()
    
    # Verify emails exist
    email_count = db.query(Email).filter(Email.gmail_account_id == account.id).count()
    assert email_count == 3
    
    # Delete account
    db.delete(account)
    db.commit()
    
    # Verify emails were deleted
    email_count = db.query(Email).filter(Email.gmail_account_id == account.id).count()
    assert email_count == 0