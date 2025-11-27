#!/usr/bin/env python3
"""
Тесты для проверки работы Groq и OpenRouter API
"""
import os
import sys
import base64
import requests
from dotenv import load_dotenv
import json

# Загружаем переменные окружения
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def create_test_image_base64():
    """Создаёт тестовое изображение в base64 (1x1 пиксель PNG)"""
    # Минимальный PNG изображение 1x1 пиксель (белый)
    png_data = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    )
    return base64.b64encode(png_data).decode('utf-8')


def test_groq_api_connection():
    """Тест 1: Проверка подключения к Groq API"""
    print("\n" + "="*80)
    print("ТЕСТ 1: Проверка подключения к Groq API")
    print("="*80)
    
    if not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY не найден в .env файле")
        print("   Пропускаем тесты Groq")
        return None
    
    if GROQ_API_KEY.strip() == "":
        print("⚠️  GROQ_API_KEY пустой")
        print("   Пропускаем тесты Groq")
        return None
    
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Подключение успешно!")
            print(f"   Доступно моделей: {len(models.get('data', []))}")
            print(f"   Примеры моделей:")
            for model in models.get('data', [])[:3]:
                print(f"     - {model.get('id', 'N/A')}")
            return True
        elif response.status_code == 403:
            print(f"⚠️  Доступ запрещён (HTTP 403)")
            print(f"   Возможные причины:")
            print(f"   - Неверный API ключ")
            print(f"   - Проблемы с сетью/прокси")
            print(f"   - IP адрес заблокирован")
            print(f"   Проверьте ключ на https://console.groq.com/keys")
            return False
        else:
            print(f"❌ Ошибка подключения: HTTP {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def test_groq_text_completion():
    """Тест 2: Проверка текстового completion через Groq"""
    print("\n" + "="*80)
    print("ТЕСТ 2: Проверка текстового completion через Groq")
    print("="*80)
    
    if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
        print("⚠️  Пропущен (нет API ключа)")
        return None
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-70b-versatile",
            "messages": [
                {
                    "role": "user",
                    "content": "Скажи 'Тест успешен' на русском языке"
                }
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Completion успешен!")
            print(f"   Ответ модели: {content}")
            return True
        else:
            print(f"❌ Ошибка: HTTP {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_groq_vision_api():
    """Тест 3: Проверка vision API через Groq"""
    print("\n" + "="*80)
    print("ТЕСТ 3: Проверка vision API через Groq")
    print("="*80)
    
    if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
        print("⚠️  Пропущен (нет API ключа)")
        return None
    
    try:
        image_base64 = create_test_image_base64()
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.2-90b-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Опиши это изображение одним словом"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Vision API работает!")
            print(f"   Ответ модели: {content[:100]}")
            return True
        else:
            print(f"❌ Ошибка: HTTP {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_openrouter_api_connection():
    """Тест 4: Проверка подключения к OpenRouter API"""
    print("\n" + "="*80)
    print("ТЕСТ 4: Проверка подключения к OpenRouter API")
    print("="*80)
    
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY не найден в .env файле")
        return False
    
    try:
        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Подключение успешно!")
            print(f"   Доступно моделей: {len(models.get('data', []))}")
            print(f"   Примеры моделей:")
            for model in models.get('data', [])[:3]:
                print(f"     - {model.get('id', 'N/A')}")
            return True
        else:
            print(f"❌ Ошибка подключения: HTTP {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def get_openrouter_models():
    """Получить список доступных моделей OpenRouter"""
    if not OPENROUTER_API_KEY:
        return []
    
    try:
        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            models = response.json()
            return [m.get('id') for m in models.get('data', [])]
    except:
        pass
    return []


def get_groq_models_from_openrouter():
    """Получает модели Groq доступные через OpenRouter"""
    if not OPENROUTER_API_KEY:
        return []
    
    try:
        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            models = response.json()
            groq_models = []
            for model in models.get('data', []):
                model_id = model.get('id', '')
                if 'groq' in model_id.lower() or model_id.startswith('groq/'):
                    groq_models.append(model_id)
            return groq_models
    except:
        pass
    return []


def test_openrouter_text_completion():
    """Тест 5: Проверка текстового completion через OpenRouter (включая модели Groq)"""
    print("\n" + "="*80)
    print("ТЕСТ 5: Проверка текстового completion через OpenRouter")
    print("="*80)
    
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
        print("⚠️  Пропущен (нет API ключа)")
        return None
    
    # Получаем доступные модели
    available_models = get_openrouter_models()
    
    # Получаем модели Groq через OpenRouter
    groq_models = get_groq_models_from_openrouter()
    if groq_models:
        print(f"   Найдено моделей Groq в OpenRouter: {len(groq_models)}")
        print(f"   Примеры: {', '.join(groq_models[:3])}")
    
    # Пробуем сначала модели Groq через OpenRouter
    test_models = []
    if groq_models:
        # Ищем текстовые модели Groq
        for groq_model in groq_models:
            if 'vision' not in groq_model.lower() and 'instruct' in groq_model.lower():
                test_models.append(groq_model)
                break
        # Если не нашли, используем первую модель Groq
        if not test_models and groq_models:
            test_models.append(groq_models[0])
    
    # Добавляем другие модели как fallback
    test_models.extend([
        "meta-llama/llama-3.1-70b-instruct",
        "meta-llama/llama-3.1-8b-instruct",
        "google/gemini-pro",
        "anthropic/claude-3-haiku"
    ])
    
    model_to_use = None
    for model in test_models:
        if model in available_models or any(model in m for m in available_models):
            model_to_use = model
            break
    
    if not model_to_use and available_models:
        # Используем первую доступную модель
        model_to_use = available_models[0]
        print(f"   Используем модель: {model_to_use}")
    
    if not model_to_use:
        print("⚠️  Не найдено доступных моделей")
        return False
    
    if 'groq' in model_to_use.lower():
        print(f"   ✅ Используем модель Groq через OpenRouter: {model_to_use}")
    
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Skin Analyzer Test"
        }
        
        payload = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "user",
                    "content": "Скажи 'Тест успешен' на русском языке"
                }
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Completion успешен!")
            print(f"   Ответ модели: {content}")
            return True
        else:
            print(f"❌ Ошибка: HTTP {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_openrouter_vision_api():
    """Тест 6: Проверка vision API через OpenRouter (включая модели Groq)"""
    print("\n" + "="*80)
    print("ТЕСТ 6: Проверка vision API через OpenRouter")
    print("="*80)
    
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
        print("⚠️  Пропущен (нет API ключа)")
        return None
    
    # Получаем доступные модели
    available_models = get_openrouter_models()
    
    # Получаем модели Groq через OpenRouter
    groq_models = get_groq_models_from_openrouter()
    
    # Ищем vision модели Groq через OpenRouter
    vision_models = []
    if groq_models:
        for groq_model in groq_models:
            if 'vision' in groq_model.lower():
                vision_models.append(groq_model)
                print(f"   ✅ Найдена модель Groq vision через OpenRouter: {groq_model}")
                break
    
    # Добавляем другие vision модели как fallback
    vision_models.extend([
        "google/gemini-pro-vision",
        "google/gemini-flash-1.5",
        "anthropic/claude-3-opus",
        "anthropic/claude-3-sonnet",
        "openai/gpt-4-vision-preview"
    ])
    
    model_to_use = None
    for model in vision_models:
        if model in available_models or any(model in m for m in available_models):
            model_to_use = model
            break
    
    if not model_to_use:
        print("⚠️  Vision модели не найдены в OpenRouter")
        print("   Доступные модели с поддержкой изображений ограничены")
        print("   Пропускаем тест")
        return None
    
    if 'groq' in model_to_use.lower():
        print(f"   ✅ Используем модель Groq vision через OpenRouter: {model_to_use}")
    else:
        print(f"   Используем модель: {model_to_use}")
    
    try:
        image_base64 = create_test_image_base64()
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Skin Analyzer Test"
        }
        
        payload = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Опиши это изображение одним словом"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Vision API работает!")
            print(f"   Ответ модели: {content[:100]}")
            return True
        else:
            print(f"❌ Ошибка: HTTP {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_backend_integration():
    """Тест 7: Проверка интеграции с backend"""
    print("\n" + "="*80)
    print("ТЕСТ 7: Проверка интеграции с backend")
    print("="*80)
    
    # Пробуем разные порты
    ports_to_try = [5000, 5001, 5002, 8000]
    
    for port in ports_to_try:
        try:
            response = requests.get(f"http://localhost:{port}/api/config", timeout=2)
            
            if response.status_code == 200:
                config = response.json()
                print(f"✅ Backend сервер работает на порту {port}!")
                print(f"   Конфигурация: {json.dumps(config, indent=2, ensure_ascii=False)}")
                return True
            elif response.status_code == 404:
                # Сервер работает, но эндпоинт не найден
                print(f"⚠️  Сервер на порту {port} отвечает, но эндпоинт /api/config не найден")
                print("   Возможно используется другой сервер")
                continue
                
        except requests.exceptions.ConnectionError:
            continue
        except Exception as e:
            continue
    
    print("⚠️  Backend сервер не найден на портах 5000, 5001, 5002, 8000")
    print("   Запустите сервер: python app.py")
    return None


def main():
    """Запуск всех тестов"""
    print("\n" + "="*80)
    print("🧪 ТЕСТЫ API ДЛЯ SKIN ANALYZER")
    print("="*80)
    
    results = []
    
    # Тесты Groq
    results.append(("Groq Connection", test_groq_api_connection()))
    results.append(("Groq Text Completion", test_groq_text_completion()))
    results.append(("Groq Vision API", test_groq_vision_api()))
    
    # Тесты OpenRouter
    results.append(("OpenRouter Connection", test_openrouter_api_connection()))
    results.append(("OpenRouter Text Completion", test_openrouter_text_completion()))
    results.append(("OpenRouter Vision API", test_openrouter_vision_api()))
    
    # Тест backend
    results.append(("Backend Integration", test_backend_integration()))
    
    # Итоги
    print("\n" + "="*80)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*80)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    total = len(results)
    
    for name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⏭️  SKIP"
        print(f"{status} - {name}")
    
    print("\n" + "-"*80)
    print(f"Пройдено: {passed}/{total} тестов")
    if failed > 0:
        print(f"Провалено: {failed}/{total} тестов")
    if skipped > 0:
        print(f"Пропущено: {skipped}/{total} тестов")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        return 0
    elif failed == 0 and skipped > 0:
        print("\n✅ ВСЕ ВОЗМОЖНЫЕ ТЕСТЫ ПРОЙДЕНЫ (некоторые пропущены)")
        return 0
    else:
        print("\n⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print("\n💡 Рекомендации:")
        if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
            print("   - Добавьте GROQ_API_KEY в .env файл")
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
            print("   - Добавьте OPENROUTER_API_KEY в .env файл")
        return 1


if __name__ == "__main__":
    sys.exit(main())


