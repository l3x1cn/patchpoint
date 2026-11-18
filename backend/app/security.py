import hashlib
import secrets
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

SESSION_COOKIE_NAME: Final = "session"
PASSWORD_MIN_LENGTH: Final = 15
PASSWORD_MAX_LENGTH: Final = 128

_password_hasher: Final = PasswordHasher()
# Verified for unknown logins so that response time does not reveal whether an account exists.
_DUMMY_PASSWORD_HASH: Final = _password_hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return _password_hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def simulate_password_check(password: str) -> None:
    verify_password(password, _DUMMY_PASSWORD_HASH)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def password_policy_violation(password: str, username: str) -> str | None:
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"Password must be at most {PASSWORD_MAX_LENGTH} characters long"
    if username.casefold() in password.casefold():
        return "Password must not contain the username"

    return None
