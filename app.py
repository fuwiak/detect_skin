#!/usr/bin/env python3
"""
Backend сервис для анализа состояния кожи
"""
import os
import base64
import json
import requests
import tempfile
import signal
from contextlib import contextmanager
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

# fal_client для SAM3 (после инициализации логгера)
try:
    import fal_client
    FAL_AVAILABLE = True
except ImportError:
    fal_client = None
    FAL_AVAILABLE = False
    logger.warning("fal_client не установлен, SAM3 режим недоступен")

# Импорт для работы с HEIC (после logger)
try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw, ImageFont
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
    logger.info("Поддержка HEIC включена")
except ImportError:
    HEIC_SUPPORT = False
    logger.warning("pillow-heif не установлен, поддержка HEIC будет ограничена")

# Импорт numpy и scipy для обработки масок
try:
    import numpy as np
    from scipy import ndimage
    NUMPY_AVAILABLE = True
    logger.info("NumPy и SciPy доступны для обработки масок")
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy/SciPy не установлены, обработка масок будет ограничена")

# Импорт модуля сегментации
try:
    from skin_segmentation import get_segmenter
    SEGMENTATION_AVAILABLE = True
    logger.info("Модуль сегментации доступен")
except ImportError as e:
    SEGMENTATION_AVAILABLE = False
    logger.warning(f"Модуль сегментации недоступен: {e}")

# Импорт модуля Hugging Face сегментации
try:
    from hf_segmentation import get_hf_segmenter
    HF_SEGMENTATION_AVAILABLE = True
    logger.info("Модуль Hugging Face сегментации доступен")
except ImportError as e:
    HF_SEGMENTATION_AVAILABLE = False
    logger.warning(f"Модуль Hugging Face сегментации недоступен: {e}")

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

# Ключ для SAM3 (fal_client)
FAL_KEY = os.getenv("FAL_KEY")
if FAL_KEY:
    os.environ['FAL_KEY'] = FAL_KEY

if not PIXELBIN_ACCESS_TOKEN:
    logger.warning("PIXELBIN_ACCESS_TOKEN не найден в переменных окружения. Функциональность Pixelbin будет недоступна.")

# Настройки моделей по умолчанию
# Порядок попыток подключения к API для детекции
# Топовые платные модели
DETECTION_FALLBACKS = [
    {"provider": "openrouter", "model": "google/gemini-2.5-flash"},  # Gemini 2.5 Flash - поддержка bounding boxes
    {"provider": "openrouter", "model": "openai/gpt-4o"},  # GPT-4o Vision - поддержка координат
    {"provider": "openrouter", "model": "anthropic/claude-3.5-sonnet"},  # Claude 3.5 Sonnet - баланс качества и стоимости
    {"provider": "openrouter", "model": "google/gemini-1.5-pro"},  # Gemini 1.5 Pro - сильные возможности обработки изображений
    # Бесплатные и бюджетные варианты
    {"provider": "openrouter", "model": "google/gemini-2.0-flash-exp"},  # Gemini 2.0 Flash Experimental (бесплатная)
    {"provider": "openrouter", "model": "qwen/qwen-2-vl-72b-instruct"},  # Qwen2-VL - высокая производительность
    {"provider": "openrouter", "model": "mistralai/pixtral-large"},  # Pixtral Large - 124B параметров
    {"provider": "openrouter", "model": "x-ai/grok-4.1-fast:free"},  # Grok 4.1 Fast (бесплатная)
    {"provider": "openrouter", "model": "google/gemini-2.0-flash-001"}  # Google Gemini 2.0 Flash
]

# Список заболеваний для SAM3 режима (ключ = prompt, значение = отображаемое имя)
SAM3_DISEASES_DEFAULT = {
    "acne": "Акне",
    "pimples": "Прыщи",
    "pustules": "Пустулы",
    "papules": "Папулы",
    "blackheads": "Черные точки",
    "whiteheads": "Белые угри",
    "comedones": "Комедоны",
    "rosacea": "Розацеа",
    "irritation": "Раздражение",
    "pigmentation": "Пигментация",
    "freckles": "Веснушки",
    "papillomas": "Папилломы",
    "warts": "Бородавки",
    "moles": "Родинки",
    "skin tags": "Кожные выросты",
    "wrinkles": "Морщины",
    "fine lines": "Мелкие морщины",
    "skin lesion": "Повреждения",
    "scars": "Шрамы",
    "post acne marks": "Следы постакне",
    "acne scars": "Шрамы от акне",
}

# Улучшенные промпты для SAM3 с детальными описаниями (few-shot через описания)
SAM3_ENHANCED_PROMPTS = {
    "acne": "acne, pimples, inflamed red bumps on skin, raised red spots, pustules with white or yellow centers",
    "pimples": "pimples, small raised red bumps on skin, inflamed spots, zits, blemishes",
    "pustules": "pustules, pus-filled bumps, white or yellow-headed pimples, infected acne lesions",
    "papules": "papules, small raised solid bumps on skin, red or pink bumps without pus",
    "blackheads": "blackheads, open comedones, dark spots in pores, clogged pores with dark centers",
    "whiteheads": "whiteheads, closed comedones, small white bumps under skin, milia",
    "comedones": "comedones, clogged pores, blackheads and whiteheads, blocked hair follicles",
    "rosacea": "rosacea, facial redness, red patches on face, visible blood vessels, flushed skin",
    "irritation": "skin irritation, red inflamed areas, rash, sensitive skin patches, redness",
    "pigmentation": "pigmentation, dark spots, hyperpigmentation, brown spots, age spots, melasma, uneven skin tone",
    "freckles": "freckles, small brown spots, ephelides, sun spots, light brown dots on skin",
    "papillomas": "papillomas, small skin growths, raised bumps, benign tumors, warty growths",
    "warts": "warts, rough skin growths, raised bumps with rough texture, viral warts, verruca",
    "moles": "moles, nevi, dark brown or black spots, raised or flat pigmented lesions",
    "skin tags": "skin tags, acrochordons, small fleshy growths hanging from skin, pedunculated skin growths, soft tissue tags, small raised bumps attached by a stalk, flesh-colored or slightly darker growths, multiple small tags clustered together, tags on neck, chest, or body folds, all skin tags including very small ones, tiny tags, medium tags, large tags, tags of any size, every single skin tag visible on the image",
    "wrinkles": "wrinkles, fine lines, creases in skin, age lines, expression lines, deep folds",
    "fine lines": "fine lines, small wrinkles, subtle creases, early signs of aging, delicate lines",
    "skin lesion": "skin lesions, abnormal skin areas, damaged skin, skin abnormalities, skin changes",
    "scars": "scars, healed wound marks, raised or depressed scar tissue, post-surgical scars, injury marks",
    "post acne marks": "post-acne marks, dark spots after acne, hyperpigmentation from acne, acne scars, PIH (post-inflammatory hyperpigmentation)",
    "acne scars": "acne scars, pitted scars, atrophic scars, depressed scars from acne, ice pick scars, boxcar scars",
}

# Настройки моделей по умолчанию
DEFAULT_VISION_MODEL = "google/gemini-2.5-flash"  # Для детекции (поддерживает bounding boxes)
DEFAULT_TEXT_MODEL = "anthropic/claude-3.5-sonnet"  # Для генерации отчёта

HF_TOKEN = os.getenv("HF_TOKEN")  # Токен HuggingFace (Railway env)

DEFAULT_CONFIG = {
    "detection_provider": "openrouter",
    "llm_provider": "openrouter",
    "vision_model": DEFAULT_VISION_MODEL,
    "text_model": DEFAULT_TEXT_MODEL,
    "temperature": 0,  # Точность важнее креативности
    "max_tokens": 300  # Краткие и лаконичные ответы
}

if HF_TOKEN:
    logger.info("HF_TOKEN найден в окружении (Railway/.env)")
else:
    logger.warning("HF_TOKEN не найден. Задайте переменную окружения HF_TOKEN в Railway/.env")


class PixelBinService:
    """Сервис для работы с Pixelbin API"""
    
    @staticmethod
    def preprocess_for_pixelbin(image_bytes: bytes, max_size: int = 1024, contrast_factor: float = 1.15) -> Optional[bytes]:
        """
        Лёгкий препроцессинг, чтобы повысить шанс успешной валидации Pixelbin:
        - авто-ориентация EXIF
        - downscale до max_size по большей стороне (с сохранением пропорций)
        - лёгкое повышение контраста
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("RGB")
                img = ImageOps.exif_transpose(img)
                
                # Масштабирование с сохранением пропорций
                w, h = img.size
                scale = min(max_size / max(w, h), 1.0)
                if scale < 1.0:
                    new_size = (int(w * scale), int(h * scale))
                    img = img.resize(new_size, Image.LANCZOS)
                
                # Лёгкое повышение контраста
                img = ImageEnhance.Contrast(img).enhance(contrast_factor)
                
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                return buf.getvalue()
        except Exception as e:
            logger.warning(f"Preprocess Pixelbin не удался: {e}")
            return None
    
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
                
                # Обрабатываем различные типы ошибок
                try:
                    error_data = response.json()
                    error_code = error_data.get('errorCode', '')
                    error_type = error_data.get('exception', '')
                    
                    # 400 - Validation Error
                    if response.status_code == 400:
                        if 'validation' in error_text.lower() or 'JR-0400' in error_code:
                            return {"error": "validation_failed", "status_code": 400, "message": error_data}
                    
                    # 403 - Usage Limit Exceeded
                    elif response.status_code == 403:
                        if 'Usage Limit' in error_text or 'JR-1000' in error_code or 'UsageBlockedError' in error_type:
                            logger.warning("Pixelbin: достигнут лимит использования, используем эвристики")
                            return {"error": "usage_limit_exceeded", "status_code": 403, "message": error_data}
                    
                    # 429 - Rate Limit
                    elif response.status_code == 429:
                        logger.warning("Pixelbin: превышен лимит запросов, используем эвристики")
                        return {"error": "rate_limit_exceeded", "status_code": 429, "message": error_data}
                    
                    # 500+ - Server Error
                    elif response.status_code >= 500:
                        logger.warning("Pixelbin: ошибка сервера, используем эвристики")
                        return {"error": "server_error", "status_code": response.status_code, "message": error_data}
                    
                    # Другие ошибки
                    else:
                        logger.warning(f"Pixelbin: неизвестная ошибка {response.status_code}, используем эвристики")
                        return {"error": "api_error", "status_code": response.status_code, "message": error_data}
                        
                except:
                    # Если не удалось распарсить JSON, возвращаем общую ошибку
                    return {"error": "api_error", "status_code": response.status_code, "message": error_text}
                
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
                
                # Обрабатываем ошибки API
                if not response.ok:
                    error_text = response.text[:500]
                    status_code = response.status_code
                    
                    # 403 - Usage Limit Exceeded
                    if status_code == 403:
                        logger.warning(f"Pixelbin: достигнут лимит использования при проверке статуса (403)")
                        return {"error": "usage_limit_exceeded", "status": "FAILURE", "status_code": 403}
                    
                    # 429 - Rate Limit
                    elif status_code == 429:
                        logger.warning(f"Pixelbin: превышен лимит запросов при проверке статуса (429)")
                        if attempt < max_attempts:
                            time.sleep(delay * 2)  # Увеличиваем задержку
                            continue
                        return {"error": "rate_limit_exceeded", "status": "FAILURE", "status_code": 429}
                    
                    # 500+ - Server Error
                    elif status_code >= 500:
                        logger.warning(f"Pixelbin: ошибка сервера при проверке статуса ({status_code})")
                        if attempt < max_attempts:
                            time.sleep(delay)
                            continue
                        return {"error": "server_error", "status": "FAILURE", "status_code": status_code}
                    
                    # Другие ошибки
                    else:
                        logger.warning(f"Pixelbin: ошибка API при проверке статуса ({status_code}): {error_text}")
                        if attempt < max_attempts:
                            time.sleep(delay)
                            continue
                        return {"error": "api_error", "status": "FAILURE", "status_code": status_code}
                
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
        
        # Определяем, поддерживает ли модель bounding boxes
        supports_bbox = model in ["google/gemini-2.5-flash", "openai/gpt-4o"]
        
        if supports_bbox:
            prompt = """Ты специалист по заболеваниям и дефектам кожи. Проанализируй это изображение лица и определи следующие параметры состояния кожи:

1. acne_score (0-100) - уровень акне
2. pigmentation_score (0-100) - уровень пигментации (ВАЖНО: пигментные пятна - это плоские участки изменённого цвета кожи, НЕ путай их с папилломами - выпуклыми образованиями)
3. pores_size (0-100) - размер пор
4. wrinkles_grade (0-100) - уровень морщин
5. skin_tone (0-100) - тон кожи
6. texture_score (0-100) - текстура кожи
7. moisture_level (0-100) - уровень увлажненности
8. oiliness (0-100) - жирность кожи

Верни результат в формате JSON с этими полями. Для каждого обнаруженного дефекта (акне, пигментация, морщины) укажи координаты bounding box в формате [y_min, x_min, y_max, x_max], нормализованные к 0-1000. Для пигментации и веснушек укажи координаты каждой точки. Для морщин укажи координаты каждой морщины по её форме.

Формат ответа:
{
  "acne_score": число,
  "pigmentation_score": число,
  "pores_size": число,
  "wrinkles_grade": число,
  "skin_tone": число,
  "texture_score": число,
  "moisture_level": число,
  "oiliness": число,
  "bounding_boxes": {
    "acne": [[y_min, x_min, y_max, x_max], ...],
    "pigmentation": [[y_min, x_min, y_max, x_max], ...],
    "wrinkles": [[y_min, x_min, y_max, x_max], ...]
  }
}"""
        else:
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
            "max_tokens": max_tokens * 2 if supports_bbox else max_tokens  # Больше токенов для координат
        }
        
        # Для Gemini 2.5 Flash добавляем response_format
        if model == "google/gemini-2.5-flash":
            payload["response_format"] = {"type": "json_object"}
        
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
        
        # Сохраняем bounding boxes, если они есть
        if "bounding_boxes" in skin_data:
            skin_data["_bounding_boxes"] = skin_data.pop("bounding_boxes")
        
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


class TimeoutException(Exception):
    """Исключение при превышении времени ожидания SAM3"""
    pass


def run_with_timeout(func, timeout: int, *args, **kwargs):
    """Запускает функцию в отдельном потоке и обрывает при превышении таймаута"""
    import threading

    result_container = {"result": None, "error": None}

    def target():
        try:
            result_container["result"] = func(*args, **kwargs)
        except Exception as e:
            result_container["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        return None, TimeoutException(f"Превышено время ожидания {timeout}с")
    if result_container["error"]:
        return None, result_container["error"]
    return result_container["result"], None


def sam3_segment(image_path: str, disease_key: str, timeout: int, statuses: List[str]):
    """Вызов SAM3 через fal_client с таймаутом и улучшенными промптами"""
    if not FAL_AVAILABLE or not FAL_KEY:
        statuses.append("❌ SAM3 недоступен (нет fal_client или FAL_KEY)")
        return None
    try:
        # Используем улучшенный промпт с детальным описанием, если доступен
        enhanced_prompt = SAM3_ENHANCED_PROMPTS.get(disease_key, disease_key)
        logger.info(f"SAM3 промпт для {disease_key}: {enhanced_prompt[:100]}...")
        
        def call_fal():
            return fal_client.subscribe(
                "fal-ai/sam-3/image",
                arguments={
                    "image_url": fal_client.upload_file(image_path),
                    "text_prompt": enhanced_prompt
                },
                with_logs=False,
            )

        result, error = run_with_timeout(call_fal, timeout)
        if error:
            if isinstance(error, TimeoutException):
                statuses.append(f"⏱️ ПРОПУЩЕНО (таймаут {timeout}с) для {disease_key}")
            else:
                statuses.append(f"⚠️ Ошибка SAM3 для {disease_key}: {error}")
            return None
        return result
    except Exception as e:
        statuses.append(f"⚠️ Ошибка SAM3 для {disease_key}: {e}")
        return None


def run_sam3_pipeline(image_bytes: bytes, diseases: Dict[str, str], timeout: int = 5) -> Dict:
    """
    Запускает последовательную сегментацию SAM3 по списку заболеваний.
    Возвращает mask_results и статус-лог.
    """
    statuses = []
    mask_results = {}

    if not FAL_AVAILABLE or not FAL_KEY:
        statuses.append("❌ SAM3 недоступен (нет fal_client или FAL_KEY)")
        return {'statuses': statuses, 'mask_results': {}}

    # Сохраняем изображение во временный файл
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
        tmp.write(image_bytes)
        tmp.flush()

        total = len(diseases)
        for idx, (disease_key, disease_name) in enumerate(diseases.items(), 1):
            statuses.append(f"🔍 [{idx}/{total}] {disease_name.upper()}")
            
            # Увеличиваем таймаут для кожных меток и других образований, которые могут быть многочисленными
            current_timeout = timeout
            if disease_key in ["skin tags", "papillomas", "moles", "freckles", "pigmentation"]:
                current_timeout = max(timeout, 10)  # Минимум 10 секунд для многочисленных образований
                logger.info(f"Увеличенный таймаут для {disease_name}: {current_timeout}с")
            
            start = time.time()
            result = sam3_segment(tmp.name, disease_key, current_timeout, statuses)
            elapsed = time.time() - start

            if result and isinstance(result, dict) and result.get('masks'):
                count = len(result['masks'])
                statuses.append(f"✅ {disease_name}: {count} маск ({elapsed:.1f}с)")
                mask_results[disease_key] = result
            else:
                statuses.append(f"⚪ {disease_name}: нет масок ({elapsed:.1f}с)")

    return {'statuses': statuses, 'mask_results': mask_results}


def create_sam3_overlay_image(original_image_bytes: bytes, mask_results: Dict) -> Optional[str]:
    """
    Создаёт изображение с наложенными масками SAM3 на оригинальное фото.
    Создаёт КОПИЮ изображения и накладывает ВСЕ маски на эту копию.
    Возвращает base64 строку готового изображения.
    """
    if not NUMPY_AVAILABLE:
        logger.warning("NumPy/SciPy недоступны, наложение масок пропущено")
        return None
    
    try:
        # Загружаем оригинальное изображение
        original = Image.open(io.BytesIO(original_image_bytes)).convert('RGB')
        width, height = original.size
        
        # СОЗДАЁМ КОПИЮ изображения (не изменяем оригинал!)
        result_img = original.copy().convert('RGBA')
        
        # Затемняем копию для контраста
        result_array = np.array(result_img).astype(float)
        dimmed = (result_array * 0.25).astype(np.uint8)
        result_img = Image.fromarray(dimmed).convert('RGBA')
        
        # Слой для подсветки (начинаем с прозрачного)
        highlight_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Цвета для разных заболеваний
        colors = {
            'acne': (255, 0, 0), 'pimples': (255, 50, 50), 'pustules': (255, 20, 20),
            'papules': (255, 100, 100), 'blackheads': (100, 0, 255), 'whiteheads': (255, 255, 0),
            'comedones': (80, 0, 200), 'redness': (255, 100, 0), 'inflammation': (255, 150, 0),
            'red spots': (255, 80, 80), 'rosacea': (255, 60, 100), 'irritation': (255, 120, 80),
            'pigmentation': (200, 0, 255), 'hyperpigmentation': (180, 0, 200), 'dark spots': (255, 0, 255),
            'age spots': (150, 0, 255), 'melasma': (160, 0, 180), 'sun spots': (140, 0, 200),
            'freckles': (120, 50, 200), 'papillomas': (0, 255, 0), 'warts': (50, 255, 50),
            'moles': (255, 200, 0), 'skin tags': (100, 255, 100), 'growths': (150, 255, 50),
            'wrinkles': (0, 200, 255), 'fine lines': (100, 200, 255), 'deep wrinkles': (0, 150, 255),
            'expression lines': (50, 180, 255), 'skin lesion': (0, 255, 255), 'scars': (255, 150, 255),
            'post-acne marks': (255, 100, 200), 'post acne marks': (255, 100, 200),
            'acne scars': (200, 100, 255), 'blemishes': (255, 120, 180), 'eczema': (255, 180, 100),
            'dermatitis': (255, 120, 60), 'psoriasis': (255, 140, 80), 'dry skin': (200, 200, 100),
            'texture issues': (180, 180, 200), 'enlarged pores': (100, 255, 200),
            'open pores': (120, 255, 220), 'uneven skin tone': (220, 180, 255),
            'discoloration': (200, 150, 255), 'broken capillaries': (255, 0, 100),
            'spider veins': (200, 0, 150), 'sunburn': (255, 40, 0), 'peeling': (255, 220, 180),
        }
        
        total_masks = 0
        mask_centers = []  # Сохраняем центры масок для добавления текста
        
        # Обрабатываем КАЖДОЕ заболевание и КАЖДУЮ маску
        for disease, result in mask_results.items():
            if not result or not isinstance(result, dict):
                continue
            
            if 'masks' not in result or not result['masks']:
                continue
            
            color = colors.get(disease, (255, 255, 255))
            # Получаем русское название болезни
            disease_name_ru = SAM3_DISEASES_DEFAULT.get(disease, disease)
            logger.info(f"Обработка масок для {disease} ({disease_name_ru}): {len(result['masks'])} масок")
            
            for i, mask_data in enumerate(result['masks']):
                if 'url' not in mask_data:
                    continue
                
                try:
                    mask_url = mask_data['url']
                    logger.debug(f"Загрузка маски {disease} #{i+1}: {mask_url}")
                    
                    # Загружаем маску
                    mask_response = requests.get(mask_url, timeout=30)
                    mask_response.raise_for_status()
                    
                    # Пробуем загрузить как grayscale, если не получается - конвертируем
                    mask_img = Image.open(io.BytesIO(mask_response.content))
                    if mask_img.mode != 'L':
                        mask_img = mask_img.convert('L')
                    
                    # Масштабируем под размер оригинала
                    if mask_img.size != (width, height):
                        mask_img = mask_img.resize((width, height), Image.Resampling.LANCZOS)
                    
                    mask_array = np.array(mask_img)
                    
                    # Проверяем, что маска не пустая
                    if np.max(mask_array) == 0:
                        logger.warning(f"Маска {disease} #{i+1} пустая, пропускаем")
                        continue
                    
                    # Основное заполнение цветом
                    mask_binary = (mask_array > 127).astype(np.uint8) * 255
                    
                    # Находим центр маски для добавления текста
                    coords = np.where(mask_binary > 0)
                    if len(coords[0]) > 0:
                        center_y = int(np.mean(coords[0]))
                        center_x = int(np.mean(coords[1]))
                        mask_centers.append((center_x, center_y, disease_name_ru, color))
                    
                    colored_fill = Image.new('RGBA', (width, height), color + (255,))
                    mask_alpha = Image.fromarray(mask_binary).convert('L')
                    
                    fill_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                    fill_layer.paste(colored_fill, (0, 0), mask_alpha)
                    
                    # Толстая белая обводка
                    dilated = ndimage.binary_dilation(mask_binary, iterations=7).astype(np.uint8) * 255
                    eroded = ndimage.binary_erosion(mask_binary, iterations=1).astype(np.uint8) * 255
                    thick_border = dilated - eroded
                    
                    border_layer = Image.new('RGBA', (width, height), (255, 255, 255, 255))
                    border_alpha = Image.fromarray(thick_border).convert('L')
                    border_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                    border_img.paste(border_layer, (0, 0), border_alpha)
                    
                    # Двойное свечение для лучшей видимости
                    glow1 = ndimage.binary_dilation(mask_binary, iterations=15).astype(np.uint8) * 255
                    glow1 = glow1 - mask_binary
                    glow1_img = Image.fromarray(glow1).convert('L').filter(ImageFilter.GaussianBlur(radius=7))
                    glow1_colored = Image.new('RGBA', (width, height), color + (200,))
                    glow1_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                    glow1_layer.paste(glow1_colored, (0, 0), glow1_img)
                    
                    glow2 = ndimage.binary_dilation(mask_binary, iterations=25).astype(np.uint8) * 255
                    glow2 = glow2 - mask_binary
                    glow2_img = Image.fromarray(glow2).convert('L').filter(ImageFilter.GaussianBlur(radius=12))
                    glow2_colored = Image.new('RGBA', (width, height), color + (120,))
                    glow2_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                    glow2_layer.paste(glow2_colored, (0, 0), glow2_img)
                    
                    # НАКЛАДЫВАЕМ все слои на highlight_layer
                    highlight_layer = Image.alpha_composite(highlight_layer, glow2_layer)
                    highlight_layer = Image.alpha_composite(highlight_layer, glow1_layer)
                    highlight_layer = Image.alpha_composite(highlight_layer, fill_layer)
                    highlight_layer = Image.alpha_composite(highlight_layer, border_img)
                    
                    total_masks += 1
                    logger.debug(f"Маска {disease} #{i+1} наложена успешно")
                    
                except Exception as e:
                    logger.warning(f"Ошибка обработки маски {disease} #{i+1}: {e}")
                    continue
        
        if total_masks == 0:
            logger.warning("Не найдено масок для наложения")
            return None
        
        logger.info(f"Всего наложено {total_masks} масок")
        
        # Объединяем затемнённое изображение с подсветкой
        result_img = Image.alpha_composite(result_img, highlight_layer).convert('RGB')
        
        # Добавляем русские названия болезней на изображение
        if mask_centers:
            draw = ImageDraw.Draw(result_img)
            # Пробуем загрузить шрифт, если не получается - используем стандартный
            try:
                # Пытаемся использовать системный шрифт
                font_size = max(20, min(width, height) // 30)
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                except:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            for center_x, center_y, disease_name, color in mask_centers:
                # Рисуем текст с обводкой для лучшей читаемости
                text = disease_name
                # Получаем размер текста (с fallback для старых версий PIL)
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                except AttributeError:
                    # Fallback для старых версий PIL
                    text_width, text_height = draw.textsize(text, font=font)
                
                # Позиция текста (центр маски)
                text_x = center_x - text_width // 2
                text_y = center_y - text_height // 2
                
                # Рисуем обводку (чёрная) для лучшей читаемости
                for adj in [(-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2),
                           (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2),
                           (0, -2), (0, -1), (0, 1), (0, 2),
                           (1, -2), (1, -1), (1, 0), (1, 1), (1, 2),
                           (2, -2), (2, -1), (2, 0), (2, 1), (2, 2)]:
                    draw.text((text_x + adj[0], text_y + adj[1]), text, font=font, fill=(0, 0, 0, 255))
                
                # Рисуем сам текст (белый)
                draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
        
        # Усиление контраста и цвета для лучшей видимости
        enhancer = ImageEnhance.Contrast(result_img)
        result_img = enhancer.enhance(2.2)
        enhancer = ImageEnhance.Color(result_img)
        result_img = enhancer.enhance(2.5)
        enhancer = ImageEnhance.Brightness(result_img)
        result_img = enhancer.enhance(1.3)
        result_img = result_img.filter(ImageFilter.SHARPEN)
        
        # Конвертируем в base64
        output = io.BytesIO()
        result_img.save(output, format='JPEG', quality=95)
        output.seek(0)
        image_base64 = base64.b64encode(output.read()).decode('utf-8')
        
        logger.info(f"✅ Изображение с наложенными масками SAM3 создано успешно ({total_masks} масок)")
        return f"data:image/jpeg;base64,{image_base64}"
        
    except Exception as e:
        logger.error(f"Ошибка создания изображения с масками: {e}", exc_info=True)
        return None


def segment_face_area(concern_type: str, value: float) -> Dict:
    """Простой алгоритм сегментации лица для определения зон проблем с естественными формами"""
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


def parse_report_locations(report_text: str) -> Dict[str, List[str]]:
    """Парсит текстовый отчёт для извлечения локализации проблем"""
    import re
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
    if HF_SEGMENTATION_AVAILABLE and image_bytes:
        try:
            hf_token = os.getenv("HF_TOKEN")
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
    if not hf_markers and SEGMENTATION_AVAILABLE and image_bytes:
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
    
    # Акне
    if skin_data.get('acne_score', 0) > 30:
        acne_value = skin_data.get('acne_score', 0)
        
        # Приоритет: HF маркеры > bounding boxes > простые эвристики
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
                        'svg_path': marker.get('svg_path'),
                        'points': marker.get('points'),
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
    
    # Пигментация - теперь отображается как точки
    if skin_data.get('pigmentation_score', 0) > 40:
        pigmentation_value = skin_data.get('pigmentation_score', 0)
        
        # Приоритет: HF маркеры > bounding boxes > отчёт > простые эвристики
        if hf_markers.get('pigmentation'):
            # Используем точные маркеры из HF сегментации (точки)
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
            # Используем координаты из bounding boxes - каждая точка отдельно
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
        elif 'pigmentation' in report_locations and ('щёки' in str(report_locations['pigmentation']) or 'щеки' in str(report_locations['pigmentation'])):
            # Создаём точки на обеих щеках
            concerns.append({
                'name': 'Пигментация',
                'tech_name': 'pigmentation',
                'value': pigmentation_value,
                'severity': 'Needs Attention' if pigmentation_value > 70 else 'Average',
                'description': f'Замечены участки пигментации на щеках. Используйте солнцезащитный крем.',
                'area': 'face',
                'position': {'x': 25, 'y': 45, 'zone': 'left_cheek', 'type': 'point', 'marker_type': 'dot'},
                'is_dot': True
            })
            concerns.append({
                'name': 'Пигментация',
                'tech_name': 'pigmentation',
                'value': pigmentation_value,
                'severity': 'Needs Attention' if pigmentation_value > 70 else 'Average',
                'description': f'Замечены участки пигментации на щеках. Используйте солнцезащитный крем.',
                'area': 'face',
                'position': {'x': 75, 'y': 45, 'zone': 'right_cheek', 'type': 'point', 'marker_type': 'dot'},
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
        wrinkles_value = skin_data.get('wrinkles_grade', 0)
        
        # Приоритет: HF маркеры > bounding boxes > отчёт > простые эвристики
        if hf_markers.get('wrinkles'):
            # Используем точные маркеры из HF сегментации
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
                        'svg_path': marker.get('svg_path'),
                        'points': marker.get('points'),
                        'type': 'area',
                        'is_wrinkle': True
                    },
                    'is_area': True
                })
        elif 'wrinkles' in bounding_boxes and bounding_boxes['wrinkles']:
            # Используем координаты из bounding boxes - каждая морщина отдельно
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
        elif 'wrinkles' in report_locations:
            locations = report_locations['wrinkles']
            if 'периорбитальная' in str(locations) or 'вокруг глаз' in str(locations):
                # Область вокруг глаз - эллипс
                concerns.append({
                    'name': 'Морщины (периорбитальная область)',
                    'tech_name': 'wrinkles',
                    'value': skin_data.get('wrinkles_grade', 0),
                    'severity': 'Needs Attention' if skin_data.get('wrinkles_grade', 0) > 60 else 'Average',
                    'description': f'Замечены морщины вокруг глаз. Увлажнение и защита от солнца помогут.',
                    'area': 'face',
                    'position': {'x': 50, 'y': 35, 'width': 35, 'height': 20, 'zone': 'periorbital', 'type': 'area', 'shape': 'ellipse'},
                    'is_area': True
                })
            if 'периоральная' in str(locations) or 'вокруг рта' in str(locations):
                # Область вокруг рта - эллипс
                concerns.append({
                    'name': 'Морщины (периоральная область)',
                    'tech_name': 'wrinkles',
                    'value': skin_data.get('wrinkles_grade', 0),
                    'severity': 'Needs Attention' if skin_data.get('wrinkles_grade', 0) > 60 else 'Average',
                    'description': f'Замечены морщины вокруг рта. Увлажнение и защита от солнца помогут.',
                    'area': 'face',
                    'position': {'x': 50, 'y': 65, 'width': 25, 'height': 15, 'zone': 'perioral', 'type': 'area', 'shape': 'ellipse'},
                    'is_area': True
                })
            if 'лоб' in str(locations) or 'forehead' in str(locations):
                concerns.append({
                    'name': 'Морщины (лоб)',
                    'tech_name': 'wrinkles',
                    'value': skin_data.get('wrinkles_grade', 0),
                    'severity': 'Needs Attention' if skin_data.get('wrinkles_grade', 0) > 60 else 'Average',
                    'description': f'Замечены морщины на лбу. Увлажнение и защита от солнца помогут.',
                    'area': 'face',
                    'position': {'x': 50, 'y': 20, 'width': 40, 'height': 15, 'zone': 'forehead', 'type': 'area', 'shape': 'ellipse'},
                    'is_area': True
                })
        else:
            # По умолчанию создаём области для морщин с эллиптической формой
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
    
    # Папилломы (только через HF сегментацию)
    if hf_markers.get('papillomas'):
        for marker in hf_markers['papillomas']:
            concerns.append({
                'name': 'Папилломы',
                'tech_name': 'papillomas',
                'value': marker.get('value', 50),
                'severity': 'Needs Attention',
                'description': f'Обнаружены папилломы. Рекомендуется консультация дерматолога.',
                'area': 'face',
                'position': {
                    'x': marker['x'],
                    'y': marker['y'],
                    'width': marker['width'],
                    'height': marker['height'],
                    'shape': marker.get('shape', 'ellipse'),
                    'svg_path': marker.get('svg_path'),
                    'points': marker.get('points'),
                    'type': 'area'
                },
                'is_area': True
            })
    
    if skin_data.get('moisture_level', 0) < 50:
        if not methods_used:
            methods_used.append("Простые эвристики")
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
        
        # Режим работы: pixelbin (по умолчанию) или sam3
        mode = data.get('mode', 'pixelbin')
        sam3_timeout = int(data.get('sam3_timeout', 5))
        sam3_diseases = data.get('sam3_diseases', [])
        selected_diseases = {
            k: v for k, v in SAM3_DISEASES_DEFAULT.items()
            if (not sam3_diseases or k in sam3_diseases)
        }
        if not selected_diseases:
            selected_diseases = SAM3_DISEASES_DEFAULT

        # Интеграция с Pixelbin API или SAM3
        pixelbin_images = []
        pixelbin_attempts = []
        analysis_method = mode
        use_heuristics = False

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
            else:
                logger.warning("HEIC файл получен, но поддержка HEIC не доступна")

        if mode == "sam3":
            # Сохраняем оригинальное изображение для наложения масок
            original_image_bytes = bytes(image_bytes)  # Создаём копию bytes
            
            statuses = []
            statuses.append("🔧 ПРЕДОБРАБОТКА")
            preprocessed = PixelBinService.preprocess_for_pixelbin(image_bytes)
            if preprocessed:
                image_bytes = preprocessed
                statuses.append("✅ Предобработка выполнена")
            else:
                statuses.append("ℹ️ Предобработка пропущена")

            statuses.append("================================================================================")
            statuses.append(f"🔬 ДИАГНОСТИКА С ТАЙМАУТОМ {sam3_timeout} СЕКУНД")
            statuses.append("================================================================================")

            sam3_result = run_sam3_pipeline(image_bytes, selected_diseases, timeout=sam3_timeout)
            combined_statuses = statuses + sam3_result.get('statuses', [])
            
            # Создаём изображение с наложенными масками на ОРИГИНАЛЬНОЕ фото
            overlay_image = None
            mask_results = sam3_result.get('mask_results', {})
            if mask_results:
                # Используем оригинальное изображение для наложения масок
                # Маски будут масштабированы под размер оригинала
                overlay_image = create_sam3_overlay_image(original_image_bytes, mask_results)
                if overlay_image:
                    logger.info("✅ Изображение с масками SAM3 создано на оригинальном фото")
                else:
                    logger.warning("⚠️ Не удалось создать изображение с масками")

            pixelbin_images = [{
                'type': 'sam3',
                'sam3_results': mask_results,
                'statuses': combined_statuses,
                'timeout': sam3_timeout,
                'diseases': list(selected_diseases.keys()),
                'message': 'SAM3 анализ с масками',
                'overlay_image': overlay_image  # Готовое изображение с наложенными масками
            }]
            analysis_method = "sam3"
            use_heuristics = False
            pixelbin_attempts.append("sam3")

        else:
            try:
                # Готовим варианты для Pixelbin: оригинал + препроцесс
                variants = [("pixelbin-original", image_bytes, filename)]
                preprocessed = PixelBinService.preprocess_for_pixelbin(image_bytes)
                if preprocessed:
                    variants.append(("pixelbin-preprocessed", preprocessed, "image-preprocessed.jpg"))
                
                # Отправляем в Pixelbin API (приоритет: оригинал, затем препроцесс)
                pixelbin_result = None
                for variant_name, variant_bytes, variant_filename in variants:
                    pixelbin_attempts.append(variant_name)
                    pixelbin_result = PixelBinService.upload_image(variant_bytes, variant_filename)
                    
                    # Если лимит/блок — дальше нет смысла пытаться
                    if pixelbin_result and pixelbin_result.get('error') in ['usage_limit_exceeded', 'rate_limit_exceeded']:
                        use_heuristics = True
                        pixelbin_result = None
                        analysis_method = "heuristics"
                        break
                    
                    # Если ошибка валидации/прочие — пробуем следующий вариант
                    if pixelbin_result and pixelbin_result.get('error'):
                        logger.warning(f"Pixelbin попытка {variant_name} вернула ошибку {pixelbin_result.get('error')}, пробуем следующий вариант")
                        pixelbin_result = None
                        continue
                    
                    # Успешная постановка задачи
                    if pixelbin_result and '_id' in pixelbin_result:
                        job_id = pixelbin_result['_id']
                        logger.info(f"Pixelbin ({variant_name}): задача создана, job_id: {job_id}")
                        
                        final_result = PixelBinService.check_status(job_id, max_attempts=10, delay=3)
                        
                        if final_result and final_result.get('status') == 'SUCCESS':
                            pixelbin_images = extract_images_from_pixelbin_response(final_result)
                            logger.info(f"Pixelbin ({variant_name}): получено {len(pixelbin_images)} изображений")
                            analysis_method = "pixelbin"
                            break
                        else:
                            if final_result and final_result.get('error'):
                                error_type = final_result.get('error')
                                status_code = final_result.get('status_code', 0)
                                logger.warning(f"Pixelbin ({variant_name}): ошибка API при проверке статуса ({error_type}, {status_code}), пробуем следующий вариант")
                            else:
                                logger.warning(f"Pixelbin ({variant_name}): задача не завершена или завершилась с ошибкой, пробуем следующий вариант")
                            pixelbin_result = None
                            continue
                
                if not pixelbin_images:
                    # Все попытки Pixelbin не дали результата — эвристики
                    logger.warning("Pixelbin: все попытки не дали результата, переключаемся на эвристики")
                    use_heuristics = True
                    analysis_method = "heuristics"
            except Exception as e:
                logger.warning(f"Ошибка при работе с Pixelbin API: {e}, используем эвристики")
                # При любой ошибке используем эвристики
                use_heuristics = True
                analysis_method = "heuristics"
        
        # Генерируем текстовый отчёт
        report = generate_report_with_llm(skin_data, llm_provider, text_model, temperature, language)
        
        # Если используем эвристики, генерируем данные с учётом отчёта и сегментации
        if use_heuristics:
            logger.info("Генерация эвристического анализа с учётом текстового отчёта и сегментации")
            # Передаем image_bytes для сегментации
            heuristic_data = generate_heuristic_analysis(skin_data, report, image_bytes)
            
            # Формируем сообщение о методах
            methods_used = heuristic_data.get('methods_used', [])
            primary_method = heuristic_data.get('primary_method', 'Простые эвристики')
            
            if methods_used:
                methods_text = ", ".join(methods_used)
                message = f'Использован эвристический анализ: {methods_text}'
            else:
                message = 'Использован эвристический анализ с простыми эвристиками'
            
            pixelbin_images = [{
                'type': 'heuristic',
                'heuristic_data': heuristic_data,
                'message': message,
                'primary_method': primary_method,
                'methods_used': methods_used
            }]
            analysis_method = f"heuristics ({primary_method})"
        
        return jsonify({
            "success": True,
            "data": skin_data,
            "report": report,
            "provider": used_provider,
            "model": used_model,
            "config": config,
            "pixelbin_images": pixelbin_images,  # Добавляем изображения из Pixelbin
            "use_heuristics": use_heuristics,  # Флаг использования эвристики
            "analysis_method": analysis_method,
            "pixelbin_attempts": pixelbin_attempts
        })
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/proxy-image', methods=['GET'])
def proxy_image():
    """Прокси для загрузки изображений (Pixelbin/FAL) для обхода CORS"""
    try:
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({"error": "URL не предоставлен"}), 400
        
        # Разрешённые домены: Pixelbin и fal.media
        allowed_domains = ['delivery.pixelbin.io', 'pixelbin.io', 'fal.media', '.fal.media', 'v3b.fal.media']
        if not any(domain in image_url for domain in allowed_domains):
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

