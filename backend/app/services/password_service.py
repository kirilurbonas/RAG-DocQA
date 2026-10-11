"""Password hashing and verification using argon2."""

import logging
from typing import Tuple

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, VerificationError
except ImportError:
    PasswordHasher = None
    VerifyMismatchError = None
    VerificationError = None

logger = logging.getLogger(__name__)


class PasswordService:
    """Secure password hashing using argon2."""

    def __init__(self):
        """Initialize password service."""
        if PasswordHasher is None:
            raise ImportError(
                "argon2-cffi is required for password hashing. "
                "Install with: pip install argon2-cffi"
            )
        self.hasher = PasswordHasher()

    def hash_password(self, password: str) -> str:
        """
        Hash a password using argon2.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        try:
            return self.hasher.hash(password)
        except Exception as e:
            logger.error(f"Failed to hash password: {e}")
            raise

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            password: Plain text password
            password_hash: Hashed password to verify against

        Returns:
            True if password matches, False otherwise
        """
        if not password or not password_hash:
            return False

        try:
            self.hasher.verify(password_hash, password)
            return True
        except (VerifyMismatchError, VerificationError):
            return False
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """
        Check if a password hash needs rehashing (e.g., algorithm changed).

        Args:
            password_hash: Password hash to check

        Returns:
            True if hash should be updated
        """
        try:
            return self.hasher.check_needs_rehash(password_hash)
        except Exception:
            return True


# Global instance
_password_service = None


def get_password_service() -> PasswordService:
    """Get or create password service instance."""
    global _password_service
    if _password_service is None:
        _password_service = PasswordService()
    return _password_service
