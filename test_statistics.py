#!/usr/bin/env python3
"""
Тест статистики и комбинирования результатов
Проверяет, что статистика формируется для всех параметров из payload
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

def test_statistics(image_path: str, mode: str = "pixelbin"):
    """Тест статистики для всех параметров"""
    print("=" * 80)
    print(f"ТЕСТ СТАТИСТИКИ (режим: {mode})")
    print("=" * 80)
    
    if not Path(image_path).exists():
        print(f"❌ Ошибка: Файл не найден: {image_path}")
        return False
    
    # Читаем изображение
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Определяем MIME тип
    ext = Path(image_path).suffix.lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"
    
    # Все параметры из payload
    all_diseases = [
        "pimples", "pustules", "comedones", "rosacea", "irritation",
        "pigmentation", "freckles", "wrinkles", "fine lines",
        "skin lesion", "scars", "acne", "papules", "whiteheads", "blackheads",
        "moles", "warts", "papillomas", "skin tags", "acne scars",
        "post acne marks", "hydration", "pores", "eye_bags",
        "large_pores", "dark_circles", "texture", "skin_tone", "excess_oil",
        "moisture", "sensitivity", "edema"
    ]
    
    payload = {
        "image": f"data:{mime_type};base64,{image_base64}",
        "mode": mode,
        "config": {
            "language": "ru"
        },
        "sam3_timeout": 15,
        "sam3_diseases": all_diseases,
        "sam3_use_llm_preanalysis": True,
        "sam3_max_coverage_percent": 25
    }
    
    url = f"{RAILWAY_URL}/api/analyze"
    print(f"\n📷 Изображение: {image_path}")
    print(f"🌐 URL: {url}")
    print(f"🎯 Режим: {mode}")
    print(f"📋 Параметров в запросе: {len(all_diseases)}")
    print(f"⏱️  Timeout: 180 секунд\n")
    
    try:
        start_time = time.time()
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=180
        )
        elapsed_time = time.time() - start_time
        
        print(f"⏱️  Время ответа: {elapsed_time:.2f} секунд")
        print(f"📊 Status Code: {response.status_code}\n")
        
        if response.ok:
            result = response.json()
            
            # Проверяем наличие statistics
            if 'statistics' in result:
                statistics = result['statistics']
                print("✅ Статистика присутствует в ответе")
                
                # Проверяем indicators
                if 'indicators' in statistics:
                    indicators = statistics['indicators']
                    print(f"\n📊 Основные показатели ({len(indicators)}):")
                    for key, value in indicators.items():
                        print(f"   {key}: {value}%")
                else:
                    print("⚠️  indicators отсутствуют")
                
                # Проверяем problems
                if 'problems' in statistics:
                    problems = statistics['problems']
                    print(f"\n🔍 Проблемы найдены ({len(problems)}):")
                    for problem in problems[:10]:  # Показываем первые 10
                        print(f"   - {problem.get('name', 'N/A')}: {problem.get('value', 0)}%")
                    if len(problems) > 10:
                        print(f"   ... и ещё {len(problems) - 10} проблем")
                else:
                    print("⚠️  problems отсутствуют")
                
                # Проверяем, что все запрошенные параметры присутствуют
                print(f"\n📋 Проверка покрытия запрошенных параметров:")
                requested_set = set(all_diseases)
                found_in_stats = set()
                
                # Проверяем в indicators
                if 'indicators' in statistics:
                    for key in statistics['indicators'].keys():
                        found_in_stats.add(key)
                
                # Проверяем в problems
                if 'problems' in statistics:
                    for problem in statistics['problems']:
                        name = problem.get('name', '').lower().replace(' ', '_')
                        found_in_stats.add(name)
                
                # Маппинг для сравнения
                disease_mapping = {
                    'pimples': 'acne',
                    'pustules': 'acne',
                    'papules': 'acne',
                    'acne': 'acne',
                    'whiteheads': 'whiteheads',
                    'blackheads': 'blackheads',
                    'comedones': 'comedones',
                    'rosacea': 'rosacea',
                    'irritation': 'irritation',
                    'pigmentation': 'pigmentation',
                    'freckles': 'freckles',
                    'wrinkles': 'wrinkles',
                    'fine_lines': 'wrinkles',
                    'skin_lesion': 'skin_lesion',
                    'scars': 'scars',
                    'acne_scars': 'post_acne_scars',
                    'post_acne_marks': 'post_acne_scars',
                    'hydration': 'hydration',
                    'moisture': 'hydration',
                    'pores': 'pores',
                    'large_pores': 'pores',
                    'eye_bags': 'eye_bags',
                    'dark_circles': 'dark_circles',
                    'texture': 'texture',
                    'skin_tone': 'skin_tone',
                    'excess_oil': 'oiliness',
                    'oiliness': 'oiliness',
                    'sensitivity': 'sensitivity',
                    'edema': 'edema',
                    'moles': 'moles',
                    'warts': 'warts',
                    'papillomas': 'papillomas',
                    'skin_tags': 'skin_tags',
                }
                
                mapped_requested = set()
                for disease in requested_set:
                    mapped = disease_mapping.get(disease.replace(' ', '_'), disease.replace(' ', '_'))
                    mapped_requested.add(mapped)
                
                coverage = len(found_in_stats.intersection(mapped_requested))
                total = len(mapped_requested)
                coverage_percent = (coverage / total * 100) if total > 0 else 0
                
                print(f"   Покрыто: {coverage}/{total} ({coverage_percent:.1f}%)")
                
                if coverage_percent < 50:
                    print("   ⚠️  Низкое покрытие - не все параметры присутствуют в статистике")
                elif coverage_percent < 80:
                    print("   ⚠️  Среднее покрытие - некоторые параметры отсутствуют")
                else:
                    print("   ✅ Хорошее покрытие - большинство параметров присутствует")
                
            else:
                print("❌ Статистика отсутствует в ответе")
                print("Ответ:")
                print(json.dumps(result, indent=2, ensure_ascii=False)[:500])
                return False
            
            # Проверяем другие поля
            print(f"\n📊 Другие поля ответа:")
            print(f"   success: {result.get('success', 'N/A')}")
            print(f"   analysis_method: {result.get('analysis_method', 'N/A')}")
            if 'data' in result:
                data = result['data']
                print(f"   data keys: {list(data.keys())[:5]}...")
            if 'warning' in result and result['warning']:
                print(f"   ⚠️  warning: {result['warning'][:100]}...")
            
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(response.text[:500])
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция"""
    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ СТАТИСТИКИ И КОМБИНИРОВАНИЯ РЕЗУЛЬТАТОВ")
    print("=" * 80)
    print(f"Railway URL: {RAILWAY_URL}")
    print("=" * 80 + "\n")
    
    image_path = sys.argv[1] if len(sys.argv) > 1 else "img/18.png"
    mode = sys.argv[2] if len(sys.argv) > 2 else "pixelbin"
    
    results = {
        "pixelbin": False,
        "sam3": False
    }
    
    # Тест pixelbin режима
    if mode == "all" or mode == "pixelbin":
        print("\n" + "=" * 80)
        print("ТЕСТ 1: PIXELBIN РЕЖИМ")
        print("=" * 80)
        results["pixelbin"] = test_statistics(image_path, "pixelbin")
    
    # Тест sam3 режима
    if mode == "all" or mode == "sam3":
        print("\n" + "=" * 80)
        print("ТЕСТ 2: SAM3 РЕЖИМ")
        print("=" * 80)
        results["sam3"] = test_statistics(image_path, "sam3")
    
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
    exit(main())

