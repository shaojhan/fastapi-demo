from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Request

router = APIRouter(prefix='/sessions', tags=['session'])

ACCESS_TOKEN_LIFE = 7

def create_access_token(username: str):
    # TODO: unfinished — jwt.encode() is called with no payload/key/algorithm
    # and will raise at runtime. No route uses this yet; finish or remove it.
    expire = datetime.now(UTC) + timedelta(days=7)
    to_encode = {'sub': username, 'exp': expire}  # noqa: F841
    return jwt.encode()


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