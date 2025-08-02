from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.api import deps
from app.models import User, Email, Category, GmailAccount
from app.schemas.email import Email as EmailSchema, EmailCreate, EmailUpdate
from app.services.gmail import GmailService

router = APIRouter()

async def sync_account(db: Session, account: GmailAccount):
    """Background task to sync a single Gmail account"""
    try:
        # Check if we've synced recently (rate limiting)
        if account.last_sync_time and datetime.utcnow() - account.last_sync_time < timedelta(minutes=5):
            return f"Skipped sync for {account.email} - too soon since last sync"

        gmail_service = GmailService(account, db)
        synced_count = 0
        
        # Fetch emails since last sync time or last 24 hours if no sync
        since_time = account.last_sync_time or (datetime.utcnow() - timedelta(days=1))
        new_emails_data = gmail_service.list_unarchived_emails(since=since_time)
        
        for email_data in new_emails_data:
            # Check if email already exists
            existing_email = db.query(Email).filter(
                Email.gmail_id == email_data["gmail_id"],
                Email.gmail_account_id == account.id
            ).first()

            if not existing_email:
                # Create new email record
                db_email = Email(
                    gmail_id=email_data["gmail_id"],
                    subject=email_data["subject"],
                    sender=email_data["sender"],
                    content=email_data["content"],
                    received_at=email_data["received_at"],
                    user_id=account.user_id,
                    gmail_account_id=account.id,
                    is_archived=True  # Mark as archived in our DB since we archive in Gmail
                )
                db.add(db_email)
                synced_count += 1
                
                # Archive email in Gmail
                gmail_service.archive_email(email_data["gmail_id"])
        
        # Update last sync time
        account.last_sync_time = datetime.utcnow()
        db.add(account)
        db.commit()
        
        return f"Successfully synced {synced_count} new emails for {account.email}"
    
    except Exception as e:
        db.rollback()
        return f"Error syncing {account.email}: {str(e)}"

async def sync_all_accounts(db: Session, user: User):
    """Background task to sync all Gmail accounts for a user"""
    results = []
    accounts = db.query(GmailAccount).filter(GmailAccount.user_id == user.id).all()
    
    for account in accounts:
        result = await sync_account(db, account)
        results.append(result)
    
    return results

@router.post("/sync")
async def sync_emails(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Start a background task to sync emails from all connected Gmail accounts"""
    # Get all Gmail accounts for the user
    accounts = db.query(GmailAccount).filter(GmailAccount.user_id == current_user.id).all()
    
    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Gmail accounts connected"
        )
    
    # Add the sync task to background tasks
    background_tasks.add_task(sync_all_accounts, db, current_user)
    
    return {
        "message": f"Started syncing emails for {len(accounts)} account(s)",
        "accounts": [account.email for account in accounts]
    }

@router.post("/{account_id}/sync")
async def sync_specific_account(
    account_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Start a background task to sync emails from a specific Gmail account"""
    account = db.query(GmailAccount).filter(
        GmailAccount.id == account_id,
        GmailAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gmail account not found"
        )
    
    # Check rate limiting
    if account.last_sync_time and datetime.utcnow() - account.last_sync_time < timedelta(minutes=5):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait at least 5 minutes between syncs",
            headers={"Retry-After": "300"}
        )
    
    # Add the sync task to background tasks
    background_tasks.add_task(sync_account, db, account)
    
    return {
        "message": f"Started syncing emails for {account.email}"
    }

@router.get("/", response_model=List[EmailSchema])
def list_emails(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    category_id: Optional[int] = Query(None),
    gmail_account_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List emails with optional filters:
    - category_id: Filter by category
    - gmail_account_id: Filter by Gmail account
    - search: Search in subject/content
    - skip/limit: Pagination
    """
    query = db.query(Email).join(Email.gmail_account).filter(Email.user_id == current_user.id)
    
    if category_id is not None:
        query = query.filter(Email.category_id == category_id)
    
    if gmail_account_id is not None:
        # Verify the account belongs to the user
        account = db.query(GmailAccount).filter(
            GmailAccount.id == gmail_account_id,
            GmailAccount.user_id == current_user.id
        ).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gmail account not found"
            )
        query = query.filter(Email.gmail_account_id == gmail_account_id)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Email.subject.ilike(search_filter)) |
            (Email.content.ilike(search_filter))
        )
    
    # Order by received_at descending (newest first)
    query = query.order_by(Email.received_at.desc())
    
    # Apply pagination
    emails = query.offset(skip).limit(limit).all()
    return emails

@router.get("/{email_id}", response_model=EmailSchema)
def get_email(
    email_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get a specific email"""
    email = db.query(Email).join(Email.gmail_account).filter(
        Email.id == email_id,
        Email.user_id == current_user.id
    ).first()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    return email

@router.put("/{email_id}", response_model=EmailSchema)
def update_email(
    email_id: int,
    email_update: EmailUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Update email details (category, summary, archived status)"""
    email = db.query(Email).filter(
        Email.id == email_id,
        Email.user_id == current_user.id
    ).first()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    # Update only provided fields
    for field, value in email_update.dict(exclude_unset=True).items():
        setattr(email, field, value)
    
    db.commit()
    db.refresh(email)
    return email

@router.delete("/{email_id}")
def delete_email(
    email_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Delete an email"""
    email = db.query(Email).filter(
        Email.id == email_id,
        Email.user_id == current_user.id
    ).first()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    db.delete(email)
    db.commit()
    return {"message": "Email deleted successfully"}

@router.post("/bulk-delete")
def bulk_delete_emails(
    email_ids: List[int],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Delete multiple emails"""
    result = db.query(Email).filter(
        Email.id.in_(email_ids),
        Email.user_id == current_user.id
    ).delete(synchronize_session=False)
    
    db.commit()
    return {
        "message": f"Successfully deleted {result} emails"
    }