# Деплой на Railway через Dockerfile

## Структура

Проект настроен для деплоя через Dockerfile. Railway автоматически обнаружит Dockerfile и использует его для сборки.

## Файлы конфигурации

### Dockerfile
- Базовый образ: `python:3.11-slim`
- Устанавливает системные зависимости для OpenCV и других библиотек
- Копирует `fastapi_app/requirements.txt` и устанавливает зависимости
- Копирует код приложения из `fastapi_app/`
- Запускает FastAPI через uvicorn

### railway.toml
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"
```

### .dockerignore
Исключает ненужные файлы из Docker образа для ускорения сборки.

## Локальная проверка

### Сборка образа
```bash
docker build -t detect-skin .
```

### Запуск контейнера
```bash
docker run -p 8000:8000 \
  -e PORT=8000 \
  -e HOST=0.0.0.0 \
  -e OPENROUTER_API_KEY=your_key \
  -e PIXELBIN_ACCESS_TOKEN=your_token \
  detect-skin
```

### Проверка работы
```bash
curl http://localhost:8000/docs
```

## Переменные окружения на Railway

В Railway Dashboard → Settings → Variables установите:

```
PORT=8000 (Railway устанавливает автоматически)
HOST=0.0.0.0 (опционально)
OPENROUTER_API_KEY=your_key_here
PIXELBIN_ACCESS_TOKEN=your_token_here
FAL_KEY=your_key_here (если используется SAM3)
HF_TOKEN=your_token_here (если используется HuggingFace)
```

## Деплой на Railway

1. **Закоммитьте изменения:**
   ```bash
   git add Dockerfile railway.toml .dockerignore
   git commit -m "Configure Dockerfile for Railway deployment"
   git push
   ```

2. **Railway автоматически:**
   - Обнаружит Dockerfile
   - Соберет Docker образ
   - Запустит контейнер

3. **После деплоя Swagger будет доступен:**
   - **Swagger UI**: `https://detect-skin-production.up.railway.app/docs`
   - **ReDoc**: `https://detect-skin-production.up.railway.app/redoc`
   - **OpenAPI JSON**: `https://detect-skin-production.up.railway.app/openapi.json`

## Проверка логов

Если что-то не работает, проверьте логи в Railway Dashboard:
1. Откройте проект
2. Перейдите в **Deployments**
3. Выберите последний деплой
4. Откройте **View Logs**

## Оптимизация образа

Текущий Dockerfile использует `python:3.11-slim` для уменьшения размера образа. Если нужны дополнительные оптимизации:

1. Используйте multi-stage build
2. Кешируйте слои pip install
3. Удаляйте ненужные зависимости после установки

## Troubleshooting

### Проблема: "Module not found"
**Решение**: Убедитесь, что все зависимости в `fastapi_app/requirements.txt`

### Проблема: "Port already in use"
**Решение**: Railway автоматически устанавливает `$PORT`, Dockerfile использует переменную окружения

### Проблема: "Cannot connect to database" или другие ошибки подключения
**Решение**: Проверьте переменные окружения в Railway Dashboard

### Проблема: Образ слишком большой
**Решение**: 
- Используйте `.dockerignore` (уже создан)
- Рассмотрите multi-stage build
- Удаляйте кеш apt после установки (уже сделано)

## Локальная разработка с Docker

### Docker Compose (опционально)

Создайте `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - HOST=0.0.0.0
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - PIXELBIN_ACCESS_TOKEN=${PIXELBIN_ACCESS_TOKEN}
    env_file:
      - .env
```

Запуск:
```bash
docker-compose up --build
```





