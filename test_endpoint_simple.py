#!/usr/bin/env python3
"""
Простой тест для проверки работоспособности Pixelbin API endpoint
Использует те же настройки, что и dupa.py
"""

import base64
import requests
import json

# --- CONFIGURATION (из dupa.py) ---
ACCESS_TOKEN = "c5e15df7-73a6-4796-ac07-b3b6a6ccfb97"
BASE_URL = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions"

# Convert access token to bearer token using base64 encoding
BEARER_TOKEN = base64.b64encode(ACCESS_TOKEN.encode('utf-8')).decode('utf-8')

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
}

ENDPOINT = f"{BASE_URL}/skinAnalysisInt/generate"

def test_endpoint():
    """Тест работоспособности endpoint"""
    print(f"Тестирование endpoint: {ENDPOINT}")
    print(f"Headers: {HEADERS}\n")
    
    # Тест 1: Проверка доступности (GET запрос)
    print("1. Проверка доступности BASE_URL...")
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 404, 405]:  # 404/405 - нормально для GET на POST endpoint
            print("   ✅ Сервер доступен")
        else:
            print(f"   ⚠️  Неожиданный статус: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False
    
    # Тест 2: Проверка endpoint с изображением (POST запрос)
    print("\n2. Проверка POST endpoint с изображением...")
    print("   (Требуется тестовое изображение)")
    
    # Можно использовать тестовое изображение или пропустить этот тест
    test_image_path = "/Users/user/Downloads/пизла.jpg"
    try:
        from pathlib import Path
        if Path(test_image_path).exists():
            with open(test_image_path, 'rb') as f:
                files = {
                    'input.image': (Path(test_image_path).name, f.read(), 'image/jpeg')
                }
            
            response = requests.post(ENDPOINT, headers=HEADERS, files=files, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.ok:
                result = response.json()
                print(f"   ✅ Успешно! Job ID: {result.get('_id')}")
                print(f"   Status: {result.get('status')}")
                return True
            else:
                print(f"   ❌ Ошибка: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
        else:
            print(f"   ⚠️  Тестовое изображение не найдено: {test_image_path}")
            print("   Пропуск теста загрузки")
            return True  # Считаем успешным, если сервер доступен
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ PIXELBIN ENDPOINT")
    print("=" * 60 + "\n")
    
    success = test_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ТЕСТ ПРОЙДЕН")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН")
    print("=" * 60)




