"""
Pydantic схемы для endpoint /api/config
"""
from typing import Dict
from pydantic import BaseModel


class ConfigRequest(BaseModel):
    """Схема запроса на обновление конфигурации"""
    detection_provider: str = None
    llm_provider: str = None
    vision_model: str = None
    text_model: str = None
    temperature: float = None
    max_tokens: int = None
    language: str = None


class ConfigResponse(BaseModel):
    """Схема ответа с конфигурацией"""
    success: bool
    config: Dict




