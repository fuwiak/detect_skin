"""
API endpoint для анализа кожи
"""
import base64
import io
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict

from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.config import settings
from app.utils.constants import (
    DEFAULT_CONFIG, DEFAULT_VISION_MODEL, DEFAULT_TEXT_MODEL, 
    DETECTION_FALLBACKS, SAM3_DISEASES_DEFAULT
)
from app.services.openrouter_service import analyze_image_with_openrouter
from app.services.llm_service import generate_report_with_llm
from app.services.pixelbin_service import PixelBinService, extract_images_from_pixelbin_response
from app.services.sam3_service import run_sam3_pipeline, create_sam3_overlay_image
from app.services.segmentation_service import generate_heuristic_analysis
from app.services.validation_service import validate_image
from app.services.image_analysis_fallback import analyze_image_fallback
from app.utils.image_utils import convert_heic_to_jpeg, detect_image_format
from app.utils.statistics import format_statistics_detailed
from app.dependencies import HEIC_SUPPORT

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Анализ состояния кожи",
    description="""
    Эндпоинт для анализа изображения кожи лица с использованием LLM и методов сегментации.
    
    Поддерживает два режима работы:
    - **pixelbin**: Использует Pixelbin API для анализа (по умолчанию)
    - **sam3**: Использует SAM3 для точной сегментации заболеваний
    
    Возвращает:
    - Данные анализа (scores для различных параметров кожи)
    - Текстовый отчёт на русском или английском языке
    - Изображения с выделенными проблемными зонами
    - Информацию о методе анализа
    """,
    responses={
        200: {
            "description": "Успешный анализ",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "acne_score": 25.5,
                            "pigmentation_score": 30.2,
                            "pores_size": 45.8,
                            "wrinkles_grade": 15.3
                        },
                        "report": "Отчёт о состоянии кожи...",
                        "analysis_method": "pixelbin"
                    }
                }
            }
        },
        400: {"description": "Неверный запрос (отсутствует изображение)"},
        503: {"description": "Все API недоступны"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def analyze_skin(request: AnalyzeRequest):
    """
    Анализ состояния кожи по изображению
    
    **Параметры:**
    - **image**: Base64 encoded image (обязательно)
    - **config**: Конфигурация анализа (опционально)
    - **mode**: Режим работы - "pixelbin" или "sam3" (по умолчанию "pixelbin")
    - **sam3_timeout**: Таймаут для SAM3 в секундах (3-20, по умолчанию 5)
    - **sam3_diseases**: Список заболеваний для анализа SAM3 (опционально)
    - **sam3_use_llm_preanalysis**: Использовать LLM предварительный анализ для SAM3 (по умолчанию True)
    - **sam3_max_coverage_percent**: Максимальный процент покрытия маски (0-100, по умолчанию 25)
    
    **Пример запроса:**
    ```json
    {
        "image": "data:image/jpeg;base64,/9j/4AAQ...",
        "mode": "pixelbin",
        "config": {
            "vision_model": "google/gemini-2.5-flash",
            "temperature": 0.0
        }
    }
    ```
    """
    import time
    start_time = time.time()
    
    # Логируем начало запроса
    logger.info("=" * 80)
    logger.info("📥 НОВЫЙ ЗАПРОС НА АНАЛИЗ КОЖИ")
    logger.info("=" * 80)
    logger.info(f"⏰ Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📋 Режим: {request.mode or 'pixelbin'}")
    logger.info(f"📋 Конфигурация: {request.config.dict() if request.config else 'по умолчанию'}")
    if request.sam3_diseases:
        logger.info(f"📋 SAM3 заболевания: {len(request.sam3_diseases)} шт.")
    
    try:
        image_base64 = request.image
        
        if not image_base64:
            logger.error("❌ Ошибка: изображение не предоставлено")
            raise HTTPException(status_code=400, detail="Изображение не предоставлено")
        
        # Логируем размер изображения
        image_size = len(image_base64)
        logger.info(f"📷 Размер изображения (base64): {image_size:,} байт ({image_size / 1024:.2f} KB)")
        
        # Убираем префикс data:image если есть и извлекаем MIME тип
        mime_type = None
        if ',' in image_base64:
            prefix = image_base64.split(',')[0]
            image_base64 = image_base64.split(',')[1]
            if 'data:' in prefix and ';' in prefix:
                mime_type = prefix.split(';')[0].split(':')[1]
                logger.info(f"📷 MIME тип: {mime_type}")
        
        # Получаем настройки из запроса или используем по умолчанию
        config = request.config.dict() if request.config else DEFAULT_CONFIG.copy()
        vision_model = config.get('vision_model', DEFAULT_VISION_MODEL)
        text_model = config.get('text_model', DEFAULT_TEXT_MODEL)
        temperature = config.get('temperature', 0.7)
        max_tokens = config.get('max_tokens', 1000)
        language = config.get('language', 'ru')
        
        logger.info(f"🤖 Vision модель: {vision_model}")
        logger.info(f"🤖 Text модель: {text_model}")
        logger.info(f"🌡️  Temperature: {temperature}")
        logger.info(f"🔢 Max tokens: {max_tokens}")
        logger.info(f"🌍 Язык: {language}")
        
        # Пробуем детекцию через доступные API
        skin_data = None
        used_provider = None
        used_model = None
        
        # Логируем доступность API ключей
        logger.info("=" * 80)
        logger.info("🔍 Проверка доступности API:")
        logger.info(f"   OpenRouter API Key: {'✅ доступен' if settings.openrouter_api_key else '❌ не найден'}")
        logger.info(f"   Pixelbin Access Token: {'✅ доступен' if settings.pixelbin_access_token else '❌ не найден'}")
        logger.info("=" * 80)
        
        # Пробуем через OpenRouter
        if settings.openrouter_api_key:
            openrouter_models_to_try = []
            openrouter_models_to_try.append(vision_model)
            logger.info(f"🎯 Приоритет: используем выбранную модель: {vision_model}")
            
            for fallback in DETECTION_FALLBACKS:
                if fallback["provider"] == "openrouter":
                    model = fallback["model"]
                    if model != vision_model:
                        openrouter_models_to_try.append(model)
            
            for model in openrouter_models_to_try:
                logger.info(f"Пробуем модель через OpenRouter: {model}")
                try:
                    skin_data = analyze_image_with_openrouter(image_base64, model, temperature, max_tokens)
                    if skin_data:
                        used_provider = "openrouter"
                        used_model = model
                        logger.info(f"✅ Успешно использована модель: {model}")
                        break
                except Exception as e:
                    logger.warning(f"Модель {model} вызвала исключение: {e}")
                    continue
        else:
            logger.warning("⚠️ OpenRouter API ключ не найден. Проверьте переменную окружения OPENROUTER_API_KEY в Railway.")
        
        # Декодируем base64 изображение в bytes (нужно для fallback анализа)
        image_bytes = base64.b64decode(image_base64)
        
        # Если OpenRouter не вернул данные или вернул только нули, используем fallback
        if not skin_data:
            logger.warning("⚠️ OpenRouter не вернул данные, используем fallback анализ")
            skin_data = analyze_image_fallback(image_bytes)
            used_provider = "fallback"
            used_model = "image_analysis"
        else:
            # Проверяем, что данные не все нули
            has_valid_data = any(
                skin_data.get(key, 0) != 0 
                for key in ['acne_score', 'pigmentation_score', 'pores_size', 'wrinkles_grade', 
                           'skin_tone', 'texture_score', 'moisture_level', 'oiliness']
            )
            if not has_valid_data:
                logger.warning("⚠️ OpenRouter вернул только нули, используем fallback анализ")
                fallback_data = analyze_image_fallback(image_bytes)
                # Объединяем данные (fallback имеет приоритет для нулевых значений)
                for key in fallback_data:
                    if skin_data.get(key, 0) == 0 and fallback_data[key] != 0:
                        skin_data[key] = fallback_data[key]
                if used_provider == "openrouter":
                    used_provider = "openrouter+fallback"
        
        # Определяем MIME type, если не передан
        if not mime_type:
            detected_mime = detect_image_format(image_bytes)
            if detected_mime:
                mime_type = detected_mime
                logger.info(f"Определен формат изображения: {mime_type}")
        
        # Конвертируем HEIC в JPEG, если нужно
        filename = "image.jpg"
        is_heic = mime_type and mime_type.lower() in ['image/heic', 'image/heif']
        if is_heic:
            if HEIC_SUPPORT:
                try:
                    logger.info(f"Конвертация HEIC в JPEG... (размер оригинала: {len(image_bytes)} bytes)")
                    original_size = len(image_bytes)
                    image_bytes = convert_heic_to_jpeg(image_bytes)
                    mime_type = 'image/jpeg'  # Обновляем mime_type после конвертации
                    logger.info(f"HEIC успешно сконвертирован в JPEG (размер после конвертации: {len(image_bytes)} bytes)")
                    
                    # Проверяем, что получился валидный JPEG
                    try:
                        from PIL import Image
                        test_img = Image.open(io.BytesIO(image_bytes))
                        logger.info(f"Проверка JPEG: размер изображения {test_img.size}, режим {test_img.mode}")
                        test_img.close()
                    except Exception as e:
                        logger.warning(f"Предупреждение: конвертированное изображение может быть некорректным: {e}")
                except Exception as e:
                    logger.error(f"Не удалось сконвертировать HEIC: {e}", exc_info=True)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Ошибка при конвертации HEIC файла: {str(e)}"
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="HEIC файлы не поддерживаются. Установите pillow-heif для поддержки HEIC."
                )
        
        # Режим работы: pixelbin (по умолчанию) или sam3
        mode = request.mode or 'pixelbin'
        pixelbin_images = []
        pixelbin_attempts = []
        analysis_method = mode
        use_heuristics = False
        warning_message = None
        
        if mode == "sam3":
            # SAM3 режим
            logger.info("=" * 80)
            logger.info("🎯 РЕЖИМ SAM3")
            logger.info("=" * 80)
            
            try:
                original_image_bytes = bytes(image_bytes)
                
                statuses = []
                statuses.append("🔧 ПРЕДОБРАБОТКА")
                preprocessed = PixelBinService.preprocess_for_pixelbin(image_bytes)
                if preprocessed:
                    image_bytes = preprocessed
                    statuses.append("✅ Предобработка выполнена")
                
                selected_diseases = {
                    k: v for k, v in SAM3_DISEASES_DEFAULT.items()
                    if (not request.sam3_diseases or k in request.sam3_diseases)
                }
                if not selected_diseases:
                    selected_diseases = SAM3_DISEASES_DEFAULT
                
                logger.info(f"📋 Заболеваний для анализа: {len(selected_diseases)}")
                logger.info(f"⏱️  Timeout: {request.sam3_timeout or 5} секунд")
                logger.info(f"🧠 LLM pre-analysis: {request.sam3_use_llm_preanalysis or True}")
                
                sam3_result = run_sam3_pipeline(
                    image_bytes,
                    selected_diseases,
                    timeout=request.sam3_timeout or 5,
                    use_llm_preanalysis=request.sam3_use_llm_preanalysis or True,
                    max_mask_coverage_percent=request.sam3_max_coverage_percent or 25.0
                )
                combined_statuses = statuses + sam3_result.get('statuses', [])
                
                overlay_image = None
                mask_results = sam3_result.get('mask_results', {})
                if mask_results:
                    logger.info(f"✅ SAM3 нашел {len(mask_results)} типов заболеваний")
                    try:
                        overlay_image = create_sam3_overlay_image(original_image_bytes, mask_results)
                        logger.info("✅ Overlay изображение создано")
                    except Exception as e:
                        logger.error(f"❌ Ошибка при создании overlay: {e}", exc_info=True)
                        overlay_image = None
                
                pixelbin_images = [{
                    'type': 'sam3',
                    'sam3_results': mask_results,
                    'statuses': combined_statuses,
                    'timeout': request.sam3_timeout or 5,
                    'overlay_image': overlay_image
                }]
                
                logger.info("=" * 80)
                logger.info("✅ SAM3 РЕЖИМ ЗАВЕРШЁН")
                logger.info("=" * 80)
                
            except Exception as e:
                logger.error("=" * 80)
                logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В SAM3 РЕЖИМЕ: {e}")
                logger.error("=" * 80, exc_info=True)
                # Возвращаем пустой результат вместо падения
                pixelbin_images = [{
                    'type': 'sam3',
                    'sam3_results': {},
                    'statuses': statuses + [f"❌ Ошибка SAM3: {str(e)}"],
                    'timeout': request.sam3_timeout or 5,
                    'overlay_image': None,
                    'error': str(e)
                }]
                warning_message = f"SAM3 режим завершился с ошибкой: {str(e)}"
        else:
            # Pixelbin режим - полная логика с вариантами
            try:
                # Валидация изображения перед отправкой в Pixelbin
                validation_result = validate_image(image_bytes, file_size=len(image_bytes), require_face=True)
                
                if not validation_result['valid']:
                    error_msg = validation_result['error']
                    logger.warning(f"Валидация изображения не пройдена: {error_msg}")
                    raise HTTPException(
                        status_code=400,
                        detail=error_msg
                    )
                
                # Добавляем предупреждения, если есть
                if validation_result.get('warnings'):
                    for warning in validation_result['warnings']:
                        logger.warning(f"Предупреждение валидации: {warning}")
                        if not warning_message:
                            warning_message = warning
                        else:
                            warning_message += f"\n{warning}"
                
                # Логируем информацию о лице, если найдено
                if validation_result.get('face_detected') and validation_result.get('face_info'):
                    face_info = validation_result['face_info']
                    logger.info(f"Найдено лицо на изображении: {face_info.get('count', 0)} лиц(а), размер самого большого: {face_info.get('largest', {}).get('width', 0)}x{face_info.get('largest', {}).get('height', 0)}")
                
                # Готовим варианты для Pixelbin: оригинал + препроцесс
                variants = [("pixelbin-original", image_bytes, filename)]
                preprocessed = PixelBinService.preprocess_for_pixelbin(image_bytes)
                if preprocessed:
                    variants.append(("pixelbin-preprocessed", preprocessed, "image-preprocessed.jpg"))
                
                # Отправляем в Pixelbin API (приоритет: оригинал, затем препроцесс)
                pixelbin_result = None
                for variant_name, variant_bytes, variant_filename in variants:
                    pixelbin_attempts.append(variant_name)
                    pixelbin_result = PixelBinService.upload_image(variant_bytes, variant_filename)
                    
                    # Если лимит/блок — дальше нет смысла пытаться
                    if pixelbin_result and pixelbin_result.get('error') in ['usage_limit_exceeded', 'rate_limit_exceeded']:
                        error_code = pixelbin_result.get('error_code', '')
                        error_type = pixelbin_result.get('error_type', '')
                        logger.warning(f"Pixelbin: ошибка {pixelbin_result.get('error')} (errorCode: {error_code}, exception: {error_type}), переключаемся на эвристики")
                        warning_message = f"Pixelbin API недоступен (ошибка 403: лимит использования достигнут). Используется эвристический анализ."
                        use_heuristics = True
                        pixelbin_result = None
                        analysis_method = "heuristics"
                        break
                    
                    # Если ошибка валидации/прочие — пробуем следующий вариант
                    if pixelbin_result and pixelbin_result.get('error'):
                        logger.warning(f"Pixelbin попытка {variant_name} вернула ошибку {pixelbin_result.get('error')}, пробуем следующий вариант")
                        pixelbin_result = None
                        continue
                    
                    # Успешная постановка задачи
                    if pixelbin_result and '_id' in pixelbin_result:
                        job_id = pixelbin_result['_id']
                        logger.info(f"Pixelbin ({variant_name}): задача создана, job_id: {job_id}")
                        
                        final_result = PixelBinService.check_status(job_id, max_attempts=10, delay=3)
                        
                        if final_result and final_result.get('status') == 'SUCCESS':
                            pixelbin_images = extract_images_from_pixelbin_response(final_result)
                            logger.info(f"Pixelbin ({variant_name}): получено {len(pixelbin_images)} изображений")
                            analysis_method = "pixelbin"
                            break
                        else:
                            if final_result and final_result.get('error'):
                                error_type = final_result.get('error')
                                status_code = final_result.get('status_code', 0)
                                
                                # Если 403 - сразу переключаемся на эвристики
                                if error_type == 'usage_limit_exceeded' or status_code == 403:
                                    logger.warning(f"Pixelbin ({variant_name}): ошибка 403 (лимит использования), переключаемся на эвристики")
                                    if not warning_message:
                                        warning_message = f"Pixelbin API недоступен (ошибка 403: лимит использования достигнут). Используется эвристический анализ."
                                    use_heuristics = True
                                    analysis_method = "heuristics"
                                    pixelbin_result = None
                                    break
                                
                                logger.warning(f"Pixelbin ({variant_name}): ошибка API при проверке статуса ({error_type}, {status_code}), пробуем следующий вариант")
                            else:
                                logger.warning(f"Pixelbin ({variant_name}): задача не завершена или завершилась с ошибкой, пробуем следующий вариант")
                            pixelbin_result = None
                            continue
                
                if not pixelbin_images:
                    # Все попытки Pixelbin не дали результата — эвристики
                    logger.warning("Pixelbin: все попытки не дали результата, переключаемся на эвристики")
                    use_heuristics = True
                    analysis_method = "heuristics"
            except Exception as e:
                logger.warning(f"Ошибка при работе с Pixelbin API: {e}, используем эвристики")
                use_heuristics = True
                analysis_method = "heuristics"
            
            # Если используем эвристики, генерируем данные с учётом отчёта и сегментации
            if use_heuristics:
                logger.info("Генерация эвристического анализа с учётом текстового отчёта и сегментации")
                # Отчёт будет сгенерирован позже, пока передаем None
                heuristic_result = generate_heuristic_analysis(skin_data, None, image_bytes)
                
                # Формируем сообщение о методах
                methods_used = heuristic_result.get('methods_used', [])
                primary_method = heuristic_result.get('primary_method', 'Простые эвристики')
                
                if methods_used:
                    methods_text = ", ".join(methods_used)
                    message = f'Использован эвристический анализ: {methods_text}'
                else:
                    message = 'Использован эвристический анализ с простыми эвристиками'
                
                pixelbin_images = [{
                    'type': 'heuristic',
                    'heuristic_data': heuristic_result,
                    'message': message,
                    'primary_method': primary_method,
                    'methods_used': methods_used
                }]
                analysis_method = f"heuristics ({primary_method})"
        
        # Генерируем текстовый отчёт
        report = generate_report_with_llm(skin_data, used_provider or "openrouter", text_model, temperature, language)
        
        # Если используем эвристики и отчёт уже сгенерирован, обновляем эвристические данные
        if use_heuristics and pixelbin_images and pixelbin_images[0].get('type') == 'heuristic':
            heuristic_result = generate_heuristic_analysis(skin_data, report, image_bytes)
            methods_used = heuristic_result.get('methods_used', [])
            primary_method = heuristic_result.get('primary_method', 'Простые эвристики')
            pixelbin_images[0]['heuristic_data'] = heuristic_result
            pixelbin_images[0]['primary_method'] = primary_method
            pixelbin_images[0]['methods_used'] = methods_used
            analysis_method = f"heuristics ({primary_method})"
        
        # Формируем статистику (числовые показатели)
        statistics = format_statistics_detailed(skin_data, pixelbin_images)
        
        elapsed_time = time.time() - start_time
        
        # Логируем успешное завершение
        logger.info("=" * 80)
        logger.info("✅ АНАЛИЗ ЗАВЕРШЁН УСПЕШНО")
        logger.info("=" * 80)
        logger.info(f"⏱️  Общее время выполнения: {elapsed_time:.2f} секунд")
        logger.info(f"📊 Метод анализа: {analysis_method}")
        logger.info(f"🤖 Провайдер: {used_provider or 'N/A'}")
        logger.info(f"🤖 Модель: {used_model or 'N/A'}")
        logger.info(f"📷 Изображений получено: {len(pixelbin_images)}")
        if warning_message:
            logger.warning(f"⚠️  Предупреждение: {warning_message}")
        logger.info("=" * 80)
        
        return AnalyzeResponse(
            success=True,
            data=skin_data,
            statistics=statistics,
            report=report,
            pixelbin_images=pixelbin_images,
            provider=used_provider,
            model=used_model,
            config=config,
            use_heuristics=use_heuristics,
            analysis_method=analysis_method,
            pixelbin_attempts=pixelbin_attempts,
            warning=warning_message
        )
        
    except HTTPException as e:
        elapsed_time = time.time() - start_time
        logger.error("=" * 80)
        logger.error(f"❌ ОШИБКА HTTP: {e.status_code} - {e.detail}")
        logger.error(f"⏱️  Время до ошибки: {elapsed_time:.2f} секунд")
        logger.error("=" * 80)
        raise
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error("=" * 80)
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        logger.error(f"⏱️  Время до ошибки: {elapsed_time:.2f} секунд")
        logger.error("=" * 80, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

