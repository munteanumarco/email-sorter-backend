from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = "http://localhost:8000/api/v1/auth/google/callback"
    
    # Frontend
    FRONTEND_URL: Optional[str] = "http://localhost:4200"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()