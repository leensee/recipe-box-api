import secrets
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(plain_password: str) -> str:
    return generate_password_hash(plain_password)

def verify_password(stored_hash: str, candidate: str) -> bool:
    return check_password_hash(stored_hash, candidate)

DUMMY_HASH = hash_password(secrets.token_urlsafe(32))
