"""
Dependency injection для FastAPI
"""
import sys
import os
import logging
from typing import Optional

# Добавляем родительскую директорию в sys.path для импорта skin_segmentation и hf_segmentation
# Эти модули находятся в корне проекта, а не в fastapi_app/
# __file__ = fastapi_app/app/dependencies.py
# Нужно получить /Users/user/detect_skin
app_dir = os.path.dirname(os.path.dirname(__file__))  # fastapi_app/app -> fastapi_app
project_root = os.path.dirname(app_dir)  # fastapi_app -> detect_skin
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

# Проверка доступности модулей
try:
    import fal_client
    FAL_AVAILABLE = True
    logger.info("fal_client установлен")
except ImportError:
    fal_client = None
    FAL_AVAILABLE = False
    logger.warning("fal_client не установлен, SAM3 режим недоступен")

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw, ImageFont
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
    logger.info("Поддержка HEIC включена")
except ImportError:
    HEIC_SUPPORT = False
    logger.warning("pillow-heif не установлен, поддержка HEIC будет ограничена")

try:
    import numpy as np
    from scipy import ndimage
    NUMPY_AVAILABLE = True
    logger.info("NumPy и SciPy доступны для обработки масок")
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy/SciPy не установлены, обработка масок будет ограничена")

try:
    from skin_segmentation import get_segmenter
    SEGMENTATION_AVAILABLE = True
    logger.info("Модуль сегментации доступен")
except ImportError as e:
    SEGMENTATION_AVAILABLE = False
    logger.warning(f"Модуль сегментации недоступен: {e}")

try:
    from hf_segmentation import get_hf_segmenter
    HF_SEGMENTATION_AVAILABLE = True
    logger.info("Модуль Hugging Face сегментации доступен")
except ImportError as e:
    HF_SEGMENTATION_AVAILABLE = False
    logger.warning(f"Модуль Hugging Face сегментации недоступен: {e}")

# Импортируем настройки
from app.config import settings

# Инициализируем fal_client с ключом, если доступен
if FAL_AVAILABLE and settings.fal_key:
    try:
        # fal_client автоматически читает FAL_KEY из os.environ
        # Но убеждаемся, что ключ установлен
        if 'FAL_KEY' not in os.environ and settings.fal_key:
            os.environ['FAL_KEY'] = settings.fal_key
        logger.info("✅ fal_client готов к работе (FAL_KEY установлен)")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при инициализации fal_client: {e}")
elif FAL_AVAILABLE and not settings.fal_key:
    logger.warning("⚠️ fal_client установлен, но FAL_KEY не найден. SAM3 будет недоступен.")

# Экспортируем доступность модулей и настройки
__all__ = [
    'FAL_AVAILABLE',
    'HEIC_SUPPORT',
    'NUMPY_AVAILABLE',
    'SEGMENTATION_AVAILABLE',
    'HF_SEGMENTATION_AVAILABLE',
    'settings',
    'fal_client',
]

