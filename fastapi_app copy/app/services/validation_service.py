"""
Сервис для валидации изображений перед отправкой в Pixelbin API
Проверяет разрешение, размер файла и наличие лица на изображении

Сервис детекции лица:
- Использует OpenCV с каскадами Хаара (haarcascade_frontalface_default.xml)
- Это встроенный метод OpenCV, не требует дополнительных зависимостей
- Альтернативы: face_recognition, MediaPipe, dlib, но OpenCV - самый простой и быстрый вариант
"""
import io
import logging
from typing import Dict, Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

# Попытка импорта OpenCV для детекции лица
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
    logger.info("OpenCV доступен для детекции лица")
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV не установлен, детекция лица будет ограничена")

# Минимальные и максимальные требования
MIN_RESOLUTION = (256, 256)  # Минимальное разрешение
MAX_RESOLUTION = (8192, 8192)  # Максимальное разрешение
MIN_FILE_SIZE = 1024  # 1 KB минимальный размер
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB максимальный размер
RECOMMENDED_RESOLUTION = (512, 512)  # Рекомендуемое разрешение для лучшего качества


class ImageValidationError(Exception):
    """Исключение для ошибок валидации изображения"""
    pass


def detect_face_opencv(image_bytes: bytes) -> Tuple[bool, Optional[Dict]]:
    """
    Детектирует лицо на изображении с помощью OpenCV
    
    Args:
        image_bytes: Байты изображения
        
    Returns:
        Tuple[bool, Optional[Dict]]: (найдено_ли_лицо, информация_о_лице)
    """
    if not CV2_AVAILABLE:
        logger.warning("OpenCV недоступен, пропускаем детекцию лица")
        return False, None
    
    try:
        # Загружаем изображение
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.warning("Не удалось декодировать изображение для детекции лица")
            return False, None
        
        # Конвертируем в grayscale для детектора
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Загружаем каскад Хаара для детекции лица
        # Используем встроенный каскад OpenCV
        face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(face_cascade_path)
        
        if face_cascade.empty():
            logger.warning("Не удалось загрузить каскад Хаара для детекции лица")
            return False, None
        
        # Детектируем лица
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(faces) > 0:
            # Берем самое большое лицо
            largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
            x, y, w, h = largest_face
            
            face_info = {
                'count': len(faces),
                'largest': {
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'area': int(w * h)
                },
                'image_size': {
                    'width': int(img.shape[1]),
                    'height': int(img.shape[0])
                }
            }
            
            logger.info(f"Найдено лицо: {face_info}")
            return True, face_info
        else:
            logger.info("Лицо не найдено на изображении")
            return False, None
            
    except Exception as e:
        logger.error(f"Ошибка при детекции лица: {e}", exc_info=True)
        return False, None


def validate_image(
    image_bytes: bytes,
    file_size: Optional[int] = None,
    require_face: bool = True
) -> Dict:
    """
    Валидирует изображение перед отправкой в Pixelbin API
    
    Args:
        image_bytes: Байты изображения
        file_size: Размер файла в байтах (опционально)
        require_face: Требовать наличие лица на изображении
        
    Returns:
        Dict: Результат валидации с полями:
            - valid: bool - прошла ли валидация
            - error: Optional[str] - сообщение об ошибке
            - warnings: List[str] - предупреждения
            - image_info: Dict - информация об изображении
            - face_detected: bool - найдено ли лицо
            - face_info: Optional[Dict] - информация о лице
    """
    result = {
        'valid': True,
        'error': None,
        'warnings': [],
        'image_info': {},
        'face_detected': False,
        'face_info': None
    }
    
    try:
        # Проверка размера файла
        if file_size is None:
            file_size = len(image_bytes)
        
        if file_size < MIN_FILE_SIZE:
            result['valid'] = False
            result['error'] = f"Файл слишком маленький ({file_size} байт). Минимальный размер: {MIN_FILE_SIZE} байт (1 KB)."
            return result
        
        if file_size > MAX_FILE_SIZE:
            result['valid'] = False
            result['error'] = f"Файл слишком большой ({file_size / 1024 / 1024:.2f} MB). Максимальный размер: {MAX_FILE_SIZE / 1024 / 1024:.2f} MB."
            return result
        
        # Загружаем изображение для проверки разрешения
        try:
            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size
            result['image_info'] = {
                'width': width,
                'height': height,
                'format': image.format,
                'mode': image.mode,
                'file_size': file_size
            }
        except Exception as e:
            result['valid'] = False
            result['error'] = f"Не удалось открыть изображение: {str(e)}"
            return result
        
        # Проверка разрешения
        if width < MIN_RESOLUTION[0] or height < MIN_RESOLUTION[1]:
            result['valid'] = False
            result['error'] = f"Разрешение изображения слишком маленькое ({width}x{height}). Минимальное разрешение: {MIN_RESOLUTION[0]}x{MIN_RESOLUTION[1]}."
            return result
        
        if width > MAX_RESOLUTION[0] or height > MAX_RESOLUTION[1]:
            result['valid'] = False
            result['error'] = f"Разрешение изображения слишком большое ({width}x{height}). Максимальное разрешение: {MAX_RESOLUTION[0]}x{MAX_RESOLUTION[1]}."
            return result
        
        # Предупреждение о низком разрешении
        if width < RECOMMENDED_RESOLUTION[0] or height < RECOMMENDED_RESOLUTION[1]:
            result['warnings'].append(
                f"Разрешение изображения ({width}x{height}) ниже рекомендуемого ({RECOMMENDED_RESOLUTION[0]}x{RECOMMENDED_RESOLUTION[1]}). "
                "Для лучшего качества анализа рекомендуется использовать изображения с более высоким разрешением."
            )
        
        # Детекция лица
        face_detected, face_info = detect_face_opencv(image_bytes)
        result['face_detected'] = face_detected
        result['face_info'] = face_info
        
        if require_face and not face_detected:
            result['valid'] = False
            result['error'] = "На изображении не обнаружено лицо. Пожалуйста, загрузите фотографию лица."
            return result
        
        if not face_detected:
            result['warnings'].append("На изображении не обнаружено лицо. Результаты анализа могут быть неточными.")
        
        logger.info(f"Валидация изображения пройдена: {width}x{height}, лицо: {face_detected}")
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при валидации изображения: {e}", exc_info=True)
        result['valid'] = False
        result['error'] = f"Ошибка при валидации изображения: {str(e)}"
        return result

