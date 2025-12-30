"""
Pydantic схемы для endpoint /api/analyze
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ConfigSchema(BaseModel):
    """Схема конфигурации анализа"""
    detection_provider: str = "openrouter"
    llm_provider: str = "openrouter"
    vision_model: str = "google/gemini-2.5-flash"
    text_model: str = "anthropic/claude-3.5-sonnet"
    temperature: float = 0.0
    max_tokens: int = 300
    language: str = "ru"


class AnalyzeRequest(BaseModel):
    """Схема запроса на анализ кожи"""
    image: str = Field(..., description="Base64 encoded image")
    mime_type: Optional[str] = Field(None, description="MIME type of the image (e.g., 'image/jpeg', 'image/png', 'image/heic', 'image/heif')")
    config: Optional[ConfigSchema] = None
    mode: Optional[str] = Field("pixelbin", description="Mode: 'pixelbin' or 'sam3'")
    sam3_timeout: Optional[int] = Field(5, ge=3, le=20, description="SAM3 timeout in seconds")
    sam3_diseases: Optional[List[str]] = Field(None, description="List of diseases to analyze with SAM3")
    sam3_use_llm_preanalysis: Optional[bool] = Field(True, description="Use LLM pre-analysis for SAM3")
    sam3_max_coverage_percent: Optional[float] = Field(25.0, ge=0, le=100, description="Max mask coverage percent")


class AnalyzeResponse(BaseModel):
    """Схема ответа на анализ кожи"""
    success: bool
    data: Optional[Dict] = None
    report: Optional[str] = None
    pixelbin_images: Optional[List[Dict]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    config: Optional[Dict] = None
    use_heuristics: Optional[bool] = None
    analysis_method: Optional[str] = None
    pixelbin_attempts: Optional[List] = None
    error: Optional[str] = None
    warning: Optional[str] = Field(None, description="Предупреждение (например, о лимите использования API)")

