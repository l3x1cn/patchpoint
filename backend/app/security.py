import hashlib
import secrets
import threading
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

PASSWORD_MIN_LENGTH: Final = 15
PASSWORD_MAX_LENGTH: Final = 128

# The default argon2-cffi PasswordHasher uses 64 MiB per call, so 4 concurrent calls take 256 MiB,
# below the API's `mem_limit: 1g` in compose.yaml. Further requests wait in their own worker
# thread, not in the event loop.
PASSWORD_HASH_CONCURRENCY: Final = 4

_password_hasher: Final = PasswordHasher()
_hash_slots: Final = threading.BoundedSemaphore(PASSWORD_HASH_CONCURRENCY)

# Verified for unknown logins so that response time does not reveal whether an account exists.
_DUMMY_PASSWORD_HASH: Final = _password_hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    with _hash_slots:
        return _password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    with _hash_slots:
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
