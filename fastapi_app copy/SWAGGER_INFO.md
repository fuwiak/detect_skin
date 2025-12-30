# Swagger/OpenAPI Документация

## Где находится Swagger?

FastAPI автоматически генерирует интерактивную документацию API. После запуска сервера она доступна по следующим адресам:

### Swagger UI (рекомендуется)
**URL:** http://localhost:8000/docs

Интерактивный интерфейс с возможностью:
- Просмотра всех endpoints
- Тестирования API прямо в браузере
- Просмотра схем запросов и ответов
- Примеров использования

### ReDoc
**URL:** http://localhost:8000/redoc

Альтернативный интерфейс документации с более читаемым форматом.

### OpenAPI JSON Schema
**URL:** http://localhost:8000/openapi.json

Сырой JSON файл со схемой OpenAPI, который можно использовать для:
- Импорта в Postman
- Генерации клиентских библиотек
- Интеграции с другими инструментами

## Как использовать Swagger UI

1. Запустите сервер:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Откройте браузер и перейдите на http://localhost:8000/docs

3. Вы увидите список всех доступных endpoints:
   - `POST /api/analyze` - Анализ кожи
   - `GET /api/config` - Получить конфигурацию
   - `POST /api/config` - Обновить конфигурацию
   - `GET /api/models/available` - Список моделей
   - `GET /api/proxy-image` - Прокси изображений

4. Нажмите на любой endpoint, чтобы:
   - Увидеть описание
   - Просмотреть схему запроса
   - Попробовать выполнить запрос прямо в браузере

5. Для тестирования `/api/analyze`:
   - Нажмите "Try it out"
   - Вставьте base64 изображение в поле `image`
   - Выберите режим (`pixelbin` или `sam3`)
   - Нажмите "Execute"

## Примеры запросов

### Анализ в режиме Pixelbin
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "mode": "pixelbin",
  "config": {
    "vision_model": "google/gemini-2.5-flash",
    "temperature": 0.0
  }
}
```

### Анализ в режиме SAM3
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "mode": "sam3",
  "sam3_timeout": 10,
  "sam3_diseases": ["acne", "pigmentation", "wrinkles"],
  "sam3_use_llm_preanalysis": true,
  "sam3_max_coverage_percent": 25.0
}
```

## Автоматическая генерация

Документация генерируется автоматически на основе:
- Pydantic схем (для валидации и описания данных)
- Docstrings функций (для описания endpoints)
- Типов параметров (для схем запросов/ответов)

Все описания написаны на русском языке для удобства использования.

