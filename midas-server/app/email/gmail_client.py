"""Gmail API client wrapper"""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    """Wrapper for Gmail API interactions"""
    
    def __init__(self, access_token: str):
        """
        Initialize Gmail client with access token from OAuth
        
        Args:
            access_token: OAuth access token from Google
        """
        # Create credentials from access token
        self.credentials = Credentials(token=access_token)
        self.service = build("gmail", "v1", credentials=self.credentials, cache_discovery=False)
    
    def get_messages(
        self, 
        query: str = "is:unread",
        max_results: int = 10
    ) -> List[dict]:
        """
        Get messages from Gmail
        
        Args:
            query: Gmail search query
            max_results: Maximum results to return
            
        Returns:
            List of message objects
        """
        try:
            results = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results
            ).execute()
            return results.get("messages", [])
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
    
    def get_message_details(self, message_id: str) -> Optional[dict]:
        """
        Get full message details
        
        Args:
            message_id: ID of the message
            
        Returns:
            Full message object with headers and body
        """
        try:
            message = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()
            return message
        except Exception as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            return None
