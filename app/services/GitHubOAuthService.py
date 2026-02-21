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

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_USER_EMAILS_URL = "https://api.github.com/user/emails"

# Authorization code TTL in seconds
AUTH_CODE_TTL = 60  # 1 minute

# In-memory store for authorization codes (use Redis in production)
_auth_codes: dict[str, dict] = {}


class GitHubOAuthService:
    """Application service for GitHub OAuth2 Authorization Code Flow."""

    def __init__(self):
        self._settings = get_settings()
        self._auth_domain_service = AuthenticationDomainService()

    def get_authorization_url(self) -> str:
        """Build the GitHub OAuth2 authorization URL."""
        params = {
            "client_id": self._settings.GITHUB_CLIENT_ID,
            "redirect_uri": self._settings.GITHUB_REDIRECT_URI,
            "scope": "read:user user:email",
        }
        return f"{GITHUB_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange the authorization code for GitHub tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": self._settings.GITHUB_CLIENT_ID,
                    "client_secret": self._settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": self._settings.GITHUB_REDIRECT_URI,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_github_user_info(self, access_token: str) -> dict:
        """Fetch user info from GitHub's API, including primary email."""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            # Get basic user info
            resp = await client.get(GITHUB_USER_URL, headers=headers)
            resp.raise_for_status()
            user_info = resp.json()

            # If email is not public, fetch from emails endpoint
            if not user_info.get("email"):
                email_resp = await client.get(GITHUB_USER_EMAILS_URL, headers=headers)
                email_resp.raise_for_status()
                emails = email_resp.json()
                primary = next((e for e in emails if e.get("primary")), None)
                if primary:
                    user_info["email"] = primary["email"]

            return user_info

    def authenticate_github_user(self, github_user: dict) -> tuple[AuthToken, UserModel]:
        """
        Find or create a user from GitHub user info, then return a JWT.

        Args:
            github_user: Dict with keys: id, email, login, name, avatar_url

        Returns:
            Tuple of (AuthToken, UserModel)
        """
        github_id = str(github_user["id"])
        email = github_user.get("email")

        with UserUnitOfWork() as uow:
            # 1. Try find by github_id (returning user)
            user = uow.repo.get_by_github_id(github_id)
            if user:
                token = self._auth_domain_service.create_token(user.id, user.uid)
                return token, user

            # 2. Try find by email (link GitHub account)
            if email:
                user = uow.repo.get_by_email(email)
                if user:
                    uow.repo.link_github_id(user.id, github_id)
                    uow.commit()
                    token = self._auth_domain_service.create_token(user.id, user.uid)
                    return token, user

            # 3. Auto-register new user
            if not email:
                raise ValueError("GitHub account has no associated email address")

            uid = self._generate_unique_uid(github_user.get("login") or email.split("@")[0], uow)
            dummy_password = pwd_context.hash(secrets.token_urlsafe(32))

            user_dict = {
                "id": uuid4(),
                "uid": uid,
                "email": email,
                "pwd": dummy_password,
                "role": "NORMAL",
                "email_verified": True,
                "github_id": github_id,
            }
            profile_dict = {
                "name": github_user.get("name") or uid,
                "birthdate": date(2000, 1, 1),
                "description": "",
            }
            uow.repo.add(user_dict, profile_dict)
            uow.commit()

            user = uow.repo.get_by_github_id(github_id)
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
    def _generate_unique_uid(base: str, uow) -> str:
        """Generate a unique uid from GitHub login or email prefix."""
        uid = base
        counter = 1
        while uow.repo.exists_by_uid(uid):
            uid = f"{base}_{counter}"
            counter += 1
        return uid
