# Примеры curl команд для тестирования /api/analyze

## Новое: Тест статистики

Для тестирования новой функциональности со статистикой для всех параметров:

```bash
# Используйте готовый скрипт
python test_statistics.py img/18.png pixelbin
python test_statistics.py img/18.png sam3
python test_statistics.py img/18.png all
```

Скрипт проверяет:
- ✅ Наличие поля `statistics` в ответе
- ✅ Наличие `indicators` и `problems`
- ✅ Покрытие всех запрошенных параметров
- ✅ Правильность значений

## Примеры curl команд для тестирования /api/analyze

## Быстрый способ

### 1. Используйте готовые скрипты:

```bash
# Pixelbin режим
./test_curl.sh img/18.png

# SAM3 режим
./test_curl_sam3.sh img/18.png

# С кастомным URL
./test_curl.sh img/18.png https://detectskin-production.up.railway.app
```

### 2. Генератор curl команды:

```bash
python3 generate_curl.py img/18.png https://detectskin-production.up.railway.app pixelbin
python3 generate_curl.py img/18.png https://detectskin-production.up.railway.app sam3
```

## Ручной способ (для локального тестирования)

### Pixelbin режим:

```bash
# 1. Конвертируем изображение в base64
IMAGE_BASE64=$(base64 -i img/18.png | tr -d '\n')

# 2. Формируем JSON
cat > /tmp/payload.json <<EOF
{
  "image": "data:image/png;base64,${IMAGE_BASE64}",
  "mode": "pixelbin",
  "config": {
    "language": "ru"
  }
}
EOF

# 3. Отправляем запрос
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d @/tmp/payload.json \
  --max-time 120 \
  | python3 -m json.tool
```

### SAM3 режим:

```bash
# 1. Конвертируем изображение в base64
IMAGE_BASE64=$(base64 -i img/18.png | tr -d '\n')

# 2. Формируем JSON
cat > /tmp/payload.json <<EOF
{
  "image": "data:image/png;base64,${IMAGE_BASE64}",
  "mode": "sam3",
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
  "sam3_use_llm_preanalysis": true,
  "sam3_max_coverage_percent": 25
}
EOF

# 3. Отправляем запрос
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d @/tmp/payload.json \
  --max-time 180 \
  | python3 -m json.tool
```

## Для Railway

Замените `http://localhost:8000` на ваш Railway URL:

```bash
curl -X POST "https://detectskin-production.up.railway.app/api/analyze" \
  -H "Content-Type: application/json" \
  -d @/tmp/payload.json \
  --max-time 120
```

## Однострочная команда (Python)

```bash
python3 -c "
import json, base64, sys
img = open('img/18.png', 'rb').read()
payload = {
    'image': f'data:image/png;base64,{base64.b64encode(img).decode()}',
    'mode': 'pixelbin',
    'config': {'language': 'ru'}
}
print(json.dumps(payload))
" | curl -X POST 'https://detectskin-production.up.railway.app/api/analyze' \
  -H 'Content-Type: application/json' \
  -d @- \
  --max-time 120 \
  | python3 -m json.tool
```

## Параметры запроса

- `mode`: `"pixelbin"` или `"sam3"`
- `config.language`: `"ru"` или `"en"`
- `sam3_timeout`: 3-20 секунд (по умолчанию 5)
- `sam3_diseases`: список заболеваний для анализа (опционально)
- `sam3_use_llm_preanalysis`: `true` или `false` (по умолчанию `true`)
- `sam3_max_coverage_percent`: 0-100 (по умолчанию 25)

