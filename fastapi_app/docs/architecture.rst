Архитектура проекта
===================

Обзор
-----

Проект следует принципам чистой архитектуры с разделением на слои:

.. code-block:: text

   ┌─────────────────────────────────────┐
   │         API Layer (FastAPI)          │
   │  ┌─────────┐  ┌─────────┐           │
   │  │ analyze │  │ config  │  ...      │
   │  └─────────┘  └─────────┘           │
   └─────────────────────────────────────┘
                    │
   ┌─────────────────────────────────────┐
   │        Service Layer                 │
   │  ┌──────────────┐  ┌──────────────┐ │
   │  │ OpenRouter   │  │ Pixelbin     │ │
   │  │ SAM3         │  │ Segmentation │ │
   │  └──────────────┘  └──────────────┘ │
   └─────────────────────────────────────┘
                    │
   ┌─────────────────────────────────────┐
   │        Utils Layer                   │
   │  ┌──────────────┐  ┌──────────────┐ │
   │  │ Parsing      │  │ Image Utils  │ │
   │  │ Constants    │  │ Timeout      │ │
   │  └──────────────┘  └──────────────┘ │
   └─────────────────────────────────────┘

Структура проекта
----------------

::

   fastapi_app/
   ├── app/
   │   ├── main.py              # Точка входа FastAPI
   │   ├── config.py            # Конфигурация (Pydantic Settings)
   │   ├── dependencies.py      # Dependency injection
   │   ├── api/                 # API endpoints
   │   │   ├── analyze.py
   │   │   ├── config.py
   │   │   ├── models.py
   │   │   └── proxy.py
   │   ├── schemas/             # Pydantic схемы
   │   │   ├── analyze.py
   │   │   ├── config.py
   │   │   └── models.py
   │   ├── services/            # Бизнес-логика
   │   │   ├── openrouter_service.py
   │   │   ├── pixelbin_service.py
   │   │   ├── sam3_service.py
   │   │   ├── segmentation_service.py
   │   │   └── llm_service.py
   │   └── utils/               # Утилиты
   │       ├── constants.py
   │       ├── parsing.py
   │       ├── image_utils.py
   │       └── timeout.py
   └── docs/                    # Sphinx документация

Поток данных
------------

1. **Запрос** → FastAPI endpoint
2. **Валидация** → Pydantic схемы
3. **Обработка** → Service layer
4. **Ответ** → JSON через FastAPI

Пример потока для анализа:

.. code-block:: text

   POST /api/analyze
   ↓
   AnalyzeRequest (Pydantic)
   ↓
   OpenRouterService.analyze_image()
   ↓
   LLMService.generate_report()
   ↓
   AnalyzeResponse (Pydantic)
   ↓
   JSON Response










