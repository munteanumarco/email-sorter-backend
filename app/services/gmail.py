from typing import List, Optional
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport import requests as google_requests
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

from app.core.config import settings
from app.models import GmailAccount
from sqlalchemy.orm import Session

class GmailService:
    def __init__(self, gmail_account: GmailAccount, db: Session):
        """Initialize Gmail service with a GmailAccount model"""
        self.gmail_account = gmail_account
        self.db = db
        self.credentials = self._get_credentials()
        self.service = build('gmail', 'v1', credentials=self.credentials)

    def _get_credentials(self) -> Credentials:
        """Get credentials, refreshing if necessary"""
        creds = Credentials(
            token=self.gmail_account.access_token,
            refresh_token=self.gmail_account.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/gmail.modify"]
        )

        # Check if token needs refresh
        if self.gmail_account.token_expiry and datetime.utcnow() >= self.gmail_account.token_expiry:
            request = google_requests.Request()
            creds.refresh(request)
            
            # Update tokens in database
            self.gmail_account.access_token = creds.token
            self.gmail_account.token_expiry = datetime.utcnow() + timedelta(seconds=creds.expiry.second)
            self.db.add(self.gmail_account)
            self.db.commit()

        return creds

    def list_unarchived_emails(self, since: Optional[datetime] = None) -> List[dict]:
        """
        List unarchived emails from Gmail, optionally since a specific time
        Returns list of email data including ID, subject, sender, etc.
        """
        query = "in:inbox"  # Only unarchived emails
        if since:
            query += f" after:{int(since.timestamp())}"

        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50  # Limit to 50 emails per sync
            ).execute()

            messages = []
            if 'messages' in results:
                for message in results['messages']:
                    # Get full message details
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
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
                    
                    # Get message body
                    if 'parts' in msg['payload']:
                        parts = msg['payload']['parts']
                        body = next(
                            (part['body']['data'] for part in parts if part['mimeType'] == 'text/plain'),
                            None
                        )
                    else:
                        body = msg['payload'].get('body', {}).get('data')

                    if body:
                        body = base64.urlsafe_b64decode(body).decode()
                    else:
                        body = ''

                    messages.append({
                        'gmail_id': msg['id'],
                        'subject': subject,
                        'sender': sender,
                        'content': body,
                        'received_at': datetime.fromtimestamp(int(msg['internalDate'])/1000)
                    })

            return messages

        except Exception as e:
            # If we get a token error, try refreshing and retry once
            if "invalid_grant" in str(e):
                self.credentials = self._get_credentials()
                self.service = build('gmail', 'v1', credentials=self.credentials)
                return self.list_unarchived_emails(since)
            raise

    def archive_email(self, message_id: str) -> None:
        """Archive an email by removing INBOX label"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
        except Exception as e:
            # If we get a token error, try refreshing and retry once
            if "invalid_grant" in str(e):
                self.credentials = self._get_credentials()
                self.service = build('gmail', 'v1', credentials=self.credentials)
                self.archive_email(message_id)
            raise