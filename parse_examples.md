# Как распарсить ответ от Pixelbin API

## Структура ответа

```json
{
    "input": {
        "image": "https://delivery.pixelbin.io/predictions/inputs/..."
    },
    "status": "ACCEPTED",
    "urls": {
        "get": "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions/..."
    },
    "orgId": 14208987,
    "retention": "30d",
    "createdAt": "2025-12-08T10:53:59.945Z",
    "_id": "skinAnalysisInt--generate--019afd98-c909-7446-9d46-3abd50d68ff3"
}
```

## 1. Python (в коде)

```python
import json

# После получения ответа
response_data = response.json()

# Извлечение полей
job_id = response_data['_id']                    # ID задачи
status = response_data['status']                 # "ACCEPTED"
result_url = response_data['urls']['get']        # URL для получения результата
uploaded_image_url = response_data['input']['image']  # URL загруженного изображения
created_at = response_data['createdAt']          # Время создания
retention = response_data['retention']            # Время хранения

# Использование
print(f"Job ID: {job_id}")
print(f"Status: {status}")
print(f"Check result at: {result_url}")
```

## 2. Bash/curl с jq

```bash
# Сохранить ответ в переменную
RESPONSE=$(curl -X POST "https://api.pixelbin.io/..." \
  -H "Authorization: Bearer TOKEN" \
  -F "input.image=@image.jpg")

# Извлечь job_id
JOB_ID=$(echo $RESPONSE | jq -r '._id')
echo "Job ID: $JOB_ID"

# Извлечь status
STATUS=$(echo $RESPONSE | jq -r '.status')
echo "Status: $STATUS"

# Извлечь URL результата
RESULT_URL=$(echo $RESPONSE | jq -r '.urls.get')
echo "Result URL: $RESULT_URL"

# Извлечь URL изображения
IMAGE_URL=$(echo $RESPONSE | jq -r '.input.image')
echo "Image URL: $IMAGE_URL"
```

## 3. curl с форматированием

```bash
# Красиво отформатировать JSON
curl -X POST "..." | python -m json.tool

# Или с jq
curl -X POST "..." | jq '.'

# Извлечь только нужные поля
curl -X POST "..." | jq '{job_id: ._id, status: .status, result_url: .urls.get}'
```

## 4. JavaScript/Node.js

```javascript
// После получения ответа
const responseData = await response.json();

// Извлечение полей
const jobId = responseData._id;
const status = responseData.status;
const resultUrl = responseData.urls.get;
const uploadedImageUrl = responseData.input.image;

console.log(`Job ID: ${jobId}`);
console.log(`Status: ${status}`);
console.log(`Result URL: ${resultUrl}`);
```

## 5. Проверка статуса задачи

После получения `_id` или `urls.get`, можно проверить статус:

```bash
# Используя job_id
curl -H "Authorization: Bearer TOKEN" \
  "https://api.pixelbin.io/service/platform/transformation/v1.0/predictions/{job_id}"

# Или используя urls.get напрямую
curl -H "Authorization: Bearer TOKEN" \
  "{urls.get}"
```

## Важные поля

- **`_id`** - уникальный идентификатор задачи (используется для проверки статуса)
- **`status`** - статус задачи ("ACCEPTED" означает, что задача принята)
- **`urls.get`** - URL для получения результата анализа
- **`input.image`** - URL загруженного изображения
- **`createdAt`** - время создания задачи
- **`retention`** - время хранения результата (например, "30d")





