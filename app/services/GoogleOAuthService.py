import secrets
import time
from datetime import date
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from passlib.context import CryptContext

from app.config import get_settings
from app.domain.UserModel import UserModel
from app.domain.services.AuthenticationService import AuthToken, AuthenticationDomainService
from app.services.unitofwork.UserUnitOfWork import UserUnitOfWork

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Authorization code TTL in seconds
AUTH_CODE_TTL = 60  # 1 minute

# In-memory store for authorization codes (use Redis in production)
_auth_codes: dict[str, dict] = {}


class GoogleOAuthService:
    """Application service for Google OAuth2 Authorization Code Flow."""

    def __init__(self):
        self._settings = get_settings()
        self._auth_domain_service = AuthenticationDomainService()

    def get_authorization_url(self) -> str:
        """Build the Google OAuth2 authorization URL."""
        params = {
            "client_id": self._settings.GOOGLE_CLIENT_ID,
            "redirect_uri": self._settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange the authorization code for Google tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": self._settings.GOOGLE_CLIENT_ID,
                "client_secret": self._settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": self._settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            return resp.json()

    async def get_google_user_info(self, access_token: str) -> dict:
        """Fetch user info from Google's userinfo endpoint."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    def authenticate_google_user(self, google_user: dict) -> tuple[AuthToken, UserModel]:
        """
        Find or create a user from Google user info, then return a JWT.

        Args:
            google_user: Dict with keys: id, email, name, picture, verified_email

        Returns:
            Tuple of (AuthToken, UserModel)
        """
        google_id = google_user["id"]
        email = google_user["email"]

        with UserUnitOfWork() as uow:
            # 1. Try find by google_id (returning user)
            user = uow.repo.get_by_google_id(google_id)
            if user:
                token = self._auth_domain_service.create_token(user.id, user.uid)
                return token, user

            # 2. Try find by email (link Google account)
            user = uow.repo.get_by_email(email)
            if user:
                uow.repo.link_google_id(user.id, google_id)
                uow.commit()
                token = self._auth_domain_service.create_token(user.id, user.uid)
                return token, user

            # 3. Auto-register new user
            uid = self._generate_unique_uid(email, uow)
            dummy_password = pwd_context.hash(secrets.token_urlsafe(32))

            user_dict = {
                "id": uuid4(),
                "uid": uid,
                "email": email,
                "pwd": dummy_password,
                "role": "NORMAL",
                "email_verified": True,
                "google_id": google_id,
            }
            profile_dict = {
                "name": google_user.get("name", uid),
                "birthdate": date(2000, 1, 1),
                "description": "",
            }
            uow.repo.add(user_dict, profile_dict)
            uow.commit()

            user = uow.repo.get_by_google_id(google_id)
            token = self._auth_domain_service.create_token(user.id, user.uid)
            return token, user

    def create_auth_code(self, token: AuthToken, user: UserModel) -> str:
        """Create a short-lived authorization code that maps to a token + user."""
        code = secrets.token_urlsafe(32)
        _auth_codes[code] = {
            "token": token,
            "user": user,
            "created_at": time.time(),
        }
        self._cleanup_expired_codes()
        return code

    def exchange_auth_code(self, code: str) -> tuple[AuthToken, UserModel]:
        """Exchange a short-lived authorization code for an access token."""
        auth_data = _auth_codes.pop(code, None)
        if not auth_data:
            raise ValueError("Invalid or expired authorization code")

        if time.time() - auth_data["created_at"] > AUTH_CODE_TTL:
            raise ValueError("Authorization code has expired")

        return auth_data["token"], auth_data["user"]

    @staticmethod
    def _cleanup_expired_codes() -> None:
        """Remove expired authorization codes."""
        now = time.time()
        expired = [k for k, v in _auth_codes.items() if now - v["created_at"] > AUTH_CODE_TTL]
        for k in expired:
            _auth_codes.pop(k, None)

    @staticmethod
    def _generate_unique_uid(email: str, uow) -> str:
        """Generate a unique uid from email prefix."""
        base_uid = email.split("@")[0]
        uid = base_uid
        counter = 1
        while uow.repo.exists_by_uid(uid):
            uid = f"{base_uid}_{counter}"
            counter += 1
        return uid
