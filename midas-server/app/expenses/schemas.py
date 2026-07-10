"""Pydantic schemas for expenses"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ExpenseBase(BaseModel):
    """Base expense schema"""
    amount: Decimal
    currency: str = "USD"
    merchant: str
    description: str
    category: str
    transaction_date: datetime
    notes: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    """Schema for creating an expense"""
    email_message_id: Optional[str] = None


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense"""
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    transaction_date: Optional[datetime] = None
    notes: Optional[str] = None


class ExpenseResponse(ExpenseBase):
    """Schema for expense response"""
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ExpenseCategory(BaseModel):
    """Schema for expense category"""
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class ExpenseSummary(BaseModel):
    """Schema for expense summary"""
    total_amount: Decimal
    currency: str
    count: int
    category: str
    average_amount: Decimal
    date_range: tuple  # (start_date, end_date)
