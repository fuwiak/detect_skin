FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для OpenCV и других библиотек
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements.txt из fastapi_app
COPY fastapi_app/requirements.txt /app/requirements.txt

# Установка зависимостей Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование всего кода приложения
COPY fastapi_app /app/fastapi_app
COPY index.html /app/index.html

# Установка рабочей директории в fastapi_app
WORKDIR /app/fastapi_app

# Открываем порт (Railway автоматически установит PORT из переменных окружения)
EXPOSE 8000

# Переменная окружения для порта (Railway установит PORT)
ENV PORT=8000
ENV HOST=0.0.0.0

# Запуск FastAPI приложения через uvicorn
# Railway автоматически устанавливает переменную PORT
# Используем простой CMD с sh -c для правильной подстановки переменной окружения
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1"]
