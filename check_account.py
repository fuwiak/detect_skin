#!/usr/bin/env python3
"""
Скрипт для проверки информации об аккаунте Яндекс Диска
"""
import os
import requests
from dotenv import load_dotenv

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


def get_disk_info():
    """Получает информацию о диске и пользователе"""
    url = f"{YANDEX_DISK_API_BASE}"
    
    formats_to_try = [(True, "OAuth <token>"), (False, "OAuth<token>")]
    
    for use_space, format_name in formats_to_try:
        try:
            response = requests.get(url, headers=get_headers(use_space=use_space), timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [401, 403] and use_space == False:
                continue
            else:
                print(f"Ошибка: HTTP {response.status_code}")
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


def get_user_info():
    """Получает информацию о пользователе через Yandex ID API"""
    # Пробуем получить информацию через токен
    url = "https://login.yandex.ru/info"
    
    formats_to_try = [(True, "OAuth <token>"), (False, "OAuth<token>")]
    
    for use_space, format_name in formats_to_try:
        try:
            headers = get_headers(use_space=use_space)
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [401, 403] and use_space == False:
                continue
                
        except requests.exceptions.RequestException as e:
            if use_space == False:
                return None
            continue
    
    return None


def main():
    """Основная функция"""
    if not OAUTH_TOKEN:
        print("❌ Ошибка: OAuth токен не найден!")
        print("Убедитесь, что файл .env содержит YANDEX_DISK_OAUTH_TOKEN")
        return
    
    print("=" * 80)
    print("🔍 Проверка информации об аккаунте Яндекс Диска")
    print("=" * 80)
    print()
    
    print("📊 Информация о диске:")
    print("-" * 80)
    disk_info = get_disk_info()
    
    if disk_info:
        print(f"Используемое пространство: {disk_info.get('used_space', 0) / 1024 / 1024 / 1024:.2f} GB")
        print(f"Общее пространство: {disk_info.get('total_space', 0) / 1024 / 1024 / 1024:.2f} GB")
        print(f"Свободное пространство: {disk_info.get('trash_size', 0) / 1024 / 1024 / 1024:.2f} GB")
        print(f"Системные папки: {disk_info.get('system_folders', {})}")
    else:
        print("❌ Не удалось получить информацию о диске")
    
    print()
    print("👤 Информация о пользователе:")
    print("-" * 80)
    user_info = get_user_info()
    
    if user_info:
        print(f"Email: {user_info.get('default_email', 'Не указан')}")
        print(f"Логин: {user_info.get('login', 'Не указан')}")
        print(f"Имя: {user_info.get('first_name', 'Не указано')}")
        print(f"Фамилия: {user_info.get('last_name', 'Не указана')}")
        print(f"Отображаемое имя: {user_info.get('display_name', 'Не указано')}")
        print(f"ID: {user_info.get('id', 'Не указан')}")
    else:
        print("⚠️  Не удалось получить информацию о пользователе через Yandex ID API")
        print("   Это нормально, если токен не имеет прав для доступа к информации профиля")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()

