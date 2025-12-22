# Skin Analyzer API (FastAPI)

Реструктурированная версия проекта на FastAPI с модульной архитектурой и полной документацией.

## Структура проекта

```
fastapi_app/
├── app/
│   ├── main.py              # Точка входа FastAPI
│   ├── config.py            # Конфигурация (Pydantic Settings)
│   ├── dependencies.py      # Dependency injection
│   ├── api/                 # API endpoints
│   ├── schemas/             # Pydantic схемы
│   ├── services/            # Бизнес-логика
│   └── utils/               # Утилиты
├── docs/                    # Sphinx документация
├── tests/                   # Unit тесты
└── requirements.txt         # Зависимости
```

## Установка

```bash
cd fastapi_app
pip install -r requirements.txt
```

## Запуск

```bash
# Development
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Документация

### Swagger UI (автоматическая)

FastAPI автоматически генерирует интерактивную документацию:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Sphinx документация

```bash
cd docs
make html
# Открыть _build/html/index.html
```

## API Endpoints

- `POST /api/analyze` - Анализ изображения кожи
- `GET /api/config` - Получить конфигурацию
- `POST /api/config` - Обновить конфигурацию
- `GET /api/models/available` - Список доступных моделей
- `GET /api/proxy-image` - Прокси изображений

## Тестирование

```bash
# Запуск всех тестов
pytest

# С подробным выводом
pytest -v

# Конкретный тест
pytest tests/test_api.py::TestAnalyzeEndpoint::test_analyze_success_pixelbin

# С покрытием
pytest --cov=app --cov-report=html
```

## Переменные окружения

Создайте файл `.env`:

```
OPENROUTER_API_KEY=your_key
PIXELBIN_ACCESS_TOKEN=your_token
FAL_KEY=your_key
HF_TOKEN=your_token
```

## Особенности

- ✅ Полная типизация с Pydantic
- ✅ Автоматическая документация Swagger/OpenAPI
- ✅ Unit тесты для всех компонентов
- ✅ Модульная архитектура
- ✅ Поддержка двух режимов: Pixelbin и SAM3
- ✅ Fallback механизмы для надёжности
