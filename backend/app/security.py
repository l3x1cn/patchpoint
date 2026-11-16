import hashlib
import time
from typing import Final

SESSION_COOKIE_NAME: Final = "session"


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def generate_session_token(username: str) -> str:
    return hashlib.md5(f"{username}:{int(time.time())}".encode()).hexdigest()
