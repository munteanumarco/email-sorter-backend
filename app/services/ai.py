from typing import List, Optional
from openai import AsyncOpenAI
from datetime import datetime
import logging
import re
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Category, Email

logger = logging.getLogger(__name__)

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
            logger.info("No categories available for classification")
            return None

        # Prepare the categories context
        categories_context = "\n".join([
            f"Category {cat.id}: {cat.name} - {cat.description}"
            for cat in categories
        ])
        logger.debug(f"Available categories for classification:\n{categories_context}")

        # Prepare the prompt
        prompt = f"""You are an email classifier. Your task is to classify the following email into one of these categories:

{categories_context}

The email content is:
{email_content}

Analyze the email and choose the most appropriate category. If none of the categories fit well, return "None".
IMPORTANT: Only respond with the numeric ID (e.g., "3") or "None". Do not include the word "Category" or any other text."""

        try:
            logger.debug("Sending classification request to OpenAI")
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise email classifier that only responds with numeric IDs or None."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # Use 0 for consistent results
                max_tokens=10  # We only need a number or "None"
            )

            result = response.choices[0].message.content.strip()
            logger.debug(f"Raw classification result: {result}")
            
            # Parse the result
            if result.lower() == "none":
                logger.info("Email did not match any category")
                return None
            try:
                # Extract just the number if it's in the format "Category X"
                number_match = re.search(r'\d+', result)
                if number_match:
                    category_id = int(number_match.group())
                else:
                    category_id = int(result)
                
                # Verify the category exists
                matching_category = next((cat for cat in categories if cat.id == category_id), None)
                if matching_category:
                    logger.info(f"Email classified into category: {matching_category.name} (ID: {category_id})")
                    return category_id
                else:
                    logger.warning(f"AI returned invalid category ID: {category_id}")
            except ValueError:
                logger.warning(f"AI returned non-numeric result: {result}")
                return None

            return None

        except Exception as e:
            logger.error(f"Error in classify_email: {str(e)}")
            return None

    async def summarize_email(self, email_content: str, subject: str) -> str:
        """
        Generate a concise summary of an email
        Returns the summary text
        """
        logger.debug(f"Generating summary for email: {subject}")
        prompt = f"""Summarize this email concisely in 2-3 sentences. Focus on the main points and any action items.

Subject: {subject}

Content:
{email_content}

Provide only the summary, no additional text."""

        try:
            logger.debug("Sending summarization request to OpenAI")
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise email summarizer that creates concise, informative summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Slightly creative but mostly consistent
                max_tokens=150  # Limit summary length
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated summary ({len(summary)} chars): {summary[:100]}...")
            return summary

        except Exception as e:
            logger.error(f"Error in summarize_email: {str(e)}")
            return "Error generating summary"

    async def find_unsubscribe_link(self, email_content: str) -> Optional[str]:
        """
        Find and extract unsubscribe link from email content
        Returns the unsubscribe URL or None if not found
        """
        logger.debug("Searching for unsubscribe link in email content")
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
            if result.lower() == "none":
                logger.info("No unsubscribe link found in email")
                return None
            else:
                logger.info(f"Found unsubscribe link: {result}")
                return result

        except Exception as e:
            logger.error(f"Error in find_unsubscribe_link: {str(e)}")
            return None

    async def process_new_email(self, db: Session, email: Email) -> None:
        """
        Process a new email:
        1. Generate a summary
        2. Classify it into a category
        Updates the email record in the database
        """
        try:
            logger.info(f"Processing new email: {email.subject} (ID: {email.id})")
            
            # Get all categories for the user
            categories = db.query(Category).filter(Category.user_id == email.user_id).all()
            logger.info(f"Found {len(categories)} categories for user {email.user_id}")

            # Generate summary
            logger.info("Generating email summary...")
            summary = await self.summarize_email(email.content, email.subject)
            email.summary = summary
            logger.info("Summary generated successfully")

            # Classify email
            logger.info("Classifying email...")
            category_id = await self.classify_email(email.content, categories)
            if category_id:
                category = next(cat for cat in categories if cat.id == category_id)
                email.category_id = category_id
                logger.info(f"Email classified into category: {category.name}")
            else:
                logger.info("Email could not be classified into any category")

            # Find unsubscribe link (store it for later use)
            logger.info("Searching for unsubscribe link...")
            unsubscribe_link = await self.find_unsubscribe_link(email.content)
            if unsubscribe_link:
                email.unsubscribe_link = unsubscribe_link
                logger.info(f"Unsubscribe link found and stored")

            # Update the email record
            db.add(email)
            db.commit()
            db.refresh(email)
            logger.info(f"Email processing completed successfully")

        except Exception as e:
            logger.error(f"Error processing email {email.id}: {str(e)}")
            db.rollback()