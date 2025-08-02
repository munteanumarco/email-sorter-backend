from fastapi import APIRouter
from app.api.api_v1.endpoints import auth, categories, emails, gmail_accounts

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(gmail_accounts.router, prefix="/gmail-accounts", tags=["gmail-accounts"])