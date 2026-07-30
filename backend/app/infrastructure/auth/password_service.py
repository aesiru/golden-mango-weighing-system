"""
Password Service
=================
Wraps bcrypt for password hashing and verification.
"""
import bcrypt


class PasswordService:
    """Password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
