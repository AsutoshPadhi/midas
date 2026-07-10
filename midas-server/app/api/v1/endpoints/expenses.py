"""Expenses endpoints for v1 API"""
from fastapi import APIRouter
from app.expenses.routes import router as expenses_router

router = APIRouter(prefix="/api/v1")
router.include_router(expenses_router)
