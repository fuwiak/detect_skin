"""
API endpoints для конфигурации
"""
from fastapi import APIRouter
from app.schemas.config import ConfigRequest, ConfigResponse
from app.utils.constants import DEFAULT_CONFIG

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

