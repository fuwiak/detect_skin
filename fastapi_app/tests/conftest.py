"""
Конфигурация pytest
"""
import pytest
import os
from unittest.mock import patch

# Устанавливаем тестовые переменные окружения
os.environ.setdefault('OPENROUTER_API_KEY', 'test_key')
os.environ.setdefault('PIXELBIN_ACCESS_TOKEN', 'test_token')
os.environ.setdefault('FAL_KEY', 'test_fal_key')


@pytest.fixture
def mock_settings():
    """Мок настроек для тестов"""
    with patch('app.config.settings') as mock:
        mock.openrouter_api_key = 'test_key'
        mock.pixelbin_access_token = 'test_token'
        mock.fal_key = 'test_fal_key'
        yield mock










