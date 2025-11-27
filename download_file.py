#!/usr/bin/env python3
"""
Скрипт для скачивания файлов с Яндекс Диска
"""
import os
import requests
from dotenv import load_dotenv
from typing import Optional
import sys

# Загружаем переменные окружения
load_dotenv()

# Константы API Яндекс Диска
YANDEX_DISK_API_BASE = "https://cloud-api.yandex.net/v1/disk"
OAUTH_TOKEN = os.getenv("YANDEX_DISK_OAUTH_TOKEN")


def get_headers(use_space: bool = True) -> dict:
    """Возвращает заголовки для запросов к API"""
    token = OAUTH_TOKEN.strip()
    if token.startswith("OAuth"):
        auth_header = token
    else:
        auth_header = f"OAuth {token}" if use_space else f"OAuth{token}"
    
    return {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }


def get_download_link(file_path: str) -> Optional[str]:
    """
    Получает прямую ссылку для скачивания файла
    
    Args:
        file_path: Путь к файлу на Яндекс Диске (например, disk:/file.zip)
    
    Returns:
        URL для скачивания или None в случае ошибки
    """
    url = f"{YANDEX_DISK_API_BASE}/resources/download"
    params = {"path": file_path}
    
    formats_to_try = [(True, "OAuth <token>"), (False, "OAuth<token>")]
    
    for use_space, format_name in formats_to_try:
        try:
            response = requests.get(url, headers=get_headers(use_space=use_space), params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("href")
            elif response.status_code in [401, 403] and use_space == False:
                continue
            else:
                print(f"Ошибка получения ссылки: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Сообщение: {error_data.get('message', error_data.get('description', ''))}")
                except:
                    print(f"Ответ: {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Ошибка запроса: {e}")
            if use_space == False:
                return None
            continue
    
    return None


def download_file(file_path: str, output_path: Optional[str] = None) -> bool:
    """
    Скачивает файл с Яндекс Диска
    
    Args:
        file_path: Путь к файлу на Яндекс Диске
        output_path: Путь для сохранения файла (если None, используется имя файла из пути)
    
    Returns:
        True если успешно, False в случае ошибки
    """
    if not OAUTH_TOKEN:
        print("❌ Ошибка: OAuth токен не найден!")
        print("Убедитесь, что файл .env содержит YANDEX_DISK_OAUTH_TOKEN")
        return False
    
    print(f"🔍 Получение ссылки для скачивания: {file_path}")
    download_url = get_download_link(file_path)
    
    if not download_url:
        print("❌ Не удалось получить ссылку для скачивания")
        return False
    
    print(f"✅ Ссылка получена")
    
    # Определяем имя файла для сохранения
    if not output_path:
        # Извлекаем имя файла из пути
        file_name = file_path.split("/")[-1]
        if file_name.startswith("disk:"):
            file_name = file_name[5:]  # Убираем "disk:"
        output_path = file_name
    
    print(f"📥 Начинаю скачивание в: {output_path}")
    
    try:
        # Скачиваем файл
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Получаем размер файла для отображения прогресса
        total_size = int(response.headers.get('content-length', 0))
        
        downloaded = 0
        chunk_size = 8192  # 8KB
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Показываем прогресс
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r📊 Прогресс: {percent:.1f}% ({downloaded / 1024 / 1024:.2f} MB / {total_size / 1024 / 1024:.2f} MB)", end='', flush=True)
                    else:
                        print(f"\r📊 Скачано: {downloaded / 1024 / 1024:.2f} MB", end='', flush=True)
        
        print(f"\n✅ Файл успешно скачан: {output_path}")
        print(f"📦 Размер: {downloaded / 1024 / 1024:.2f} MB")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Ошибка при скачивании: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python download_file.py <путь_к_файлу> [путь_для_сохранения]")
        print("\nПримеры:")
        print("  python download_file.py disk:/face-api.js.zip")
        print("  python download_file.py disk:/face-api.js.zip ./my_file.zip")
        return
    
    file_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("=" * 80)
    print("📥 Скачивание файла с Яндекс Диска")
    print("=" * 80)
    print()
    
    success = download_file(file_path, output_path)
    
    if success:
        print("\n" + "=" * 80)
        print("✅ Готово!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ Ошибка при скачивании")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()

