from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Request

from app.config import get_settings

router = APIRouter(prefix='/sessions', tags=['session'])

ACCESS_TOKEN_LIFE = 7

def create_access_token(username: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=ACCESS_TOKEN_LIFE)
    to_encode = {'sub': username, 'exp': expire}
    return jwt.encode(to_encode, get_settings().JWT_KEY, algorithm='HS256')


def validate_session(request: Request) -> bool:
    session_authorization = request.cookies.get("Authorization")
    session_id = request.session.get("session_id")
    session_access_token = request.session.get("access_token")

    if not session_authorization and not session_access_token:
        return False
    if session_authorization != session_id:
        return False
    # if is_token_expired(token_exp):
    #     return False
    
    return True