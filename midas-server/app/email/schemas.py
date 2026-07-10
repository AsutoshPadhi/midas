"""Pydantic schemas for email data"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EmailMessage(BaseModel):
    """Schema for an email message"""
    message_id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    received_at: datetime
    labels: list = []


class ParsedEmail(BaseModel):
    """Schema for parsed email content"""
    message_id: str
    original_subject: str
    original_sender: str
    text_content: str
    html_content: Optional[str] = None
    received_at: datetime


class EmailSync(BaseModel):
    """Schema for email sync status"""
    user_id: int
    last_synced_at: datetime
    total_emails: int
    sync_status: str = "completed"  # in_progress, completed, failed
