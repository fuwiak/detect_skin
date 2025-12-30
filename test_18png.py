#!/usr/bin/env python3
"""
Скрипт для проверки Pixelbin API endpoint с изображением
Использует конфигурацию из dupa.py
Принимает путь к изображению через аргумент командной строки
Результаты сохраняются в папку output/ с именем, связанным с входным файлом
"""

import os
import base64
import requests
import json
from pathlib import Path
import time
import argparse
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (если есть)
load_dotenv()

# --- CONFIGURATION из переменных окружения ---
ACCESS_TOKEN = os.getenv("PIXELBIN_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    print("❌ ОШИБКА: PIXELBIN_ACCESS_TOKEN не найден в переменных окружения.")
    print("   Установите его в .env файле или Railway variables.")
    sys.exit(1)

BASE_URL = "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions"

# Convert access token to bearer token using base64 encoding
BEARER_TOKEN = base64.b64encode(ACCESS_TOKEN.encode('utf-8')).decode('utf-8')

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
}

ENDPOINT = f"{BASE_URL}/skinAnalysisInt/generate"

# Папка для результатов
OUTPUT_DIR = Path("output")

def test_endpoint_with_image(image_path: Path, output_file: Path):
    """Тест endpoint с изображением"""
    print("=" * 60)
    print("ТЕСТ PIXELBIN ENDPOINT")
    print("=" * 60)
    print(f"\nBASE_URL: {BASE_URL}")
    print(f"ENDPOINT: {ENDPOINT}")
    print(f"Изображение: {image_path}")
    print(f"Выходной файл: {output_file}\n")
    
    # Проверка существования файла
    if not image_path.exists():
        print(f"❌ ОШИБКА: Файл не найден: {image_path}")
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
    
    # Определение MIME типа на основе расширения
    mime_type = 'image/png' if image_path.suffix.lower() == '.png' else 'image/jpeg'
    
    # Подготовка запроса
    files = {
        'input.image': (image_path.name, image_data, mime_type)
    }
    
    print("Отправка POST запроса к Pixelbin API...")
    print(f"URL: {ENDPOINT}")
    print(f"Headers: Authorization: Bearer {BEARER_TOKEN[:20]}...")
    print(f"File: {image_path.name} ({len(image_data):,} bytes, {mime_type})\n")
    
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
                # Создаём папку output если её нет
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
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

def check_status(job_id: str, max_attempts: int = 5, delay: int = 3):
    """Проверка статуса задачи с повторными попытками"""
    if not job_id:
        return None
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА СТАТУСА ЗАДАЧИ")
    print("=" * 60)
    
    status_url = f"{BASE_URL}/{job_id}"
    print(f"URL: {status_url}\n")
    
    for attempt in range(1, max_attempts + 1):
        print(f"Попытка {attempt}/{max_attempts}...")
        
        try:
            response = requests.get(status_url, headers=HEADERS, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.ok:
                result = response.json()
                print(f"\n✅ Статус задачи:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                if 'status' in result:
                    status = result['status']
                    print(f"\n📊 Текущий статус: {status}")
                    
                    if status == 'SUCCESS':
                        print("\n🎉 Задача успешно завершена!")
                        if 'output' in result:
                            print(f"📋 Output: {result['output']}")
                        return result
                    elif status == 'FAILURE':
                        print("\n❌ Задача завершилась с ошибкой")
                        if 'error' in result:
                            print(f"❌ Ошибка: {result['error']}")
                        return result
                    elif status in ['ACCEPTED', 'PREPARING', 'PROCESSING']:
                        if attempt < max_attempts:
                            print(f"⏳ Задача ещё обрабатывается (статус: {status}), ждём {delay} секунд...")
                            time.sleep(delay)
                            continue
                        else:
                            print(f"⏳ Задача всё ещё обрабатывается после {max_attempts} попыток")
                            return result
                
                return result
            else:
                print(f"\n❌ Ошибка: {response.status_code}")
                print(response.text[:500])
                if attempt < max_attempts:
                    print(f"⏳ Повтор через {delay} секунд...")
                    time.sleep(delay)
                    continue
                return None
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            if attempt < max_attempts:
                print(f"⏳ Повтор через {delay} секунд...")
                time.sleep(delay)
                continue
            return None
    
    return None

def get_output_filename(image_path: Path) -> Path:
    """Генерирует имя выходного файла на основе имени входного файла"""
    # Получаем имя файла без расширения
    stem = image_path.stem
    # Создаём имя выходного файла: имя_входного_файла_result.json
    output_filename = f"{stem}_result.json"
    return OUTPUT_DIR / output_filename

def main():
    """Главная функция"""
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(
        description='Тест Pixelbin API endpoint для анализа кожи',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Пример использования:\n  python test_18png.py /path/to/image.png'
    )
    parser.add_argument(
        'image_path',
        type=str,
        help='Путь к изображению для анализа'
    )
    
    args = parser.parse_args()
    
    # Преобразуем путь в Path объект
    image_path = Path(args.image_path).resolve()
    
    # Проверяем существование файла
    if not image_path.exists():
        print(f"❌ ОШИБКА: Файл не найден: {image_path}")
        sys.exit(1)
    
    # Генерируем имя выходного файла
    output_file = get_output_filename(image_path)
    
    print("\n")
    print("=" * 60)
    print("НАСТРОЙКИ")
    print("=" * 60)
    print(f"Входной файл: {image_path}")
    print(f"Выходной файл: {output_file}")
    print("=" * 60)
    print()
    
    # Тест загрузки изображения
    result = test_endpoint_with_image(image_path, output_file)
    
    # Проверка статуса, если есть job_id
    if result and '_id' in result:
        print("\n⏳ Ожидание 3 секунды перед проверкой статуса...")
        time.sleep(3)
        final_result = check_status(result['_id'], max_attempts=10, delay=5)
        
        # Если получили финальный результат, обновляем файл
        if final_result and output_file.exists():
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Финальный результат обновлен в: {output_file}")
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()

