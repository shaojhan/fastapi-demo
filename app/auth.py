from passlib.context import CryptContext
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer

import jwt

pwd_context = CryptContext(['md5_crypt'], deprecated='auto')

async def verfify_account_password(account, to_verify_password):
    _valid, _new_hash = pwd_context.verify_and_update()