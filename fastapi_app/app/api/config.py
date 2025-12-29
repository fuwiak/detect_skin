"""
API endpoints для конфигурации
"""
import os
from fastapi import APIRouter
from app.schemas.config import ConfigRequest, ConfigResponse
from app.utils.constants import DEFAULT_CONFIG
from app.config import settings

router = APIRouter()

# Глобальная конфигурация (в production лучше использовать БД или файл)
current_config = DEFAULT_CONFIG.copy()


@router.get(
    "/config",
    response_model=ConfigResponse,
    summary="Получить конфигурацию",
    description="Возвращает текущую конфигурацию анализа кожи"
)
async def get_config():
    """
    Получить текущую конфигурацию
    
    Возвращает все настройки анализа:
    - Провайдеры (detection_provider, llm_provider)
    - Модели (vision_model, text_model)
    - Параметры (temperature, max_tokens, language)
    """
    return ConfigResponse(success=True, config=current_config)


@router.post(
    "/config",
    response_model=ConfigResponse,
    summary="Обновить конфигурацию",
    description="Обновляет настройки анализа кожи. Можно обновить только нужные параметры."
)
async def update_config(request: ConfigRequest):
    """
    Обновить конфигурацию
    
    Позволяет обновить любые параметры конфигурации:
    - detection_provider: Провайдер для детекции (openrouter)
    - llm_provider: Провайдер для LLM (openrouter)
    - vision_model: Модель для анализа изображений
    - text_model: Модель для генерации отчётов
    - temperature: Температура (0.0-1.0)
    - max_tokens: Максимальное количество токенов
    - language: Язык отчёта (ru/en)
    
    **Пример:**
    ```json
    {
        "temperature": 0.5,
        "max_tokens": 500,
        "language": "ru"
    }
    ```
    """
    try:
        config_dict = request.dict(exclude_unset=True)
        current_config.update(config_dict)
        return ConfigResponse(success=True, config=current_config)
    except Exception as e:
        return ConfigResponse(success=False, config=current_config)


@router.get(
    "/config/env-check",
    summary="Проверка переменных окружения",
    description="Диагностический эндпоинт для проверки доступности API ключей (без показа самих ключей)"
)
async def check_env_variables():
    """
    Проверка переменных окружения
    
    Возвращает статус доступности API ключей без показа самих ключей.
    Полезно для диагностики проблем с переменными окружения в Railway.
    """
    env_vars = {
        "OPENROUTER_API_KEY": {
            "available": bool(settings.openrouter_api_key),
            "from_settings": bool(settings.openrouter_api_key),
            "from_os_env": bool(os.getenv("OPENROUTER_API_KEY")),
            "length": len(settings.openrouter_api_key) if settings.openrouter_api_key else 0
        },
        "PIXELBIN_ACCESS_TOKEN": {
            "available": bool(settings.pixelbin_access_token),
            "from_settings": bool(settings.pixelbin_access_token),
            "from_os_env": bool(os.getenv("PIXELBIN_ACCESS_TOKEN")),
            "length": len(settings.pixelbin_access_token) if settings.pixelbin_access_token else 0
        },
        "FAL_KEY": {
            "available": bool(settings.fal_key),
            "from_settings": bool(settings.fal_key),
            "from_os_env": bool(os.getenv("FAL_KEY")),
            "length": len(settings.fal_key) if settings.fal_key else 0
        },
        "HF_TOKEN": {
            "available": bool(settings.hf_token),
            "from_settings": bool(settings.hf_token),
            "from_os_env": bool(os.getenv("HF_TOKEN")),
            "length": len(settings.hf_token) if settings.hf_token else 0
        },
        "PORT": {
            "available": True,
            "value": os.getenv("PORT", "не установлен"),
            "settings_value": settings.port
        },
        "HOST": {
            "available": True,
            "value": os.getenv("HOST", "не установлен"),
            "settings_value": settings.host
        }
    }
    
    return {
        "success": True,
        "message": "Проверка переменных окружения",
        "variables": env_vars,
        "recommendations": {
            "OPENROUTER_API_KEY": "Убедитесь, что переменная установлена в Railway Dashboard → Variables",
            "PIXELBIN_ACCESS_TOKEN": "Убедитесь, что переменная установлена в Railway Dashboard → Variables",
            "FAL_KEY": "Опционально, требуется только для SAM3",
            "HF_TOKEN": "Опционально, требуется только для HuggingFace сегментации"
        }
    }

