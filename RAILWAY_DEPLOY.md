# Деплой на Railway

## Проблема: "The train has not arrived at the station"

Эта ошибка означает, что приложение не запускается на Railway. Вот что нужно проверить:

## Решение

### 1. Проверьте логи в Railway Dashboard

1. Зайдите в Railway Dashboard
2. Откройте ваш проект
3. Перейдите в раздел **Deployments** или **Logs**
4. Проверьте ошибки при запуске

### 2. Убедитесь, что все файлы на месте

В корне проекта должны быть:
- `Procfile` - команда запуска
- `railway.toml` - конфигурация Railway
- `nixpacks.toml` - конфигурация сборки (опционально)
- `fastapi_app/requirements.txt` - зависимости

### 3. Переменные окружения

В Railway Dashboard → Settings → Variables убедитесь, что установлены:

```
PORT=8000 (Railway устанавливает автоматически, но можно указать явно)
HOST=0.0.0.0 (опционально)
OPENROUTER_API_KEY=your_key_here
PIXELBIN_ACCESS_TOKEN=your_token_here
FAL_KEY=your_key_here
HF_TOKEN=your_token_here
```

### 4. Команда запуска

Railway использует один из следующих способов запуска (в порядке приоритета):

1. **Procfile** (если есть):
   ```
   web: cd fastapi_app && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
   ```

2. **railway.toml** (startCommand):
   ```
   cd fastapi_app && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
   ```

3. **nixpacks.toml** (start.cmd):
   ```
   cd fastapi_app && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### 5. Проверка после деплоя

После успешного деплоя Swagger будет доступен по адресу:

- **Swagger UI**: `https://detect-skin-production.up.railway.app/docs`
- **ReDoc**: `https://detect-skin-production.up.railway.app/redoc`
- **OpenAPI JSON**: `https://detect-skin-production.up.railway.app/openapi.json`

### 6. Типичные проблемы

#### Проблема: "Module not found"
**Решение**: Убедитесь, что `fastapi_app/requirements.txt` содержит все зависимости

#### Проблема: "Port already in use"
**Решение**: Railway автоматически устанавливает `$PORT`, убедитесь, что используете его

#### Проблема: "Command not found: uvicorn"
**Решение**: Используйте `python -m uvicorn` вместо просто `uvicorn`

#### Проблема: "No such file or directory"
**Решение**: Проверьте пути - команда должна выполняться из корня проекта

### 7. Локальная проверка

Перед деплоем проверьте локально:

```bash
cd fastapi_app
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Если работает локально, но не на Railway - проверьте логи Railway.

### 8. Пересборка

Если ничего не помогает:

1. В Railway Dashboard → Settings → Delete Service
2. Создайте новый сервис
3. Подключите репозиторий заново
4. Установите переменные окружения
5. Дождитесь деплоя

## Контакты

Если проблема не решена, проверьте логи Railway и убедитесь, что:
- Все зависимости установлены
- Команда запуска правильная
- Переменные окружения установлены
- Порт использует переменную `$PORT`





