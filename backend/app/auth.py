import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def _get_secret() -> str:
    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured. Add it to the backend .env file."
        )
    return JWT_SECRET_KEY


def hash_password(password: str) -> str:
    """Hash a password with scrypt using a random salt."""
    if not password:
        raise ValueError("Password cannot be empty")

    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return (
        "scrypt$16384$8$1$"
        + salt.hex()
        + "$"
        + derived.hex()
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against an scrypt hash."""
    try:
        scheme, n, r, p, salt_hex, hash_hex = stored_hash.split("$", 5)
        if scheme != "scrypt":
            return False

        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        _get_secret(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _get_secret(),
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
