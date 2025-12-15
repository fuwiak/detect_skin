#!/usr/bin/env python3
"""
Пример парсинга ответа от Pixelbin API
"""

import json

# Пример ответа от API
response_json = """{"input":{"image":"https://delivery.pixelbin.io/predictions/inputs/skinAnalysisInt/generate/019afd98-c909-7446-9d46-3abd50d68ff3/image/0.jpeg"},"status":"ACCEPTED","urls":{"get":"https://api.pixelbin.io/service/platform/transformation/v1.0/predictions/skinAnalysisInt--generate--019afd98-c909-7446-9d46-3abd50d68ff3"},"orgId":14208987,"retention":"30d","createdAt":"2025-12-08T10:53:59.945Z","_id":"skinAnalysisInt--generate--019afd98-c909-7446-9d46-3abd50d68ff3"}"""

# Парсинг JSON
data = json.loads(response_json)

print("=" * 60)
print("РАСПАРСЕННЫЙ ОТВЕТ ОТ PIXELBIN API")
print("=" * 60)

# Основные поля
print(f"\n📋 Статус задачи: {data['status']}")
print(f"🆔 ID задачи (_id): {data['_id']}")
print(f"📅 Создано: {data['createdAt']}")
print(f"⏰ Хранение: {data['retention']}")
print(f"🏢 Org ID: {data['orgId']}")

# URL для получения результата
print(f"\n🔗 URL для получения результата:")
print(f"   {data['urls']['get']}")

# URL загруженного изображения
print(f"\n🖼️  URL загруженного изображения:")
print(f"   {data['input']['image']}")

# Извлечение job_id для проверки статуса
job_id = data['_id']
print(f"\n💡 Job ID для проверки статуса: {job_id}")

# Пример использования
print("\n" + "=" * 60)
print("ПРИМЕР ИСПОЛЬЗОВАНИЯ В КОДЕ:")
print("=" * 60)
print("""
# После получения ответа от upload_image:
response_data = response.json()

# Извлечь job_id
job_id = response_data['_id']

# Проверить статус
status = response_data['status']  # "ACCEPTED"

# URL для получения результата
result_url = response_data['urls']['get']

# Использовать для проверки статуса задачи
# GET {result_url} или GET {BASE_URL}/{job_id}
""")










