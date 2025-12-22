"""
Сервис для генерации отчетов через LLM
"""
import json
import logging
import requests
from typing import Dict

from app.config import settings

logger = logging.getLogger(__name__)


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
    if settings.openrouter_api_key:
        models_to_try = [model]  # Пробуем запрошенную модель
        
        for model_to_use in models_to_try:
            try:
                url = settings.openrouter_api_url
                headers = {
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
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

