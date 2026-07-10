"""Expense API routes"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from datetime import datetime, timedelta
from typing import List, Optional
from jose import JWTError
from app.expenses.schemas import ExpenseResponse, ExpenseCreate, ExpenseUpdate
from app.expenses.repository import ExpenseRepository
from app.core.security import verify_token

router = APIRouter(prefix="/expenses", tags=["expenses"])


def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """
    Dependency to extract and verify user_id from JWT token
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        user_id
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        payload = verify_token(token)
        user_id = str(payload.get("sub"))
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return user_id


@router.post("", response_model=ExpenseResponse)
async def create_expense(
    expense: ExpenseCreate,
    user_id: str = Depends(get_current_user)
):
    """Create a new expense"""
    return ExpenseRepository.create_expense(user_id, expense)


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: int,
    user_id: str = Depends(get_current_user)
):
    """Get expense by ID"""
    expense = ExpenseRepository.get_expense(expense_id, user_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.get("", response_model=List[ExpenseResponse])
async def list_expenses(
    user_id: str = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """List user expenses with optional filters"""
    return ExpenseRepository.get_user_expenses(
        user_id,
        skip=skip,
        limit=limit,
        category=category,
        start_date=start_date,
        end_date=end_date
    )


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    user_id: str = Depends(get_current_user)
):
    """Update an expense"""
    expense = ExpenseRepository.update_expense(expense_id, user_id, expense_update)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    user_id: str = Depends(get_current_user)
):
    """Delete an expense"""
    success = ExpenseRepository.delete_expense(expense_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted successfully"}


@router.get("/summary/by-category")
async def get_expense_summary(
    user_id: str = Depends(get_current_user),
    days: int = Query(30, ge=1),
):
    """Get expense summary by category for the last N days"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return ExpenseRepository.get_expense_summary(user_id, start_date, end_date)
