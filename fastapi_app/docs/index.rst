Skin Analyzer API Documentation
===============================

Добро пожаловать в документацию Skin Analyzer API!

Этот проект предоставляет REST API для анализа состояния кожи с использованием больших языковых моделей (LLM) и методов сегментации изображений.

Содержание
----------

.. toctree::
   :maxdepth: 2
   :caption: Содержание:

   architecture
   api
   services

Архитектура
-----------

Проект построен на FastAPI и следует принципам чистой архитектуры:

- **API Layer**: FastAPI endpoints для обработки HTTP запросов
- **Service Layer**: Бизнес-логика и интеграция с внешними API
- **Utils Layer**: Утилиты и вспомогательные функции

Основные возможности
--------------------

- Анализ изображений кожи через OpenRouter API
- Сегментация с использованием SAM3, Hugging Face моделей и эвристических методов
- Генерация текстовых отчётов с помощью LLM
- Поддержка различных форматов изображений (JPEG, PNG, HEIC)

Быстрый старт
------------

.. code-block:: python

   from fastapi import FastAPI
   from app.main import app

   # Запуск сервера
   uvicorn app.main:app --reload

API Endpoints
-------------

- ``POST /api/analyze`` - Анализ изображения кожи
- ``GET /api/config`` - Получить конфигурацию
- ``POST /api/config`` - Обновить конфигурацию
- ``GET /api/models/available`` - Список доступных моделей
- ``GET /api/proxy-image`` - Прокси изображений

Подробнее см. в разделе :doc:`api`.




