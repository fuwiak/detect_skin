#!/usr/bin/env python3
"""
Прямое тестирование SAM3 API через fal_client
Проверяет, работает ли SAM3 и что он возвращает для данного изображения
"""

import os
import sys
import base64
import json
import time
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Проверка доступности fal_client
try:
    import fal_client
    FAL_AVAILABLE = True
except ImportError:
    print("❌ Ошибка: fal_client не установлен")
    print("   Установите: pip install fal-client")
    sys.exit(1)

# Проверка FAL_KEY
FAL_KEY = os.getenv("FAL_KEY")
if not FAL_KEY:
    print("❌ Ошибка: FAL_KEY не найден в переменных окружения")
    print("   Установите переменную окружения FAL_KEY")
    sys.exit(1)

# Устанавливаем FAL_KEY в окружение для fal_client
os.environ['FAL_KEY'] = FAL_KEY

print("✅ fal_client доступен")
print(f"✅ FAL_KEY: {'✅ установлен' if FAL_KEY else '❌ не найден'}")

# Импортируем константы из проекта
fastapi_app_path = os.path.join(os.path.dirname(__file__), 'fastapi_app')
if os.path.exists(fastapi_app_path):
    sys.path.insert(0, fastapi_app_path)
    try:
        from app.utils.constants import SAM3_ENHANCED_PROMPTS, SAM3_DISEASES_DEFAULT
        print("✅ Константы импортированы из проекта")
    except ImportError as e:
        print(f"⚠️  Не удалось импортировать константы: {e}")
        # Fallback если не можем импортировать
        SAM3_ENHANCED_PROMPTS = {}
        SAM3_DISEASES_DEFAULT = {
            "pimples": "Прыщи",
            "pustules": "Пустулы",
            "comedones": "Комедоны",
            "rosacea": "Розацеа",
            "irritation": "Раздражение",
            "pigmentation": "Пигментация",
            "freckles": "Веснушки",
            "wrinkles": "Морщины",
            "fine lines": "Мелкие морщины",
            "acne": "Акне",
            "papules": "Папулы",
            "blackheads": "Черные точки",
            "whiteheads": "Белые угри"
        }
else:
    # Fallback если fastapi_app не найден
    SAM3_ENHANCED_PROMPTS = {}
    SAM3_DISEASES_DEFAULT = {
        "pimples": "Прыщи",
        "pustules": "Пустулы",
        "comedones": "Комедоны",
        "rosacea": "Розацеа",
        "irritation": "Раздражение",
        "pigmentation": "Пигментация",
        "freckles": "Веснушки",
        "wrinkles": "Морщины",
        "fine lines": "Мелкие морщины"
    }

def test_sam3_segment(image_path: str, disease_key: str, disease_name: str, timeout: int = 15):
    """Тест сегментации одного заболевания через SAM3"""
    print(f"\n🔍 Тест: {disease_name.upper()} ({disease_key})")
    print(f"   Timeout: {timeout} секунд")
    
    try:
        # Загружаем изображение
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_data)
            tmp.flush()
            tmp_path = tmp.name
        
        # Генерируем промпт
        base_prompt = SAM3_ENHANCED_PROMPTS.get(disease_key, disease_key)
        prompt = f"Find and segment all instances of {disease_name.lower()} on the face"
        
        print(f"   Промпт: {prompt[:100]}...")
        print(f"   Загрузка изображения в fal_client...")
        
        # Загружаем изображение в fal_client
        start_time = time.time()
        image_url = fal_client.upload_file(tmp_path)
        upload_time = time.time() - start_time
        print(f"   ✅ Изображение загружено за {upload_time:.2f}с")
        
        # Вызываем SAM3
        print(f"   🚀 Вызов SAM3 API...")
        start_time = time.time()
        
        try:
            result = fal_client.subscribe(
                "fal-ai/sam-3/image",
                arguments={
                    "image_url": image_url,
                    "text_prompt": prompt
                },
                with_logs=False,
            )
            elapsed_time = time.time() - start_time
            
            print(f"   ⏱️  Время ответа: {elapsed_time:.2f} секунд")
            
            if result and isinstance(result, dict):
                masks = result.get('masks', [])
                print(f"   ✅ Успешно! Найдено масок: {len(masks)}")
                
                if masks:
                    print(f"   📊 Детали:")
                    for i, mask in enumerate(masks[:3]):  # Показываем первые 3
                        if isinstance(mask, dict):
                            score = mask.get('score', 0)
                            bbox = mask.get('bbox', [])
                            print(f"      Маска {i+1}: score={score:.3f}, bbox={bbox}")
                    if len(masks) > 3:
                        print(f"      ... и ещё {len(masks) - 3} масок")
                
                return result
            else:
                print(f"   ⚠️  Пустой результат")
                return None
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"   ❌ Ошибка после {elapsed_time:.2f}с: {e}")
            return None
        
        finally:
            # Удаляем временный файл
            try:
                os.unlink(tmp_path)
            except:
                pass
                
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_sam3_multiple_diseases(image_path: str, diseases: dict, timeout: int = 15, max_diseases: int = 5):
    """Тест сегментации нескольких заболеваний"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Сегментация нескольких заболеваний")
    print("=" * 80)
    
    results = {}
    total_start = time.time()
    
    # Ограничиваем количество заболеваний для теста
    test_diseases = dict(list(diseases.items())[:max_diseases])
    
    print(f"📋 Тестируем {len(test_diseases)} заболеваний:")
    for i, (key, name) in enumerate(test_diseases.items(), 1):
        print(f"   {i}. {name} ({key})")
    
    print(f"\n⏱️  Timeout на заболевание: {timeout} секунд")
    print(f"⏱️  Ожидаемое время: ~{len(test_diseases) * timeout} секунд\n")
    
    for idx, (disease_key, disease_name) in enumerate(test_diseases.items(), 1):
        print(f"\n[{idx}/{len(test_diseases)}] ", end="")
        result = test_sam3_segment(image_path, disease_key, disease_name, timeout)
        results[disease_key] = {
            'name': disease_name,
            'result': result,
            'masks_count': len(result.get('masks', [])) if result else 0
        }
    
    total_elapsed = time.time() - total_start
    
    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print(f"⏱️  Общее время: {total_elapsed:.2f} секунд")
    print(f"📊 Протестировано заболеваний: {len(results)}")
    
    found_diseases = sum(1 for r in results.values() if r['masks_count'] > 0)
    print(f"✅ Найдено заболеваний: {found_diseases}")
    print(f"❌ Не найдено: {len(results) - found_diseases}")
    
    print("\nДетали:")
    for disease_key, data in results.items():
        status = "✅" if data['masks_count'] > 0 else "❌"
        print(f"  {status} {data['name']}: {data['masks_count']} масок")
    
    return results

def main():
    """Главная функция"""
    image_path = sys.argv[1] if len(sys.argv) > 1 else "img/18.png"
    test_mode = sys.argv[2] if len(sys.argv) > 2 else "multiple"  # single, multiple
    
    print("\n" + "=" * 80)
    print("ПРЯМОЕ ТЕСТИРОВАНИЕ SAM3 API")
    print("=" * 80)
    print(f"📷 Изображение: {image_path}")
    print(f"🔑 FAL_KEY: {'✅ установлен' if FAL_KEY else '❌ не найден'}")
    print(f"🎯 Режим теста: {test_mode}")
    print("=" * 80 + "\n")
    
    if not Path(image_path).exists():
        print(f"❌ Ошибка: Файл не найден: {image_path}")
        sys.exit(1)
    
    if test_mode == "single":
        # Тест одного заболевания
        disease_key = sys.argv[3] if len(sys.argv) > 3 else "pimples"
        disease_name = SAM3_DISEASES_DEFAULT.get(disease_key, disease_key)
        
        print("=" * 80)
        print("ТЕСТ: Сегментация одного заболевания")
        print("=" * 80)
        
        result = test_sam3_segment(image_path, disease_key, disease_name, timeout=15)
        
        if result:
            masks = result.get('masks', [])
            print(f"\n✅ SAM3 РАБОТАЕТ")
            print(f"📊 Найдено масок: {len(masks)}")
            
            if masks:
                print("\n✅ SAM3 нашел проблемы на изображении")
            else:
                print("\n⚠️  SAM3 не нашел проблем (возможно, их нет на изображении)")
        else:
            print("\n❌ SAM3 НЕ РАБОТАЕТ или произошла ошибка")
    
    else:
        # Тест нескольких заболеваний
        diseases = SAM3_DISEASES_DEFAULT
        max_diseases = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 5
        
        results = test_sam3_multiple_diseases(image_path, diseases, timeout=15, max_diseases=max_diseases)
        
        # Итоговая оценка
        found_count = sum(1 for r in results.values() if r['masks_count'] > 0)
        
        print("\n" + "=" * 80)
        if found_count > 0:
            print("✅ SAM3 API РАБОТАЕТ")
            print(f"📊 Найдено проблем на изображении: {found_count} из {len(results)}")
        else:
            print("⚠️  SAM3 API РАБОТАЕТ, но проблем не найдено")
            print("   Это может означать:")
            print("   - Кожа в хорошем состоянии")
            print("   - Изображение не содержит тестируемых проблем")
            print("   - Промпты не подходят для данного изображения")
        print("=" * 80)
    
    print()

if __name__ == "__main__":
    main()

