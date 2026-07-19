# Архитектура VibeShopping — Clean Architecture + DDD

Этот документ — учебный. Он объясняет **почему** проект устроен именно так, а не
иначе. Цель — помочь понять принципы Clean Architecture и DDD на конкретном
примере.

---

## 1. Зачем вообще архитектура?

Представьте приложение как живой организм. Бизнес-логика — это его **ядро**,
сердце. То, что важно и редко меняется: «пользователь владеет списком»,
«в списке не может быть двух одинаковых участников», «купленный товар
перестаёт быть активным».

Вокруг ядра — **механизмы**: HTTP-сервер, база данных, фреймворк аутентификации,
bcrypt для паролей. Они меняются часто: переходим с PostgreSQL на что-то ещё,
меняем JWT-библиотеку, добавляем WebSocket.

Если ядро зависит от механизмов — каждое изменение механизма ломает ядро.
Clean Architecture решает эту проблему через **Dependency Rule**.

---

## 2. Dependency Rule (правило зависимостей)

> Зависимости направлены строго внутрь. Внешний слой знает о внутреннем,
> внутренний не знает о внешнем.

```
┌──────────────────────────────────────────────────────────────┐
│                          views                               │   ← HTTP, FastAPI
│  ┌────────────────────────────────────────────────────────┐  │
│  │                       services                         │  │   ← use cases
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │                     domain                       │  │  │   ← бизнес-ядро
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│   repos ◀── реализует протоколы из domain                    │   ← SQLAlchemy Core
│   infrastructure ◀── предоставляет db, config, security      │
└──────────────────────────────────────────────────────────────┘
```

В нашем коде:
```
views ──▶ services ──▶ domain ◀── repos
                                  │
                                  └─▶ infrastructure (db, config, security)
```

**Ключевое наблюдение:** `repos` и `infrastructure` — это **внешние** слои,
хотя они «ниже» по уровню. Они зависят от `domain`, но `domain` **не зависит**
от них. Это и есть **Dependency Inversion**.

---

## 3. Dependency Inversion (обращение зависимостей)

Это самый важный принцип в проекте. Покажу на примере.

### Проблема (наивный подход)

```
services/auth.py  ──импорт──▶  SQLAlchemy   ──импорт──▶  User row
```

Здесь `auth.py` (бизнес-логика) жестко завязан на SQLAlchemy. Чтобы протестировать
`RegisterUser`, нужна БД. Чтобы сменить ORM, нужно переписывать use case.

### Решение (Dependency Inversion)

1. **Домен объявляет интерфейс** (Protocol) того, что ему нужно:

```python
# domain/repositories.py
from typing import Protocol
from .models import User

class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def add(self, user: User) -> User: ...
```

Домен говорит: «Мне нужен способ сохранить пользователя. Как именно — не моё дело».

2. **Слой `repos` предоставляет реализацию**:

```python
# repos/user_repository.py
from sqlalchemy import select
from infrastructure import tables
from infrastructure.db import AsyncSession
from domain.models import User

class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(tables.users).where(tables.users.c.email == email)
        row = (await self._session.execute(stmt)).first()
        return _row_to_user(row) if row else None

    async def add(self, user: User) -> User:
        # INSERT через SQLAlchemy Core, маппинг вручную
        ...
```

3. **Use case зависит от интерфейса, не от реализации**:

```python
# services/auth.py
from domain.repositories import UserRepository
from services.ports import PasswordHasher

class RegisterUser:
    def __init__(
        self,
        users: UserRepository,      # ← интерфейс, не реализация
        hasher: PasswordHasher,     # ← интерфейс, не реализация
    ) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, email: str, password: str) -> User:
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(email)
        hashed = self._hasher.hash(password)
        user = User(email=email, hashed_password=hashed)
        return await self._users.add(user)
```

### Что это даёт?

- **Тестируемость:** в `tests/unit/use_cases/test_auth_use_cases.py` подставляем
  in-memory реализацию `UserRepository` и фейковый `PasswordHasher`. Use case
  тестируется **без БД и без bcrypt** — мгновенно и детерминированно.
- **Гибкость:** заменить SQLAlchemy на чистый SQL или MongoDB — нужно лишь
  написать новый репозиторий. Use case и домен не трогаются.
- **Чёткость:** при чтении `domain/repositories.py` сразу видно, **какие операции
  нужны бизнесу**. Это не «таблицы в БД», а язык предметной области.

---

## 4. Слои в нашем проекте

| Пакет | Слой | Что внутри | Знает о |
|---|---|---|---|
| `domain/` | Домен | Сущности (pydantic), протоколы репозиториев | (ничего внешнего) |
| `services/` | Application | Use cases, порты (PasswordHasher, TokenService) | `domain` |
| `repos/` | Infrastructure (DB) | Реализация репозиториев на SQLAlchemy Core | `domain`, `infrastructure` |
| `infrastructure/` | Infrastructure | DB engine, config, security | (внешние библиотеки) |
| `views/` | Presentation | FastAPI роутеры, composition root | `services`, `repos`, `schemas` |
| `schemas/` | Presentation | Pydantic request/response DTO | `domain` (для маппинга) |

### Что где живёт — на примере аутентификации

| Артефакт | Локация | Зависит от |
|---|---|---|
| `User` (сущность) | `domain/models.py` | pydantic |
| `UserRepository` (Protocol) | `domain/repositories.py` | `domain/models.py` |
| `PasswordHasher` (Protocol) | `services/ports.py` | (ничего) |
| `RegisterUser` (use case) | `services/auth.py` | `domain`, `services/ports.py` |
| `users` table (SQLAlchemy) | `infrastructure/tables.py` | SQLAlchemy |
| `SqlAlchemyUserRepository` | `repos/user_repository.py` | `domain`, `infrastructure` |
| `BcryptPasswordHasher` | `infrastructure/security/password_hasher.py` | `services/ports.py`, bcrypt |
| `register_user` HTTP endpoint | `views/auth.py` | `services`, `schemas` |
| `UserCreate`, `UserResponse` DTO | `schemas/auth.py` | pydantic |

---

## 5. DDD: агрегаты и инварианты

### Что такое агрегат?

**Агрегат** — это кластер связанных сущностей, которые меняются вместе как единое
целое. Один из них — **корень** (aggregate root); доступ к остальным частям
агрегата идёт только через него.

### Наш агрегат: ShoppingList

```
                  ShoppingList (корень агрегата)
                 /             \
          ListItem            ListMember
   (товары в списке)    (участники + владелец)
```

**Почему так?** Спецификация требует (FR-30..36):
- Только владелец может приглашать участников.
- Один пользователь не может быть участником дважды.
- Удаление списка удаляет все его items и members.
- Передача владения меняет роли.

Это **инварианты агрегата** — правила, которые должны всегда выполняться.
Если дать доступ к `ListItem` напрямую (минуя список), их легко нарушить:
кто угодно может «добавить участника» через отдельный endpoint.

Поэтому:

- `ShoppingList` — корень. `ListItem` и `ListMember` — внутренние части.
- `ShoppingListRepository` загружает агрегат целиком (с items и members).
- Все операции с items/members — через методы корня:
  ```python
  shopping_list.add_item(name="Молоко", quantity=2)
  shopping_list.mark_item_purchased(item_id)
  shopping_list.invite_member(user_id)
  shopping_list.remove_member(user_id)
  shopping_list.transfer_ownership_to(user_id)
  ```
- Репозиторий сохраняет **весь агрегат** целиком — гарантируется
  транзакционная консистентность.

### Богатые vs анемичные модели

Принят смешанный подход:

- **Богатая модель** — там, где логика естественно защищает инвариант агрегата.
  Например, `shopping_list.invite_member(user_id)` сам проверит:
  - что этот пользователь уже не участник (FR-32),
  - и добавит его.
  
  Calling code не может «забыть» проверить — проверка встроена в метод.

- **Анемичная модель** — там, где вынос в сущность искусственный.
  Например, регистрация пользователя: проверка уникальности email требует
  обращения к репозиторию, а это уже инфраструктура. Поэтому `RegisterUser`
  use case выполняет проверку и хеширование пароля, а `User` остаётся
  почти пустым контейнером данных.

Критерий выбора: **где код читается проще и где инварианты защищены надёжнее**.

---

## 6. SQLAlchemy Core, а не ORM

ORM (Object-Relational Mapper) связывает классы Python с таблицами БД напрямую:
один класс = одна таблица, объект = строка. Это удобно, но:

- Доменные модели становятся привязанными к схеме БД → нарушается Clean Architecture.
- Скрытые запросы (lazy loading) ломают производительность и предсказуемость.
- Сложно тестировать домен без БД.

Мы используем **SQLAlchemy Core** — конструктор запросов без ORM:
- `Table`, `Column` описывают схему (в `infrastructure/tables.py`).
- Запросы — через `select(t).where(...)`.
- Маппинг строки БД → доменная модель — **вручную** в репозиториях.

Доменная модель (pydantic) живёт в `domain/models.py` и ничего не знает
о таблицах. Репозиторий — мост между двумя мирами:

```python
# repos/user_repository.py
def _row_to_user(row: Row) -> User:
    return User(
        id=row.id,
        email=row.email,
        hashed_password=row.hashed_password,
        created_at=row.created_at,
    )
```

---

## 7. Composition Root (где всё связывается)

Views — это **composition root**: место, где абстрактные интерфейсы получают
конкретные реализации. В FastAPI это делается через `Depends`:

```python
# views/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_session
from infrastructure.security.password_hasher import BcryptPasswordHasher
from repos.user_repository import SqlAlchemyUserRepository
from services.auth import RegisterUser
from services.ports import PasswordHasher


def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)


def get_password_hasher() -> PasswordHasher:
    return BcryptPasswordHasher()


def get_register_user_use_case(
    users: SqlAlchemyUserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> RegisterUser:
    return RegisterUser(users=users, hasher=hasher)
```

```python
# views/auth.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    payload: UserCreate,
    use_case: RegisterUser = Depends(get_register_user_use_case),
):
    user = await use_case.execute(email=payload.email, password=payload.password)
    return UserResponse.model_validate(user.model_dump())
```

Заметьте: use case (`RegisterUser`) принимает интерфейсы (`UserRepository`,
`PasswordHasher`), а FastAPI подставляет реализации через `Depends`. Это
и есть внедрение зависимостей в точке входа.

---

## 8. Почему это важно для разработки с AI

Clean Architecture + DDD отлично сочетаются с AI-разработкой, потому что:

1. **Чёткие границы.** AI-агент всегда знает, где какой код должен жить.
   Нечего «расползаться» по слоям — структура каталогов диктует архитектуру.

2. **Тесты без инфраструктуры.** Домен и use cases тестируются in-memory,
   без БД и без Docker. Это критично для TDD: Red-фаза занимает секунды.

3. **Маленькие изменения.** Задача вида «добавить категорию» затрагивает
   только `domain/models.py` + `domain/repositories.py` + один use case
   + один view + тесты. AI-агент делает предсказуемые, малые правки.

4. **Согласованность с spec.** User stories и FR из `docs/spec.md` прямо
   ложатся на use cases: одна user story ≈ один-два use case. Легко
   отследить покрытие.

5. **AGENTS.md как контракт.** Dependency Rule, «только Core, не ORM»,
   «богатые модели где естественно» — все эти правила зафиксированы в
   `AGENTS.md`, и AI-агент следует им в каждой сессии.

---

## 9. Где почитать подробнее

- Robert C. Martin — *Clean Architecture*
- Eric Evans — *Domain-Driven Design*
- Vaughn Vernon — *Implementing Domain-Driven Design*
- https://fastapi.tiangolo.com/tutorial/dependencies/
- https://docs.sqlalchemy.org/en/20/core/
