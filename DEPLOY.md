# Деплой на Railway

## Подготовка

1. Убедитесь, что у вас установлены:
   - Docker
   - Docker Compose
   - Git

## Локальная проверка с Docker

```bash
# Сборка образа
docker-compose build

# Запуск контейнера
docker-compose up

# Или в фоновом режиме
docker-compose up -d
```

Приложение будет доступно на `http://localhost:5000`

## Деплой на Railway

### 1. Подготовка репозитория

```bash
# Добавьте все файлы
git add .

# Создайте коммит
git commit -m "Prepare for Railway deployment"

# Отправьте в репозиторий
git push origin main
```

### 2. Создание проекта на Railway

1. Зайдите на [railway.app](https://railway.app)
2. Войдите через GitHub
3. Нажмите "New Project"
4. Выберите "Deploy from GitHub repo"
5. Выберите ваш репозиторий

### 3. Настройка переменных окружения

В Railway Dashboard перейдите в Settings → Variables и добавьте:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
PORT=5000
```

**Важно:** Railway автоматически устанавливает переменную `PORT`, но лучше указать её явно.

### 4. Настройка деплоя

Railway автоматически обнаружит:
- `Dockerfile` - для сборки образа
- `railway.json` или `railway.toml` - для конфигурации

### 5. Получение URL

После деплоя Railway предоставит публичный URL вашего приложения.

## Переменные окружения для Railway

Убедитесь, что в Railway Variables установлены:

- `OPENROUTER_API_KEY` - ваш API ключ OpenRouter
- `PORT` - порт (обычно Railway устанавливает автоматически)

## Проверка деплоя

После успешного деплоя откройте предоставленный Railway URL и проверьте работу приложения.

## Локальная разработка

Для локальной разработки используйте:

```bash
# Активация виртуального окружения
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python app.py
```

## Troubleshooting

### Проблемы с портом

Railway автоматически устанавливает переменную `PORT`. Убедитесь, что `app.py` использует её:

```python
port = int(os.getenv('PORT', 5000))
```

### Проблемы с переменными окружения

Проверьте, что все переменные окружения установлены в Railway Dashboard → Settings → Variables.

### Проблемы с Docker

Для локальной проверки:

```bash
docker-compose build --no-cache
docker-compose up
```

