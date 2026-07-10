"""Pydantic schemas for authentication"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for user creation"""
    google_id: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    google_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    """Schema for user info"""
    user_uuid: str
    email: str
    name: str


class TokenResponse(BaseModel):
    """Schema for token response with user info"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class DeeplinkResponse(BaseModel):
    """Schema for deeplink response after OAuth callback"""
    deeplink_url: str
    user_email: str


class LoginResponse(BaseModel):
    """Schema for login response with authorization URL"""
    authorization_url: str
