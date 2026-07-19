"""Реализация TokenService на JWT (python-jose).

Реализует Protocol из services/ports.py. Access и refresh токены
различаются типом claim (`sub` — user_id, `type` — access/refresh).
"""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from uuid import UUID

from vibeshopping.infrastructure.config import Settings
from vibeshopping.services.ports import TokenService

settings = Settings()


class JoseTokenService(TokenService):
    """JWT-токены через python-jose (FR-03, FR-04, FR-05)."""

    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str | None = None,
        access_expire_minutes: int | None = None,
        refresh_expire_days: int | None = None,
    ) -> None:
        self._secret_key = secret_key or settings.JWT_SECRET_KEY
        self._algorithm = algorithm or settings.JWT_ALGORITHM
        self._access_expire = timedelta(
            minutes=access_expire_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        self._refresh_expire = timedelta(
            days=refresh_expire_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    def create_access_token(self, user_id: UUID) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "type": "access",
            "exp": now + self._access_expire,
            "iat": now,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: UUID) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": now + self._refresh_expire,
            "iat": now,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_user_id(self, token: str) -> UUID | None:
        try:
            payload = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
            )
            return UUID(payload["sub"])
        except (JWTError, KeyError, ValueError):
            return None
