"""Application configuration and settings"""
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App
    app_name: str = "Midas Server"
    app_version: str = "0.1.0"
    debug: bool = False
    server_url: str = "http://localhost:8000"  # Used for OAuth redirect
    frontend_url: str = "http://localhost:3000"  # Frontend URL for deeplinks
    
    # Database
    database_url: str = "sqlite:///./midas.db"
    
    # OAuth (Google)
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    
    # Gmail API
    gmail_api_scopes: list = ["https://www.googleapis.com/auth/gmail.readonly"]
    
    # LLM
    llm_provider: str = "openai"  # openai, groq, ollama, etc.
    llm_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None  # For Groq provider
    ollama_api_key: Optional[str] = None  # Optional; Ollama commonly uses a dummy key
    llm_base_url: Optional[str] = None
    llm_model: str = "gpt-4-turbo"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env
    
    def __init__(self, **data):
        super().__init__(**data)
        # Select API key based on provider and strip quotes
        if self.llm_provider == "groq" and self.groq_api_key:
            self.llm_api_key = self.groq_api_key.strip('"\'')
        elif self.llm_provider == "ollama":
            key = self.llm_api_key or self.ollama_api_key or "ollama"
            self.llm_api_key = key.strip('"\'')
            if not self.llm_base_url:
                self.llm_base_url = "http://localhost:11434/v1"
        elif self.llm_api_key:
            self.llm_api_key = self.llm_api_key.strip('"\'')


settings = Settings()
