"""Google OAuth2 implementation using Authlib"""
from authlib.integrations.httpx_client import AsyncOAuth2Client
from app.config import settings
import logging
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode
import secrets

logger = logging.getLogger(__name__)


class GoogleOAuth:
    """Handle Google OAuth2 flow using Authlib"""
    
    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = f"{settings.server_url}/api/v1/auth/callback"
        self.scopes = " ".join([
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ] + settings.gmail_api_scopes)
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"

    def is_configured(self) -> bool:
        """Return True when required Google OAuth settings are present."""
        return bool(self.client_id and self.client_secret)

    def missing_config_fields(self) -> list[str]:
        """List missing OAuth settings so callers can report actionable errors."""
        missing = []
        if not self.client_id:
            missing.append("GOOGLE_CLIENT_ID")
        if not self.client_secret:
            missing.append("GOOGLE_CLIENT_SECRET")
        return missing
    
    def get_authorization_url(self) -> Tuple[str, str]:
        """
        Generate the authorization URL for user login
        
        Returns:
            Authorization URL and OAuth state token
        """
        if not self.is_configured():
            raise RuntimeError(
                f"Google OAuth is not configured. Missing: {', '.join(self.missing_config_fields())}"
            )

        state = secrets.token_urlsafe(32)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scopes,
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        auth_url = f"{self.authorization_endpoint}?{urlencode(params)}"
        logger.info(f"Generated authorization URL with state: {state}")
        return auth_url, state
    
    async def exchange_code_for_token(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from callback
            state: State parameter for validation
            
        Returns:
            Token information including access_token and user info
        """
        try:
            async with AsyncOAuth2Client(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri
            ) as client:
                token = await client.fetch_token(
                    self.token_endpoint,
                    code=code
                )
                logger.info("Successfully exchanged code for token")
                return token
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return None

    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh Google access token using refresh token.

        Args:
            refresh_token: Google OAuth refresh token

        Returns:
            Refreshed token payload
        """
        if not self.is_configured():
            logger.error("Google OAuth is not configured")
            return None

        try:
            async with AsyncOAuth2Client(
                client_id=self.client_id,
                client_secret=self.client_secret,
            ) as client:
                token = await client.refresh_token(
                    self.token_endpoint,
                    refresh_token=refresh_token,
                )
                logger.info("Successfully refreshed Google access token")
                return token
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user info from access token
        
        Args:
            access_token: OAuth access token
            
        Returns:
            User information (email, name, picture, etc.)
        """
        try:
            async with AsyncOAuth2Client(token={"access_token": access_token}) as client:
                resp = await client.get(self.userinfo_endpoint)
                user_info = resp.json()
                logger.info(f"Retrieved user info for {user_info.get('email')}")
                return user_info
        except Exception as e:
            logger.error(f"Error fetching user info: {e}")
            return None


oauth_handler = GoogleOAuth()
