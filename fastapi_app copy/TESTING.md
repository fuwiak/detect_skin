# Руководство по тестированию

## Запуск тестов

### Все тесты
```bash
cd fastapi_app
pytest
```

### С подробным выводом
```bash
pytest -v
```

### Конкретный файл тестов
```bash
pytest tests/test_api.py
```

### Конкретный тест
```bash
pytest tests/test_api.py::TestAnalyzeEndpoint::test_analyze_success_pixelbin
```

### С покрытием кода
```bash
pytest --cov=app --cov-report=html
```

После этого откройте `htmlcov/index.html` в браузере.

## Структура тестов

### test_utils.py
Unit тесты для утилит:
- `parse_skin_analysis_from_text` - парсинг анализа из текста
- `parse_report_locations` - парсинг локализации из отчёта
- `convert_bbox_to_position` - конвертация bounding box
- `segment_face_area` - сегментация зон лица

### test_services.py
Unit тесты для сервисов:
- `PixelBinService` - загрузка и проверка статуса
- `extract_images_from_pixelbin_response` - извлечение изображений
- `generate_fallback_report` - генерация простого отчёта

### test_schemas.py
Unit тесты для Pydantic схем:
- `AnalyzeRequest` - валидация запроса анализа
- `AnalyzeResponse` - структура ответа
- `ConfigRequest/Response` - конфигурация
- `AvailableModelsResponse` - список моделей

### test_api.py
Unit тесты для API endpoints:
- `POST /api/analyze` - анализ кожи
- `GET/POST /api/config` - конфигурация
- `GET /api/models/available` - список моделей
- `GET /api/proxy-image` - прокси изображений

### test_integration.py
Интеграционные тесты:
- Доступность Swagger UI
- Доступность OpenAPI схемы
- Наличие всех endpoints

### test_constants.py
Тесты для констант:
- `SAM3_DISEASES_DEFAULT` - список заболеваний
- `SKIN_DISEASE_KNOWLEDGE_BASE` - база знаний
- `DETECTION_FALLBACKS` - fallback модели

## Моки и фикстуры

Тесты используют моки для:
- HTTP запросов (requests)
- API ключей (settings)
- Внешних сервисов (Pixelbin, OpenRouter, SAM3)

Фикстуры определены в `conftest.py`:
- `mock_settings` - мок настроек

## Примеры тестов

### Тест парсинга
```python
def test_parse_skin_analysis_from_text(self):
    text = "acne_score: 25.5"
    result = parse_skin_analysis_from_text(text)
    assert result['acne_score'] == 25.5
```

### Тест API endpoint
```python
def test_get_config(self):
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()['success'] is True
```

### Тест сервиса с моком
```python
@patch('app.services.pixelbin_service.requests.post')
def test_upload_image_success(self, mock_post):
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {'_id': 'test'}
    mock_post.return_value = mock_response
    
    result = PixelBinService.upload_image(b'test', 'test.jpg')
    assert result['_id'] == 'test'
```

## Покрытие кода

Цель: покрытие > 80% для всех модулей.

Проверка покрытия:
```bash
pytest --cov=app --cov-report=term-missing
```

## Запуск в CI/CD

Для автоматического запуска тестов в CI/CD добавьте в конфигурацию:

```yaml
- name: Run tests
  run: |
    cd fastapi_app
    pip install -r requirements.txt
    pytest --cov=app --cov-report=xml
```





