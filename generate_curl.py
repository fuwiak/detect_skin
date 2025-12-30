#!/usr/bin/env python3
"""
Генератор curl команды для тестирования /api/analyze
Использование: python generate_curl.py [image_path] [railway_url] [mode]
"""

import sys
import base64
import json
from pathlib import Path

def generate_curl_command(image_path: str, railway_url: str = "https://detectskin-production.up.railway.app", mode: str = "pixelbin"):
    """Генерирует curl команду для тестирования"""
    
    # Читаем изображение
    if not Path(image_path).exists():
        print(f"❌ Ошибка: Файл не найден: {image_path}")
        return None
    
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Конвертируем в base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Определяем MIME тип
    ext = Path(image_path).suffix.lower()
    mime_type = "image/jpeg"
    if ext == ".png":
        mime_type = "image/png"
    elif ext in [".heic", ".heif"]:
        mime_type = "image/heic"
    
    # Формируем payload
    payload = {
        "image": f"data:{mime_type};base64,{image_base64}",
        "mode": mode,
        "config": {
            "language": "ru"
        },
        "sam3_timeout": 15,
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
    
    endpoint = f"{railway_url}/api/analyze"
    timeout = 180 if mode == "sam3" else 120
    
    # Сохраняем payload в файл
    payload_file = "/tmp/analyze_payload.json"
    with open(payload_file, 'w') as f:
        json.dump(payload, f, indent=2)
    
    # Генерируем curl команду
    curl_cmd = f"""curl -X POST "{endpoint}" \\
  -H "Content-Type: application/json" \\
  -d @{payload_file} \\
  --max-time {timeout} \\
  --connect-timeout 10 \\
  -w "\\n\\n⏱️  Время: %{{time_total}}s\\n📊 HTTP Status: %{{http_code}}\\n" \\
  | python3 -m json.tool"""
    
    print("=" * 80)
    print("CURL КОМАНДА ДЛЯ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print()
    print(f"📷 Изображение: {image_path}")
    print(f"🌐 URL: {endpoint}")
    print(f"🎯 Режим: {mode}")
    print(f"⏱️  Timeout: {timeout} секунд")
    print()
    print("Команда:")
    print("-" * 80)
    print(curl_cmd)
    print("-" * 80)
    print()
    print("Или выполните:")
    print(f"  python3 -c \"import json, base64; img=open('{image_path}','rb').read(); payload={{'image':f'data:{mime_type};base64,'+base64.b64encode(img).decode(),'mode':'{mode}','config':{{'language':'ru'}},'sam3_timeout':15,'sam3_use_llm_preanalysis':True,'sam3_max_coverage_percent':25}}; print(json.dumps(payload))\" | curl -X POST '{endpoint}' -H 'Content-Type: application/json' -d @-")
    print()
    print("=" * 80)
    
    return curl_cmd

if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else "img/18.png"
    railway_url = sys.argv[2] if len(sys.argv) > 2 else "https://detectskin-production.up.railway.app"
    mode = sys.argv[3] if len(sys.argv) > 3 else "pixelbin"
    
    generate_curl_command(image_path, railway_url, mode)

