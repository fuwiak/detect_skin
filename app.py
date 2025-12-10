#!/usr/bin/env python3
"""
Backend сервис для анализа состояния кожи
"""
import os
import base64
import json
import requests
import time
import io
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from typing import Dict, Optional, List
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорт для работы с HEIC (после logger)
try:
    from PIL import Image
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
    logger.info("Поддержка HEIC включена")
except ImportError:
    HEIC_SUPPORT = False
    logger.warning("pillow-heif не установлен, поддержка HEIC будет ограничена")

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Конфигурация API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")

# Конфигурация Pixelbin API
PIXELBIN_ACCESS_TOKEN = os.getenv("PIXELBIN_ACCESS_TOKEN")
PIXELBIN_BASE_URL = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions"
PIXELBIN_BEARER_TOKEN = base64.b64encode(PIXELBIN_ACCESS_TOKEN.encode('utf-8')).decode('utf-8') if PIXELBIN_ACCESS_TOKEN else None
PIXELBIN_HEADERS = {
    "Authorization": f"Bearer {PIXELBIN_BEARER_TOKEN}",
} if PIXELBIN_BEARER_TOKEN else {}

if not PIXELBIN_ACCESS_TOKEN:
    logger.warning("PIXELBIN_ACCESS_TOKEN не найден в переменных окружения. Функциональность Pixelbin будет недоступна.")

# Настройки моделей по умолчанию
# Порядок попыток подключения к API для детекции
# Топовые платные модели
DETECTION_FALLBACKS = [
    {"provider": "openrouter", "model": "openai/gpt-4o"},  # GPT-4o - лучшая для медицинского анализа
    {"provider": "openrouter", "model": "anthropic/claude-3.5-sonnet"},  # Claude 3.5 Sonnet - баланс качества и стоимости
    {"provider": "openrouter", "model": "google/gemini-1.5-pro"},  # Gemini 1.5 Pro - сильные возможности обработки изображений
    # Бесплатные и бюджетные варианты
    {"provider": "openrouter", "model": "google/gemini-2.0-flash-exp"},  # Gemini 2.0 Flash Experimental (бесплатная)
    {"provider": "openrouter", "model": "qwen/qwen-2-vl-72b-instruct"},  # Qwen2-VL - высокая производительность
    {"provider": "openrouter", "model": "mistralai/pixtral-large"},  # Pixtral Large - 124B параметров
    {"provider": "openrouter", "model": "x-ai/grok-4.1-fast:free"},  # Grok 4.1 Fast (бесплатная)
    {"provider": "openrouter", "model": "google/gemini-2.0-flash-001"}  # Google Gemini 2.0 Flash
]

# Настройки моделей по умолчанию
DEFAULT_VISION_MODEL = "google/gemini-2.0-flash-001"  # Для детекции
DEFAULT_TEXT_MODEL = "anthropic/claude-3.5-sonnet"  # Для генерации отчёта

DEFAULT_CONFIG = {
    "detection_provider": "openrouter",
    "llm_provider": "openrouter",
    "vision_model": DEFAULT_VISION_MODEL,
    "text_model": DEFAULT_TEXT_MODEL,
    "temperature": 0,  # Точность важнее креативности
    "max_tokens": 300  # Краткие и лаконичные ответы
}


class PixelBinService:
    """Сервис для работы с Pixelbin API"""
    
    @staticmethod
    def upload_image(image_data: bytes, filename: str = "image.jpg") -> Optional[Dict]:
        """Загрузка изображения в Pixelbin API"""
        if not PIXELBIN_ACCESS_TOKEN:
            logger.warning("Pixelbin: ACCESS_TOKEN не настроен, пропускаем загрузку")
            return None
        
        try:
            url = f"{PIXELBIN_BASE_URL}/skinAnalysisInt/generate"
            
            # Определяем MIME тип на основе расширения
            mime_type = 'image/png' if filename.lower().endswith('.png') else 'image/jpeg'
            
            files = {
                'input.image': (filename, image_data, mime_type)
            }
            
            logger.info(f"Отправка изображения в Pixelbin API: {filename} ({len(image_data)} bytes)")
            response = requests.post(url, headers=PIXELBIN_HEADERS, files=files, timeout=60)
            
            if not response.ok:
                error_text = response.text[:500]
                logger.warning(f"Pixelbin API ошибка: {response.status_code} - {error_text}")
                # Если это ошибка валидации (400), возвращаем специальный флаг
                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        if 'validation' in error_text.lower() or 'JR-0400' in error_text:
                            return {"error": "validation_failed", "status_code": 400, "message": error_data}
                    except:
                        pass
                return None
            
            result = response.json()
            logger.info(f"Pixelbin: изображение загружено, job_id: {result.get('_id')}")
            return result
            
        except Exception as e:
            logger.warning(f"Ошибка при загрузке в Pixelbin: {e}")
            return None
    
    @staticmethod
    def check_status(job_id: str, max_attempts: int = 10, delay: int = 3) -> Optional[Dict]:
        """Проверка статуса задачи в Pixelbin API"""
        if not PIXELBIN_ACCESS_TOKEN:
            logger.warning("Pixelbin: ACCESS_TOKEN не настроен, пропускаем проверку статуса")
            return None
        
        if not job_id:
            return None
        
        status_url = f"{PIXELBIN_BASE_URL}/{job_id}"
        
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(status_url, headers=PIXELBIN_HEADERS, timeout=30)
                
                if response.ok:
                    result = response.json()
                    status = result.get('status', 'UNKNOWN')
                    
                    if status == 'SUCCESS':
                        logger.info(f"Pixelbin: задача завершена успешно")
                        return result
                    elif status == 'FAILURE':
                        logger.warning(f"Pixelbin: задача завершилась с ошибкой")
                        return result
                    elif status in ['ACCEPTED', 'PREPARING', 'PROCESSING']:
                        if attempt < max_attempts:
                            logger.debug(f"Pixelbin: статус {status}, ждём {delay} секунд...")
                            time.sleep(delay)
                            continue
                        else:
                            logger.warning(f"Pixelbin: задача всё ещё обрабатывается после {max_attempts} попыток")
                            return result
                
                return result
            except Exception as e:
                logger.warning(f"Ошибка при проверке статуса Pixelbin: {e}")
                if attempt < max_attempts:
                    time.sleep(delay)
                    continue
                return None
        
        return None


def extract_images_from_pixelbin_response(pixelbin_data: Dict) -> List[Dict]:
    """Извлекает все URL изображений из ответа Pixelbin API"""
    images = []
    
    if not pixelbin_data or 'output' not in pixelbin_data:
        logger.warning("Pixelbin: нет данных output в ответе")
        return images
    
    output = pixelbin_data.get('output', {})
    skin_data = output.get('skinData', {})
    
    # Исходное изображение
    if 'input' in pixelbin_data and 'image' in pixelbin_data['input']:
        images.append({
            'url': pixelbin_data['input']['image'],
            'title': 'Исходное изображение',
            'type': 'input'
        })
    
    # Обработанное изображение
    if 'inputImage' in skin_data:
        images.append({
            'url': skin_data['inputImage'],
            'title': 'Обработанное изображение',
            'type': 'processed'
        })
    
    # Facial hair URL (если есть)
    if 'facial_hair_url' in skin_data and skin_data.get('facial_hair_url'):
        images.append({
            'url': skin_data['facial_hair_url'],
            'title': 'Facial Hair',
            'type': 'facial_hair'
        })
    
    # Зоны лица
    if 'zones' in skin_data:
        zones = skin_data['zones']
        if 't_zone' in zones and 'image' in zones['t_zone']:
            images.append({
                'url': zones['t_zone']['image'],
                'title': f'T-зона ({zones["t_zone"].get("type", "")})',
                'type': 'zone'
            })
        if 'u_zone' in zones and 'image' in zones['u_zone']:
            images.append({
                'url': zones['u_zone']['image'],
                'title': f'U-зона ({zones["u_zone"].get("type", "")})',
                'type': 'zone'
            })
    
    # Комбинированная маска
    if 'combine_masked_url' in skin_data:
        images.append({
            'url': skin_data['combine_masked_url'],
            'title': 'Комбинированная маска',
            'type': 'mask'
        })
    
    # Изображения проблем (concerns)
    if 'concerns' in skin_data:
        concerns_count = 0
        for concern in skin_data['concerns']:
            if 'image' in concern and concern.get('image'):
                images.append({
                    'url': concern['image'],
                    'title': concern.get('name', 'Проблема'),
                    'type': 'concern',
                    'concern_name': concern.get('tech_name', ''),
                    'value': concern.get('value', 0),
                    'severity': concern.get('severity', '')
                })
                concerns_count += 1
        logger.info(f"Pixelbin: извлечено {concerns_count} изображений из concerns")
    
    logger.info(f"Pixelbin: всего извлечено {len(images)} изображений")
    return images






def analyze_image_with_openrouter(image_base64: str, model: str, temperature: float, max_tokens: int) -> Optional[Dict]:
    """Анализ изображения через OpenRouter API"""
    if not OPENROUTER_API_KEY:
        logger.warning("OpenRouter API key not found")
        return None
    
    try:
        url = OPENROUTER_API_URL
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Skin Analyzer"
        }
        
        prompt = """Ты специалист по заболеваниям и дефектам кожи. Проанализируй это изображение лица и определи следующие параметры состояния кожи:

1. acne_score (0-100) - уровень акне
2. pigmentation_score (0-100) - уровень пигментации (ВАЖНО: пигментные пятна - это плоские участки изменённого цвета кожи, НЕ путай их с папилломами - выпуклыми образованиями)
3. pores_size (0-100) - размер пор
4. wrinkles_grade (0-100) - уровень морщин
5. skin_tone (0-100) - тон кожи
6. texture_score (0-100) - текстура кожи
7. moisture_level (0-100) - уровень увлажненности
8. oiliness (0-100) - жирность кожи

Верни результат в формате JSON с этими полями. Кратко и лаконично опиши проблемы, укажи в каких местах на лице они находятся и сколько их."""
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            error_text = response.text[:500]
            logger.error(f"OpenRouter API error: HTTP {response.status_code}")
            logger.error(f"Ответ сервера: {error_text}")
            try:
                error_data = response.json()
                logger.error(f"Детали ошибки: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                pass
            return None
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        try:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                skin_data = json.loads(content[json_start:json_end])
            else:
                skin_data = parse_skin_analysis_from_text(content)
        except:
            skin_data = parse_skin_analysis_from_text(content)
        
        return skin_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenRouter API error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
        return None
    except Exception as e:
        logger.error(f"OpenRouter unexpected error: {e}")
        return None




def parse_skin_analysis_from_text(text: str) -> Dict:
    """Парсинг анализа из текстового ответа"""
    import re
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


def generate_report_with_llm(skin_data: Dict, provider: str, model: str, temperature: float, language: str = 'ru') -> str:
    """Генерация текстового отчёта с помощью LLM"""
    
    if language == 'en':
        report_prompt = f"""You are a specialist in skin diseases and defects. Based on the following skin analysis data, create a brief and concise text report in English:

{json.dumps(skin_data, ensure_ascii=False, indent=2)}

The report should include:
1. A brief assessment of skin condition
2. Description of problems: Acne, Pigmentation (IMPORTANT: pigmentation spots are flat areas of changed skin color, DO NOT confuse them with papillomas - raised formations), Pore size, Wrinkles, Skin tone, Texture, Moisture, Oiliness
3. Indication of where on the face the problems are located and how many there are

The report should be brief, concise and professional."""
    else:
        report_prompt = f"""Ты специалист по заболеваниям и дефектам кожи. На основе следующих данных анализа кожи создай краткий и лаконичный текстовый отчёт на русском языке:

{json.dumps(skin_data, ensure_ascii=False, indent=2)}

Отчёт должен включать:
1. Краткую оценку состояния кожи
2. Описание проблем: Акне, Пигментация (ВАЖНО: пигментные пятна - это плоские участки изменённого цвета кожи, НЕ путай их с папилломами - выпуклыми образованиями), Размер пор, Морщины, Тон кожи, Текстура, Увлажненность, Жирность
3. Указание в каких местах на лице находятся проблемы и сколько их

Отчёт должен быть кратким, лаконичным и профессиональным."""
    
    # Пробуем через OpenRouter
    if OPENROUTER_API_KEY:
        models_to_try = [model]  # Пробуем запрошенную модель
        
        for model_to_use in models_to_try:
            try:
                url = OPENROUTER_API_URL
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "Skin Analyzer"
                }
                
                payload = {
                    "model": model_to_use,
                    "messages": [{"role": "user", "content": report_prompt}],
                    "temperature": temperature,
                    "max_tokens": 1000
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    logger.info(f"Отчёт сгенерирован через OpenRouter с моделью: {model_to_use}")
                    return content
            except Exception as e:
                logger.debug(f"Модель {model_to_use} не сработала: {e}")
                continue
    
    # Простой отчёт без LLM (если LLM недоступны)
    logger.warning("Не удалось сгенерировать отчёт через LLM, используем простой формат")
    return generate_fallback_report(skin_data)


def convert_heic_to_jpeg(image_bytes: bytes) -> bytes:
    """Конвертирует HEIC/HEIF изображение в JPEG"""
    if not HEIC_SUPPORT:
        raise ValueError("Поддержка HEIC не доступна. Установите pillow-heif.")
    
    try:
        # Открываем HEIC изображение
        image = Image.open(io.BytesIO(image_bytes))
        
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
        
        # Сохраняем в JPEG
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=95)
        return output.getvalue()
    except Exception as e:
        logger.error(f"Ошибка при конвертации HEIC: {e}")
        raise


def segment_face_area(concern_type: str, value: float) -> Dict:
    """Простой алгоритм сегментации лица для определения зон проблем"""
    # Базовые зоны лица в процентах от размера изображения
    zones = {
        'forehead': {'x': 50, 'y': 20, 'width': 40, 'height': 15},  # Лоб
        'left_cheek': {'x': 25, 'y': 45, 'width': 20, 'height': 25},  # Левая щека
        'right_cheek': {'x': 75, 'y': 45, 'width': 20, 'height': 25},  # Правая щека
        'nose': {'x': 50, 'y': 50, 'width': 15, 'height': 20},  # Нос
        'chin': {'x': 50, 'y': 75, 'width': 25, 'height': 15},  # Подбородок
        't_zone': {'x': 50, 'y': 40, 'width': 30, 'height': 30},  # Т-зона
        'u_zone': {'x': 50, 'y': 55, 'width': 50, 'height': 30},  # U-зона
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
    import random
    x_offset = random.uniform(-5, 5)
    y_offset = random.uniform(-5, 5)
    
    return {
        'x': zone['x'] + x_offset,
        'y': zone['y'] + y_offset,
        'width': zone['width'],
        'height': zone['height'],
        'zone': zone_name
    }


def generate_heuristic_analysis(skin_data: Dict) -> Dict:
    """Генерирует эвристический анализ на основе данных OpenRouter"""
    concerns = []
    
    # Определяем проблемы на основе значений с сегментацией
    if skin_data.get('acne_score', 0) > 30:
        position = segment_face_area('acne', skin_data.get('acne_score', 0))
        concerns.append({
            'name': 'Акне',
            'tech_name': 'acne',
            'value': skin_data.get('acne_score', 0),
            'severity': 'Needs Attention' if skin_data.get('acne_score', 0) > 60 else 'Average',
            'description': f'Обнаружены признаки акне. Рекомендуется консультация дерматолога.',
            'area': 'face',
            'position': position
        })
    
    if skin_data.get('pigmentation_score', 0) > 40:
        position = segment_face_area('pigmentation', skin_data.get('pigmentation_score', 0))
        concerns.append({
            'name': 'Пигментация',
            'tech_name': 'pigmentation',
            'value': skin_data.get('pigmentation_score', 0),
            'severity': 'Needs Attention' if skin_data.get('pigmentation_score', 0) > 70 else 'Average',
            'description': f'Замечены участки пигментации. Используйте солнцезащитный крем.',
            'area': 'face',
            'position': position
        })
    
    if skin_data.get('pores_size', 0) > 50:
        position = segment_face_area('pores', skin_data.get('pores_size', 0))
        concerns.append({
            'name': 'Расширенные поры',
            'tech_name': 'pores',
            'value': skin_data.get('pores_size', 0),
            'severity': 'Needs Attention' if skin_data.get('pores_size', 0) > 70 else 'Average',
            'description': f'Поры требуют внимания. Рекомендуется регулярное очищение.',
            'area': 'face',
            'position': position
        })
    
    if skin_data.get('wrinkles_grade', 0) > 40:
        position = segment_face_area('wrinkles', skin_data.get('wrinkles_grade', 0))
        concerns.append({
            'name': 'Морщины',
            'tech_name': 'wrinkles',
            'value': skin_data.get('wrinkles_grade', 0),
            'severity': 'Needs Attention' if skin_data.get('wrinkles_grade', 0) > 60 else 'Average',
            'description': f'Замечены признаки старения. Увлажнение и защита от солнца помогут.',
            'area': 'face',
            'position': position
        })
    
    if skin_data.get('moisture_level', 0) < 50:
        position = segment_face_area('hydration', skin_data.get('moisture_level', 0))
        concerns.append({
            'name': 'Недостаточное увлажнение',
            'tech_name': 'hydration',
            'value': skin_data.get('moisture_level', 0),
            'severity': 'Needs Attention' if skin_data.get('moisture_level', 0) < 30 else 'Average',
            'description': f'Кожа нуждается в дополнительном увлажнении.',
            'area': 'face',
            'position': position
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
    
    return {
        'concerns': concerns,
        'summary': summary,
        'total_skin_score': max(0, min(100, 100 - total_score)),
        'skin_health': 'Good' if total_score < 40 else 'Average' if total_score < 60 else 'Needs Attention'
    }


def generate_fallback_report(skin_data: Dict) -> str:
    """Генерация простого отчёта без LLM"""
    report = "ОТЧЁТ О СОСТОЯНИИ КОЖИ\n\n"
    report += f"Акне: {skin_data.get('acne_score', 0):.1f}%\n"
    report += f"Пигментация: {skin_data.get('pigmentation_score', 0):.1f}%\n"
    report += f"Размер пор: {skin_data.get('pores_size', 0):.1f}%\n"
    report += f"Морщины: {skin_data.get('wrinkles_grade', 0):.1f}%\n"
    report += f"Тон кожи: {skin_data.get('skin_tone', 0):.1f}%\n"
    report += f"Текстура: {skin_data.get('texture_score', 0):.1f}%\n"
    report += f"Увлажненность: {skin_data.get('moisture_level', 0):.1f}%\n"
    report += f"Жирность: {skin_data.get('oiliness', 0):.1f}%\n"
    return report


@app.route('/')
def index():
    """Главная страница"""
    return send_from_directory('.', 'index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze_skin():
    """Эндпоинт для анализа кожи"""
    try:
        data = request.json
        image_base64 = data.get('image', '')
        
        if not image_base64:
            return jsonify({"error": "Изображение не предоставлено"}), 400
        
        # Убираем префикс data:image если есть и извлекаем MIME тип
        mime_type = None
        if ',' in image_base64:
            prefix = image_base64.split(',')[0]
            image_base64 = image_base64.split(',')[1]
            # Извлекаем MIME тип из префикса
            if 'data:' in prefix and ';' in prefix:
                mime_type = prefix.split(';')[0].split(':')[1]
        
        # Получаем настройки из запроса или используем по умолчанию
        config = data.get('config', DEFAULT_CONFIG)
        detection_provider = config.get('detection_provider', 'openrouter')
        llm_provider = config.get('llm_provider', 'openrouter')
        vision_model = config.get('vision_model', DEFAULT_VISION_MODEL)
        text_model = config.get('text_model', DEFAULT_TEXT_MODEL)
        temperature = config.get('temperature', 0.7)
        max_tokens = config.get('max_tokens', 1000)
        language = config.get('language', 'ru')  # Язык для генерации отчёта
        
        # Пробуем детекцию через доступные API
        skin_data = None
        used_provider = None
        used_model = None
        
        # Пробуем через OpenRouter
        if OPENROUTER_API_KEY:
            openrouter_models_to_try = []
            
            # СНАЧАЛА пробуем выбранную пользователем модель
            openrouter_models_to_try.append(vision_model)
            logger.info(f"🎯 Приоритет: используем выбранную модель: {vision_model}")
            
            # Затем добавляем fallback модели из DETECTION_FALLBACKS (кроме уже добавленной)
            for fallback in DETECTION_FALLBACKS:
                if fallback["provider"] == "openrouter":
                    model = fallback["model"]
                    if model != vision_model:  # Не добавляем, если уже есть
                        openrouter_models_to_try.append(model)
            
            # Пробуем каждую модель по порядку
            for model in openrouter_models_to_try:
                logger.info(f"Пробуем модель через OpenRouter: {model}")
                try:
                    skin_data = analyze_image_with_openrouter(image_base64, model, temperature, max_tokens)
                    if skin_data:
                        used_provider = "openrouter"
                        used_model = model
                        logger.info(f"✅ Успешно использована модель: {model}")
                        break
                    else:
                        logger.warning(f"Модель {model} не вернула данные")
                except Exception as e:
                    logger.debug(f"Модель {model} вызвала исключение: {e}")
                    continue
        
        # Если всё ещё не сработало, пробуем обычные модели OpenRouter
        if not skin_data and OPENROUTER_API_KEY:
            logger.info("Пробуем стандартные модели OpenRouter")
            skin_data = analyze_image_with_openrouter(image_base64, vision_model, temperature, max_tokens)
            if skin_data:
                used_provider = "openrouter"
                used_model = vision_model
        
        # Если все API недоступны, возвращаем ошибку
        if not skin_data:
            logger.error("="*80)
            logger.error("❌ ОШИБКА: Все API недоступны!")
            logger.error("   Проверьте:")
            logger.error("   1. API ключи в .env файле")
            logger.error("   2. Интернет-соединение")
            logger.error("   3. Доступность API провайдеров")
            logger.error("="*80)
            return jsonify({
                "success": False,
                "error": "Все API недоступны. Проверьте API ключи в .env файле и интернет-соединение.",
                "details": {
                    "openrouter_available": bool(OPENROUTER_API_KEY)
                }
            }), 503
        
        # Логируем итоговый результат
        logger.info("="*80)
        logger.info(f"✅ Анализ завершён")
        logger.info(f"   Провайдер: {used_provider}")
        logger.info(f"   Модель: {used_model}")
        logger.info("="*80)
        
        # Интеграция с Pixelbin API для получения изображений
        pixelbin_images = []
        try:
            # Декодируем base64 изображение в bytes
            image_bytes = base64.b64decode(image_base64)
            
            # Конвертируем HEIC в JPEG, если нужно
            filename = "image.jpg"
            if mime_type and mime_type in ['image/heic', 'image/heif']:
                if HEIC_SUPPORT:
                    try:
                        logger.info("Конвертация HEIC в JPEG...")
                        image_bytes = convert_heic_to_jpeg(image_bytes)
                        logger.info("HEIC успешно сконвертирован в JPEG")
                    except Exception as e:
                        logger.warning(f"Не удалось сконвертировать HEIC: {e}")
                        # Продолжаем с оригинальным файлом
                else:
                    logger.warning("HEIC файл получен, но поддержка HEIC не доступна")
            
            # Отправляем в Pixelbin API
            pixelbin_result = PixelBinService.upload_image(image_bytes, filename)
            
            # Проверяем, была ли ошибка валидации
            use_heuristics = False
            if pixelbin_result and pixelbin_result.get('error') == 'validation_failed':
                logger.warning("Pixelbin вернул ошибку валидации, используем эвристики")
                use_heuristics = True
                pixelbin_result = None
            
            if pixelbin_result and '_id' in pixelbin_result:
                job_id = pixelbin_result['_id']
                logger.info(f"Pixelbin: задача создана, job_id: {job_id}")
                
                # Ждём завершения обработки
                final_result = PixelBinService.check_status(job_id, max_attempts=10, delay=3)
                
                if final_result and final_result.get('status') == 'SUCCESS':
                    # Извлекаем все изображения из ответа
                    pixelbin_images = extract_images_from_pixelbin_response(final_result)
                    logger.info(f"Pixelbin: получено {len(pixelbin_images)} изображений")
                else:
                    # Если задача завершилась с ошибкой или не завершена, используем эвристики
                    logger.warning(f"Pixelbin: задача не завершена или завершилась с ошибкой, используем эвристики")
                    use_heuristics = True
            elif use_heuristics:
                # Используем эвристический анализ
                logger.info("Использование эвристического анализа вместо Pixelbin")
                heuristic_data = generate_heuristic_analysis(skin_data)
                # Добавляем информацию об эвристике
                pixelbin_images = [{
                    'type': 'heuristic',
                    'heuristic_data': heuristic_data,
                    'message': 'Использован эвристический анализ'
                }]
        except Exception as e:
            logger.warning(f"Ошибка при работе с Pixelbin API: {e}, используем эвристики")
            # При любой ошибке используем эвристики
            use_heuristics = True
            heuristic_data = generate_heuristic_analysis(skin_data)
            pixelbin_images = [{
                'type': 'heuristic',
                'heuristic_data': heuristic_data,
                'message': 'Использован эвристический анализ'
            }]
        
        # Генерируем текстовый отчёт
        report = generate_report_with_llm(skin_data, llm_provider, text_model, temperature, language)
        
        return jsonify({
            "success": True,
            "data": skin_data,
            "report": report,
            "provider": used_provider,
            "model": used_model,
            "config": config,
            "pixelbin_images": pixelbin_images,  # Добавляем изображения из Pixelbin
            "use_heuristics": use_heuristics  # Флаг использования эвристики
        })
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/proxy-image', methods=['GET'])
def proxy_image():
    """Прокси для загрузки изображений Pixelbin (обход CORS)"""
    try:
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({"error": "URL не предоставлен"}), 400
        
        # Проверяем, что URL от Pixelbin
        if 'delivery.pixelbin.io' not in image_url and 'pixelbin.io' not in image_url:
            return jsonify({"error": "Недопустимый URL"}), 400
        
        # Загружаем изображение
        response = requests.get(image_url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Возвращаем изображение с правильными заголовками
        from flask import Response
        return Response(
            response.content,
            mimetype=response.headers.get('Content-Type', 'image/jpeg'),
            headers={
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Allow-Origin': '*'
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при проксировании изображения: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """Получить текущую конфигурацию"""
    return jsonify(DEFAULT_CONFIG)


@app.route('/api/config', methods=['POST'])
def update_config():
    """Обновить конфигурацию"""
    try:
        data = request.json
        DEFAULT_CONFIG.update(data)
        return jsonify({"success": True, "config": DEFAULT_CONFIG})
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route('/api/models/available', methods=['GET'])
def get_available_models():
    """Получить список всех доступных моделей для каждого провайдера"""
    try:
        # Модели для OpenRouter (из DETECTION_FALLBACKS)
        openrouter_models = []
        for fallback in DETECTION_FALLBACKS:
            if fallback["provider"] == "openrouter":
                model = fallback["model"]
                # Красивое название для отображения
                label = model.replace("x-ai/", "").replace("google/", "").replace(":free", " (бесплатно)")
                openrouter_models.append({
                    "value": model,
                    "label": label
                })
        
        return jsonify({
            "success": True,
            "models": {
                "openrouter": {
                    "vision": openrouter_models,
                    "text": openrouter_models
                }
            },
            "detection_fallbacks": DETECTION_FALLBACKS
        })
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return jsonify({"error": str(e)}), 500


def find_free_port(start_port=5000, max_attempts=10):
    """Находит свободный порт начиная с start_port"""
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Не удалось найти свободный порт в диапазоне {start_port}-{start_port + max_attempts}")


if __name__ == '__main__':
    # В production (Railway) используем PORT из переменных окружения напрямую
    # В development пробуем найти свободный порт
    default_port = int(os.getenv('PORT', 5000))
    is_production = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('PRODUCTION')
    
    if is_production:
        # В production используем порт напрямую
        port = default_port
        debug_mode = False
    else:
        # В development ищем свободный порт
        port = find_free_port(default_port)
        debug_mode = True
        if port != default_port:
            logger.info(f"Порт {default_port} занят, используем порт {port}")
    
    print("=" * 80)
    print("🔬 Skin Analyzer Backend")
    print("=" * 80)
    print(f"📡 Сервер запущен на http://0.0.0.0:{port}")
    if not is_production:
        print(f"🌍 Откройте браузер и перейдите по адресу http://localhost:{port}")
    print("=" * 80)
    if not is_production:
        print("Для остановки нажмите Ctrl+C")
    print()
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

