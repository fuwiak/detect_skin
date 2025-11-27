#!/usr/bin/env python3
"""
Скрипт для просмотра директорий и файлов на Яндекс Диске
"""
import os
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Загружаем переменные окружения из .env
load_dotenv()

# Константы API Яндекс Диска
YANDEX_DISK_API_BASE = "https://cloud-api.yandex.net/v1/disk"
OAUTH_TOKEN = os.getenv("YANDEX_DISK_OAUTH_TOKEN")


def get_headers(use_space: bool = False, token_override: Optional[str] = None) -> Dict[str, str]:
    """
    Возвращает заголовки для запросов к API
    
    Args:
        use_space: Если True, использует формат "OAuth <token>", иначе "OAuth<token>" (по умолчанию False, как в документации)
        token_override: Альтернативный токен для использования (для тестирования разных форматов)
    """
    token = (token_override or OAUTH_TOKEN).strip()
    
    # Если токен уже содержит "OAuth", используем как есть
    if token.startswith("OAuth"):
        auth_header = token
    else:
        # Согласно документации Яндекс Диска: "Authorization: OAuth<token>" (БЕЗ пробела)
        # Пример: Authorization: OAuth0c4181a7c2cf4521964a72ff57a34a07
        if use_space:
            auth_header = f"OAuth {token}"
        else:
            auth_header = f"OAuth{token}"
    
    return {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }


def handle_api_error(response: requests.Response) -> None:
    """Обрабатывает ошибки API и выводит понятные сообщения"""
    error_codes = {
        "DiskUnsupportedUserAccountTypeError": (
            "❌ Тип аккаунта не поддерживается.\n"
            "   Возможные причины:\n"
            "   - Ваш аккаунт не имеет доступа к API Яндекс Диска\n"
            "   - Требуется аккаунт с полным доступом к Диску\n"
            "   - Токен недействителен или истек\n"
            "   Решение: Проверьте токен и убедитесь, что аккаунт поддерживает API"
        ),
        "UnauthorizedError": (
            "❌ Ошибка авторизации.\n"
            "   Токен недействителен или истек.\n"
            "   Решение: Получите новый OAuth токен"
        ),
        "ForbiddenError": (
            "❌ Доступ запрещен.\n"
            "   У вас нет прав для выполнения этого действия.\n"
            "   Решение: Проверьте права доступа токена"
        )
    }
    
    try:
        error_data = response.json()
        error_code = error_data.get("error", "")
        error_message = error_data.get("message", error_data.get("description", ""))
        
        if error_code in error_codes:
            print(error_codes[error_code])
        else:
            print(f"❌ Ошибка API: {error_code}")
            if error_message:
                print(f"   Сообщение: {error_message}")
    except:
        print(f"❌ HTTP {response.status_code}: {response.reason}")
        print(f"   Ответ: {response.text[:200]}")


def list_resources(path: str = "/", limit: int = 20, offset: int = 0, use_space: bool = False, token_override: Optional[str] = None) -> Optional[Dict]:
    """
    Получает список ресурсов (файлов и папок) по указанному пути
    
    Args:
        path: Путь к директории (по умолчанию корень диска)
        limit: Максимальное количество элементов
        offset: Смещение для пагинации
        use_space: Использовать пробел в заголовке Authorization (по умолчанию False - формат из документации)
        token_override: Альтернативный токен для использования
    
    Returns:
        Словарь с данными о ресурсах или None в случае ошибки
    """
    url = f"{YANDEX_DISK_API_BASE}/resources"
    params = {
        "path": path,
        "limit": limit,
        "offset": offset
    }
    
    try:
        response = requests.get(url, headers=get_headers(use_space=use_space, token_override=token_override), params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Если получили 401/403 без пробела, пробуем с пробелом
        if e.response is not None and e.response.status_code in [401, 403] and not use_space:
            print("⚠️  Попытка с альтернативным форматом заголовка (с пробелом)...")
            try:
                response = requests.get(url, headers=get_headers(use_space=True, token_override=token_override), params=params)
                response.raise_for_status()
                return response.json()
            except:
                pass
        
        if e.response is not None:
            handle_api_error(e.response)
        else:
            print(f"❌ HTTP ошибка: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при запросе: {e}")
        return None


def format_size(size: int) -> str:
    """Форматирует размер файла в читаемый вид"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def display_resources(data: Dict, path: str = "/"):
    """
    Выводит информацию о ресурсах в читаемом виде
    
    Args:
        data: Данные о ресурсах от API
        path: Текущий путь
    """
    if not data:
        print("Нет данных для отображения")
        return
    
    print(f"\n📁 Путь: {path}")
    print("=" * 80)
    
    # Информация о текущей директории
    if "_embedded" in data:
        items = data["_embedded"].get("items", [])
        total = len(items)
        
        print(f"\nВсего элементов: {total}\n")
        
        # Разделяем на папки и файлы
        folders = [item for item in items if item.get("type") == "dir"]
        files = [item for item in items if item.get("type") == "file"]
        
        # Выводим папки
        if folders:
            print("📂 ДИРЕКТОРИИ:")
            print("-" * 80)
            for folder in folders:
                name = folder.get("name", "Неизвестно")
                path = folder.get("path", "")
                print(f"  📁 {name}")
                print(f"     Путь: {path}")
                print()
        
        # Выводим файлы
        if files:
            print("📄 ФАЙЛЫ:")
            print("-" * 80)
            for file in files:
                name = file.get("name", "Неизвестно")
                size = file.get("size", 0)
                path = file.get("path", "")
                mime_type = file.get("mime_type", "Неизвестно")
                modified = file.get("modified", "")
                
                print(f"  📄 {name}")
                print(f"     Размер: {format_size(size)}")
                print(f"     Путь: {path}")
                print(f"     Тип: {mime_type}")
                if modified:
                    print(f"     Изменен: {modified}")
                print()
        
        if not folders and not files:
            print("Директория пуста")
    else:
        # Если это файл, а не директория
        print(f"📄 {data.get('name', 'Неизвестно')}")
        print(f"   Размер: {format_size(data.get('size', 0))}")
        print(f"   Путь: {data.get('path', '')}")


def check_token_validity() -> bool:
    """Проверяет валидность токена через запрос информации о диске"""
    url = f"{YANDEX_DISK_API_BASE}"
    
    token = OAUTH_TOKEN.strip()
    
    # Пробуем разные варианты токена и формата заголовка
    variants = [
        # Формат из документации: OAuth<token> (без пробела)
        (False, token),
        # Стандартный формат: OAuth <token> (с пробелом)
        (True, token),
    ]
    
    # Если токен начинается с y0__ или y1__, пробуем также без префикса
    if token.startswith("y0__") or token.startswith("y1__"):
        token_without_prefix = token[3:]  # Убираем "y0_" или "y1_"
        variants.extend([
            (False, token_without_prefix),
            (True, token_without_prefix),
        ])
    
    for use_space, test_token in variants:
        try:
            response = requests.get(url, headers=get_headers(use_space=use_space, token_override=test_token))
            if response.status_code == 200:
                if test_token != token:
                    print(f"✅ Токен работает (использован вариант без префикса)")
                return True
        except requests.exceptions.RequestException:
            continue
    
    # Если все варианты не сработали, показываем ошибку
    try:
        response = requests.get(url, headers=get_headers(use_space=False))
        handle_api_error(response)
    except:
        pass
    return False


def main():
    """Основная функция"""
    import sys
    
    # Получаем путь из аргументов командной строки, если указан
    path = "/"
    if len(sys.argv) > 1:
        path = sys.argv[1]
        # Если путь не начинается с disk:, добавляем его
        if not path.startswith("disk:"):
            if path.startswith("/"):
                path = f"disk:{path}"
            else:
                path = f"disk:/{path}"
        # Убираем disk: для API запроса
        if path.startswith("disk:"):
            path = path[5:]  # Убираем "disk:"
    
    if not OAUTH_TOKEN:
        print("❌ Ошибка: OAuth токен не найден в переменных окружения!")
        print("Убедитесь, что файл .env существует и содержит YANDEX_DISK_OAUTH_TOKEN")
        return
    
    print("🔍 Подключение к Яндекс Диску...")
    print(f"Токен: {OAUTH_TOKEN[:20]}...")
    print()
    
    # Проверяем валидность токена
    print("🔐 Проверка токена...")
    if not check_token_validity():
        print("\n💡 Советы по решению проблемы:")
        print("   1. Убедитесь, что токен актуален и не истек")
        print("   2. Проверьте, что ваш аккаунт имеет доступ к API Яндекс Диска")
        print("   3. Получите новый токен по адресу:")
        print("      https://oauth.yandex.ru/authorize?response_type=token&client_id=047b883acf9042e2a85f901255b81520")
        return
    
    print("✅ Токен валиден\n")
    
    # Получаем список ресурсов
    print(f"📂 Получение списка файлов и директорий для пути: {path}")
    # Используем формат без пробела по умолчанию (как в документации)
    data = list_resources(path=path, limit=100, use_space=False)
    
    if data:
        display_resources(data, path)
    else:
        print("❌ Не удалось получить данные с Яндекс Диска")


if __name__ == "__main__":
    main()

