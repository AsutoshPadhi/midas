from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.base import init_db
from app.core.logging import setup_logging
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.expenses import router as expenses_router
from app.api.v1.endpoints.email import router as email_router

# Setup logging
logger = setup_logging(settings.app_name)

# Validate OAuth configuration
if not settings.google_client_id or not settings.google_client_secret:
    logger.warning("Google OAuth credentials not configured. Auth will not work.")

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# Add CORS middleware
cors_origins = [
    "http://localhost:8081",
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(expenses_router)
app.include_router(email_router)


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Midas server starting up")
    logger.info(
        "LLM configuration provider=%s model=%s base_url=%s",
        settings.llm_provider,
        settings.llm_model,
        settings.llm_base_url or "default",
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Midas server shutting down")


def main():
    """Run the server"""
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )


if __name__ == "__main__":
    main()
