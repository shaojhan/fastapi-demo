"""
Password hashing and verification using bcrypt directly.

Replaces passlib.context.CryptContext. All hashes produced are standard
$2b$... bcrypt strings, fully compatible with hashes previously created
via passlib.
"""
import bcrypt


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt. Returns a $2b$... string."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
