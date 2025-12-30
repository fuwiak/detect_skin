"""
Утилиты для комбинирования результатов из разных источников анализа
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def combine_skin_data(sources: List[Dict[str, Dict]]) -> Dict:
    """
    Комбинирует данные из разных источников анализа.
    
    Args:
        sources: Список словарей вида [{"source": "pixelbin", "data": {...}}, ...]
    
    Returns:
        Объединённый словарь с данными анализа
    """
    combined = {}
    
    # Приоритет источников (чем выше, тем больше приоритет)
    source_priority = {
        'pixelbin': 3,
        'sam3': 2,
        'openrouter': 1,
        'fallback': 0
    }
    
    # Сортируем источники по приоритету
    sorted_sources = sorted(sources, key=lambda x: source_priority.get(x.get('source', ''), -1), reverse=True)
    
    # Маппинг полей
    field_mapping = {
        'acne_score': 'acne_score',
        'pigmentation_score': 'pigmentation_score',
        'pores_size': 'pores_size',
        'wrinkles_grade': 'wrinkles_grade',
        'skin_tone': 'skin_tone',
        'texture_score': 'texture_score',
        'moisture_level': 'moisture_level',
        'oiliness': 'oiliness',
        'gender': 'gender',
        'estimated_age': 'estimated_age',
    }
    
    # Объединяем данные, приоритет отдаём более приоритетным источникам
    for source_info in sorted_sources:
        source = source_info.get('source', '')
        data = source_info.get('data', {})
        
        if not data:
            continue
        
        logger.debug(f"Комбинируем данные из {source}")
        
        # Обновляем значения, если их ещё нет или они равны 0
        for field, mapped_field in field_mapping.items():
            if mapped_field in data and data[mapped_field] is not None:
                current_value = combined.get(field, 0)
                new_value = data[mapped_field]
                
                # Если текущее значение 0 или отсутствует, используем новое
                if current_value == 0 or current_value is None:
                    combined[field] = new_value
                # Если новое значение больше, обновляем (приоритет более точным данным)
                elif new_value > current_value:
                    combined[field] = new_value
        
        # Сохраняем bounding boxes, если есть
        if '_bounding_boxes' in data:
            if '_bounding_boxes' not in combined:
                combined['_bounding_boxes'] = {}
            combined['_bounding_boxes'].update(data['_bounding_boxes'])
    
    # Убеждаемся, что все основные поля присутствуют
    for field in field_mapping.keys():
        if field not in combined:
            combined[field] = 0 if field not in ['gender', 'estimated_age'] else None
    
    logger.info(f"✅ Объединены данные из {len(sorted_sources)} источников")
    
    return combined


def extract_statistics_from_sam3_results(sam3_results: Dict, requested_diseases: Optional[List[str]] = None) -> Dict:
    """
    Извлекает статистику из результатов SAM3.
    
    Args:
        sam3_results: Результаты SAM3 (словарь {disease_key: [masks]})
        requested_diseases: Список запрошенных заболеваний
    
    Returns:
        Словарь со статистикой для каждого заболевания
    """
    statistics = {}
    
    # Маппинг заболеваний на стандартные названия
    disease_mapping = {
        'pimples': 'acne',
        'pustules': 'acne',
        'papules': 'acne',
        'acne': 'acne',
        'whiteheads': 'whiteheads',
        'blackheads': 'blackheads',
        'comedones': 'comedones',
        'rosacea': 'rosacea',
        'irritation': 'irritation',
        'pigmentation': 'pigmentation',
        'freckles': 'freckles',
        'wrinkles': 'wrinkles',
        'fine_lines': 'wrinkles',
        'skin_lesion': 'skin_lesion',
        'scars': 'scars',
        'acne_scars': 'post_acne_scars',
        'post_acne_marks': 'post_acne_scars',
        'hydration': 'hydration',
        'moisture': 'hydration',
        'pores': 'pores',
        'large_pores': 'pores',
        'eye_bags': 'eye_bags',
        'dark_circles': 'dark_circles',
        'texture': 'texture',
        'skin_tone': 'skin_tone',
        'excess_oil': 'oiliness',
        'oiliness': 'oiliness',
        'sensitivity': 'sensitivity',
        'edema': 'edema',
        'moles': 'moles',
        'warts': 'warts',
        'papillomas': 'papillomas',
        'skin_tags': 'skin_tags',
    }
    
    # Обрабатываем результаты SAM3
    for disease_key, masks in sam3_results.items():
        if masks and len(masks) > 0:
            # Вычисляем покрытие (процент изображения, покрытый масками)
            # Упрощённая версия: если есть маски, устанавливаем значение на основе количества масок
            mask_count = len(masks)
            
            # Базовое значение зависит от количества масок
            if mask_count == 1:
                value = 20
            elif mask_count <= 3:
                value = 40
            elif mask_count <= 5:
                value = 60
            elif mask_count <= 10:
                value = 80
            else:
                value = 100
            
            # Маппим название заболевания
            mapped_name = disease_mapping.get(disease_key, disease_key)
            statistics[mapped_name] = value
    
    # Добавляем запрошенные заболевания, для которых нет результатов (0%)
    if requested_diseases:
        for disease in requested_diseases:
            mapped_name = disease_mapping.get(disease, disease)
            if mapped_name not in statistics:
                statistics[mapped_name] = 0
    
    return statistics


def extract_statistics_from_pixelbin(pixelbin_data: Dict) -> Dict:
    """
    Извлекает статистику из ответа Pixelbin.
    
    Args:
        pixelbin_data: Данные от Pixelbin API
    
    Returns:
        Словарь со статистикой
    """
    statistics = {}
    
    if not pixelbin_data or 'output' not in pixelbin_data:
        return statistics
    
    output = pixelbin_data.get('output', {})
    skin_data = output.get('skinData', {})
    concerns = skin_data.get('concerns', [])
    
    # Маппинг concerns на стандартные названия
    concern_mapping = {
        'acne': 'acne',
        'pimples': 'acne',
        'pustules': 'acne',
        'papules': 'acne',
        'whiteheads': 'whiteheads',
        'blackheads': 'blackheads',
        'comedones': 'comedones',
        'rosacea': 'rosacea',
        'irritation': 'irritation',
        'pigmentation': 'pigmentation',
        'freckles': 'freckles',
        'wrinkles': 'wrinkles',
        'fine_lines': 'wrinkles',
        'skin_lesion': 'skin_lesion',
        'scars': 'scars',
        'post_acne_scars': 'post_acne_scars',
        'acne_scars': 'post_acne_scars',
        'hydration': 'hydration',
        'moisture': 'hydration',
        'pores': 'pores',
        'large_pores': 'pores',
        'eye_bags': 'eye_bags',
        'dark_circles': 'dark_circles',
        'texture': 'texture',
        'skin_tone': 'skin_tone',
        'excess_oil': 'oiliness',
        'oiliness': 'oiliness',
        'sensitivity': 'sensitivity',
        'edema': 'edema',
    }
    
    for concern in concerns:
        tech_name = concern.get('tech_name', '').lower()
        value = concern.get('value', 0)
        name = concern.get('name', '')
        
        # Ищем соответствие
        mapped_name = None
        for key, mapped in concern_mapping.items():
            if key in tech_name or key in name.lower():
                mapped_name = mapped
                break
        
        if mapped_name:
            # Обновляем, если значение больше текущего
            current_value = statistics.get(mapped_name, 0)
            if value > current_value:
                statistics[mapped_name] = round(float(value))
        else:
            # Добавляем как есть
            stat_key = tech_name.replace(' ', '_').replace('-', '_')
            if stat_key:
                statistics[stat_key] = round(float(value))
    
    return statistics

