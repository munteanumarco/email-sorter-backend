from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from oauthlib.oauth2 import WebApplicationClient
import requests
import os
import jwt

# Allow OAuth over HTTP for development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from app.api import deps
from app.core.config import settings
from app.models import User, GmailAccount
from app.schemas.user import User as UserSchema

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

def create_access_token(user_id: int) -> str:
    """Create a JWT access token for the user"""
    expires_delta = timedelta(days=7)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def get_user_from_token(token: str, db: Session) -> User | None:
    """Get user from JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
        return db.query(User).filter(User.id == user_id).first()
    except:
        return None

@router.get("/google-auth-url", response_model=dict)
def get_google_auth_url(
    connect_account: bool = False,
    current_user: User | None = Depends(deps.get_current_user_optional)
):
    """
    Get the Google OAuth2 authorization URL
    If connect_account=True, this is for connecting an additional account
    """
    # Add state to differentiate between first login and connecting account
    state = f"connect_{current_user.id}" if connect_account else "login"
    
    client = WebApplicationClient(settings.GOOGLE_CLIENT_ID)
    auth_url = client.prepare_request_uri(
        GOOGLE_AUTH_URL,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        scope=["openid", "email", "https://www.googleapis.com/auth/gmail.modify"],
        prompt="consent",
        access_type="offline",
        state=state
    )
    
    return {"url": auth_url}

@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str,
    state: str = "login",
    db: Session = Depends(deps.get_db)
):
    """
    Handle the OAuth2 callback from Google
    This endpoint is called by Google's OAuth service
    """
    try:
        result = await handle_oauth_callback(request, code, state, db)
        
        # Redirect to frontend with the result
        params = "&".join([f"{k}={v}" for k, v in result.items()])
        frontend_url = f"{settings.FRONTEND_URL}/auth/callback?{params}"
        return RedirectResponse(url=frontend_url)
    except Exception as e:
        # Redirect to frontend with error
        error_msg = str(e)
        frontend_url = f"{settings.FRONTEND_URL}/auth/callback?error={error_msg}"
        return RedirectResponse(url=frontend_url)

@router.post("/exchange-code")
async def exchange_code(
    request: Request,
    code: str,
    state: str = "login",
    db: Session = Depends(deps.get_db)
):
    """
    Exchange authorization code for tokens
    This endpoint is called by our frontend
    """
    try:
        return await handle_oauth_callback(request, code, state, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

async def handle_oauth_callback(
    request: Request,
    code: str,
    state: str,
    db: Session
) -> dict:
    """Common logic for handling OAuth callback"""
    try:
        # Handle connect flow
        current_user = None
        if state.startswith("connect_"):
            try:
                user_id = int(state.split("_")[1])
                current_user = db.query(User).filter(User.id == user_id).first()
                if not current_user:
                    raise ValueError("Invalid user ID in state")
            except (IndexError, ValueError):
                raise ValueError("Invalid state parameter")

        client = WebApplicationClient(settings.GOOGLE_CLIENT_ID)
        
        # Exchange code for tokens
        token_url, headers, body = client.prepare_token_request(
            GOOGLE_TOKEN_URL,
            authorization_response=str(request.url),
            redirect_url=settings.GOOGLE_REDIRECT_URI,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET),
        )
        
        if not token_response.ok:
            raise ValueError(f"Token exchange failed: {token_response.text}")

        # Parse token response
        client.parse_request_body_response(token_response.text)
        
        # Get user info from ID token
        id_info = id_token.verify_oauth2_token(
            client.token["id_token"],
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )

        # Handle user lookup/creation based on flow type
        if state.startswith("connect_"):
            # For connect flow, use the user ID from state
            if not current_user:
                raise ValueError("User not found for connect flow")
            user = current_user
        else:
            # For login flow, find or create user based on email
            user = db.query(User).filter(User.email == id_info["email"]).first()
            if not user:
                user = User(email=id_info["email"])
                db.add(user)
                db.commit()
        
        # Check if this Gmail account is already connected
        existing_account = db.query(GmailAccount).filter(
            GmailAccount.google_id == id_info["sub"]
        ).first()
        
        if existing_account:
            if existing_account.user_id == user.id:
                # If this is the same user trying to log in again, just update the tokens
                existing_account.access_token = client.token["access_token"]
                existing_account.refresh_token = client.token.get("refresh_token")
                existing_account.token_expiry = datetime.utcnow() + timedelta(seconds=int(client.token["expires_in"]))
                db.commit()
                
                # Return success response
                access_token = create_access_token(user.id)
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "gmail_account_id": existing_account.id
                }
            else:
                # If another user has connected this Gmail account, return error
                raise ValueError("This Gmail account is already connected to another user")

        # Check if this is the first Gmail account for the user
        is_first_account = not db.query(GmailAccount).filter(GmailAccount.user_id == user.id).first()

        # Create new Gmail account connection
        gmail_account = GmailAccount(
            email=id_info["email"],
            google_id=id_info["sub"],
            access_token=client.token["access_token"],
            refresh_token=client.token.get("refresh_token"),
            token_expiry=datetime.utcnow() + timedelta(seconds=int(client.token["expires_in"])),
            user_id=user.id,
            is_primary=is_first_account  # Set is_primary=True for the first account
        )
        
        db.add(gmail_account)
        db.commit()

        if state.startswith("connect_"):
            return {
                "message": "Gmail account connected successfully",
                "gmail_account_id": gmail_account.id
            }
        else:
            access_token = create_access_token(user.id)
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "gmail_account_id": gmail_account.id
            }

    except Exception as e:
        raise ValueError(f"Could not validate OAuth flow: {str(e)}")

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(deps.get_current_user)):
    """Test endpoint to verify current user"""
    return current_user