# Быстрый старт

## 1. Установка

```bash
cd fastapi_app
pip install -r requirements.txt
```

## 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
OPENROUTER_API_KEY=your_openrouter_key
PIXELBIN_ACCESS_TOKEN=your_pixelbin_token
FAL_KEY=your_fal_key
HF_TOKEN=your_hf_token
```

## 3. Запуск сервера

```bash
uvicorn app.main:app --reload
```

Сервер запустится на http://localhost:8000

## 4. Открыть Swagger документацию

Откройте в браузере: **http://localhost:8000/docs**

Здесь вы увидите:
- Все доступные endpoints
- Схемы запросов и ответов
- Возможность протестировать API прямо в браузере

## 5. Запуск тестов

```bash
# Все тесты
pytest

# С подробным выводом
pytest -v

# С покрытием
pytest --cov=app
```

## Основные endpoints

### POST /api/analyze
Анализ изображения кожи

**Пример запроса:**
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "mode": "pixelbin"
}
```

### GET /api/config
Получить текущую конфигурацию

### POST /api/config
Обновить конфигурацию

### GET /api/models/available
Список доступных моделей

### GET /api/proxy-image?url=...
Прокси изображений для обхода CORS

## Документация

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Структура проекта

```
fastapi_app/
├── app/              # Основной код приложения
│   ├── api/         # API endpoints
│   ├── services/    # Бизнес-логика
│   ├── schemas/     # Pydantic схемы
│   └── utils/       # Утилиты
├── tests/           # Unit тесты
└── docs/            # Sphinx документация
```

