"""
Сервис для работы с OpenRouter API
"""
import json
import logging
import requests
from typing import Dict, Optional

from app.config import settings
from app.utils.parsing import parse_skin_analysis_from_text

logger = logging.getLogger(__name__)


def analyze_image_with_openrouter(image_base64: str, model: str, temperature: float, max_tokens: int) -> Optional[Dict]:
    """Анализ изображения через OpenRouter API"""
    if not settings.openrouter_api_key:
        logger.warning("OpenRouter API key not found")
        return None
    
    try:
        url = settings.openrouter_api_url
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
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

ДОПОЛНИТЕЛЬНО определи:
9. gender - пол человека на фото: "мужчина" или "женщина"
10. estimated_age - предположительный возраст в годах (целое число)

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
  "gender": "мужчина" или "женщина",
  "estimated_age": число,
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

ДОПОЛНИТЕЛЬНО определи:
9. gender - пол человека на фото: "мужчина" или "женщина"
10. estimated_age - предположительный возраст в годах (целое число)

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

