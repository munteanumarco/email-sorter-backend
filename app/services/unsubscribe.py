from typing import Optional
import asyncio
import json
from openai import AsyncOpenAI
from browser_use import Agent
from browser_use.llm import ChatOpenAI
import logging
from datetime import datetime

from app.core.config import settings
from app.models import Email
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class UnsubscribeService:
    def __init__(self):
        """Initialize OpenAI client"""
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def unsubscribe_from_url(self, db: Session, email_id: int, url: str) -> bool:
        """
        Uses browser-use to navigate to the URL and complete the unsubscribe flow
        Returns True if successful, False otherwise
        """
        try:
            # Get a fresh email object from the database
            email = db.query(Email).filter(Email.id == email_id).first()
            if not email:
                logger.error(f"Email {email_id} not found")
                return False

            logger.info(f"Starting unsubscribe process for email {email_id} with URL: {url}")
            
            # Update status to pending
            email.unsubscribe_status = 'pending'
            db.add(email)
            db.commit()

            # Create an agent with specific unsubscribe task
            agent = Agent(
                task=f"""Navigate to {url} and complete the unsubscribe process. Follow these steps:
                1. Wait for the page to load completely
                2. Look for unsubscribe elements like:
                   - "Unsubscribe" or "Confirm" buttons
                   - Email input fields (use {email.sender} if needed)
                   - Checkboxes to confirm unsubscribe
                   - Dropdown menus for unsubscribe reasons
                3. Complete any required forms or confirmations
                4. Verify the unsubscribe was successful by looking for confirmation messages
                5. Return 'true' if successful, 'false' if not successful""",
                llm=ChatOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    model="gpt-4o",
                ),
                max_actions_per_step=1,
                tool_call_in_content=False
            )

            # Run the agent and get the result
            result = await agent.run()
            logger.info(f"Browser-use result: {result}")
            
            # Use OpenAI to validate the unsubscribe success
            validation_prompt = f"""
            Analyze this browser automation result and determine if the unsubscribe process was truly successful.
            Consider:
            1. Was the unsubscribe URL successfully accessed?
            2. Were any unsubscribe buttons or forms found and interacted with?
            3. Was there a clear confirmation message?
            4. Were there any errors or warnings?
            5. Did the process complete all necessary steps?

            Browser interaction result:
            {result}

            Respond with a JSON object containing:
            - success: boolean indicating if unsubscribe was successful
            - confidence: number between 0-1 indicating confidence in the assessment
            - reason: string explaining why you made this determination
            """

            validation_response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": validation_prompt}],
                response_format={"type": "json_object"}
            )
            
            validation_result = validation_response.choices[0].message.content
            logger.info(f"OpenAI validation result: {validation_result}")
            
            try:
                validation_data = json.loads(validation_result)
                success = validation_data.get("success", False)
                confidence = validation_data.get("confidence", 0)
                reason = validation_data.get("reason", "Unknown")
                
                logger.info(f"Unsubscribe validation: success={success}, confidence={confidence}, reason={reason}")
                
                # Only consider it successful if confidence is high enough
                success = success and confidence >= 0.8
            except Exception as e:
                logger.error(f"Error parsing validation result: {str(e)}")
                success = False

            # Get a fresh email object again (in case the session expired)
            email = db.query(Email).filter(Email.id == email_id).first()
            if not email:
                logger.error(f"Email {email_id} not found after unsubscribe attempt")
                return False

            if success:
                logger.info(f"Successfully unsubscribed from email {email_id}")
                # Update email record
                email.unsubscribed_at = datetime.utcnow()
                email.unsubscribe_status = 'success'
            else:
                logger.warning(f"Could not verify successful unsubscribe for email {email_id}")
                email.unsubscribe_status = 'failed'

            db.add(email)
            db.commit()
            return success

        except Exception as e:
            logger.error(f"Error during unsubscribe process for email {email_id}: {str(e)}")
            try:
                # Try to update the email status to failed
                email = db.query(Email).filter(Email.id == email_id).first()
                if email:
                    email.unsubscribe_status = 'failed'
                    db.add(email)
                    db.commit()
            except Exception as inner_e:
                logger.error(f"Error updating email status: {str(inner_e)}")
            return False