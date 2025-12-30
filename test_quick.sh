#!/bin/bash

# Быстрый тест через curl для macOS
# Использование: ./test_quick.sh [image_path]

IMAGE_PATH="${1:-img/18.png}"
RAILWAY_URL="${2:-https://detectskin-production.up.railway.app}"
ENDPOINT="${RAILWAY_URL}/api/analyze"

if [ ! -f "$IMAGE_PATH" ]; then
    echo "❌ Ошибка: Файл не найден: $IMAGE_PATH"
    echo "Использование: $0 [image_path] [railway_url]"
    exit 1
fi

echo "📷 Изображение: $IMAGE_PATH"
echo "🌐 URL: $ENDPOINT"
echo ""

# Конвертируем изображение в base64 (macOS синтаксис)
echo "📦 Конвертация изображения в base64..."
IMAGE_BASE64=$(base64 "$IMAGE_PATH" | tr -d '\n')

if [ -z "$IMAGE_BASE64" ]; then
    echo "❌ Ошибка: Не удалось конвертировать изображение"
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
  "sam3_timeout": 5,
  "sam3_diseases": [
    "pimples", "pustules", "comedones", "rosacea", "irritation",
    "pigmentation", "freckles", "wrinkles", "fine lines",
    "skin lesion", "scars", "acne", "papules", "whiteheads", "blackheads",
    "moles", "warts", "papillomas", "skin tags", "acne scars",
    "post acne marks", "hydration", "pores", "eye_bags",
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
  --max-time 60 \
  --connect-timeout 10 \
  -w "\n\n⏱️  Время: %{time_total}s\n📊 HTTP Status: %{http_code}\n" \
  -s | python3 -m json.tool 2>/dev/null || cat

# Удаляем временный файл
rm -f "$TMP_FILE"

echo ""
echo "✅ ТЕСТ ЗАВЕРШЁН"

