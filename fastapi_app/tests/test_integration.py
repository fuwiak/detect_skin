"""
Интеграционные тесты
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestIntegration:
    """Интеграционные тесты для всего приложения"""
    
    def test_root_endpoint(self):
        """Тест корневого endpoint"""
        response = client.get("/")
        assert response.status_code in [200, 404]  # Может быть 404 если нет index.html
    
    def test_openapi_schema(self):
        """Тест доступности OpenAPI схемы"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert 'openapi' in schema
        assert 'info' in schema
        assert 'paths' in schema
    
    def test_docs_endpoint(self):
        """Тест доступности Swagger UI"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert 'text/html' in response.headers['content-type']
    
    def test_redoc_endpoint(self):
        """Тест доступности ReDoc"""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert 'text/html' in response.headers['content-type']
    
    def test_api_endpoints_exist(self):
        """Тест наличия всех API endpoints в схеме"""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema['paths']
        
        assert '/api/analyze' in paths
        assert '/api/config' in paths
        assert '/api/models/available' in paths
        assert '/api/proxy-image' in paths
    
    def test_api_endpoints_methods(self):
        """Тест HTTP методов для endpoints"""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema['paths']
        
        # Проверяем методы
        assert 'post' in paths['/api/analyze']
        assert 'get' in paths['/api/config']
        assert 'post' in paths['/api/config']
        assert 'get' in paths['/api/models/available']
        assert 'get' in paths['/api/proxy-image']










