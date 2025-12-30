# Пример переменных окружения

Создайте файл `.env` в корне проекта со следующим содержимым:

```bash
# OpenRouter API Key для работы с LLM моделями
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Pixelbin Access Token для анализа кожи
# Получите токен на https://pixelbin.io
PIXELBIN_ACCESS_TOKEN=your_pixelbin_access_token_here

# FAL Key для SAM3 сегментации (опционально)
FAL_KEY=your_fal_key_here

# HuggingFace Token для сегментации (опционально)
HF_TOKEN=your_hf_token_here

# Server configuration
PORT=8000
HOST=0.0.0.0
```

## Для Railway

Добавьте эти переменные в Railway Dashboard → Variables:

- `OPENROUTER_API_KEY` - ваш ключ OpenRouter
- `PIXELBIN_ACCESS_TOKEN` - ваш токен Pixelbin
- `FAL_KEY` - (опционально) для SAM3
- `HF_TOKEN` - (опционально) для HuggingFace

## Для локальной разработки

1. Скопируйте `.env.example` в `.env` (если есть)
2. Или создайте `.env` файл вручную
3. Заполните реальными значениями

**ВАЖНО:** Никогда не коммитьте `.env` файл в Git! Он уже добавлен в `.gitignore`.

