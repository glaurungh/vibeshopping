"""SQLAlchemy Core таблицы (НЕ ORM).

Используем Table, Column, select(t).where(...) — без declarative_base,
Mapped, mapped_column и прочего ORM. Маппинг строки → доменная модель
выполняется вручную в репозиториях (repos/).

Таблицы:
- users: пользовательские аккаунты
- shopping_lists: списки покупок
- list_members: участники списков (владелец + приглашённые)
- list_items: элементы списка
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    Uuid,
)
from sqlalchemy.sql import func

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("hashed_password", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

shopping_lists = Table(
    "shopping_lists",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

list_members = Table(
    "list_members",
    metadata,
    Column(
        "list_id",
        Uuid,
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id",
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("role", String(16), nullable=False),
    Column("joined_at", DateTime(timezone=True), server_default=func.now()),
)

list_items = Table(
    "list_items",
    metadata,
    Column(
        "id",
        Uuid,
        primary_key=True,
    ),
    Column(
        "list_id",
        Uuid,
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("name", String(255), nullable=False),
    Column("quantity", String(255), nullable=True),
    Column("purchased", Boolean, nullable=False, server_default="false"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)
