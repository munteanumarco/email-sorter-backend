from typing import List, Optional
from openai import AsyncOpenAI
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Category, Email

class AIService:
    def __init__(self):
        """Initialize OpenAI client with API key"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def classify_email(self, email_content: str, categories: List[Category]) -> Optional[int]:
        """
        Classify an email into one of the available categories
        Returns the category ID or None if no suitable category found
        """
        if not categories:
            return None

        # Prepare the categories context
        categories_context = "\n".join([
            f"Category {cat.id}: {cat.name} - {cat.description}"
            for cat in categories
        ])

        # Prepare the prompt
        prompt = f"""You are an email classifier. Your task is to classify the following email into one of these categories:

{categories_context}

The email content is:
{email_content}

Analyze the email and choose the most appropriate category. If none of the categories fit well, return "None".
Only respond with the category ID number or "None". No other text."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise email classifier that only responds with category IDs or None."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # Use 0 for consistent results
                max_tokens=10  # We only need a number or "None"
            )

            result = response.choices[0].message.content.strip()
            
            # Parse the result
            if result.lower() == "none":
                return None
            try:
                category_id = int(result)
                # Verify the category exists
                if any(cat.id == category_id for cat in categories):
                    return category_id
            except ValueError:
                return None

            return None

        except Exception as e:
            print(f"Error in classify_email: {str(e)}")
            return None

    async def summarize_email(self, email_content: str, subject: str) -> str:
        """
        Generate a concise summary of an email
        Returns the summary text
        """
        prompt = f"""Summarize this email concisely in 2-3 sentences. Focus on the main points and any action items.

Subject: {subject}

Content:
{email_content}

Provide only the summary, no additional text."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise email summarizer that creates concise, informative summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Slightly creative but mostly consistent
                max_tokens=150  # Limit summary length
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Error in summarize_email: {str(e)}")
            return "Error generating summary"

    async def find_unsubscribe_link(self, email_content: str) -> Optional[str]:
        """
        Find and extract unsubscribe link from email content
        Returns the unsubscribe URL or None if not found
        """
        prompt = f"""Find the unsubscribe link or instructions in this email. If found, return ONLY the complete URL or instructions. If not found, return "None".

Email content:
{email_content}

Return only the unsubscribe URL or instructions, or "None". No other text."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an unsubscribe link finder that only returns URLs or None."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=100
            )

            result = response.choices[0].message.content.strip()
            return None if result.lower() == "none" else result

        except Exception as e:
            print(f"Error in find_unsubscribe_link: {str(e)}")
            return None

    async def process_new_email(self, db: Session, email: Email) -> None:
        """
        Process a new email:
        1. Generate a summary
        2. Classify it into a category
        Updates the email record in the database
        """
        try:
            # Get all categories for the user
            categories = db.query(Category).filter(Category.user_id == email.user_id).all()

            # Generate summary
            summary = await self.summarize_email(email.content, email.subject)
            email.summary = summary

            # Classify email
            category_id = await self.classify_email(email.content, categories)
            if category_id:
                email.category_id = category_id

            # Find unsubscribe link (store it for later use)
            unsubscribe_link = await self.find_unsubscribe_link(email.content)
            if unsubscribe_link:
                email.unsubscribe_link = unsubscribe_link

            # Update the email record
            db.add(email)
            db.commit()
            db.refresh(email)

        except Exception as e:
            print(f"Error in process_new_email: {str(e)}")
            db.rollback()