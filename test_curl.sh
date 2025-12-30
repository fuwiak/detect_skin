#!/bin/bash

# Скрипт для тестирования /api/analyze через curl
# Использование: ./test_curl.sh [image_path] [railway_url]

# Параметры
IMAGE_PATH="${1:-img/18.png}"
RAILWAY_URL="${2:-https://detectskin-production.up.railway.app}"
ENDPOINT="${RAILWAY_URL}/api/analyze"

# Проверка наличия изображения
if [ ! -f "$IMAGE_PATH" ]; then
    echo "❌ Ошибка: Файл не найден: $IMAGE_PATH"
    echo "Использование: $0 [image_path] [railway_url]"
    exit 1
fi

echo "=" | tr -d '\n' | head -c 80 && echo ""
echo "ТЕСТИРОВАНИЕ /api/analyze через curl"
echo "=" | tr -d '\n' | head -c 80 && echo ""
echo ""
echo "📷 Изображение: $IMAGE_PATH"
echo "🌐 URL: $ENDPOINT"
echo ""

# Конвертируем изображение в base64
echo "📦 Конвертация изображения в base64..."
IMAGE_BASE64=$(base64 -i "$IMAGE_PATH" 2>/dev/null || base64 "$IMAGE_PATH" 2>/dev/null)

if [ -z "$IMAGE_BASE64" ]; then
    echo "❌ Ошибка: Не удалось конвертировать изображение в base64"
    exit 1
fi

# Определяем MIME тип
MIME_TYPE="image/jpeg"
if [[ "$IMAGE_PATH" == *.png ]]; then
    MIME_TYPE="image/png"
elif [[ "$IMAGE_PATH" == *.heic ]] || [[ "$IMAGE_PATH" == *.heif ]]; then
    MIME_TYPE="image/heic"
fi

echo "✅ Изображение конвертировано (MIME: $MIME_TYPE)"
echo ""

# Формируем JSON payload
PAYLOAD=$(cat <<EOF
{
  "image": "data:${MIME_TYPE};base64,${IMAGE_BASE64}",
  "mode": "pixelbin",
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
)

# Сохраняем payload во временный файл
TMP_FILE=$(mktemp)
echo "$PAYLOAD" > "$TMP_FILE"

echo "🚀 Отправка запроса..."
echo ""

# Выполняем curl запрос
curl -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d @"$TMP_FILE" \
  --max-time 120 \
  --connect-timeout 10 \
  -w "\n\n⏱️  Время выполнения: %{time_total}s\n📊 HTTP Status: %{http_code}\n" \
  -s | python3 -m json.tool 2>/dev/null || cat

# Удаляем временный файл
rm -f "$TMP_FILE"

echo ""
echo "=" | tr -d '\n' | head -c 80 && echo ""
echo "✅ ТЕСТ ЗАВЕРШЁН"
echo "=" | tr -d '\n' | head -c 80 && echo ""

