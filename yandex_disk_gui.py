#!/usr/bin/env python3
"""
Веб-интерфейс (GUI) для просмотра файлов и директорий на Яндекс Диске
"""
import os
import requests
from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv
from typing import Dict, Optional
from urllib.parse import quote, unquote

# Загружаем переменные окружения
load_dotenv()

# Константы API Яндекс Диска
YANDEX_DISK_API_BASE = "https://cloud-api.yandex.net/v1/disk"
OAUTH_TOKEN = os.getenv("YANDEX_DISK_OAUTH_TOKEN")

app = Flask(__name__)

# HTML шаблон для интерфейса
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Яндекс Диск - Просмотр файлов</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .breadcrumb {
            background: #f5f5f5;
            padding: 15px 30px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .breadcrumb a {
            color: #667eea;
            text-decoration: none;
            margin-right: 10px;
        }
        
        .breadcrumb a:hover {
            text-decoration: underline;
        }
        
        .content {
            padding: 30px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .error {
            background: #fee;
            border: 1px solid #fcc;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            color: #c33;
        }
        
        .file-list {
            display: grid;
            gap: 15px;
        }
        
        .item {
            display: flex;
            align-items: center;
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .item:hover {
            background: #f5f5f5;
            transform: translateX(5px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .item.folder {
            background: #e3f2fd;
            border-color: #90caf9;
        }
        
        .item.file {
            background: #fff;
        }
        
        .icon {
            font-size: 2em;
            margin-right: 15px;
            width: 50px;
            text-align: center;
        }
        
        .item-info {
            flex: 1;
        }
        
        .item-name {
            font-weight: 600;
            font-size: 1.1em;
            color: #333;
            margin-bottom: 5px;
        }
        
        .item-details {
            font-size: 0.9em;
            color: #666;
        }
        
        .empty {
            text-align: center;
            padding: 60px;
            color: #999;
            font-size: 1.2em;
        }
        
        .stats {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-around;
        }
        
        .stat {
            text-align: center;
        }
        
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 Яндекс Диск</h1>
            <p>Просмотр файлов и директорий</p>
        </div>
        
        <div class="breadcrumb" id="breadcrumb">
            <a href="/">🏠 Корень</a>
        </div>
        
        <div class="content" id="content">
            <div class="loading">Загрузка...</div>
        </div>
    </div>
    
    <script>
        let currentPath = '/';
        let isLoading = false;
        let currentRequest = null;
        
        function formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        function formatDate(dateString) {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleString('ru-RU');
        }
        
        function updateBreadcrumb(path) {
            const breadcrumb = document.getElementById('breadcrumb');
            const parts = path.split('/').filter(p => p);
            let html = '<a href="/" onclick="loadPath(\'/\'); return false;">🏠 Корень</a>';
            
            let current = '';
            parts.forEach((part, index) => {
                current += '/' + part;
                html += ' / <a href="#" onclick="loadPath(\'' + current + '\'); return false;">' + 
                        decodeURIComponent(part) + '</a>';
            });
            
            breadcrumb.innerHTML = html;
        }
        
        function loadPath(path) {
            // Защита от множественных одновременных запросов
            if (isLoading) {
                console.log('Запрос уже выполняется, пропускаю...');
                return;
            }
            
            // Отменяем предыдущий запрос, если он есть
            if (currentRequest) {
                console.log('Отменяю предыдущий запрос');
                // currentRequest.abort(); // если это AbortController
            }
            
            isLoading = true;
            currentPath = path;
            updateBreadcrumb(path);
            
            const content = document.getElementById('content');
            if (!content) {
                console.error('Элемент content не найден!');
                isLoading = false;
                return;
            }
            
            content.innerHTML = '<div class="loading">Загрузка...</div>';
            
            // Таймаут для запроса
            const timeoutId = setTimeout(() => {
                if (isLoading) {
                    isLoading = false;
                    const safePath = path.replace(/'/g, "\\'");
                    content.innerHTML = '<div class="error">⏱️ Запрос выполняется слишком долго...<br>' +
                    'Возможно, проблема с подключением или токеном.<br><br>' +
                    '<button onclick="loadPath(\'' + safePath + '\')" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer;">Повторить</button></div>';
                }
            }, 15000); // 15 секунд
            
            console.log('Начинаю загрузку пути:', path);
            currentRequest = fetch('/api/list?path=' + encodeURIComponent(path))
                .then(response => {
                    clearTimeout(timeoutId);
                    console.log('Ответ получен, статус:', response.status);
                    if (!response.ok) {
                        throw new Error('HTTP ' + response.status + ': ' + response.statusText);
                    }
                    return response.json();
                })
                .then(data => {
                    clearTimeout(timeoutId);
                    isLoading = false;
                    currentRequest = null;
                    
                    console.log('Данные получены от сервера:', data);
                    console.log('Тип данных:', typeof data);
                    console.log('Есть ли items?', data && data.items);
                    console.log('Количество items:', data && data.items ? data.items.length : 0);
                    
                    if (!data) {
                        content.innerHTML = '<div class="error">❌ Ошибка: пустой ответ от сервера</div>';
                        return;
                    }
                    
                    if (data.error) {
                        const safePath = path.replace(/'/g, "\\'");
                        content.innerHTML = '<div class="error">❌ ' + (data.error || 'Неизвестная ошибка').replace(/</g, '&lt;').replace(/>/g, '&gt;') + 
                            '<br><br><button onclick="loadPath(\'' + safePath + '\')" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;">Повторить</button></div>';
                        return;
                    }
                    
                    if (!data.items) {
                        console.error('Нет поля items в данных:', data);
                        content.innerHTML = '<div class="error">❌ Ошибка: неверный формат данных от сервера</div>';
                        return;
                    }
                    
                    console.log('Вызываю displayItems с', data.items.length, 'элементами');
                    displayItems(data);
                })
                .catch(error => {
                    clearTimeout(timeoutId);
                    isLoading = false;
                    currentRequest = null;
                    console.error('Ошибка загрузки:', error);
                    const safePath = path.replace(/'/g, "\\'");
                    const errorMsg = (error.message || 'Неизвестная ошибка').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    content.innerHTML = '<div class="error">❌ Ошибка загрузки: ' + errorMsg + 
                        '<br><br>Проверьте консоль браузера (F12) для подробностей.' +
                        '<br><br><button onclick="loadPath(\'' + safePath + '\')" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;">Повторить</button></div>';
                });
        }
        
        function displayItems(data) {
            const content = document.getElementById('content');
            
            console.log('Отображаю данные:', data);
            
            if (!data || !data.items) {
                console.error('Нет данных items:', data);
                content.innerHTML = '<div class="error">❌ Ошибка: данные не получены</div>';
                return;
            }
            
            if (data.items.length === 0) {
                content.innerHTML = '<div class="empty">📭 Директория пуста</div>';
                return;
            }
            
            const folders = data.items.filter(item => item && item.type === 'dir');
            const files = data.items.filter(item => item && item.type === 'file');
            
            console.log('Найдено папок:', folders.length, 'файлов:', files.length);
            
            let html = '<div class="stats">';
            html += '<div class="stat"><div class="stat-value">' + folders.length + '</div><div class="stat-label">Папок</div></div>';
            html += '<div class="stat"><div class="stat-value">' + files.length + '</div><div class="stat-label">Файлов</div></div>';
            html += '<div class="stat"><div class="stat-value">' + data.items.length + '</div><div class="stat-label">Всего</div></div>';
            html += '</div>';
            
            html += '<div class="file-list">';
            
            // Показываем папки
            folders.forEach(folder => {
                const safePath = folder.path.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                html += '<div class="item folder" onclick="loadPath(\'' + safePath + '\')">';
                html += '<div class="icon">📁</div>';
                html += '<div class="item-info">';
                html += '<div class="item-name">' + (folder.name || 'Без названия').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>';
                html += '<div class="item-details">Путь: ' + (folder.path || '').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>';
                html += '</div>';
                html += '</div>';
            });
            
            // Показываем файлы
            files.forEach(file => {
                html += '<div class="item file">';
                html += '<div class="icon">📄</div>';
                html += '<div class="item-info">';
                html += '<div class="item-name">' + (file.name || 'Без названия').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>';
                html += '<div class="item-details">';
                html += 'Размер: ' + formatSize(file.size || 0);
                if (file.modified) {
                    html += ' • Изменен: ' + formatDate(file.modified);
                }
                if (file.mime_type) {
                    html += ' • Тип: ' + (file.mime_type || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                }
                html += '</div>';
                html += '</div>';
                html += '</div>';
            });
            
            html += '</div>';
            content.innerHTML = html;
        }
        
        // Загружаем корневую директорию при загрузке страницы
        let pageLoaded = false;
        window.addEventListener('DOMContentLoaded', function() {
            if (!pageLoaded) {
                pageLoaded = true;
                console.log('Страница загружена, начинаю загрузку корневой директории...');
                loadPath('/');
            }
        });
        
        // Добавляем обработчик для отображения ошибок сети
        window.addEventListener('error', function(e) {
            console.error('Глобальная ошибка:', e);
        });
    </script>
</body>
</html>
"""


def get_headers(use_space: bool = False) -> Dict[str, str]:
    """Возвращает заголовки для запросов к API"""
    token = OAUTH_TOKEN.strip()
    if token.startswith("OAuth"):
        auth_header = token
    else:
        auth_header = f"OAuth{token}" if not use_space else f"OAuth {token}"
    
    return {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }


def list_resources(path: str = "/", limit: int = 100) -> Optional[Dict]:
    """Получает список ресурсов по указанному пути"""
    url = f"{YANDEX_DISK_API_BASE}/resources"
    params = {
        "path": path,
        "limit": limit,
        "offset": 0
    }
    
    # Пробуем оба формата заголовка
    formats_to_try = [
        (False, "OAuth<token> (без пробела)"),
        (True, "OAuth <token> (с пробелом)")
    ]
    
    for use_space, format_name in formats_to_try:
        headers = get_headers(use_space=use_space)
        print(f"[API] Попытка с форматом: {format_name}")
        print(f"[API] URL: {url}")
        print(f"[API] Параметры: {params}")
        print(f"[API] Заголовок Authorization: {headers.get('Authorization', '')[:30]}...")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"[API] Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"[API] Успешный ответ от API")
                return result
            elif response.status_code in [401, 403]:
                # Пробуем следующий формат
                print(f"[API] Ошибка авторизации, пробуем другой формат...")
                continue
            else:
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            print("[API] Таймаут запроса")
            return {"error": "Таймаут запроса к API. Проверьте подключение к интернету."}
            
        except requests.exceptions.HTTPError as e:
            print(f"[API] HTTP ошибка: {e}")
            if e.response is not None:
                print(f"[API] Статус: {e.response.status_code}")
                print(f"[API] Ответ: {e.response.text[:200]}")
                
                # Если это ошибка авторизации, пробуем другой формат
                if e.response.status_code in [401, 403] and use_space == False:
                    continue
                    
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("message", error_data.get("description", "Ошибка API"))
                    error_code = error_data.get("error", "")
                    return {"error": f"{error_code}: {error_msg}" if error_code else error_msg}
                except:
                    return {"error": f"HTTP {e.response.status_code}: {e.response.reason}"}
            return {"error": str(e)}
            
        except requests.exceptions.RequestException as e:
            print(f"[API] Ошибка запроса: {e}")
            return {"error": f"Ошибка подключения: {str(e)}"}
    
    # Если все форматы не сработали
    return {"error": "Не удалось авторизоваться. Проверьте токен в файле .env"}


@app.route('/')
def index():
    """Главная страница"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/list')
def api_list():
    """API endpoint для получения списка файлов"""
    try:
        path = request.args.get('path', '/')
        # Декодируем путь
        path = unquote(path)
        
        print(f"[API] Запрос списка файлов для пути: {path}")
        
        if not OAUTH_TOKEN:
            print("[API] Ошибка: OAuth токен не найден")
            return jsonify({"error": "OAuth токен не найден. Проверьте файл .env"}), 500
        
        print(f"[API] Выполняю запрос к API Яндекс Диска...")
        data = list_resources(path=path)
        
        if data and "error" not in data:
            items = []
            if "_embedded" in data and "items" in data["_embedded"]:
                items = data["_embedded"]["items"]
            
            print(f"[API] Успешно получено {len(items)} элементов")
            return jsonify({
                "items": items,
                "path": path
            })
        else:
            error_msg = data.get("error", "Неизвестная ошибка") if data else "Не удалось получить данные"
            print(f"[API] Ошибка: {error_msg}")
            return jsonify({"error": error_msg}), 500
            
    except Exception as e:
        print(f"[API] Исключение: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500


if __name__ == '__main__':
    if not OAUTH_TOKEN:
        print("❌ Ошибка: OAuth токен не найден!")
        print("Убедитесь, что файл .env содержит YANDEX_DISK_OAUTH_TOKEN")
    else:
        print("=" * 80)
        print("🌐 Веб-интерфейс Яндекс Диска")
        print("=" * 80)
        print("📡 Сервер запущен на http://127.0.0.1:5000")
        print("🌍 Откройте браузер и перейдите по адресу выше")
        print("=" * 80)
        print("Для остановки нажмите Ctrl+C")
        print()
        app.run(debug=True, host='127.0.0.1', port=5000)

