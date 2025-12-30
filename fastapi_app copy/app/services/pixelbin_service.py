"""
Сервис для работы с Pixelbin API
"""
import io
import time
import logging
import requests
from typing import Dict, List, Optional
from PIL import Image, ImageOps, ImageEnhance

from app.config import settings, PIXELBIN_HEADERS, PIXELBIN_BASE_URL

logger = logging.getLogger(__name__)


class PixelBinService:
    """Сервис для работы с Pixelbin API"""
    
    @staticmethod
    def preprocess_for_pixelbin(image_bytes: bytes, max_size: int = 1024, contrast_factor: float = 1.15) -> Optional[bytes]:
        """
        Лёгкий препроцессинг, чтобы повысить шанс успешной валидации Pixelbin:
        - авто-ориентация EXIF
        - downscale до max_size по большей стороне (с сохранением пропорций)
        - лёгкое повышение контраста
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("RGB")
                img = ImageOps.exif_transpose(img)
                
                # Масштабирование с сохранением пропорций
                w, h = img.size
                scale = min(max_size / max(w, h), 1.0)
                if scale < 1.0:
                    new_size = (int(w * scale), int(h * scale))
                    img = img.resize(new_size, Image.LANCZOS)
                
                # Лёгкое повышение контраста
                img = ImageEnhance.Contrast(img).enhance(contrast_factor)
                
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                return buf.getvalue()
        except Exception as e:
            logger.warning(f"Preprocess Pixelbin не удался: {e}")
            return None
    
    @staticmethod
    def upload_image(image_data: bytes, filename: str = "image.jpg") -> Optional[Dict]:
        """Загрузка изображения в Pixelbin API"""
        if not settings.pixelbin_access_token:
            logger.warning("Pixelbin: ACCESS_TOKEN не настроен, пропускаем загрузку")
            return None
        
        try:
            url = f"{PIXELBIN_BASE_URL}/skinAnalysisInt/generate"
            
            # Определяем MIME тип на основе расширения
            mime_type = 'image/png' if filename.lower().endswith('.png') else 'image/jpeg'
            
            files = {
                'input.image': (filename, image_data, mime_type)
            }
            
            logger.info(f"Отправка изображения в Pixelbin API: {filename} ({len(image_data)} bytes)")
            response = requests.post(url, headers=PIXELBIN_HEADERS, files=files, timeout=60)
            
            if not response.ok:
                error_text = response.text[:500]
                logger.warning(f"Pixelbin API ошибка: {response.status_code} - {error_text}")
                
                # Обрабатываем различные типы ошибок
                try:
                    error_data = response.json()
                    error_code = error_data.get('errorCode', '')
                    error_type = error_data.get('exception', '')
                    
                    # 400 - Validation Error
                    if response.status_code == 400:
                        if 'validation' in error_text.lower() or 'JR-0400' in error_code:
                            return {"error": "validation_failed", "status_code": 400, "message": error_data}
                    
                    # 403 - Usage Limit Exceeded или Forbidden
                    elif response.status_code == 403:
                        # Любая 403 ошибка - это лимит использования или запрет доступа
                        logger.warning(f"Pixelbin: ошибка 403 (Forbidden/Limit) - errorCode: {error_code}, exception: {error_type}")
                        logger.warning("Pixelbin: достигнут лимит использования или доступ запрещён, используем эвристики")
                        return {"error": "usage_limit_exceeded", "status_code": 403, "error_code": error_code, "error_type": error_type, "message": error_data}
                    
                    # 429 - Rate Limit
                    elif response.status_code == 429:
                        logger.warning("Pixelbin: превышен лимит запросов, используем эвристики")
                        return {"error": "rate_limit_exceeded", "status_code": 429, "message": error_data}
                    
                    # 500+ - Server Error
                    elif response.status_code >= 500:
                        logger.warning("Pixelbin: ошибка сервера, используем эвристики")
                        return {"error": "server_error", "status_code": response.status_code, "message": error_data}
                    
                    # Другие ошибки
                    else:
                        logger.warning(f"Pixelbin: неизвестная ошибка {response.status_code}, используем эвристики")
                        return {"error": "api_error", "status_code": response.status_code, "message": error_data}
                        
                except:
                    # Если не удалось распарсить JSON, возвращаем общую ошибку
                    return {"error": "api_error", "status_code": response.status_code, "message": error_text}
                
                return None
            
            result = response.json()
            logger.info(f"Pixelbin: изображение загружено, job_id: {result.get('_id')}")
            return result
            
        except Exception as e:
            logger.warning(f"Ошибка при загрузке в Pixelbin: {e}")
            return None
    
    @staticmethod
    def check_status(job_id: str, max_attempts: int = 10, delay: int = 3) -> Optional[Dict]:
        """Проверка статуса задачи в Pixelbin API"""
        if not settings.pixelbin_access_token:
            logger.warning("Pixelbin: ACCESS_TOKEN не настроен, пропускаем проверку статуса")
            return None
        
        if not job_id:
            return None
        
        status_url = f"{PIXELBIN_BASE_URL}/{job_id}"
        
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(status_url, headers=PIXELBIN_HEADERS, timeout=30)
                
                if response.ok:
                    result = response.json()
                    status = result.get('status', 'UNKNOWN')
                    
                    if status == 'SUCCESS':
                        logger.info(f"Pixelbin: задача завершена успешно")
                        return result
                    elif status == 'FAILURE':
                        logger.warning(f"Pixelbin: задача завершилась с ошибкой")
                        return result
                    elif status in ['ACCEPTED', 'PREPARING', 'PROCESSING']:
                        if attempt < max_attempts:
                            logger.debug(f"Pixelbin: статус {status}, ждём {delay} секунд...")
                            time.sleep(delay)
                            continue
                        else:
                            logger.warning(f"Pixelbin: задача всё ещё обрабатывается после {max_attempts} попыток")
                            return result
                
                # Обрабатываем ошибки API
                if not response.ok:
                    error_text = response.text[:500]
                    status_code = response.status_code
                    
                    # 403 - Usage Limit Exceeded или Forbidden
                    if status_code == 403:
                        logger.warning(f"Pixelbin: ошибка 403 при проверке статуса (Forbidden/Limit)")
                        logger.warning("Pixelbin: достигнут лимит использования или доступ запрещён при проверке статуса")
                        return {"error": "usage_limit_exceeded", "status": "FAILURE", "status_code": 403}
                    
                    # 429 - Rate Limit
                    elif status_code == 429:
                        logger.warning(f"Pixelbin: превышен лимит запросов при проверке статуса (429)")
                        if attempt < max_attempts:
                            time.sleep(delay * 2)  # Увеличиваем задержку
                            continue
                        return {"error": "rate_limit_exceeded", "status": "FAILURE", "status_code": 429}
                    
                    # 500+ - Server Error
                    elif status_code >= 500:
                        logger.warning(f"Pixelbin: ошибка сервера при проверке статуса ({status_code})")
                        if attempt < max_attempts:
                            time.sleep(delay)
                            continue
                        return {"error": "server_error", "status": "FAILURE", "status_code": status_code}
                    
                    # Другие ошибки
                    else:
                        logger.warning(f"Pixelbin: ошибка API при проверке статуса ({status_code}): {error_text}")
                        if attempt < max_attempts:
                            time.sleep(delay)
                            continue
                        return {"error": "api_error", "status": "FAILURE", "status_code": status_code}
                
                return result
            except Exception as e:
                logger.warning(f"Ошибка при проверке статуса Pixelbin: {e}")
                if attempt < max_attempts:
                    time.sleep(delay)
                    continue
                return None
        
        return None


def extract_images_from_pixelbin_response(pixelbin_data: Dict) -> List[Dict]:
    """Извлекает все URL изображений из ответа Pixelbin API"""
    images = []
    
    if not pixelbin_data or 'output' not in pixelbin_data:
        logger.warning("Pixelbin: нет данных output в ответе")
        return images
    
    output = pixelbin_data.get('output', {})
    skin_data = output.get('skinData', {})
    
    # Исходное изображение
    if 'input' in pixelbin_data and 'image' in pixelbin_data['input']:
        images.append({
            'url': pixelbin_data['input']['image'],
            'title': 'Исходное изображение',
            'type': 'input'
        })
    
    # Изображения из concerns
    concerns_count = 0
    for concern in skin_data.get('concerns', []):
        if 'image' in concern and concern.get('image'):
            images.append({
                'url': concern['image'],
                'title': concern.get('name', 'Проблема'),
                'type': 'concern',
                'concern_name': concern.get('tech_name', ''),
                'value': concern.get('value', 0),
                'severity': concern.get('severity', '')
            })
            concerns_count += 1
    logger.info(f"Pixelbin: извлечено {concerns_count} изображений из concerns")
    
    logger.info(f"Pixelbin: всего извлечено {len(images)} изображений")
    return images

