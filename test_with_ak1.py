#!/usr/bin/env python3
"""
Скрипт для проверки Pixelbin API endpoint с изображением ak1.jpeg
Использует конфигурацию из dupa.py
"""

import base64
import requests
import json
from pathlib import Path

# --- CONFIGURATION (из dupa.py строки 32-40) ---
ACCESS_TOKEN = "c5e15df7-73a6-4796-ac07-b3b6a6ccfb97"
BASE_URL = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions"

# Convert access token to bearer token using base64 encoding
BEARER_TOKEN = base64.b64encode(ACCESS_TOKEN.encode('utf-8')).decode('utf-8')

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
}

ENDPOINT = f"{BASE_URL}/skinAnalysisInt/generate"

# Путь к изображению
IMAGE_PATH = "/Users/user/Downloads/ak1.jpeg"

def test_endpoint_with_image():
    """Тест endpoint с изображением ak1.jpeg"""
    print("=" * 60)
    print("ТЕСТ PIXELBIN ENDPOINT С ИЗОБРАЖЕНИЕМ ak1.jpeg")
    print("=" * 60)
    print(f"\nBASE_URL: {BASE_URL}")
    print(f"ENDPOINT: {ENDPOINT}")
    print(f"Изображение: {IMAGE_PATH}\n")
    
    # Проверка существования файла
    image_path = Path(IMAGE_PATH)
    if not image_path.exists():
        print(f"❌ ОШИБКА: Файл не найден: {IMAGE_PATH}")
        return False
    
    file_size = image_path.stat().st_size
    print(f"✅ Файл найден")
    print(f"   Размер: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
    
    # Чтение изображения
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        print(f"✅ Изображение прочитано: {len(image_data):,} bytes\n")
    except Exception as e:
        print(f"❌ ОШИБКА при чтении файла: {e}")
        return False
    
    # Подготовка запроса
    files = {
        'input.image': (image_path.name, image_data, 'image/jpeg')
    }
    
    print("Отправка POST запроса к Pixelbin API...")
    print(f"URL: {ENDPOINT}")
    print(f"Headers: Authorization: Bearer {BEARER_TOKEN[:20]}...")
    print(f"File: {image_path.name} ({len(image_data):,} bytes)\n")
    
    # Отправка запроса
    try:
        response = requests.post(ENDPOINT, headers=HEADERS, files=files, timeout=60)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'content-length', 'date']:
                print(f"  {key}: {value}")
        
        if response.ok:
            try:
                result = response.json()
                print("\n" + "=" * 60)
                print("✅ УСПЕШНЫЙ ОТВЕТ ОТ API")
                print("=" * 60)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                # Парсинг важных полей
                print("\n" + "=" * 60)
                print("РАСПАРСЕННЫЕ ДАННЫЕ")
                print("=" * 60)
                if '_id' in result:
                    print(f"📋 Job ID: {result['_id']}")
                if 'status' in result:
                    print(f"📋 Status: {result['status']}")
                if 'urls' in result and 'get' in result['urls']:
                    print(f"📋 Result URL: {result['urls']['get']}")
                if 'input' in result and 'image' in result['input']:
                    print(f"📋 Uploaded Image URL: {result['input']['image']}")
                if 'createdAt' in result:
                    print(f"📋 Created At: {result['createdAt']}")
                if 'retention' in result:
                    print(f"📋 Retention: {result['retention']}")
                
                # Сохранение результата в файл
                output_file = "ak1_test_result.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Результат сохранен в: {output_file}")
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"\n❌ ОШИБКА: Ответ не является валидным JSON")
                print(f"Response text: {response.text[:500]}")
                return None
        else:
            print("\n" + "=" * 60)
            print(f"❌ ОШИБКА API: {response.status_code}")
            print("=" * 60)
            print(f"Response: {response.text}")
            
            # Попытка распарсить ошибку
            try:
                error_data = response.json()
                print(f"\nРаспарсенная ошибка:")
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                pass
            
            return None
            
    except requests.exceptions.Timeout:
        print(f"\n❌ ОШИБКА: Таймаут запроса (превышено 60 секунд)")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ОШИБКА: Проблема с подключением")
        print(f"Детали: {e}")
        return None
    except Exception as e:
        print(f"\n❌ НЕОЖИДАННАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_status(job_id: str):
    """Проверка статуса задачи"""
    if not job_id:
        return None
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА СТАТУСА ЗАДАЧИ")
    print("=" * 60)
    
    status_url = f"{BASE_URL}/{job_id}"
    print(f"URL: {status_url}\n")
    
    try:
        response = requests.get(status_url, headers=HEADERS, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print(f"\n✅ Статус задачи:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if 'status' in result:
                print(f"\n📊 Текущий статус: {result['status']}")
            
            return result
        else:
            print(f"\n❌ Ошибка: {response.status_code}")
            print(response.text[:500])
            return None
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return None

def main():
    """Главная функция"""
    print("\n")
    
    # Тест загрузки изображения
    result = test_endpoint_with_image()
    
    # Проверка статуса, если есть job_id
    if result and '_id' in result:
        import time
        print("\n⏳ Ожидание 3 секунды перед проверкой статуса...")
        time.sleep(3)
        check_status(result['_id'])
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()

