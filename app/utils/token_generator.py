import secrets
import jwt
import time

JWT_SECRET = "secret"

def generate_token_with_expiry(uid: str):
    payload = {
        "user_id": uid,
        "expires": time.time() + 900
    }
    token = jwt.encode(payload, 'your_secret_key', algorithm='HS256')
    return token

def verify_token(token: str):
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return {} if decoded_token['expires'] < time.time() else decoded_token
    except:
        return {}