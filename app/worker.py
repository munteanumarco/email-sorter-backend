import asyncio
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
import re
import base64

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

async def extract_unsubscribe_link(headers: list, html_content: str = None) -> str | None:
    """Extract unsubscribe link using List-Unsubscribe header and AI analysis"""
    # Check List-Unsubscribe header first (most reliable)
    unsubscribe_header = next(
        (h['value'] for h in headers if h['name'].lower() == 'list-unsubscribe'),
        None
    )
    
    if unsubscribe_header:
        # Extract URL from <http://example.com/unsubscribe>
        url_match = re.search(r'<(https?://[^>]+)>', unsubscribe_header)
        if url_match:
            return url_match.group(1)
        
        # Some emails use mailto: in List-Unsubscribe
        mailto_match = re.search(r'<mailto:([^>]+)>', unsubscribe_header)
        if mailto_match:
            return f"mailto:{mailto_match.group(1)}"

    # If no header, use GPT to analyze the content
    if html_content:
        try:
            prompt = f"""
            Analyze this email content and find the unsubscribe URL or email address.
            The content might be in HTML format. Look for:
            1. Unsubscribe links (containing words like unsubscribe, opt-out, remove)
            2. Email management or preference center URLs
            3. Unsubscribe email addresses

            Return ONLY the full URL or mailto link if found, exactly as it appears.
            Return "None" if no unsubscribe mechanism is found.
            Do not include any explanation or additional text.

            Email Content:
            {html_content[:2000]}  # First 2000 chars should be enough
            """
            
            response = await ai_service.chat_completion_create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that finds unsubscribe links in emails. Return only the URL or None."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            url = response.choices[0].message.content.strip()
            if url.lower() != "none" and (url.startswith("http") or url.startswith("mailto:")):
                return url

        except Exception as e:
            logger.error(f"Error using AI to extract unsubscribe link: {str(e)}")

    return None

async def process_email_content(msg: dict) -> tuple[str, str | None, str | None]:
    """Process email content and extract text, HTML, and unsubscribe link"""
    html_content = None
    text_content = None
    
    if 'parts' in msg['payload']:
        parts = msg['payload']['parts']
        for part in parts:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                text_content = base64.urlsafe_b64decode(part['body']['data']).decode()
            elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                html_content = base64.urlsafe_b64decode(part['body']['data']).decode()
    else:
        body_data = msg['payload'].get('body', {}).get('data')
        if body_data:
            content = base64.urlsafe_b64decode(body_data).decode()
            if msg['payload'].get('mimeType') == 'text/html':
                html_content = content
            else:
                text_content = content

    # Extract unsubscribe link using AI
    unsubscribe_link = await extract_unsubscribe_link(msg['payload']['headers'], html_content or text_content)
    
    return text_content or '', html_content, unsubscribe_link

async def sync_account(db: Session, account: GmailAccount):
    """Sync a single Gmail account"""
    try:
        logger.info(f"Starting sync for {account.email}")
        gmail_service = GmailService(account, db)
        synced_count = 0
        
        # Fetch emails since last sync time or last 24 hours if no sync
        since_time = account.last_sync_time or (datetime.utcnow() - timedelta(days=1))
        new_messages = gmail_service.list_unarchived_emails(since=since_time)
        
        for message in new_messages:
            # Check if email already exists
            existing_email = db.query(Email).filter(
                Email.gmail_id == message["id"],
                Email.gmail_account_id == account.id
            ).first()

            if not existing_email:
                # Get full message content
                msg = gmail_service.get_message(message["id"])
                
                # Extract headers
                headers = msg['payload']['headers']
                subject = next(
                    (h['value'] for h in headers if h['name'].lower() == 'subject'),
                    'No Subject'
                )
                sender = next(
                    (h['value'] for h in headers if h['name'].lower() == 'from'),
                    'Unknown'
                )
                
                # Process content and extract unsubscribe link
                content, html_content, unsubscribe_link = await process_email_content(msg)
                
                # Create new email record
                db_email = Email(
                    gmail_id=message["id"],
                    subject=subject,
                    sender=sender,
                    content=content,
                    received_at=datetime.fromtimestamp(int(msg['internalDate'])/1000),
                    user_id=account.user_id,
                    gmail_account_id=account.id,
                    is_archived=True,
                    unsubscribe_link=unsubscribe_link
                )
                db.add(db_email)
                db.commit()  # Commit to get the email ID
                
                # Process with AI
                logger.info(f"Processing email '{db_email.subject}' with AI")
                await ai_service.process_new_email(db, db_email)
                
                # Archive email in Gmail
                gmail_service.archive_email(message["id"])
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