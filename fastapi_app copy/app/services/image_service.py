"""
Сервис для обработки изображений
"""
import io
import base64
import logging
from typing import Optional
from PIL import Image

from app.dependencies import HEIC_SUPPORT
from app.utils.image_utils import convert_heic_to_jpeg

logger = logging.getLogger(__name__)





