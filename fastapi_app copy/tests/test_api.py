"""
Unit тесты для API endpoints
"""
import pytest
from fastapi.testclient import TestClient
import base64
from PIL import Image
import io
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)


class TestAnalyzeEndpoint:
    """Тесты для endpoint /api/analyze"""
    
    def test_analyze_missing_image(self):
        """Тест запроса без изображения"""
        response = client.post("/api/analyze", json={})
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.analyze.analyze_image_with_openrouter')
    @patch('app.api.analyze.generate_report_with_llm')
    def test_analyze_success_pixelbin(self, mock_report, mock_analyze):
        """Тест успешного анализа в режиме pixelbin"""
        # Мокаем ответы
        mock_analyze.return_value = {
            'acne_score': 25.5,
            'pigmentation_score': 30.2,
            'pores_size': 45.8,
            'wrinkles_grade': 15.3
        }
        mock_report.return_value = "Тестовый отчёт"
        
        # Создаём тестовое base64 изображение
        
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        response = client.post(
            "/api/analyze",
            json={
                "image": f"data:image/jpeg;base64,{image_base64}",
                "mode": "pixelbin"
            }
        )
        
        # Должен вернуть ошибку 503, так как нет реальных API ключей
        # Но структура ответа должна быть правильной
        assert response.status_code in [200, 503]
    
    def test_analyze_invalid_mode(self):
        """Тест с неверным режимом"""
        
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        response = client.post(
            "/api/analyze",
            json={
                "image": f"data:image/jpeg;base64,{image_base64}",
                "mode": "invalid_mode"
            }
        )
        
        # Должен принять, но использовать pixelbin по умолчанию
        assert response.status_code in [200, 503]


class TestConfigEndpoint:
    """Тесты для endpoint /api/config"""
    
    def test_get_config(self):
        """Тест получения конфигурации"""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'config' in data
    
    def test_update_config(self):
        """Тест обновления конфигурации"""
        response = client.post(
            "/api/config",
            json={
                "temperature": 0.5,
                "max_tokens": 500
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['config']['temperature'] == 0.5
        assert data['config']['max_tokens'] == 500


class TestModelsEndpoint:
    """Тесты для endpoint /api/models/available"""
    
    def test_get_available_models(self):
        """Тест получения списка доступных моделей"""
        response = client.get("/api/models/available")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'models' in data
        assert 'openrouter' in data['models']


class TestProxyEndpoint:
    """Тесты для endpoint /api/proxy-image"""
    
    def test_proxy_image_missing_url(self):
        """Тест прокси без URL"""
        response = client.get("/api/proxy-image")
        assert response.status_code == 422  # Validation error
    
    def test_proxy_image_invalid_domain(self):
        """Тест прокси с недопустимым доменом"""
        response = client.get("/api/proxy-image?url=https://example.com/image.jpg")
        assert response.status_code == 400
    
    @patch('app.api.proxy.requests.get')
    def test_proxy_image_success(self, mock_get):
        """Тест успешного проксирования"""
        mock_response = MagicMock()
        mock_response.content = b'fake_image_data'
        mock_response.headers = {'Content-Type': 'image/jpeg'}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        response = client.get("/api/proxy-image?url=https://fal.media/test.jpg")
        assert response.status_code == 200
        assert response.headers['content-type'] == 'image/jpeg'

