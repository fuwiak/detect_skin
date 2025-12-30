"""
FastAPI приложение для анализа состояния кожи
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.api.router import router

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events для инициализации и очистки ресурсов"""
    # Startup
    logger.info("=" * 80)
    logger.info("🔬 Skin Analyzer Backend (FastAPI)")
    logger.info("=" * 80)
    # Показываем оба адреса для удобства
    if settings.host == "0.0.0.0":
        logger.info(f"📡 Сервер запущен на http://0.0.0.0:{settings.port} (доступен по http://localhost:{settings.port})")
    else:
        logger.info(f"📡 Сервер запущен на http://{settings.host}:{settings.port}")
    logger.info("=" * 80)
    yield
    # Shutdown (если нужно)
    logger.info("Сервер остановлен")


# Создаём FastAPI приложение
app = FastAPI(
    title="Skin Analyzer API",
    description="""
    API для анализа состояния кожи лица с использованием больших языковых моделей (LLM) и методов сегментации.
    
    ## Возможности
    
    * Анализ изображений кожи через OpenRouter API
    * Сегментация с использованием SAM3, Hugging Face моделей и эвристических методов
    * Генерация текстовых отчётов на русском и английском языках
    * Поддержка различных форматов изображений (JPEG, PNG, HEIC)
    * Два режима работы: Pixelbin и SAM3
    
    ## Swagger документация
    
    Полная интерактивная документация доступна по адресу `/docs` (Swagger UI) или `/redoc` (ReDoc).
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True}  # Сохранять авторизацию в Swagger
)

# CORS middleware - добавляем ПОСЛЕ создания app, но ПЕРЕД роутерами
# Это важно для правильной работы Swagger UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все источники
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы
    allow_headers=["*"],  # Разрешаем все заголовки
)

# Подключаем роутеры
app.include_router(router)

# Статические файлы (для index.html)
# В production лучше использовать nginx или CDN
# static_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..")
# if os.path.exists(os.path.join(static_path, "index.html")):
#     app.mount("/", StaticFiles(directory=static_path, html=True), name="static")


@app.get("/")
async def index():
    """Главная страница"""
    # Ищем index.html в родительской директории проекта
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    parent_dir = os.path.dirname(current_dir)
    index_path = os.path.join(parent_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Skin Analyzer API",
        "docs": "/docs",
        "swagger": "/docs",
        "redoc": "/redoc",
        "api": "/api",
        "note": "Используйте http://localhost:8000/docs для доступа к Swagger UI"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

