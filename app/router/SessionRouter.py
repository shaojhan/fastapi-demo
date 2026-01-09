from fastapi import APIRouter, HTTPException, Request

from datetime import datetime, timedelta, timezone
import jwt

router = APIRouter(prefix='/sessions', tags=['session'])

ACCESS_TOKEN_LIFE = 7

def create_access_token(username: str):
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode = {'sub': username, 'exp': expire}
    return jwt.encode()


def validate_session(request: Request) -> bool:
    session_authorization = request.cookies.get("Authorization")
    session_id = request.session.get("session_id")
    session_access_token = request.session.get("access_token")
    token_exp = request.session.get("token_expiry")

    if not session_authorization and not session_access_token:
        return False
    if session_authorization != session_id:
        return False
    # if is_token_expired(token_exp):
    #     return False
    
    return True