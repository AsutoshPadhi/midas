"""Authentication routes using Authlib"""
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import RedirectResponse
from app.auth.schemas import TokenResponse, LoginResponse, DeeplinkResponse, UserInfo
from app.auth.oauth import oauth_handler
from app.core.security import create_access_token
from app.database.base import get_connection
from app.config import settings
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Store states in memory (TODO: Use Redis in production)
auth_states = {}
# Store temporary tokens for deeplink exchange (TODO: Use Redis in production)
token_exchange = {}


@router.get("/login", response_model=LoginResponse)
async def login():
    """
    Initiate Google OAuth login flow
    
    Returns authorization URL for user to login
    """
    if not oauth_handler.is_configured():
        missing = oauth_handler.missing_config_fields()
        logger.error("Google OAuth not configured. Missing: %s", ", ".join(missing))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Google OAuth is not configured. Missing: {', '.join(missing)}"
        )

    auth_url, state = oauth_handler.get_authorization_url()
    # Store state for validation in callback
    auth_states[state] = state
    return LoginResponse(authorization_url=auth_url)


@router.get("/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    """
    Handle OAuth callback after user authorization
    
    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection
        
    Returns:
        302 Redirect to deeplink on frontend with token for exchanging access token
    """
    if not oauth_handler.is_configured():
        missing = oauth_handler.missing_config_fields()
        logger.error("Google OAuth not configured. Missing: %s", ", ".join(missing))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Google OAuth is not configured. Missing: {', '.join(missing)}"
        )

    # Validate state
    if state not in auth_states:
        logger.error(f"Invalid state parameter: {state}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    
    # Clean up state
    del auth_states[state]
    
    # Exchange code for token
    token = await oauth_handler.exchange_code_for_token(code, state)
    if not token:
        logger.error("Failed to exchange code for token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate"
        )
    
    # Get user info
    user_info = await oauth_handler.get_user_info(token.get("access_token"))
    if not user_info:
        logger.error("Failed to retrieve user info")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to retrieve user info"
        )
    
    # Get or create user in database
    try:
        email = user_info.get("email")
        display_name = user_info.get("name") or "User"
        google_id = user_info.get("sub")

        expires_at = token.get("expires_at")
        token_expiry = None
        if expires_at:
            try:
                token_expiry = datetime.fromtimestamp(int(expires_at), tz=timezone.utc).isoformat()
            except (TypeError, ValueError):
                token_expiry = None

        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT u.user_uuid, e.email_address
                FROM users u
                JOIN user_emails e ON e.user_uuid = u.user_uuid
                WHERE e.email_address = ?
                LIMIT 1
                """,
                (email,),
            ).fetchone()

            if not row:
                user_uuid = str(uuid.uuid4())
                connection.execute(
                    """
                    INSERT INTO users (
                        user_uuid, display_name, google_id, google_access_token,
                        google_refresh_token, google_token_expiry, google_token_scope,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        user_uuid,
                        display_name,
                        google_id,
                        token.get("access_token"),
                        token.get("refresh_token"),
                        token_expiry,
                        token.get("scope"),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO user_emails (user_uuid, email_address, is_primary)
                    VALUES (?, ?, 1)
                    """,
                    (user_uuid, email),
                )
                logger.info("Created new user: %s", email)
            else:
                user_uuid = row["user_uuid"]
                refresh_token = token.get("refresh_token")
                if refresh_token:
                    connection.execute(
                        """
                        UPDATE users
                        SET display_name = ?,
                            google_id = ?,
                            google_access_token = ?,
                            google_refresh_token = ?,
                            google_token_expiry = ?,
                            google_token_scope = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_uuid = ?
                        """,
                        (
                            display_name,
                            google_id,
                            token.get("access_token"),
                            refresh_token,
                            token_expiry,
                            token.get("scope"),
                            user_uuid,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE users
                        SET display_name = ?,
                            google_id = ?,
                            google_access_token = ?,
                            google_token_expiry = ?,
                            google_token_scope = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_uuid = ?
                        """,
                        (
                            display_name,
                            google_id,
                            token.get("access_token"),
                            token_expiry,
                            token.get("scope"),
                            user_uuid,
                        ),
                    )
                logger.info("Updated user: %s", email)
        
        # Create JWT access token
        access_token = create_access_token({"sub": user_uuid, "email": email})
        logger.info("Generated access token for user: %s", email)
        
        # Create a temporary token for deeplink exchange
        exchange_token = str(uuid.uuid4())
        token_exchange[exchange_token] = {
            "access_token": access_token,
            "expires_in": 1800,
            "user_uuid": user_uuid,
            "user_email": email,
            "user_name": display_name,
            "created_at": datetime.now(timezone.utc)
        }
        
        # Generate deeplink to frontend (strip trailing slash to avoid double slashes)
        frontend_base = settings.frontend_url.rstrip("/")
        deeplink_url = f"{frontend_base}/auth/callback?token={exchange_token}"
        logger.info("Generated deeplink for user: %s - redirecting to: %s", email, deeplink_url)
        
        # Return 302 redirect to deeplink
        return RedirectResponse(url=deeplink_url, status_code=302)
    
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    finally:
        pass


@router.post("/logout")
async def logout():
    """
    Logout user (invalidates JWT on client side)
    """
    logger.info("User logged out")
    return {"message": "Logged out successfully"}


@router.get("/exchange", response_model=TokenResponse)
async def exchange_token(token: str = Query(...)):
    """
    Exchange a temporary token (from deeplink) for an access token
    
    Args:
        token: Temporary exchange token from deeplink
        
    Returns:
        Access token and expiration info
    """
    if token not in token_exchange:
        logger.error(f"Invalid exchange token: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    token_data = token_exchange[token]
    
    # Clean up the used token
    del token_exchange[token]
    
    return TokenResponse(
        access_token=token_data["access_token"],
        expires_in=token_data["expires_in"],
        user=UserInfo(
            user_uuid=token_data["user_uuid"],
            email=token_data["user_email"],
            name=token_data["user_name"]
        )
    )
