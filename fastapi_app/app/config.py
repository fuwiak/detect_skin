"""
Конфигурация приложения с использованием Pydantic Settings
"""
import os
import base64
import logging
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (если есть)
load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""
    
    # OpenRouter API
    openrouter_api_key: Optional[str] = None
    openrouter_api_url: str = "https://openrouter.ai/api/v1/chat/completions"
    
    # Pixelbin API
    pixelbin_access_token: Optional[str] = None
    pixelbin_base_url: str = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions"
    
    # SAM3 (FAL)
    fal_key: Optional[str] = None
    
    # HuggingFace
    hf_token: Optional[str] = None
    
    # Server
    port: int = int(os.getenv("PORT", 8000))  # Railway автоматически устанавливает PORT
    host: str = os.getenv("HOST", "0.0.0.0")  # 0.0.0.0 для Railway, 127.0.0.1 для локальной разработки
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Явно указываем, что нужно читать из переменных окружения системы
        env_file_encoding = 'utf-8'


# Создаём экземпляр настроек
settings = Settings()

# Дополнительная проверка: читаем переменные окружения напрямую из os.environ
# Это важно для Railway, где переменные могут быть установлены в системе, но не в .env файле
if not settings.openrouter_api_key:
    settings.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not settings.pixelbin_access_token:
    settings.pixelbin_access_token = os.getenv("PIXELBIN_ACCESS_TOKEN")
if not settings.fal_key:
    settings.fal_key = os.getenv("FAL_KEY")
if not settings.hf_token:
    settings.hf_token = os.getenv("HF_TOKEN")

# Логируем статус API ключей (без показа самих ключей)
logger.info("=" * 80)
logger.info("🔑 Проверка API ключей:")
logger.info(f"   OPENROUTER_API_KEY: {'✅ установлен' if settings.openrouter_api_key else '❌ не найден'}")
logger.info(f"   PIXELBIN_ACCESS_TOKEN: {'✅ установлен' if settings.pixelbin_access_token else '❌ не найден'}")
logger.info(f"   FAL_KEY: {'✅ установлен' if settings.fal_key else '❌ не найден'}")
logger.info(f"   HF_TOKEN: {'✅ установлен' if settings.hf_token else '❌ не найден'}")
logger.info("=" * 80)

# Устанавливаем FAL_KEY в окружение, если он есть
if settings.fal_key:
    os.environ['FAL_KEY'] = settings.fal_key

# Pixelbin Bearer Token
PIXELBIN_BEARER_TOKEN = (
    base64.b64encode(settings.pixelbin_access_token.encode('utf-8')).decode('utf-8')
    if settings.pixelbin_access_token
    else None
)

PIXELBIN_HEADERS = {
    "Authorization": f"Bearer {PIXELBIN_BEARER_TOKEN}",
} if PIXELBIN_BEARER_TOKEN else {}

# Экспортируем константы для использования в сервисах
PIXELBIN_BASE_URL = settings.pixelbin_base_url

