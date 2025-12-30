"""
API endpoint для проксирования изображений
"""
import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter()


@router.get(
    "/proxy-image",
    summary="Прокси изображений",
    description="Проксирует изображения из Pixelbin и FAL для обхода CORS ограничений"
)
async def proxy_image(url: str = Query(..., description="URL изображения для проксирования")):
    """
    Прокси для загрузки изображений (Pixelbin/FAL) для обхода CORS
    
    Разрешённые домены:
    - delivery.pixelbin.io
    - pixelbin.io
    - fal.media
    - v3b.fal.media
    
    **Параметры:**
    - **url**: URL изображения для проксирования (обязательно)
    
    **Пример:**
    ```
    GET /api/proxy-image?url=https://fal.media/image.jpg
    ```
    
    Возвращает изображение с правильными CORS заголовками.
    """
    try:
        if not url:
            raise HTTPException(status_code=400, detail="URL не предоставлен")
        
        # Разрешённые домены: Pixelbin и fal.media
        allowed_domains = ['delivery.pixelbin.io', 'pixelbin.io', 'fal.media', '.fal.media', 'v3b.fal.media']
        if not any(domain in url for domain in allowed_domains):
            raise HTTPException(status_code=400, detail="Недопустимый URL")
        
        # Загружаем изображение
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Возвращаем изображение с правильными заголовками
        return Response(
            content=response.content,
            media_type=response.headers.get('Content-Type', 'image/jpeg'),
            headers={
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Allow-Origin': '*'
            }
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при проксировании изображения: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

