import asyncio
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

from app.core.config import settings
from app.models import GmailAccount, Email
from app.services.gmail import GmailService
from app.services.ai import AIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Create database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize AI service
ai_service = AIService()

async def sync_account(db: Session, account: GmailAccount):
    """Sync a single Gmail account"""
    try:
        # Check if we've synced recently (reduced to 1 minute)
        # if account.last_sync_time and datetime.utcnow() - account.last_sync_time < timedelta(minutes=1):
        #     logger.info(f"Skipping sync for {account.email} - too soon since last sync")
        #     return

        logger.info(f"Starting sync for {account.email}")
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
                    is_archived=True
                )
                db.add(db_email)
                db.commit()  # Commit to get the email ID
                
                # Process with AI
                logger.info(f"Processing email '{db_email.subject}' with AI")
                await ai_service.process_new_email(db, db_email)
                
                # Archive email in Gmail
                gmail_service.archive_email(email_data["gmail_id"])
                synced_count += 1
        
        # Update last sync time
        account.last_sync_time = datetime.utcnow()
        db.add(account)
        db.commit()
        
        logger.info(f"Successfully synced and processed {synced_count} new emails for {account.email}")
    
    except Exception as e:
        logger.error(f"Error syncing {account.email}: {str(e)}")
        db.rollback()

async def sync_all_accounts():
    """Sync all Gmail accounts"""
    try:
        db = SessionLocal()
        accounts = db.query(GmailAccount).all()
        
        for account in accounts:
            await sync_account(db, account)
            
    except Exception as e:
        logger.error(f"Error in sync_all_accounts: {str(e)}")
    finally:
        db.close()

async def main():
    """Main worker loop"""
    logger.info("Starting email sync worker (1-minute intervals)")
    
    while True:
        try:
            await sync_all_accounts()
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
        
        # Wait for 1 minute before next sync
        await asyncio.sleep(60)  # 60 seconds = 1 minute

if __name__ == "__main__":
    asyncio.run(main())