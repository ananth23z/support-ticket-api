"""
app/core/security.py
====================
WHAT:  Two security jobs:
         1. Password hashing with Argon2 (hash on register, verify on login).
         2. Creating and decoding JWT access tokens.
WHY:   - We must NEVER store plain-text passwords. If the DB leaks, attackers would
         see every password. A hash is one-way: you can check a password against it
         but you can't turn it back into the password.
       - After login the client gets a JWT. It sends it with every request in the
         header `Authorization: Bearer <token>`, so the server knows who is calling
         without asking for the password again.

ASP.NET ANALOGY:
    - Argon2 hashing   ~ `PasswordHasher<TUser>` from ASP.NET Identity
    - create/decode JWT ~ `JwtSecurityTokenHandler` + `AddJwtBearer(...)` options

WHO USES IT:
    - services/auth_service.py  -> hash_password, verify_password, create_access_token
    - dependencies.py           -> decode_access_token (to find the current user)
"""

from datetime import datetime, timedelta, timezone

import jwt  # PyJWT library
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from app.core.config import settings

# ---------------------------------------------------------------------------
# PASSWORD HASHING (Argon2)
# ---------------------------------------------------------------------------
# Argon2 won the "Password Hashing Competition" and is the modern recommended
# algorithm. It is deliberately SLOW and memory-hungry, which makes brute-force
# guessing very expensive for attackers. It also adds a random "salt"
# automatically, so two users with the same password get different hashes.
_password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """Turn 'Secret123' into something like '$argon2id$v=19$m=65536,t=3,p=4$...'."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain password matches the stored hash."""
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        # argon2 raises an exception on mismatch; we convert that to a simple False
        return False


# ---------------------------------------------------------------------------
# JWT TOKENS
# ---------------------------------------------------------------------------
# A JWT has 3 parts separated by dots:  HEADER.PAYLOAD.SIGNATURE
#   - payload holds "claims" e.g. {"sub": "5", "role": "agent", "exp": 1700000000}
#   - signature = HMAC(header + payload, SECRET_KEY)
# The payload is only base64-encoded (NOT encrypted) - anyone can read it - so
# never put secrets in it. But nobody can CHANGE it without breaking the signature.

def create_access_token(user_id: int, role: str) -> str:
    """Create a signed token that says 'this is user <id> with role <role>'."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),  # "subject" = who the token is about (JWT standard says string)
        "role": role,         # extra info, handy for clients
        "exp": expire,        # "expiry" - PyJWT automatically rejects expired tokens
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Verify the signature + expiry and return the payload.
    Returns None if the token is fake, tampered with, or expired.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
