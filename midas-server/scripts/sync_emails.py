"""Background task to sync emails from Gmail and extract expenses"""
import asyncio
import logging
from datetime import datetime
from app.email.gmail_client import GmailClient
from app.email.email_parser import EmailParser
from app.expenses.expense_extractor import get_expense_extractor
from app.expenses.categorizer import get_expense_categorizer
from app.expenses.repository import ExpenseRepository, EmailMessageRepository

logger = logging.getLogger(__name__)


async def sync_emails_for_user(user_uuid: str, gmail_client: GmailClient):
    """
    Sync emails from Gmail and extract expenses
    
    Args:
        user_uuid: User UUID to sync emails for
        gmail_client: Configured Gmail client
    """
    try:
        logger.info(f"Starting email sync for user {user_uuid}")
        
        # Get messages from Gmail
        messages = gmail_client.get_messages(query="in:inbox", max_results=50)
        
        if not messages:
            logger.info(f"No new messages for user {user_uuid}")
            return
        
        extractor = get_expense_extractor()
        categorizer = get_expense_categorizer()
        
        for message in messages:
            message_id = message.get("id")
            
            # Get full message details
            full_message = gmail_client.get_message_details(message_id)
            if not full_message:
                continue
            
            # Parse email content
            parser = EmailParser()
            headers = parser.extract_headers(full_message)
            text_body, html_body = parser.extract_body(full_message)
            
            subject = headers.get("subject", "")
            sender = headers.get("from", "")
            received_at = headers.get("date", datetime.utcnow())
            
            # Store email message
            email_record = EmailMessageRepository.create_email_message(
                user_uuid=user_uuid,
                gmail_id=message_id,
                subject=subject,
                sender=sender,
                body_text=text_body or "",
                body_html=html_body,
                received_at=received_at
            )
            
            # Extract expenses using LLM
            if text_body:
                extraction_result = extractor.extract_expenses(
                    email_content=text_body,
                    email_subject=subject,
                    email_sender=sender
                )
                
                if extraction_result and extraction_result.get("expenses"):
                    # Save extracted expenses
                    for expense_data in extraction_result["expenses"]:
                        # Categorize expense
                        categorization = categorizer.categorize_expense(
                            merchant=expense_data.get("merchant", "Unknown"),
                        )
                        
                        # Create expense in database
                        from app.expenses.schemas import ExpenseCreate
                        from datetime import datetime as dt
                        
                        expense_create = ExpenseCreate(
                            amount=expense_data.get("amount"),
                            currency=expense_data.get("currency", "USD"),
                            merchant=expense_data.get("merchant"),
                            description=expense_data.get("description", ""),
                            category=categorization.get("category", "Other"),
                            transaction_date=dt.fromisoformat(
                                expense_data.get("date", dt.utcnow().isoformat())
                            ),
                            email_message_id=message_id,
                            notes=None,
                        )
                        
                        expense = ExpenseRepository.create_expense(user_uuid, expense_create)
                        logger.info(f"Created expense {expense['id']} from email")
            
            # Mark email as processed
            EmailMessageRepository.mark_as_processed(email_record["id"])
        
        logger.info(f"Email sync completed for user {user_uuid}")
    
    except Exception as e:
        logger.error(f"Error syncing emails for user {user_uuid}: {e}")


async def run_email_sync_scheduler():
    """
    Run email sync scheduler
    
    This would typically be run as a background task/cron job
    """
    # TODO: Implement periodic scheduling
    # This is a placeholder for the scheduling logic
    logger.info("Email sync scheduler started")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        user_uuid = sys.argv[1]
        # TODO: Initialize Gmail client with user credentials
        # gmail_client = GmailClient(credentials)
        # asyncio.run(sync_emails_for_user(user_uuid, gmail_client))
    else:
        print("Usage: python sync_emails.py <user_uuid>")
