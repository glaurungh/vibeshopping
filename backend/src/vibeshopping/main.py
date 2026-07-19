"""VibeShopping — FastAPI application.

Composition root: здесь подключаются роутеры и настраивается middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vibeshopping.views.auth import router as auth_router
from vibeshopping.views.items import router as items_router
from vibeshopping.views.lists import router as lists_router
from vibeshopping.views.members import router as members_router

app = FastAPI(
    title="VibeShopping",
    description="API для управления списками покупок с поддержкой совместных списков.",
    version="0.1.0",
)

# CORS для frontend (PWA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production — ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(auth_router)
app.include_router(lists_router)
app.include_router(items_router)
app.include_router(members_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Простейший health-check endpoint."""
    return {"status": "ok"}
