"""Реализация PasswordHasher на bcrypt.

Реализует Protocol из services/ports.py. Используется в production
через Depends (views/dependencies.py).
"""

import bcrypt

from vibeshopping.services.ports import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    """Хеширование паролей через bcrypt (FR-02)."""

    def hash(self, password: str) -> str:
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), hashed.encode("utf-8")
            )
        except ValueError:
            return False
