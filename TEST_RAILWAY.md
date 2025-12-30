# Тестирование эндпоинтов на Railway

## Быстрый старт

### 1. Health Check (базовая проверка)

```bash
python test_railway_endpoint.py
```

Проверяет:
- `/api/health` - базовая проверка работоспособности
- `/api/health/detailed` - детальная проверка всех компонентов
- `/api/analyze` в режиме pixelbin

### 2. Тестирование с изображением

```bash
python test_railway_endpoint.py /path/to/image.jpg
```

### 3. Тестирование SAM3 режима

```bash
python test_railway_endpoint.py /path/to/image.jpg sam3
```

### 4. Тестирование только Pixelbin режима

```bash
python test_railway_endpoint.py /path/to/image.jpg pixelbin
```

### 5. Тестирование всех режимов

```bash
python test_railway_endpoint.py /path/to/image.jpg all
```

## Параметры

- `image_path` - Путь к тестовому изображению (опционально)
- `mode` - Режим тестирования: `all`, `pixelbin`, `sam3` (по умолчанию: `all`)

## Переменные окружения

```bash
export RAILWAY_URL=https://detectskin-production.up.railway.app
python test_railway_endpoint.py
```

## Health Check эндпоинты

### `/api/health`
Быстрая проверка работоспособности API.

**Ответ:**
```json
{
  "status": "healthy",
  "service": "Skin Analyzer API",
  "version": "1.0.0",
  "timestamp": 1234567890.123
}
```

### `/api/health/detailed`
Детальная проверка всех компонентов системы.

**Ответ:**
```json
{
  "status": "healthy",
  "service": "Skin Analyzer API",
  "version": "1.0.0",
  "timestamp": 1234567890.123,
  "components": {
    "api_keys": {
      "openrouter": {"available": true, "status": "ok"},
      "pixelbin": {"available": true, "status": "ok"},
      "fal": {"available": false, "status": "optional"},
      "hf": {"available": false, "status": "optional"}
    },
    "server": {
      "host": "0.0.0.0",
      "port": 8000,
      "status": "ok"
    }
  }
}
```

## Логирование

Все запросы к `/api/analyze` логируются с детальной информацией:

- ⏰ Время начала и завершения
- 📋 Параметры запроса (режим, конфигурация)
- 📷 Информация об изображении
- 🤖 Используемые модели и провайдеры
- ⏱️ Время выполнения
- ✅/❌ Результат выполнения

Логи доступны в Railway Dashboard → Deployments → View Logs.

## Примеры использования

### Тест SAM3 с изображением 18.png

```bash
python test_railway_endpoint.py img/18.png sam3
```

### Тест только health check

```bash
curl https://detectskin-production.up.railway.app/api/health
```

### Тест детального health check

```bash
curl https://detectskin-production.up.railway.app/api/health/detailed
```

## Проверка логов на Railway

1. Откройте Railway Dashboard
2. Перейдите в ваш проект
3. Откройте **Deployments**
4. Выберите последний деплой
5. Нажмите **View Logs**

В логах вы увидите:
- 🔑 Проверка API ключей при старте
- 📥 Каждый новый запрос на анализ
- ⏱️ Время выполнения каждого этапа
- ✅/❌ Результаты выполнения

