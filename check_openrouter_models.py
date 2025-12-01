#!/usr/bin/env python3
"""
Скрипт для проверки доступных моделей в OpenRouter
"""
import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    print("❌ OPENROUTER_API_KEY не найден в .env")
    exit(1)

print("🔍 Получение списка моделей из OpenRouter...")
print("="*80)

try:
    url = "https://openrouter.ai/api/v1/models"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        models = response.json()
        all_models = models.get('data', [])
        
        print(f"✅ Всего моделей: {len(all_models)}\n")
        
        # Модели Groq
        groq_models = [m for m in all_models if 'groq' in m.get('id', '').lower()]
        print(f"📦 Модели Groq: {len(groq_models)}")
        for model in groq_models[:10]:
            model_id = model.get('id', '')
            supports_vision = model.get('context_length', 0) > 0
            print(f"   - {model_id}")
        if len(groq_models) > 10:
            print(f"   ... и ещё {len(groq_models) - 10}")
        print()
        
        # Vision модели
        vision_keywords = ['vision', 'gemini', 'claude', 'gpt-4-vision']
        vision_models = []
        for model in all_models:
            model_id = model.get('id', '').lower()
            if any(kw in model_id for kw in vision_keywords):
                vision_models.append(model.get('id', ''))
        
        print(f"👁️  Vision модели (примеры): {len(vision_models)}")
        for model_id in vision_models[:15]:
            print(f"   - {model_id}")
        if len(vision_models) > 15:
            print(f"   ... и ещё {len(vision_models) - 15}")
        print()
        
        # Проверяем конкретные модели
        test_models = [
            "groq/llama-3.2-90b-vision-preview",
            "meta-llama/llama-3.2-90b-vision-preview",
            "google/gemini-pro-vision",
            "google/gemini-flash-1.5"
        ]
        
        print("🔍 Проверка конкретных моделей:")
        for test_model in test_models:
            found = any(test_model in m.get('id', '') for m in all_models)
            status = "✅" if found else "❌"
            print(f"   {status} {test_model}")
        
    else:
        print(f"❌ Ошибка: HTTP {response.status_code}")
        print(f"Ответ: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")











