"""
Unit тесты для Pydantic схем
"""
import pytest
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse, ConfigSchema
from app.schemas.config import ConfigRequest, ConfigResponse
from app.schemas.models import AvailableModelsResponse, ModelInfo


class TestAnalyzeSchemas:
    """Тесты для схем анализа"""
    
    def test_analyze_request_valid(self):
        """Тест валидного запроса на анализ"""
        request = AnalyzeRequest(
            image="data:image/jpeg;base64,/9j/4AAQ...",
            mode="pixelbin",
            sam3_timeout=5
        )
        assert request.image.startswith("data:image")
        assert request.mode == "pixelbin"
        assert request.sam3_timeout == 5
    
    def test_analyze_request_defaults(self):
        """Тест значений по умолчанию"""
        request = AnalyzeRequest(image="test")
        assert request.mode == "pixelbin"
        assert request.sam3_timeout == 5
        assert request.sam3_use_llm_preanalysis is True
        assert request.sam3_max_coverage_percent == 25.0
    
    def test_analyze_request_validation_timeout(self):
        """Тест валидации таймаута"""
        with pytest.raises(Exception):  # Pydantic validation error
            AnalyzeRequest(
                image="test",
                sam3_timeout=25  # Превышает максимум 20
            )
    
    def test_config_schema(self):
        """Тест схемы конфигурации"""
        config = ConfigSchema(
            detection_provider="openrouter",
            vision_model="google/gemini-2.5-flash",
            temperature=0.0
        )
        assert config.detection_provider == "openrouter"
        assert config.vision_model == "google/gemini-2.5-flash"
        assert config.temperature == 0.0


class TestConfigSchemas:
    """Тесты для схем конфигурации"""
    
    def test_config_request(self):
        """Тест запроса конфигурации"""
        request = ConfigRequest(temperature=0.5, max_tokens=500)
        assert request.temperature == 0.5
        assert request.max_tokens == 500
    
    def test_config_response(self):
        """Тест ответа конфигурации"""
        response = ConfigResponse(
            success=True,
            config={"temperature": 0.5}
        )
        assert response.success is True
        assert response.config["temperature"] == 0.5


class TestModelsSchemas:
    """Тесты для схем моделей"""
    
    def test_model_info(self):
        """Тест информации о модели"""
        model = ModelInfo(value="google/gemini-2.5-flash", label="Gemini 2.5 Flash")
        assert model.value == "google/gemini-2.5-flash"
        assert model.label == "Gemini 2.5 Flash"
    
    def test_available_models_response(self):
        """Тест ответа со списком моделей"""
        response = AvailableModelsResponse(
            success=True,
            models={
                "openrouter": {
                    "vision": [ModelInfo(value="test", label="Test")]
                }
            },
            detection_fallbacks=[]
        )
        assert response.success is True
        assert "openrouter" in response.models










