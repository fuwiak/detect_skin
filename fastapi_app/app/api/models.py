"""
API endpoint для получения списка доступных моделей
"""
from fastapi import APIRouter, HTTPException
from app.schemas.models import AvailableModelsResponse, ModelInfo
from app.utils.constants import DETECTION_FALLBACKS

router = APIRouter()


@router.get(
    "/models/available",
    response_model=AvailableModelsResponse,
    summary="Список доступных моделей",
    description="Возвращает список всех доступных моделей для анализа кожи"
)
async def get_available_models():
    """
    Получить список всех доступных моделей для каждого провайдера
    
    Возвращает:
    - Модели для OpenRouter (vision и text)
    - Список fallback моделей для автоматического переключения
    
    Модели отсортированы по приоритету использования.
    """
    try:
        # Модели для OpenRouter (из DETECTION_FALLBACKS)
        openrouter_models = []
        for fallback in DETECTION_FALLBACKS:
            if fallback["provider"] == "openrouter":
                model = fallback["model"]
                # Красивое название для отображения
                label = model.replace("x-ai/", "").replace("google/", "").replace(":free", " (бесплатно)")
                openrouter_models.append(ModelInfo(value=model, label=label))
        
        return AvailableModelsResponse(
            success=True,
            models={
                "openrouter": {
                    "vision": openrouter_models,
                    "text": openrouter_models
                }
            },
            detection_fallbacks=DETECTION_FALLBACKS
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

