#!/bin/bash

# Скрипт для парсинга ответа от Pixelbin API
# Использование: echo 'JSON_RESPONSE' | ./parse_response.sh
# Или: curl ... | ./parse_response.sh

if [ -t 0 ]; then
    echo "Использование: echo 'JSON' | $0"
    echo "Или: curl ... | $0"
    exit 1
fi

# Читаем JSON из stdin
JSON_RESPONSE=$(cat)

# Проверяем наличие jq
if command -v jq &> /dev/null; then
    echo "=== Распарсенный ответ ==="
    echo "$JSON_RESPONSE" | jq '.'
    
    echo ""
    echo "=== Важные поля ==="
    echo "Job ID:     $(echo "$JSON_RESPONSE" | jq -r '._id')"
    echo "Status:     $(echo "$JSON_RESPONSE" | jq -r '.status')"
    echo "Result URL: $(echo "$JSON_RESPONSE" | jq -r '.urls.get')"
    echo "Image URL:  $(echo "$JSON_RESPONSE" | jq -r '.input.image')"
    echo "Created:    $(echo "$JSON_RESPONSE" | jq -r '.createdAt')"
else
    # Используем Python если jq нет
    echo "$JSON_RESPONSE" | python3 -c "
import json
import sys

data = json.load(sys.stdin)
print('=== Распарсенный ответ ===')
print(json.dumps(data, indent=2, ensure_ascii=False))
print()
print('=== Важные поля ===')
print(f'Job ID:     {data[\"_id\"]}')
print(f'Status:     {data[\"status\"]}')
print(f'Result URL: {data[\"urls\"][\"get\"]}')
print(f'Image URL:  {data[\"input\"][\"image\"]}')
print(f'Created:    {data[\"createdAt\"]}')
"
fi





