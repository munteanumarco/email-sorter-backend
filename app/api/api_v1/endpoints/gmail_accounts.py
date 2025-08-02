from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.api import deps
from app.models import User, GmailAccount
from app.schemas.gmail_account import GmailAccount as GmailAccountSchema
from app.services.gmail import GmailService
from app.worker import sync_all_accounts

router = APIRouter()

@router.get("/", response_model=List[GmailAccountSchema])
def list_gmail_accounts(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """List all Gmail accounts connected to the user"""
    return current_user.gmail_accounts

@router.post("/connect", response_model=GmailAccountSchema)
async def connect_gmail_account(
    auth_code: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Connect a new Gmail account using OAuth"""
    try:
        # Exchange auth code for tokens (implementation in auth.py)
        tokens = await deps.exchange_auth_code(auth_code)
        
        # Get user info from Google
        user_info = await deps.get_google_user_info(tokens["access_token"])
        
        # Check if account already exists
        existing_account = db.query(GmailAccount).filter(
            GmailAccount.google_id == user_info["sub"]
        ).first()
        
        if existing_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This Gmail account is already connected"
            )
        
        # Create new Gmail account
        gmail_account = GmailAccount(
            email=user_info["email"],
            google_id=user_info["sub"],
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_expiry=datetime.utcnow() + tokens["expires_in"],
            user_id=current_user.id
        )
        
        db.add(gmail_account)
        db.commit()
        db.refresh(gmail_account)
        
        return gmail_account
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect Gmail account: {str(e)}"
        )

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_gmail_account(
    account_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Disconnect a Gmail account"""
    account = db.query(GmailAccount).filter(
        GmailAccount.id == account_id,
        GmailAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gmail account not found"
        )
    
    db.delete(account)
    db.commit()
    return None

@router.post("/{account_id}/sync", status_code=status.HTTP_200_OK)
async def sync_gmail_account(
    account_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Sync emails for a specific Gmail account"""
    account = db.query(GmailAccount).filter(
        GmailAccount.id == account_id,
        GmailAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gmail account not found"
        )
    
    try:
        # Initialize Gmail service with account's credentials
        gmail_service = GmailService(
            access_token=account.access_token,
            refresh_token=account.refresh_token
        )
        
        # Get new emails since last sync
        new_emails = gmail_service.list_unarchived_emails(
            since=account.last_sync_time
        )
        
        processed_count = 0
        for email_data in new_emails:
            # Store email in database
            email = Email(
                gmail_id=email_data["gmail_id"],
                subject=email_data["subject"],
                sender=email_data["sender"],
                content=email_data["content"],
                received_at=email_data["received_at"],
                user_id=current_user.id,
                gmail_account_id=account.id
            )
            db.add(email)
            
            # Archive the email in Gmail
            gmail_service.archive_email(email_data["gmail_id"])
            processed_count += 1
        
        # Update last sync time
        account.last_sync_time = datetime.utcnow()
        db.commit()
        
        return {"message": f"Successfully synced {processed_count} new emails"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync emails: {str(e)}"
        )

@router.post("/sync-all", status_code=status.HTTP_200_OK)
async def sync_all_gmail_accounts(
    current_user: User = Depends(deps.get_current_user)
):
    """Trigger a sync of all Gmail accounts"""
    try:
        await sync_all_accounts()
        return {"message": "Successfully triggered sync for all accounts"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync all accounts: {str(e)}"
        )