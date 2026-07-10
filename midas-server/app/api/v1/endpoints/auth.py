"""Auth endpoints for v1 API"""
from fastapi import APIRouter
from app.auth.routes import router as auth_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
