"""
Сервис для эвристической сегментации
"""
import sys
import os
import logging
from typing import Dict, List, Optional

# Добавляем родительскую директорию в sys.path для импорта модулей сегментации
# __file__ = fastapi_app/app/services/segmentation_service.py
# Нужно получить /Users/user/detect_skin
services_dir = os.path.dirname(__file__)  # fastapi_app/app/services
app_dir = os.path.dirname(services_dir)  # fastapi_app/app
fastapi_dir = os.path.dirname(app_dir)  # fastapi_app
project_root = os.path.dirname(fastapi_dir)  # detect_skin
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.dependencies import SEGMENTATION_AVAILABLE, HF_SEGMENTATION_AVAILABLE
from app.config import settings
from app.utils.parsing import parse_report_locations, convert_bbox_to_position
from app.utils.image_utils import segment_face_area

logger = logging.getLogger(__name__)

# Импортируем модули сегментации если доступны
if SEGMENTATION_AVAILABLE:
    try:
        from skin_segmentation import get_segmenter
    except ImportError:
        get_segmenter = None

if HF_SEGMENTATION_AVAILABLE:
    try:
        from hf_segmentation import get_hf_segmenter
    except ImportError:
        get_hf_segmenter = None


def generate_heuristic_analysis(skin_data: Dict, report_text: str = None, image_bytes: Optional[bytes] = None) -> Dict:
    """
    Генерирует эвристический анализ на основе данных OpenRouter и текстового отчёта
    Использует приоритет методов: HF сегментация > обычная сегментация > bounding boxes > простые эвристики
    """
    concerns = []
    methods_used = []  # Отслеживаем использованные методы
    
    # Получаем bounding boxes, если они есть
    bounding_boxes = skin_data.get('_bounding_boxes', {})
    
    # Словарь для хранения маркеров от разных методов сегментации
    hf_markers = {}
    segmentation_markers = {}
    
    # ПРИОРИТЕТ 1: Hugging Face сегментация (самая точная)
    if HF_SEGMENTATION_AVAILABLE and image_bytes and get_hf_segmenter:
        try:
            hf_token = settings.hf_token
            hf_segmenter = get_hf_segmenter(hf_token)
            hf_results = hf_segmenter.segment_image(image_bytes)
            
            if hf_results and hf_results.get('method') == 'hf_segmentation':
                logger.info("✅ Использована Hugging Face сегментация")
                methods_used.append("Hugging Face сегментация")
                
                # Извлекаем маркеры для каждого типа дефекта
                hf_markers = {
                    'acne': hf_results.get('acne', []),
                    'pigmentation': hf_results.get('pigmentation', []),
                    'wrinkles': hf_results.get('wrinkles', []),
                    'papillomas': hf_results.get('papillomas', [])
                }
        except Exception as e:
            logger.warning(f"Ошибка при HF сегментации: {e}")
    
    # ПРИОРИТЕТ 2: Обычная сегментация (MobileNetV2+UNet)
    if not hf_markers and SEGMENTATION_AVAILABLE and image_bytes and get_segmenter:
        try:
            segmenter = get_segmenter()
            segmentation_results = segmenter.segment_image(image_bytes)
            logger.info("✅ Использована обычная сегментация (MobileNetV2+UNet)")
            methods_used.append("Сегментация MobileNetV2+UNet")
            
            # Добавляем результаты сегментации в bounding_boxes
            if segmentation_results:
                if 'wrinkles' in segmentation_results and segmentation_results['wrinkles']:
                    if 'wrinkles' not in bounding_boxes:
                        bounding_boxes['wrinkles'] = []
                    for wrinkle in segmentation_results['wrinkles']:
                        if wrinkle.get('confidence', 0) > 0.3:
                            bounding_boxes['wrinkles'].append(wrinkle['bbox'])
                
                if 'pigmentation' in segmentation_results and segmentation_results['pigmentation']:
                    if 'pigmentation' not in bounding_boxes:
                        bounding_boxes['pigmentation'] = []
                    for pig in segmentation_results['pigmentation']:
                        if pig.get('confidence', 0) > 0.2:
                            bounding_boxes['pigmentation'].append(pig['bbox'])
        except Exception as e:
            logger.warning(f"Ошибка при сегментации: {e}")
    
    # ПРИОРИТЕТ 3: Bounding boxes из LLM (Gemini/GPT-4o Vision)
    if bounding_boxes:
        logger.info("✅ Использованы bounding boxes из LLM")
        methods_used.append("Bounding boxes (LLM)")
    
    # Парсим локализацию из отчёта, если он есть
    report_locations = {}
    if report_text:
        report_locations = parse_report_locations(report_text)
    
    # Определяем проблемы на основе значений с сегментацией
    # (Упрощенная версия - полная версия в app.py очень большая)
    
    # Акне
    if skin_data.get('acne_score', 0) > 30:
        acne_value = skin_data.get('acne_score', 0)
        
        if hf_markers.get('acne'):
            # Используем точные маркеры из HF сегментации
            for marker in hf_markers['acne']:
                concerns.append({
                    'name': 'Акне',
                    'tech_name': 'acne',
                    'value': marker.get('value', acne_value),
                    'severity': 'Needs Attention' if acne_value > 60 else 'Average',
                    'description': f'Обнаружены признаки акне. Рекомендуется консультация дерматолога.',
                    'area': 'face',
                    'position': {
                        'x': marker['x'],
                        'y': marker['y'],
                        'width': marker['width'],
                        'height': marker['height'],
                        'shape': marker.get('shape', 'polygon'),
                        'type': 'area'
                    },
                    'is_area': True
                })
        elif 'acne' in bounding_boxes and bounding_boxes['acne']:
            # Используем координаты из bounding boxes
            for bbox in bounding_boxes['acne']:
                position = convert_bbox_to_position(bbox)
                concerns.append({
                    'name': 'Акне',
                    'tech_name': 'acne',
                    'value': acne_value,
                    'severity': 'Needs Attention' if acne_value > 60 else 'Average',
                    'description': f'Обнаружены признаки акне. Рекомендуется консультация дерматолога.',
                    'area': 'face',
                    'position': {**position, 'type': 'point'}
                })
        else:
            # Простые эвристики
            if not methods_used:
                methods_used.append("Простые эвристики")
            position = segment_face_area('acne', acne_value)
            concerns.append({
                'name': 'Акне',
                'tech_name': 'acne',
                'value': acne_value,
                'severity': 'Needs Attention' if acne_value > 60 else 'Average',
                'description': f'Обнаружены признаки акне. Рекомендуется консультация дерматолога.',
                'area': 'face',
                'position': position
            })
    
    # Пигментация
    if skin_data.get('pigmentation_score', 0) > 40:
        pigmentation_value = skin_data.get('pigmentation_score', 0)
        
        if hf_markers.get('pigmentation'):
            for marker in hf_markers['pigmentation']:
                concerns.append({
                    'name': 'Пигментация',
                    'tech_name': 'pigmentation',
                    'value': marker.get('value', pigmentation_value),
                    'severity': 'Needs Attention' if pigmentation_value > 70 else 'Average',
                    'description': f'Замечены участки пигментации. Используйте солнцезащитный крем.',
                    'area': 'face',
                    'position': {
                        'x': marker['x'],
                        'y': marker['y'],
                        'width': marker.get('width', 2),
                        'height': marker.get('height', 2),
                        'shape': 'dot',
                        'type': 'point',
                        'marker_type': 'dot'
                    },
                    'is_dot': True
                })
        elif 'pigmentation' in bounding_boxes and bounding_boxes['pigmentation']:
            for bbox in bounding_boxes['pigmentation']:
                position = convert_bbox_to_position(bbox)
                concerns.append({
                    'name': 'Пигментация',
                    'tech_name': 'pigmentation',
                    'value': pigmentation_value,
                    'severity': 'Needs Attention' if pigmentation_value > 70 else 'Average',
                    'description': f'Замечены участки пигментации. Используйте солнцезащитный крем.',
                    'area': 'face',
                    'position': {**position, 'type': 'point', 'marker_type': 'dot'},
                    'is_dot': True
                })
        else:
            if not methods_used:
                methods_used.append("Простые эвристики")
            position = segment_face_area('pigmentation', pigmentation_value)
            concerns.append({
                'name': 'Пигментация',
                'tech_name': 'pigmentation',
                'value': pigmentation_value,
                'severity': 'Needs Attention' if pigmentation_value > 70 else 'Average',
                'description': f'Замечены участки пигментации. Используйте солнцезащитный крем.',
                'area': 'face',
                'position': {**position, 'type': 'point', 'marker_type': 'dot'},
                'is_dot': True
            })
    
    # Морщины
    if skin_data.get('wrinkles_grade', 0) > 40:
        wrinkles_value = skin_data.get('wrinkles_grade', 0)
        
        if hf_markers.get('wrinkles'):
            for marker in hf_markers['wrinkles']:
                concerns.append({
                    'name': 'Морщины',
                    'tech_name': 'wrinkles',
                    'value': marker.get('value', wrinkles_value),
                    'severity': 'Needs Attention' if wrinkles_value > 60 else 'Average',
                    'description': f'Замечены морщины. Увлажнение и защита от солнца помогут.',
                    'area': 'face',
                    'position': {
                        'x': marker['x'],
                        'y': marker['y'],
                        'width': marker['width'],
                        'height': marker['height'],
                        'shape': marker.get('shape', 'wrinkle'),
                        'type': 'area',
                        'is_wrinkle': True
                    },
                    'is_area': True
                })
        elif 'wrinkles' in bounding_boxes and bounding_boxes['wrinkles']:
            for bbox in bounding_boxes['wrinkles']:
                position = convert_bbox_to_position(bbox)
                concerns.append({
                    'name': 'Морщины',
                    'tech_name': 'wrinkles',
                    'value': wrinkles_value,
                    'severity': 'Needs Attention' if wrinkles_value > 60 else 'Average',
                    'description': f'Замечены морщины. Увлажнение и защита от солнца помогут.',
                    'area': 'face',
                    'position': {**position, 'type': 'area', 'shape': 'wrinkle', 'is_wrinkle': True},
                    'is_area': True
                })
        else:
            if not methods_used:
                methods_used.append("Простые эвристики")
            position = segment_face_area('wrinkles', wrinkles_value)
            concerns.append({
                'name': 'Морщины',
                'tech_name': 'wrinkles',
                'value': wrinkles_value,
                'severity': 'Needs Attention' if wrinkles_value > 60 else 'Average',
                'description': f'Замечены признаки старения. Увлажнение и защита от солнца помогут.',
                'area': 'face',
                'position': {**position, 'type': 'area', 'shape': position.get('shape', 'ellipse')},
                'is_area': True
            })
    
    # Генерируем общий текст
    total_score = sum([
        skin_data.get('acne_score', 0),
        skin_data.get('pigmentation_score', 0),
        skin_data.get('pores_size', 0),
        skin_data.get('wrinkles_grade', 0)
    ]) / 4
    
    if total_score < 40:
        summary = "Состояние кожи хорошее. Рекомендуется поддерживать текущий уход."
    elif total_score < 60:
        summary = "Состояние кожи удовлетворительное. Некоторые области требуют внимания."
    else:
        summary = "Обнаружены проблемы, требующие внимания. Рекомендуется консультация специалиста."
    
    # Определяем основной метод (самый точный из использованных)
    primary_method = methods_used[0] if methods_used else "Простые эвристики"
    
    return {
        'concerns': concerns,
        'summary': summary,
        'total_skin_score': max(0, min(100, 100 - total_score)),
        'skin_health': 'Good' if total_score < 40 else 'Average' if total_score < 60 else 'Needs Attention',
        'methods_used': methods_used,
        'primary_method': primary_method
    }

