"""Email parsing utilities"""
import base64
from email.mime.text import MIMEText
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class EmailParser:
    """Parse and extract content from Gmail messages"""
    
    @staticmethod
    def extract_body(message: dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text and HTML body from message
        
        Args:
            message: Gmail message object
            
        Returns:
            Tuple of (text_body, html_body)
        """
        text_body = None
        html_body = None
        
        try:
            payload = message.get("payload", {})
            
            if "parts" in payload:
                # Multipart message
                for part in payload["parts"]:
                    mime_type = part.get("mimeType", "")
                    if mime_type == "text/plain":
                        data = part.get("body", {}).get("data", "")
                        if data:
                            text_body = base64.urlsafe_b64decode(data).decode("utf-8")
                    elif mime_type == "text/html":
                        data = part.get("body", {}).get("data", "")
                        if data:
                            html_body = base64.urlsafe_b64decode(data).decode("utf-8")
            else:
                # Simple message
                data = payload.get("body", {}).get("data", "")
                if data:
                    text_body = base64.urlsafe_b64decode(data).decode("utf-8")
        
        except Exception as e:
            logger.error(f"Error extracting body: {e}")
        
        return text_body, html_body
    
    @staticmethod
    def extract_headers(message: dict) -> dict:
        """
        Extract important headers from message
        
        Args:
            message: Gmail message object
            
        Returns:
            Dictionary with headers (subject, from, to, date)
        """
        headers = {}
        
        try:
            header_list = message.get("payload", {}).get("headers", [])
            
            for header in header_list:
                name = header.get("name", "").lower()
                value = header.get("value", "")
                
                if name in ["subject", "from", "to", "date"]:
                    headers[name] = value
        
        except Exception as e:
            logger.error(f"Error extracting headers: {e}")
        
        return headers
    
    @staticmethod
    def extract_attachments(message: dict) -> list:
        """
        Extract attachment information from message
        
        Args:
            message: Gmail message object
            
        Returns:
            List of attachment metadata
        """
        attachments = []
        
        try:
            payload = message.get("payload", {})
            
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("filename"):
                        attachments.append({
                            "filename": part.get("filename"),
                            "mime_type": part.get("mimeType"),
                            "attachment_id": part.get("body", {}).get("attachmentId")
                        })
        
        except Exception as e:
            logger.error(f"Error extracting attachments: {e}")
        
        return attachments
