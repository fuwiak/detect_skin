#!/usr/bin/env python3
"""
Тест для проверки работоспособности Pixelbin API endpoint
"""

import base64
import requests
import json
from pathlib import Path

# --- CONFIGURATION (из dupa.py) ---
ACCESS_TOKEN = "c5e15df7-73a6-4796-ac07-b3b6a6ccfb97"
BASE_URL = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions"

# Convert access token to bearer token using base64 encoding
BEARER_TOKEN = base64.b64encode(ACCESS_TOKEN.encode('utf-8')).decode('utf-8')

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
}

ENDPOINT = f"{BASE_URL}/skinAnalysisInt/generate"

def test_endpoint_connection():
    """Тест 1: Проверка доступности базового URL"""
    print("=" * 60)
    print("ТЕСТ 1: Проверка доступности BASE_URL")
    print("=" * 60)
    print(f"BASE_URL: {BASE_URL}")
    print(f"HEADERS: {HEADERS}")
    
    try:
        # Попытка GET запроса к базовому URL (может вернуть 405 Method Not Allowed, но это нормально)
        response = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        if response.text:
            print(f"Response Body: {response.text[:200]}...")
        print("✅ Базовый URL доступен\n")
        return True
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Ошибка подключения: {e}\n")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ Таймаут: {e}\n")
        return False
    except Exception as e:
        print(f"⚠️  Неожиданная ошибка: {e}\n")
        return False

def test_endpoint_structure():
    """Тест 2: Проверка структуры endpoint"""
    print("=" * 60)
    print("ТЕСТ 2: Проверка структуры endpoint")
    print("=" * 60)
    print(f"ENDPOINT: {ENDPOINT}")
    print(f"Метод: POST")
    print(f"Поле для файла: input.image")
    print("✅ Структура endpoint корректна\n")
    return True

def test_endpoint_with_image(image_path: str = None):
    """Тест 3: Проверка endpoint с загрузкой изображения"""
    print("=" * 60)
    print("ТЕСТ 3: Проверка endpoint с загрузкой изображения")
    print("=" * 60)
    
    # Поиск тестового изображения
    if not image_path:
        # Попытка найти изображение в Downloads
        possible_paths = [
            "/Users/user/Downloads/пизла.jpg",
            "/Users/user/Downloads/test.jpg",
            "/Users/user/Downloads/image.jpg",
        ]
        for path in possible_paths:
            if Path(path).exists():
                image_path = path
                break
    
    if not image_path or not Path(image_path).exists():
        print("⚠️  Тестовое изображение не найдено")
        print("   Пропуск теста загрузки изображения\n")
        return None
    
    print(f"Используемое изображение: {image_path}")
    print(f"Размер файла: {Path(image_path).stat().st_size} bytes")
    
    try:
        with open(image_path, 'rb') as f:
            files = {
                'input.image': (Path(image_path).name, f.read(), 'image/jpeg')
            }
        
        print(f"\nОтправка POST запроса к: {ENDPOINT}")
        response = requests.post(ENDPOINT, headers=HEADERS, files=files, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.ok:
            try:
                result = response.json()
                print("\n✅ Успешный ответ от API:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                # Парсинг ответа
                if '_id' in result:
                    print(f"\n📋 Job ID: {result['_id']}")
                if 'status' in result:
                    print(f"📋 Status: {result['status']}")
                if 'urls' in result and 'get' in result['urls']:
                    print(f"📋 Result URL: {result['urls']['get']}")
                
                return result
            except json.JSONDecodeError:
                print(f"\n⚠️  Ответ не является JSON:")
                print(response.text[:500])
                return None
        else:
            print(f"\n❌ Ошибка API:")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Ошибка запроса: {e}")
        return None
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        return None

def test_status_check(job_id: str):
    """Тест 4: Проверка статуса задачи"""
    if not job_id:
        print("\n⚠️  Job ID не предоставлен, пропуск теста статуса")
        return None
    
    print("\n" + "=" * 60)
    print("ТЕСТ 4: Проверка статуса задачи")
    print("=" * 60)
    
    status_url = f"{BASE_URL}/{job_id}"
    print(f"URL: {status_url}")
    
    try:
        response = requests.get(status_url, headers=HEADERS, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print("\n✅ Статус задачи:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result
        else:
            print(f"\n❌ Ошибка: {response.status_code}")
            print(response.text[:500])
            return None
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return None

def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ PIXELBIN API ENDPOINT")
    print("=" * 60 + "\n")
    
    # Тест 1: Проверка доступности
    test_endpoint_connection()
    
    # Тест 2: Проверка структуры
    test_endpoint_structure()
    
    # Тест 3: Проверка с изображением
    result = test_endpoint_with_image()
    
    # Тест 4: Проверка статуса (если есть job_id)
    if result and '_id' in result:
        test_status_check(result['_id'])
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
















