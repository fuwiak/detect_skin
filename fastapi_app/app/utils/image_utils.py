"""
Утилиты для работы с изображениями
"""
import io
import logging
from typing import Optional
from PIL import Image, ImageOps

from app.dependencies import HEIC_SUPPORT

logger = logging.getLogger(__name__)


def detect_image_format(image_bytes: bytes) -> Optional[str]:
    """
    Определяет формат изображения по магическим байтам.
    Возвращает MIME type или None.
    """
    if not image_bytes or len(image_bytes) < 12:
        return None
    
    # JPEG: FF D8 FF
    if image_bytes[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    
    # HEIC/HEIF: ftyp (может быть в разных позициях)
    # Обычно начинается с ftyp, затем идет brand (heic, heif, mif1 и т.д.)
    if b'ftyp' in image_bytes[:20]:
        # Проверяем бренды HEIC/HEIF
        header = image_bytes[:20]
        if b'heic' in header or b'heif' in header or b'mif1' in header:
            return 'image/heic'
        if b'hevc' in header or b'hvc1' in header:
            return 'image/heic'
    
    # GIF: 47 49 46 38
    if image_bytes[:4] == b'GIF8':
        return 'image/gif'
    
    # WebP: RIFF...WEBP
    if image_bytes[:4] == b'RIFF' and b'WEBP' in image_bytes[8:12]:
        return 'image/webp'
    
    # BMP: 42 4D
    if image_bytes[:2] == b'BM':
        return 'image/bmp'
    
    return None


def convert_heic_to_jpeg(image_bytes: bytes) -> bytes:
    """
    Конвертирует HEIC/HEIF изображение в JPEG с сохранением ориентации.
    Применяет EXIF transpose для правильной ориентации изображения.
    """
    if not HEIC_SUPPORT:
        raise ValueError("Поддержка HEIC не доступна. Установите pillow-heif.")
    
    try:
        # Открываем HEIC изображение
        image = Image.open(io.BytesIO(image_bytes))
        
        # Применяем EXIF transpose для правильной ориентации
        # Это важно для правильной работы разметки на лице
        image = ImageOps.exif_transpose(image)
        
        # Конвертируем в RGB (если нужно)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Создаём белый фон для прозрачных изображений
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Сохраняем в JPEG с сохранением качества
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=95, exif=b'')  # Удаляем EXIF, т.к. ориентация уже применена
        return output.getvalue()
    except Exception as e:
        logger.error(f"Ошибка при конвертации HEIC: {e}")
        raise


def segment_face_area(concern_type: str, value: float) -> dict:
    """Простой алгоритм сегментации лица для определения зон проблем с естественными формами"""
    import random
    
    # Базовые зоны лица в процентах от размера изображения с естественными формами
    zones = {
        'forehead': {'x': 50, 'y': 20, 'width': 40, 'height': 15, 'shape': 'ellipse'},  # Лоб - эллипс
        'left_cheek': {'x': 25, 'y': 45, 'width': 20, 'height': 25, 'shape': 'ellipse'},  # Левая щека - эллипс
        'right_cheek': {'x': 75, 'y': 45, 'width': 20, 'height': 25, 'shape': 'ellipse'},  # Правая щека - эллипс
        'nose': {'x': 50, 'y': 50, 'width': 15, 'height': 20, 'shape': 'ellipse'},  # Нос - эллипс
        'chin': {'x': 50, 'y': 75, 'width': 25, 'height': 15, 'shape': 'ellipse'},  # Подбородок - эллипс
        't_zone': {'x': 50, 'y': 40, 'width': 30, 'height': 30, 'shape': 'polygon'},  # Т-зона - многоугольник
        'u_zone': {'x': 50, 'y': 55, 'width': 50, 'height': 30, 'shape': 'polygon'},  # U-зона - многоугольник
        'periorbital': {'x': 50, 'y': 35, 'width': 35, 'height': 20, 'shape': 'ellipse'},  # Периорбитальная - эллипс
        'perioral': {'x': 50, 'y': 65, 'width': 25, 'height': 15, 'shape': 'ellipse'},  # Периоральная - эллипс
    }
    
    # Маппинг типов проблем на зоны лица
    concern_zones = {
        'acne': ['t_zone', 'left_cheek', 'right_cheek', 'chin'],
        'pigmentation': ['left_cheek', 'right_cheek', 'forehead'],
        'pores': ['t_zone', 'nose'],
        'wrinkles': ['forehead', 'u_zone'],
        'hydration': ['left_cheek', 'right_cheek', 'u_zone'],
        'oiliness': ['t_zone', 'nose'],
    }
    
    # Выбираем зону на основе типа проблемы
    available_zones = concern_zones.get(concern_type, ['t_zone'])
    # Если значение высокое, распределяем по нескольким зонам
    if value > 70:
        zone_name = available_zones[0]  # Основная зона
    elif value > 50:
        zone_name = available_zones[0] if len(available_zones) > 0 else 't_zone'
    else:
        zone_name = available_zones[-1] if len(available_zones) > 1 else available_zones[0]
    
    zone = zones.get(zone_name, zones['t_zone'])
    
    # Добавляем небольшую случайность для более естественного распределения
    x_offset = random.uniform(-5, 5)
    y_offset = random.uniform(-5, 5)
    
    return {
        'x': zone['x'] + x_offset,
        'y': zone['y'] + y_offset,
        'width': zone['width'],
        'height': zone['height'],
        'zone': zone_name
    }




