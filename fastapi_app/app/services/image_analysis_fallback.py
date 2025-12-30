"""
Fallback анализ изображения без LLM
Используется, когда OpenRouter недоступен или возвращает некорректные данные
"""
import logging
import numpy as np
from typing import Dict, Optional
from PIL import Image
import io

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV недоступен, fallback анализ будет ограничен")


def analyze_image_fallback(image_bytes: bytes) -> Dict:
    """
    Базовый анализ изображения без LLM
    Использует компьютерное зрение для определения базовых параметров кожи
    """
    logger.info("🔄 Запуск fallback анализа изображения (без LLM)")
    
    try:
        # Загружаем изображение
        img = Image.open(io.BytesIO(image_bytes))
        img_rgb = img.convert('RGB')
        width, height = img_rgb.size
        
        # Конвертируем в numpy array для анализа
        img_array = np.array(img_rgb)
        
        # Базовые значения (консервативные оценки)
        result = {
            'acne_score': 0.0,
            'pigmentation_score': 0.0,
            'pores_size': 0.0,
            'wrinkles_grade': 0.0,
            'skin_tone': 50.0,  # Средний тон
            'texture_score': 50.0,  # Средняя текстура
            'moisture_level': 50.0,  # Средняя увлажненность
            'oiliness': 50.0,  # Средняя жирность
            'gender': None,
            'estimated_age': None
        }
        
        if CV2_AVAILABLE:
            # Анализ с OpenCV
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Анализ текстуры (вариация яркости)
            texture_variance = np.var(gray)
            if texture_variance > 500:
                result['texture_score'] = min(100, texture_variance / 10)
            else:
                result['texture_score'] = max(0, texture_variance / 5)
            
            # Анализ тона кожи (средняя яркость)
            mean_brightness = np.mean(gray)
            result['skin_tone'] = (mean_brightness / 255.0) * 100
            
            # Детекция контуров для оценки пор и текстуры
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (width * height)
            result['pores_size'] = min(100, edge_density * 1000)
            
            # Анализ вариации цвета для пигментации
            hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
            saturation_variance = np.var(hsv[:, :, 1])
            result['pigmentation_score'] = min(100, saturation_variance / 2)
            
            logger.info(f"✅ Fallback анализ завершён (OpenCV)")
        else:
            # Простой анализ без OpenCV
            # Анализ яркости
            mean_brightness = np.mean(img_array)
            result['skin_tone'] = (mean_brightness / 255.0) * 100
            
            # Анализ вариации (текстура)
            variance = np.var(img_array)
            result['texture_score'] = min(100, variance / 100)
            
            logger.info(f"✅ Fallback анализ завершён (базовый)")
        
        logger.info(f"📊 Результаты fallback анализа:")
        logger.info(f"   Acne: {result['acne_score']:.1f}")
        logger.info(f"   Pigmentation: {result['pigmentation_score']:.1f}")
        logger.info(f"   Pores: {result['pores_size']:.1f}")
        logger.info(f"   Wrinkles: {result['wrinkles_grade']:.1f}")
        logger.info(f"   Skin tone: {result['skin_tone']:.1f}")
        logger.info(f"   Texture: {result['texture_score']:.1f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка при fallback анализе: {e}", exc_info=True)
        # Возвращаем минимальные значения
        return {
            'acne_score': 0.0,
            'pigmentation_score': 0.0,
            'pores_size': 0.0,
            'wrinkles_grade': 0.0,
            'skin_tone': 50.0,
            'texture_score': 50.0,
            'moisture_level': 50.0,
            'oiliness': 50.0,
            'gender': None,
            'estimated_age': None
        }

