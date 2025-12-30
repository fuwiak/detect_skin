"""
Unit тесты для сервисов
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io
from app.services.pixelbin_service import PixelBinService, extract_images_from_pixelbin_response
from app.services.llm_service import generate_fallback_report


class TestPixelBinService:
    """Тесты для PixelBinService"""
    
    def test_preprocess_for_pixelbin(self):
        """Тест предобработки изображения для Pixelbin"""
        # Создаём тестовое изображение
        
        img = Image.new('RGB', (2000, 2000), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        image_bytes = buf.getvalue()
        
        result = PixelBinService.preprocess_for_pixelbin(image_bytes, max_size=1024)
        
        assert result is not None
        assert len(result) < len(image_bytes)  # Изображение должно быть уменьшено
    
    @patch('app.services.pixelbin_service.requests.post')
    def test_upload_image_success(self, mock_post):
        """Тест успешной загрузки изображения"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {'_id': 'test_job_id', 'status': 'ACCEPTED'}
        mock_post.return_value = mock_response
        
        result = PixelBinService.upload_image(b'test_image_data', 'test.jpg')
        
        assert result is not None
        assert result['_id'] == 'test_job_id'
    
    @patch('app.services.pixelbin_service.requests.post')
    def test_upload_image_error_403(self, mock_post):
        """Тест обработки ошибки 403 (лимит использования)"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.text = 'Usage Limit Exceeded'
        mock_response.json.return_value = {
            'errorCode': 'JR-1000',
            'exception': 'UsageBlockedError'
        }
        mock_post.return_value = mock_response
        
        result = PixelBinService.upload_image(b'test_image_data', 'test.jpg')
        
        assert result is not None
        assert result['error'] == 'usage_limit_exceeded'
        assert result['status_code'] == 403
    
    def test_extract_images_from_pixelbin_response(self):
        """Тест извлечения изображений из ответа Pixelbin"""
        pixelbin_data = {
            'input': {
                'image': 'https://example.com/input.jpg'
            },
            'output': {
                'skinData': {
                    'concerns': [
                        {
                            'name': 'Акне',
                            'tech_name': 'acne',
                            'value': 50,
                            'severity': 'Average',
                            'image': 'https://example.com/acne.jpg'
                        }
                    ]
                }
            }
        }
        
        images = extract_images_from_pixelbin_response(pixelbin_data)
        
        assert len(images) == 2  # input + concern
        assert images[0]['type'] == 'input'
        assert images[1]['type'] == 'concern'
        assert images[1]['concern_name'] == 'acne'


class TestLLMService:
    """Тесты для LLM сервиса"""
    
    def test_generate_fallback_report(self):
        """Тест генерации простого отчёта без LLM"""
        skin_data = {
            'acne_score': 25.5,
            'pigmentation_score': 30.2,
            'pores_size': 45.8,
            'wrinkles_grade': 15.3,
            'skin_tone': 60.0,
            'texture_score': 55.5,
            'moisture_level': 70.2,
            'oiliness': 40.1
        }
        
        report = generate_fallback_report(skin_data)
        
        assert 'ОТЧЁТ О СОСТОЯНИИ КОЖИ' in report
        assert 'Акне: 25.5%' in report
        assert 'Пигментация: 30.2%' in report

