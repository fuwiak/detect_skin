"""
Главный роутер для объединения всех API endpoints
"""
from fastapi import APIRouter

from app.api import analyze, config, models, proxy, health

router = APIRouter()

# Подключаем все роутеры
router.include_router(health.router, prefix="/api", tags=["health"])
router.include_router(analyze.router, prefix="/api", tags=["analyze"])
router.include_router(config.router, prefix="/api", tags=["config"])
router.include_router(models.router, prefix="/api", tags=["models"])
router.include_router(proxy.router, prefix="/api", tags=["proxy"])










