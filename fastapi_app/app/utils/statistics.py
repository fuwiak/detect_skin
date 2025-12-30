"""
Утилиты для формирования статистики анализа кожи
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def format_statistics(skin_data: Dict, pixelbin_images: Optional[List[Dict]] = None) -> Dict:
    """
    Формирует числовые показатели (проценты) для каждого параметра кожи.
    
    Возвращает словарь с показателями в формате:
    {
        "acne": 0,
        "pigmentation": 0,
        "pores": 0,
        "wrinkles": 0,
        "skin_tone": 0,
        "texture": 0,
        "hydration": 0,
        "oiliness": 0,
        ...
    }
    """
    statistics = {}
    
    # Маппинг полей из skin_data в названия для статистики
    field_mapping = {
        'acne_score': 'acne',
        'pigmentation_score': 'pigmentation',
        'pores_size': 'pores',
        'wrinkles_grade': 'wrinkles',
        'skin_tone': 'skin_tone',
        'texture_score': 'texture',
        'moisture_level': 'hydration',
        'oiliness': 'oiliness',
    }
    
    # Извлекаем основные показатели из skin_data
    for field, stat_name in field_mapping.items():
        value = skin_data.get(field, 0)
        # Округляем до целого числа (процент)
        statistics[stat_name] = round(float(value)) if value is not None else 0
    
    # Если есть pixelbin_images, извлекаем concerns из них
    if pixelbin_images:
        for img in pixelbin_images:
            # Из Pixelbin response
            if img.get('type') == 'pixelbin' and 'pixelbin_data' in img:
                pixelbin_data = img.get('pixelbin_data', {})
                output = pixelbin_data.get('output', {})
                skin_data_pb = output.get('skinData', {})
                concerns = skin_data_pb.get('concerns', [])
                
                # Добавляем concerns в статистику
                for concern in concerns:
                    tech_name = concern.get('tech_name', '').lower()
                    value = concern.get('value', 0)
                    name = concern.get('name', '')
                    
                    # Маппинг названий concerns на стандартные названия
                    concern_mapping = {
                        'acne': 'acne',
                        'pimples': 'acne',
                        'pustules': 'acne',
                        'papules': 'acne',
                        'whiteheads': 'whiteheads',
                        'blackheads': 'blackheads',
                        'comedones': 'comedones',
                        'pigmentation': 'pigmentation',
                        'freckles': 'freckles',
                        'wrinkles': 'wrinkles',
                        'fine_lines': 'wrinkles',
                        'pores': 'pores',
                        'large_pores': 'pores',
                        'hydration': 'hydration',
                        'moisture': 'hydration',
                        'dark_circles': 'dark_circles',
                        'eye_bags': 'eye_bags',
                        'post_acne_scars': 'post_acne_scars',
                        'acne_scars': 'post_acne_scars',
                        'scars': 'scars',
                        'skin_tone': 'skin_tone',
                        'texture': 'texture',
                        'excess_oil': 'oiliness',
                        'oiliness': 'oiliness',
                        'sensitivity': 'sensitivity',
                        'edema': 'edema',
                    }
                    
                    # Ищем соответствие
                    mapped_name = None
                    for key, mapped in concern_mapping.items():
                        if key in tech_name or key in name.lower():
                            mapped_name = mapped
                            break
                    
                    if mapped_name:
                        # Обновляем статистику, если значение больше текущего
                        current_value = statistics.get(mapped_name, 0)
                        if value > current_value:
                            statistics[mapped_name] = round(float(value))
                    else:
                        # Добавляем как есть, если нет маппинга
                        stat_key = tech_name.replace(' ', '_').replace('-', '_')
                        if stat_key:
                            statistics[stat_key] = round(float(value))
            
            # Из SAM3 результатов
            elif img.get('type') == 'sam3' and 'sam3_results' in img:
                sam3_results = img.get('sam3_results', {})
                # SAM3 возвращает маски, но не проценты напрямую
                # Можно добавить логику для подсчета покрытия масок
                for disease_key, masks in sam3_results.items():
                    if masks and len(masks) > 0:
                        # Если есть маски, это означает наличие проблемы
                        # Можно установить базовое значение или вычислить покрытие
                        disease_mapping = {
                            'pimples': 'acne',
                            'pustules': 'acne',
                            'papules': 'acne',
                            'acne': 'acne',
                            'whiteheads': 'whiteheads',
                            'blackheads': 'blackheads',
                            'comedones': 'comedones',
                            'pigmentation': 'pigmentation',
                            'freckles': 'freckles',
                            'wrinkles': 'wrinkles',
                            'fine_lines': 'wrinkles',
                            'pores': 'pores',
                            'large_pores': 'pores',
                        }
                        
                        mapped_name = disease_mapping.get(disease_key, disease_key)
                        # Если есть маски, устанавливаем минимальное значение
                        if mapped_name not in statistics or statistics[mapped_name] == 0:
                            statistics[mapped_name] = 10  # Минимальное значение при наличии масок
    
    # Убеждаемся, что все основные поля присутствуют
    default_fields = ['acne', 'pigmentation', 'pores', 'wrinkles', 'skin_tone', 'texture', 'hydration', 'oiliness']
    for field in default_fields:
        if field not in statistics:
            statistics[field] = 0
    
    # Сортируем статистику: сначала основные поля, потом остальные
    sorted_stats = {}
    for field in default_fields:
        if field in statistics:
            sorted_stats[field] = statistics[field]
    
    # Добавляем остальные поля
    for key, value in statistics.items():
        if key not in sorted_stats:
            sorted_stats[key] = value
    
    logger.info(f"📊 Сформирована статистика: {len(sorted_stats)} показателей")
    
    return sorted_stats


def format_statistics_detailed(skin_data: Dict, pixelbin_images: Optional[List[Dict]] = None) -> Dict:
    """
    Формирует детальную статистику с разделением на категории.
    
    Возвращает:
    {
        "indicators": {
            "acne": 0,
            "pigmentation": 0,
            ...
        },
        "problems": [
            {"name": "Acne", "value": 100},
            {"name": "Pores", "value": 100},
            ...
        ]
    }
    """
    statistics = format_statistics(skin_data, pixelbin_images)
    
    # Основные показатели (всегда присутствуют)
    indicators = {
        'acne': statistics.get('acne', 0),
        'pigmentation': statistics.get('pigmentation', 0),
        'pores': statistics.get('pores', 0),
        'wrinkles': statistics.get('wrinkles', 0),
        'skin_tone': statistics.get('skin_tone', 0),
        'texture': statistics.get('texture', 0),
        'hydration': statistics.get('hydration', 0),
        'oiliness': statistics.get('oiliness', 0),
    }
    
    # Проблемы (только те, где value > 0)
    problems = []
    problem_names = {
        'acne': 'Acne',
        'pigmentation': 'Pigmentation',
        'pores': 'Pores',
        'wrinkles': 'Wrinkles',
        'whiteheads': 'Whiteheads',
        'blackheads': 'Blackheads',
        'comedones': 'Comedones',
        'freckles': 'Freckles',
        'dark_circles': 'Dark circles',
        'eye_bags': 'Eye_bags',
        'post_acne_scars': 'Post Acne Scars',
        'scars': 'Scars',
        'sensitivity': 'Sensitivity',
        'edema': 'Edema',
    }
    
    for key, value in statistics.items():
        if value > 0 and key in problem_names:
            problems.append({
                'name': problem_names[key],
                'value': value
            })
    
    # Сортируем проблемы по значению (от большего к меньшему)
    problems.sort(key=lambda x: x['value'], reverse=True)
    
    return {
        'indicators': indicators,
        'problems': problems
    }

