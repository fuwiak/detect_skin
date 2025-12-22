"""
Pydantic схемы для endpoint /api/models/available
"""
from typing import Dict, List
from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Информация о модели"""
    value: str
    label: str


class AvailableModelsResponse(BaseModel):
    """Схема ответа со списком доступных моделей"""
    success: bool
    models: Dict[str, Dict[str, List[ModelInfo]]]
    detection_fallbacks: List[Dict]




