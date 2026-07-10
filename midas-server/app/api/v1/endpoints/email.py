"""Email endpoints for v1 API"""
from fastapi import APIRouter
from app.email.routes import router as email_router

router = APIRouter(prefix="/api/v1")
router.include_router(email_router)
