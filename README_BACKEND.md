# Backend сервис для анализа кожи

## Описание

Backend-сервис для анализа состояния кожи лица с использованием больших языковых моделей (LLM) через Groq и OpenRouter API.

## Основные возможности

- Приём изображений лица (base64 или ссылка из Yandex Cloud)
- Анализ состояния кожи через vision модели (llama-3.2-90b-vision-preview)
- Fallback механизм для детекции (Groq → OpenRouter → Local)
- Генерация текстового отчёта с помощью LLM
- Настройка параметров модели через API

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Добавьте API ключи в `.env`:
```
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## Запуск

```bash
python app.py
```

Сервер запустится на `http://localhost:5000`

## API Endpoints

### POST /api/analyze

Анализ изображения кожи.

**Request:**
```json
{
  "image": "data:image/jpeg;base64,...",
  "config": {
    "detection_provider": "groq",
    "llm_provider": "groq",
    "vision_model": "llama-3.2-90b-vision-preview",
    "text_model": "llama-3.1-70b-versatile",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "acne_score": 25.5,
    "pigmentation_score": 30.2,
    "pores_size": 45.8,
    "wrinkles_grade": 15.3,
    "skin_tone": 60.0,
    "texture_score": 55.5,
    "moisture_level": 70.2,
    "oiliness": 40.1
  },
  "report": "Текстовый отчёт о состоянии кожи...",
  "provider": "groq",
  "config": {...}
}
```

### GET /api/config

Получить текущую конфигурацию.

### POST /api/config

Обновить конфигурацию.

### GET /api/models/groq-via-openrouter

Получить список моделей Groq доступных через OpenRouter.

**Response:**
```json
{
  "success": true,
  "models": [
    "groq/llama-3.2-90b-vision-preview",
    "groq/llama-3.1-70b-versatile",
    ...
  ],
  "count": 5
}
```

## Механизм переключения между провайдерами

Сервис автоматически переключается между провайдерами:

1. **Groq API** - основной провайдер (быстрый и бесплатный)
2. **Groq через OpenRouter** - если Groq API недоступен, используются модели Groq через OpenRouter
3. **OpenRouter** - резервный провайдер с другими моделями

**Важно:** Если все API недоступны, сервис возвращает ошибку. Случайные/тестовые данные не используются.

### Автоматический поиск моделей Groq

Сервис автоматически находит модели Groq доступные через OpenRouter и использует их как fallback, если прямой доступ к Groq API недоступен.

## Структура проекта

```
.
├── app.py                 # Основной backend сервис
├── index.html            # Frontend интерфейс
├── requirements.txt      # Зависимости Python
├── .env                  # Переменные окружения (не в git)
└── README_BACKEND.md     # Документация
```

## Логирование

Все операции логируются в консоль с уровнем INFO.

## Обработка ошибок

- Валидация входных данных
- Обработка ошибок API
- Автоматический fallback при сбоях
- Понятные сообщения об ошибках



