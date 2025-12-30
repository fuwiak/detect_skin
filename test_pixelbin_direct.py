#!/usr/bin/env python3
"""
Прямое тестирование Pixelbin API
Проверяет, работает ли API и что он возвращает для данного изображения
"""

import os
import sys
import base64
import requests
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
PIXELBIN_ACCESS_TOKEN = os.getenv("PIXELBIN_ACCESS_TOKEN")
if not PIXELBIN_ACCESS_TOKEN:
    print("❌ Ошибка: PIXELBIN_ACCESS_TOKEN не найден в переменных окружения")
    sys.exit(1)

PIXELBIN_BASE_URL = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions"
PIXELBIN_BEARER_TOKEN = base64.b64encode(PIXELBIN_ACCESS_TOKEN.encode('utf-8')).decode('utf-8')
PIXELBIN_HEADERS = {
    "Authorization": f"Bearer {PIXELBIN_BEARER_TOKEN}",
}

def test_pixelbin_upload(image_path: str):
    """Тест загрузки изображения в Pixelbin"""
    print("=" * 80)
    print("ТЕСТ 1: Загрузка изображения в Pixelbin API")
    print("=" * 80)
    
    if not Path(image_path).exists():
        print(f"❌ Ошибка: Файл не найден: {image_path}")
        return None
    
    print(f"📷 Изображение: {image_path}")
    print(f"📦 Размер: {Path(image_path).stat().st_size:,} байт")
    
    # Читаем изображение
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Определяем MIME тип
    ext = Path(image_path).suffix.lower()
    mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
    filename = Path(image_path).name
    
    url = f"{PIXELBIN_BASE_URL}/skinAnalysisInt/generate"
    
    files = {
        'input.image': (filename, image_data, mime_type)
    }
    
    print(f"\n🌐 URL: {url}")
    print(f"📋 Headers: Authorization: Bearer {PIXELBIN_BEARER_TOKEN[:20]}...")
    print(f"📋 Files: {filename} ({len(image_data):,} bytes, {mime_type})")
    print("\n🚀 Отправка запроса...")
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=PIXELBIN_HEADERS, files=files, timeout=60)
        elapsed_time = time.time() - start_time
        
        print(f"\n⏱️  Время ответа: {elapsed_time:.2f} секунд")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print("\n✅ Успешный ответ от Pixelbin API:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            job_id = result.get('_id')
            status = result.get('status')
            
            print(f"\n📋 Job ID: {job_id}")
            print(f"📋 Status: {status}")
            
            if 'urls' in result and 'get' in result['urls']:
                print(f"📋 Status URL: {result['urls']['get']}")
            
            return result
        else:
            print(f"\n❌ Ошибка API: {response.status_code}")
            print(f"Response: {response.text}")
            
            try:
                error_data = response.json()
                print("\nДетали ошибки:")
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                pass
            
            return None
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_pixelbin_status(job_id: str, max_attempts: int = 10, delay: int = 3):
    """Тест проверки статуса задачи"""
    if not job_id:
        print("\n⚠️  Job ID не предоставлен, пропуск проверки статуса")
        return None
    
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Проверка статуса задачи")
    print("=" * 80)
    
    status_url = f"{PIXELBIN_BASE_URL}/{job_id}"
    print(f"🌐 URL: {status_url}")
    print(f"⏱️  Максимум попыток: {max_attempts}, задержка: {delay} секунд\n")
    
    for attempt in range(1, max_attempts + 1):
        print(f"Попытка {attempt}/{max_attempts}...")
        
        try:
            response = requests.get(status_url, headers=PIXELBIN_HEADERS, timeout=30)
            print(f"   Status Code: {response.status_code}")
            
            if response.ok:
                result = response.json()
                status = result.get('status', 'UNKNOWN')
                print(f"   Status: {status}")
                
                if status == 'SUCCESS':
                    print("\n✅ Задача завершена успешно!")
                    print("\nПолный ответ:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    
                    # Проверяем наличие данных
                    if 'output' in result:
                        output = result.get('output', {})
                        skin_data = output.get('skinData', {})
                        concerns = skin_data.get('concerns', [])
                        print(f"\n📊 Найдено проблем: {len(concerns)}")
                        
                        if concerns:
                            print("\nПроблемы:")
                            for concern in concerns:
                                print(f"  - {concern.get('name', 'N/A')}: {concern.get('value', 0)}")
                        else:
                            print("\n⚠️  Проблем не найдено (возможно, кожа в хорошем состоянии)")
                    
                    return result
                elif status == 'FAILURE':
                    print("\n❌ Задача завершилась с ошибкой")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    return result
                elif status in ['ACCEPTED', 'PREPARING', 'PROCESSING']:
                    if attempt < max_attempts:
                        print(f"   ⏳ Задача обрабатывается, ждём {delay} секунд...")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"\n⏳ Задача всё ещё обрабатывается после {max_attempts} попыток")
                        return result
            else:
                print(f"\n❌ Ошибка: {response.status_code}")
                print(response.text[:500])
                if attempt < max_attempts:
                    time.sleep(delay)
                    continue
                return None
                
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            if attempt < max_attempts:
                time.sleep(delay)
                continue
            return None
    
    return None

def main():
    """Главная функция"""
    image_path = sys.argv[1] if len(sys.argv) > 1 else "img/18.png"
    
    print("\n" + "=" * 80)
    print("ПРЯМОЕ ТЕСТИРОВАНИЕ PIXELBIN API")
    print("=" * 80)
    print(f"📷 Изображение: {image_path}")
    print(f"🔑 PIXELBIN_ACCESS_TOKEN: {'✅ установлен' if PIXELBIN_ACCESS_TOKEN else '❌ не найден'}")
    print("=" * 80 + "\n")
    
    # Тест 1: Загрузка
    result = test_pixelbin_upload(image_path)
    
    # Тест 2: Проверка статуса
    if result and '_id' in result:
        job_id = result['_id']
        print(f"\n⏳ Ожидание 3 секунды перед проверкой статуса...")
        time.sleep(3)
        final_result = test_pixelbin_status(job_id, max_attempts=10, delay=5)
        
        if final_result and final_result.get('status') == 'SUCCESS':
            print("\n" + "=" * 80)
            print("✅ PIXELBIN API РАБОТАЕТ")
            print("=" * 80)
            
            # Проверяем, есть ли результаты
            if 'output' in final_result:
                output = final_result.get('output', {})
                skin_data = output.get('skinData', {})
                concerns = skin_data.get('concerns', [])
                
                if concerns:
                    print(f"📊 Найдено проблем: {len(concerns)}")
                    print("✅ API вернул результаты для данного изображения")
                else:
                    print("⚠️  API вернул успешный ответ, но проблем не найдено")
                    print("   Это может означать, что кожа в хорошем состоянии")
            else:
                print("⚠️  API вернул успешный ответ, но нет данных output")
        elif final_result and final_result.get('status') == 'FAILURE':
            print("\n" + "=" * 80)
            print("❌ PIXELBIN API ВЕРНУЛ ОШИБКУ")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("⚠️  НЕ УДАЛОСЬ ПОЛУЧИТЬ ФИНАЛЬНЫЙ СТАТУС")
            print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ НЕ УДАЛОСЬ ЗАГРУЗИТЬ ИЗОБРАЖЕНИЕ В PIXELBIN")
        print("=" * 80)
    
    print()

if __name__ == "__main__":
    main()

