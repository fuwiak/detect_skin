#!/usr/bin/env python3
"""
Тест эндпоинта /api/analyze на Railway
Проверяет работоспособность API после деплоя
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

# URL Railway (можно переопределить через переменную окружения)
RAILWAY_URL = os.getenv("RAILWAY_URL", "https://detectskin-production.up.railway.app")

def test_health_check():
    """Тест health check эндпоинта"""
    print("=" * 80)
    print("ТЕСТ 1: Health Check")
    print("=" * 80)
    
    try:
        url = f"{RAILWAY_URL}/api/health"
        print(f"URL: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print("✅ Health check успешен:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ Health check не прошёл: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Ошибка при проверке health: {e}")
        return False

def test_detailed_health():
    """Тест детального health check"""
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Детальный Health Check")
    print("=" * 80)
    
    try:
        url = f"{RAILWAY_URL}/api/health/detailed"
        print(f"URL: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print("✅ Детальный health check:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ Детальный health check не прошёл: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Ошибка при проверке детального health: {e}")
        return False

def load_test_image(image_path: str = None):
    """Загрузка тестового изображения"""
    if not image_path:
        possible_paths = [
            "/Users/user/detect_skin/img/18.png",
            "/Users/user/Downloads/test.jpg",
            "/Users/user/Downloads/image.jpg",
        ]
        for path in possible_paths:
            if Path(path).exists():
                image_path = path
                break
    
    if not image_path or not Path(image_path).exists():
        print("⚠️  Тестовое изображение не найдено, используем минимальный тест")
        # Создаём минимальное тестовое изображение (1x1 пиксель PNG)
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==", "image/png"
    else:
        print(f"📷 Используемое изображение: {image_path}")
        with open(image_path, 'rb') as f:
            image_data = f.read()
        test_image_base64 = base64.b64encode(image_data).decode('utf-8')
        print(f"📷 Размер изображения: {len(image_data):,} байт")
        
        # Определяем MIME тип
        ext = Path(image_path).suffix.lower()
        mime_type = "image/png" if ext == ".png" else "image/jpeg"
        return test_image_base64, mime_type

def test_analyze_endpoint_pixelbin(image_path: str = None):
    """Тест эндпоинта /api/analyze в режиме pixelbin"""
    print("\n" + "=" * 80)
    print("ТЕСТ 3: Эндпоинт /api/analyze (режим PIXELBIN)")
    print("=" * 80)
    
    test_image_base64, mime_type = load_test_image(image_path)
    
    # Подготовка запроса для pixelbin режима
    payload = {
        "image": f"data:{mime_type};base64,{test_image_base64}",
        "mode": "pixelbin",
        "config": {
            "language": "ru"
        }
    }
    
    return _test_analyze_request(payload, "pixelbin", 120)

def test_analyze_endpoint_sam3(image_path: str = None):
    """Тест эндпоинта /api/analyze в режиме SAM3"""
    print("\n" + "=" * 80)
    print("ТЕСТ 4: Эндпоинт /api/analyze (режим SAM3)")
    print("=" * 80)
    
    test_image_base64, mime_type = load_test_image(image_path)
    
    # Подготовка запроса для SAM3 режима
    payload = {
        "image": f"data:{mime_type};base64,{test_image_base64}",
        "mode": "sam3",
        "config": {
            "language": "ru"
        },
        "sam3_timeout": 5,  # Быстрое тестирование
        "sam3_diseases": [
            "pimples", "pustules", "comedones", "rosacea", "irritation",
            "pigmentation", "freckles", "wrinkles", "fine lines",
            "skin lesion", "scars", "acne", "papules", "whiteheads", "blackheads",
            "moles", "warts", "papillomas", "skin tags", "acne scars",
            "post acne marks", "hydration", "pores", "eye_bags", "input",
            "large_pores", "dark_circles", "texture", "skin_tone", "excess_oil",
            "moisture", "sensitivity", "edema"
        ],
        "sam3_use_llm_preanalysis": True,
        "sam3_max_coverage_percent": 25
    }
    
    print(f"📋 SAM3 параметры:")
    print(f"   - Timeout: {payload['sam3_timeout']} секунд")
    print(f"   - Заболеваний: {len(payload['sam3_diseases'])}")
    print(f"   - LLM pre-analysis: {payload['sam3_use_llm_preanalysis']}")
    print(f"   - Max coverage: {payload['sam3_max_coverage_percent']}%")
    
    return _test_analyze_request(payload, "sam3", 60)  # Быстрое тестирование

def _test_analyze_request(payload: dict, mode: str, timeout: int):
    """Внутренняя функция для выполнения запроса к /api/analyze"""
    url = f"{RAILWAY_URL}/api/analyze"
    print(f"\nURL: {url}")
    print(f"Mode: {mode}")
    print(f"Timeout: {timeout} секунд")
    print(f"Payload keys: {list(payload.keys())}")
    
    try:
        start_time = time.time()
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        elapsed_time = time.time() - start_time
        
        print(f"\n⏱️  Время ответа: {elapsed_time:.2f} секунд")
        print(f"Status Code: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print("\n✅ Запрос успешен!")
            print(f"Success: {result.get('success', 'N/A')}")
            print(f"Analysis Method: {result.get('analysis_method', 'N/A')}")
            
            if 'data' in result:
                data = result['data']
                if isinstance(data, dict):
                    print(f"Data keys: {list(data.keys())}")
                    # Показываем некоторые значения
                    for key in ['acne_score', 'pigmentation_score', 'wrinkles_grade', 'gender', 'estimated_age']:
                        if key in data:
                            print(f"  {key}: {data[key]}")
            
            if 'report' in result:
                report_preview = result['report'][:200] if result['report'] else "N/A"
                print(f"Report preview: {report_preview}...")
            
            if mode == "sam3" and 'pixelbin_images' in result:
                images = result['pixelbin_images']
                if images:
                    sam3_image = next((img for img in images if img.get('type') == 'sam3'), None)
                    if sam3_image:
                        print(f"\n📊 SAM3 результаты:")
                        if 'statuses' in sam3_image:
                            print(f"   Статусы: {len(sam3_image['statuses'])}")
                            for status in sam3_image['statuses'][-5:]:  # Последние 5
                                print(f"     - {status}")
                        if 'sam3_results' in sam3_image:
                            mask_results = sam3_image['sam3_results']
                            print(f"   Найдено заболеваний: {len(mask_results)}")
                            for disease, masks in mask_results.items():
                                if masks:
                                    print(f"     - {disease}: {len(masks)} масок")
            
            if 'warning' in result and result['warning']:
                print(f"\n⚠️  Warning: {result['warning']}")
            
            return True
        else:
            print(f"\n❌ Ошибка запроса: {response.status_code}")
            try:
                error_data = response.json()
                print("Детали ошибки:")
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(f"Response text: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n❌ Таймаут запроса (превышено {timeout} секунд)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Ошибка подключения: {e}")
        print(f"Проверьте, что сервис доступен по адресу: {RAILWAY_URL}")
        return False
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция"""
    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ RAILWAY ENDPOINT")
    print("=" * 80)
    print(f"Railway URL: {RAILWAY_URL}")
    print("=" * 80 + "\n")
    
    # Определяем режим тестирования из аргументов
    test_mode = sys.argv[2] if len(sys.argv) > 2 else "all"  # all, pixelbin, sam3
    image_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    results = {
        "health_check": False,
        "detailed_health": False,
        "analyze_pixelbin": False,
        "analyze_sam3": False
    }
    
    # Тест 1: Health check
    results["health_check"] = test_health_check()
    
    # Тест 2: Детальный health check
    results["detailed_health"] = test_detailed_health()
    
    # Тест 3: Analyze endpoint - pixelbin
    if test_mode in ["all", "pixelbin"]:
        results["analyze_pixelbin"] = test_analyze_endpoint_pixelbin(image_path)
    
    # Тест 4: Analyze endpoint - SAM3
    if test_mode in ["all", "sam3"]:
        results["analyze_sam3"] = test_analyze_endpoint_sam3(image_path)
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    for test_name, result in results.items():
        status = "✅ ПРОЙДЕН" if result else "❌ НЕ ПРОЙДЕН"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("=" * 80)
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
    print("=" * 80 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("""
Использование:
  python test_railway_endpoint.py [image_path] [mode]

Параметры:
  image_path  - Путь к тестовому изображению (опционально)
  mode        - Режим тестирования: all, pixelbin, sam3 (по умолчанию: all)

Примеры:
  python test_railway_endpoint.py
  python test_railway_endpoint.py /path/to/image.jpg
  python test_railway_endpoint.py /path/to/image.jpg sam3
  python test_railway_endpoint.py /path/to/image.jpg pixelbin

Переменные окружения:
  RAILWAY_URL - URL Railway сервиса (по умолчанию: https://detectskin-production.up.railway.app)
        """)
        exit(0)
    exit(main())

