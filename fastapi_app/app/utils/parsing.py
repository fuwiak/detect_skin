"""
Утилиты для парсинга ответов LLM и обработки данных
"""
import json
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def parse_skin_analysis_from_text(text: str) -> Dict:
    """Парсинг анализа из текстового ответа"""
    result = {}
    
    patterns = {
        "acne_score": r"acne[_\s]?score[:\s]+(\d+\.?\d*)",
        "pigmentation_score": r"pigmentation[_\s]?score[:\s]+(\d+\.?\d*)",
        "pores_size": r"pores[_\s]?size[:\s]+(\d+\.?\d*)",
        "wrinkles_grade": r"wrinkles[_\s]?grade[:\s]+(\d+\.?\d*)",
        "skin_tone": r"skin[_\s]?tone[:\s]+(\d+\.?\d*)",
        "texture_score": r"texture[_\s]?score[:\s]+(\d+\.?\d*)",
        "moisture_level": r"moisture[_\s]?level[:\s]+(\d+\.?\d*)",
        "oiliness": r"oiliness[:\s]+(\d+\.?\d*)"
    }
    
    text_lower = text.lower()
    for key, pattern in patterns.items():
        match = re.search(pattern, text_lower)
        if match:
            try:
                result[key] = float(match.group(1))
            except:
                result[key] = 0.0
        else:
            result[key] = 0.0
    
    return result


def parse_report_locations(report_text: str) -> Dict[str, List[str]]:
    """Парсит текстовый отчёт для извлечения локализации проблем"""
    locations = {}
    
    # Ищем секцию "Локализация проблем" или похожую
    location_section = re.search(r'Локализация проблем[:\-]?\s*(.*?)(?:\n\n|\Z)', report_text, re.IGNORECASE | re.DOTALL)
    if not location_section:
        # Ищем упоминания зон в тексте
        location_section = re.search(r'(?:Локализация|расположение|находятся|в зоне|область)[:\-]?\s*(.*?)(?:\n\n|\Z)', report_text, re.IGNORECASE | re.DOTALL)
    
    if location_section:
        location_text = location_section.group(1)
        
        # Извлекаем упоминания различных зон
        zones_keywords = {
            'pigmentation': ['щёки', 'щеки', 'cheeks', 'пигмент', 'пятна'],
            'wrinkles': ['периорбитальная', 'периоральная', 'вокруг глаз', 'вокруг рта', 'лоб', 'forehead'],
            'pores': ['т-зона', 't-zone', 'нос', 'nose', 'щёки', 'щеки'],
            'acne': ['т-зона', 't-zone', 'щёки', 'щеки', 'подбородок', 'chin']
        }
        
        for concern_type, keywords in zones_keywords.items():
            found_zones = []
            for keyword in keywords:
                if keyword.lower() in location_text.lower():
                    found_zones.append(keyword)
            if found_zones:
                locations[concern_type] = found_zones
    
    # Также ищем упоминания в основном тексте
    if 'пигмент' in report_text.lower() or 'пятна' in report_text.lower():
        if 'щёки' in report_text.lower() or 'щеки' in report_text.lower():
            if 'pigmentation' not in locations:
                locations['pigmentation'] = ['щёки']
    
    if 'морщин' in report_text.lower() or 'wrinkles' in report_text.lower():
        if 'периорбитальная' in report_text.lower() or 'вокруг глаз' in report_text.lower():
            if 'wrinkles' not in locations:
                locations['wrinkles'] = ['периорбитальная']
        if 'периоральная' in report_text.lower() or 'вокруг рта' in report_text.lower():
            if 'wrinkles' in locations:
                locations['wrinkles'].append('периоральная')
            else:
                locations['wrinkles'] = ['периоральная']
    
    return locations


def convert_bbox_to_position(bbox: List[float], image_width: int = 1000, image_height: int = 1000) -> Dict:
    """Конвертирует bounding box [y_min, x_min, y_max, x_max] в позицию для маркера"""
    y_min, x_min, y_max, x_max = bbox
    
    # Нормализуем координаты к процентам (0-100)
    x_center = ((x_min + x_max) / 2) / 10  # 0-1000 -> 0-100
    y_center = ((y_min + y_max) / 2) / 10
    width = (x_max - x_min) / 10
    height = (y_max - y_min) / 10
    
    return {
        'x': x_center,
        'y': y_center,
        'width': width,
        'height': height
    }










