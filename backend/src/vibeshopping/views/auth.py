"""HTTP-обработчики аутентификации.

Тонкий слой: парсинг DTO → вызов use case → маппинг в response DTO.
Никакой бизнес-логики. Ошибки маппятся через domain_error_handler.
"""

from fastapi import APIRouter, Depends

from vibeshopping.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
)
from vibeshopping.services.auth import TokenPair
from vibeshopping.services.ports import TokenService
from vibeshopping.views.dependencies import (
    _token_service,
    domain_error_handler,
    get_login_user,
    get_refresh_token,
    get_register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair_to_dto(pair: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
    )


@router.post("/register", status_code=201)
async def register(
    body: UserCreate,
    use_case=Depends(get_register_user),
    tokens: TokenService = Depends(lambda: _token_service),
) -> TokenResponse:
    """Регистрация нового пользователя (FR-01).

    После успешной регистрации сразу выпускаем пару токенов,
    чтобы клиенту не нужен был дополнительный запрос на логин.
    """
    try:
        user = await use_case.execute(email=body.email, password=body.password)
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    pair = TokenPair(
        access_token=tokens.create_access_token(user.id),
        refresh_token=tokens.create_refresh_token(user.id),
    )
    return _token_pair_to_dto(pair)


@router.post("/login")
async def login(
    body: LoginRequest,
    use_case=Depends(get_login_user),
) -> TokenResponse:
    """Аутентификация по email и паролю (FR-02..04)."""
    try:
        pair = await use_case.execute(email=body.email, password=body.password)
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    return _token_pair_to_dto(pair)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    use_case=Depends(get_refresh_token),
) -> TokenResponse:
    """Обновление пары токенов по refresh-токену (FR-05)."""
    try:
        pair = await use_case.execute(refresh_token=body.refresh_token)
    except Exception as exc:
        raise domain_error_handler(exc)  # type: ignore[arg-type]
    return _token_pair_to_dto(pair)
