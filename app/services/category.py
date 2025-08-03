from sqlalchemy.orm import Session
from app.models import Category, Email

class CategoryService:
    def __init__(self, db: Session):
        self.db = db

    def create_category(self, category_data: dict, user_id: int) -> Category:
        category = Category(
            name=category_data["name"],
            description=category_data.get("description"),
            user_id=user_id
        )
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def get_user_categories(self, user_id: int) -> list[Category]:
        return self.db.query(Category).filter(Category.user_id == user_id).all()

    def get_category_emails(self, category_id: int, user_id: int) -> list[Email]:
        return self.db.query(Email).filter(
            Email.category_id == category_id,
            Email.user_id == user_id
        ).all()