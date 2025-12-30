"""
Health check и диагностические эндпоинты
"""
import logging
import time
from fastapi import APIRouter
from typing import Dict

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description="Проверка работоспособности API"
)
async def health_check() -> Dict:
    """
    Health check эндпоинт для проверки работоспособности сервиса
    
    Используется для мониторинга и проверки доступности на Railway
    """
    return {
        "status": "healthy",
        "service": "Skin Analyzer API",
        "version": "1.0.0",
        "timestamp": time.time()
    }


@router.get(
    "/health/detailed",
    summary="Детальная проверка здоровья",
    description="Проверка работоспособности всех компонентов системы"
)
async def detailed_health_check() -> Dict:
    """
    Детальная проверка здоровья всех компонентов
    
    Проверяет:
    - Доступность API ключей
    - Статус сервисов
    - Конфигурацию
    """
    health_status = {
        "status": "healthy",
        "service": "Skin Analyzer API",
        "version": "1.0.0",
        "timestamp": time.time(),
        "components": {
            "api_keys": {
                "openrouter": {
                    "available": bool(settings.openrouter_api_key),
                    "status": "ok" if settings.openrouter_api_key else "missing"
                },
                "pixelbin": {
                    "available": bool(settings.pixelbin_access_token),
                    "status": "ok" if settings.pixelbin_access_token else "missing"
                },
                "fal": {
                    "available": bool(settings.fal_key),
                    "status": "ok" if settings.fal_key else "optional"
                },
                "hf": {
                    "available": bool(settings.hf_token),
                    "status": "ok" if settings.hf_token else "optional"
                }
            },
            "server": {
                "host": settings.host,
                "port": settings.port,
                "status": "ok"
            }
        }
    }
    
    # Определяем общий статус
    critical_services = [
        health_status["components"]["api_keys"]["openrouter"]["available"]
    ]
    
    if not all(critical_services):
        health_status["status"] = "degraded"
        health_status["message"] = "Некоторые критичные сервисы недоступны"
    
    return health_status

