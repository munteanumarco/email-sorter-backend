import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test_secret_key_123"
os.environ["GOOGLE_CLIENT_ID"] = "test_client_id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test_client_secret"
os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8000/api/v1/auth/google/callback"
os.environ["OPENAI_API_KEY"] = "test_openai_key"
os.environ["FRONTEND_URL"] = "http://localhost:4200"

from app.core.database import Base
from app.models import User, Category, Email, GmailAccount

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db):
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_category(db, test_user):
    category = Category(
        name="Test Category",
        description="Test Description",
        user_id=test_user.id
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category