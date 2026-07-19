# AGENTS.md — Инструкции для AI-агента

Этот файл описывает правила и конвенции для работы AI-агента в проекте VibeShopping.

## О проекте

VibeShopping — приложение для управления списками покупок с поддержкой совместных списков.
Spec: `docs/spec.md`
Архитектура: `docs/architecture.md`

## Стек технологий

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (async, **Core** — НЕ ORM), Alembic
- **БД:** PostgreSQL 16
- **Frontend:** HTML + vanilla JavaScript (Fetch API)
- **Мобильное:** PWA (Progressive Web App)
- **Тесты:** pytest, httpx, pytest-asyncio
- **Качество кода:** ruff (linting + formatting), mypy (type checking)
- **Окружение:** Docker Compose

---

## Архитектура: Clean Architecture + DDD

### Dependency Rule (правило зависимостей)

Зависимости направлены **строго внутрь**. Внешние слои знают о внутренних, внутренние
не знают о внешних.

```
views ──▶ services ──▶ domain ◀── repos
                                  │
                                  └─▶ infrastructure (db, config, security)
```

- `domain` — ядро, **не зависит ни от чего** в проекте.
- `services` — знает о `domain`, не знает о БД и HTTP.
- `repos` — реализация репозиториев; знает о `domain` (импортирует модели/протоколы)
  и `infrastructure` (SQLAlchemy tables), но `domain` про него не знает.
- `views` — HTTP-слой; связывает всё вместе (composition root).

### Dependency Inversion (обращение зависимостей)

Это центральный принцип проекта.

- **`domain/repositories.py`** содержит `Protocol` — абстрактные интерфейсы репозиториев.
  Домен объявляет, **что** ему нужно, но не знает, **как** это реализовано.
- **`repos/`** содержит конкретные реализации на SQLAlchemy Core. Импортирует `domain`
  (модели и протоколы), реализует протоколы. Но `domain` **не** импортирует `repos/`.

Следствие: домен и use cases можно тестировать с in-memory заглушками, без БД вообще.

### Слои и их ответственность

| Пакет | Слой | Ответственность |
|---|---|---|
| `domain/` | Domain | Сущности и инварианты агрегатов (pydantic), протоколы репозиториев |
| `services/` | Application | Use cases — оркестрация бизнес-операций, порты (PasswordHasher, TokenService) |
| `repos/` | Infrastructure (DB) | Реализация репозиториев на SQLAlchemy Core, маппинг row→модель |
| `infrastructure/` | Infrastructure | DB engine, config, security (bcrypt, JWT) — сантехника |
| `views/` | Presentation | FastAPI роутеры, DTO (через `schemas/`), composition root |
| `schemas/` | Presentation | Pydantic request/response DTO |

### Бизнес-логика: богатые vs анемичные модели

**Принятый подход:** смешанный.

- **Богатые доменные модели** — там, где бизнес-логика естественно укладывается в
  инварианты агрегата. Например, `ShoppingList.add_item(...)`, `ShoppingList.invite_member(...)`,
  `list.mark_item_purchased(item_id)` — эти операции защищают целостность агрегата
  (роли, принадлежность, уникальность).
- **Анемичные модели** — допустимы там, где вынос логики в модель искусственный и
  усложняет код. В таких случаях логика живёт в use cases (`services/`).

Решение «богатая или анемичная» принимается по месту, исходя из того, где код
читается проще и где инварианты защищены надёжнее.

### Value Objects

Используем **примитивные типы** (str, int, bool). Отдельные классы для Email,
HashedPassword, MemberRole и т.д. **не** создаются. Валидация — через pydantic-поля
в доменных моделях.

### Агрегаты (Aggregate Boundaries)

- **`ShoppingList` — корень агрегата.** `ListItem` и `ListMember` входят в агрегат.
- Доступ к items/members — **только** через корень (`list.add_item`, `list.remove_member`).
- Репозиторий `ShoppingListRepository` загружает агрегат целиком (с items и members).
- Транзакционная консистентность гарантируется в границах агрегата.

### SQLAlchemy Core (НЕ ORM)

- Используем `Table`, `Column`, `select(t).where(...)`. **Без** declarative моделей
  (`declarative_base`, `Mapped`, `mapped_column` и т.п.).
- Маппинг строки БД → доменная модель — **вручную** в репозиториях.
- Доменные модели (pydantic) **не** связаны со схемой БД.

---

## Структура проекта

```
backend/src/vibeshopping/
├── domain/
│   ├── models.py              # User, ShoppingList, ListItem, ListMember
│   └── repositories.py        # Protocols: UserRepository, ShoppingListRepository
├── services/
│   ├── ports.py               # PasswordHasher, TokenService (Protocol)
│   ├── auth.py                # RegisterUser, LoginUser, RefreshToken
│   ├── lists.py               # CreateList, GetLists, RenameList, DeleteList
│   ├── items.py               # AddItem, UpdateItem, TogglePurchased, DeleteItem
│   └── members.py             # InviteMember, RemoveMember, LeaveList, TransferOwnership
├── repos/
│   ├── user_repository.py
│   └── shopping_list_repository.py
├── infrastructure/
│   ├── config.py              # pydantic-settings
│   ├── db.py                  # async engine + session factory
│   ├── tables.py              # SQLAlchemy Core Table definitions
│   └── security/
│       ├── password_hasher.py # bcrypt (реализация services.ports.PasswordHasher)
│       └── token_service.py   # JWT (реализация services.ports.TokenService)
├── views/                     # HTTP-слой (бывшие routers)
│   ├── dependencies.py        # composition root: FastAPI Depends wiring
│   ├── auth.py
│   ├── lists.py
│   ├── items.py
│   └── members.py
├── schemas/                   # Pydantic request/response DTO (HTTP-слой)
│   ├── auth.py
│   ├── lists.py
│   ├── items.py
│   └── members.py
└── main.py

backend/tests/
├── conftest.py
├── unit/                      # без БД — чистая логика домена и use cases
│   ├── domain/
│   │   ├── test_user.py
│   │   └── test_shopping_list.py        # инварианты агрегата
│   └── use_cases/
│       ├── test_auth_use_cases.py       # с in-memory репозиториями
│       ├── test_list_use_cases.py
│       ├── test_item_use_cases.py
│       └── test_member_use_cases.py
└── integration/               # с реальной БД
    ├── repos/
    │   ├── test_user_repository.py
    │   └── test_shopping_list_repository.py
    └── api/
        ├── test_auth_views.py
        ├── test_list_views.py
        ├── test_item_views.py
        └── test_member_views.py

frontend/                      # HTML + JS + PWA
docs/                          # spec.md, architecture.md
docker/                        # Dockerfile.backend, nginx.conf
docker-compose.yml
```

---

## Процесс работы

### 1. Spec-first
Перед разработкой любой функции — читай `docs/spec.md`. Все требования, user stories
и functional requirements описаны там. Если что-то не покрыто спецификацией — спроси
пользователя, не придумывай сам.

### 2. TDD (Test-Driven Development)
Backend-код **всегда** пишется через TDD в три фазы:

1. **Red** — Напиши тесты для новой функции. Убедись, что они падают.
2. **Green** — Напиши минимальный код, чтобы тесты прошли. Не пиши лишнего.
3. **Refactor** — Почисти код, улучши структуру, удали дублирование. Тесты должны
   оставаться зелёными.

Порядок тестирования слоёв (наружу → внутрь для Red, внутрь → наружу для реализации):
- Сначала доменные инварианты (`tests/unit/domain/`)
- Затем use cases (`tests/unit/use_cases/`) с in-memory репозиториями
- Затем репозитории (`tests/integration/repos/`) с реальной БД
- Наконец API (`tests/integration/api/`) через httpx

### 3. Коммиты
- Один логический шаг = один коммит
- Формат: `[тип] краткое описание` на английском
  - `feat: add user registration use case`
  - `test: add domain tests for shopping list aggregate`
  - `refactor: extract member role invariant into ShoppingList`
  - `fix: handle duplicate list member invitation`
- Не коммить сломанные тесты

---

## Правила кода

### Python / Backend

- Следуй PEP 8. Форматирование через `ruff format`, линтинг через `ruff check`.
- Используй type hints везде. Стремись к полной совместимости с mypy strict.
- Импорты: стандартная библиотека → сторонние → локальные (пустая строка между группами).
- **SQLAlchemy Core только.** `Table`, `Column`, `select`, `where` и т.п. Без ORM.
  Маппинг строки в доменную модель — вручную в репозиториях.
- **Репозитории**: интерфейсы (`Protocol`) в `domain/repositories.py`, реализации
  в `repos/`. Домен не знает про реализации.
- **Use cases** принимают репозитории и порты через конструктор (`__init__`);
  в тестах подменяются in-memory реализациями.
- **Views** — тонкие: парсинг DTO → вызов use case → маппинг в response DTO.
  Никакой бизнес-логики в views.
- **Доменные модели** на pydantic. Инварианты агрегата — методы моделей (там, где
  это естественно) или use cases (там, где проще).
- Конфигурация — через pydantic-settings в `infrastructure/config.py`. Секреты —
  через переменные окружения (`.env`).

### Схемы (DTO)

- Запрос/ответ HTTP — Pydantic-схемы в `schemas/`.
- Именование: `<Entity>Create`, `<Entity>Update`, `<Entity>Response`, `<Entity>List`.
- Доменные модели **не** возвращаются напрямую из API — всегда маппинг в DTO.

### Тесты

- Структура: `tests/unit/` (без БД) и `tests/integration/` (с БД), внутри — по фичам.
- Файл тестов: `tests/<layer>/<feature>/test_<what>.py`
- Фикстуры — в `conftest.py` соответствующего уровня.
- Имена тестов описывают ожидаемое поведение:
  `test_shopping_list_invite_member_rejects_duplicate`
- Каждый тест независим.
- Unit-тесты use cases используют **in-memory** реализации протоколов репозиториев.
- Integration-тесты репозиториев и API — с реальной PostgreSQL (через Docker Compose).
- Используй `httpx.AsyncClient` для тестирования FastAPI views.

---

## Ограничения

- Не добавляй зависимости без согласия пользователя.
- Не используй SQLAlchemy ORM (declarative models) — только Core.
- Не меняй `docs/spec.md` или `docs/architecture.md` без согласия пользователя.
- Не нарушай Dependency Rule: `domain` не должен импортировать `repos`,
  `infrastructure`, `views`, `services`.
- Если в процессе работы возникает вопрос или неопределённость — спроси.
- Не пиши код для требований, которых нет в spec (даже если кажется очевидным).

---

## Полезные команды

```bash
# Запустить все тесты
cd backend && python -m pytest

# Только unit-тесты (быстро, без БД)
cd backend && python -m pytest tests/unit

# Только integration-тесты (нужен Docker Compose с PostgreSQL)
cd backend && python -m pytest tests/integration

# Запустить тесты с выводом печати
cd backend && python -m pytest -s

# Линтинг и форматирование
cd backend && ruff check . && ruff format --check .

# Автофикс
cd backend && ruff check --fix . && ruff format .

# Проверка типов
cd backend && mypy src

# Запустить backend
cd backend && uvicorn vibeshopping.main:app --reload

# Миграции
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "description"

# Docker
docker compose up -d    # запустить PostgreSQL
docker compose down     # остановить
docker compose logs -f  # логи
```
