import os
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()
def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Passwords must contain at least 12 characters")
    return _password_hash.hash(password)
def authenticate(password: str, encoded: str) -> bool:
    try:
        return _password_hash.verify(password, encoded)
    except Exception:
        return False
def create_access_token(claims: dict) -> str:
    secret = os.getenv("CBC_JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("CBC_JWT_SECRET must be configured with at least 32 characters")
    payload = dict(claims)
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("CBC_TOKEN_MINUTES", "30")))
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, secret, algorithm="HS256")
def decode_access_token(token: str) -> dict:
    secret = os.getenv("CBC_JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("CBC_JWT_SECRET is not configured securely")
    return jwt.decode(token, secret, algorithms=["HS256"])
