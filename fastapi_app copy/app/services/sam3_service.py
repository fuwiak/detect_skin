"""
Сервис для работы с SAM3 сегментацией
"""
import base64
import tempfile
import time
import io
import logging
import requests
from typing import Dict, List, Optional
from PIL import Image

from app.dependencies import FAL_AVAILABLE, fal_client, NUMPY_AVAILABLE
from app.config import settings
from app.utils.constants import (
    SAM3_ENHANCED_PROMPTS, SAM3_DISEASES_DEFAULT, SKIN_DISEASE_KNOWLEDGE_BASE, DEFAULT_VISION_MODEL
)
from app.utils.timeout import run_with_timeout, TimeoutException

logger = logging.getLogger(__name__)

# Импортируем numpy и scipy если доступны
if NUMPY_AVAILABLE:
    import numpy as np
    from scipy import ndimage
    from PIL import ImageFilter, ImageDraw, ImageFont, ImageEnhance
else:
    np = None
    ndimage = None
    ImageFilter = None
    ImageDraw = None
    ImageFont = None
    ImageEnhance = None


def generate_rag_enhanced_prompt(disease_key: str, base_prompt: str) -> str:
    """
    Генерирует улучшенный промпт используя RAG (базу знаний о заболеваниях)
    Комбинирует базовый промпт с информацией из knowledge base
    """
    if disease_key not in SKIN_DISEASE_KNOWLEDGE_BASE:
        return base_prompt
    
    knowledge = SKIN_DISEASE_KNOWLEDGE_BASE[disease_key]
    
    # Строим промпт с few-shot примерами и характеристиками
    enhanced_parts = [base_prompt]
    
    # Добавляем характеристики
    if "characteristics" in knowledge:
        characteristics = ", ".join(knowledge["characteristics"])
        enhanced_parts.append(f"Characteristics: {characteristics}")
    
    # Добавляем few-shot примеры
    if "few_shot_examples" in knowledge and knowledge["few_shot_examples"]:
        examples = " | ".join(knowledge["few_shot_examples"])
        enhanced_parts.append(f"Examples: {examples}")
    
    return ". ".join(enhanced_parts)


def analyze_image_for_sam3_prompts(image_base64: str) -> Optional[Dict[str, str]]:
    """
    Использует LLM для предварительного анализа изображения и генерации 
    улучшенных промптов для SAM3 (RAG + LLM pre-analysis)
    """
    if not settings.openrouter_api_key:
        return None
    
    try:
        import requests
        import json
        
        prompt = """Analyze this skin image and provide enhanced prompts for SAM3 segmentation model.
For each visible skin condition, suggest specific, detailed descriptions that will help SAM3 accurately segment them.

Focus on:
- Specific visual characteristics (size, color, texture, shape)
- Location patterns (clustered, scattered, specific body areas)
- Distinguishing features that help identify the condition

Return JSON with disease keys and enhanced prompts. Example:
{
  "skin tags": "multiple small flesh-colored pedunculated growths, 1-5mm, hanging from thin stalks, clustered on neck and chest",
  "papillomas": "raised warty bumps, benign growths, various sizes"
}

Only include conditions that are clearly visible in the image."""
        
        url = settings.openrouter_api_url
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Skin Analyzer"
        }
        
        payload = {
            "model": DEFAULT_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 500,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            try:
                prompts = json.loads(content)
                logger.info(f"LLM сгенерировал {len(prompts)} улучшенных промптов для SAM3")
                return prompts
            except json.JSONDecodeError:
                logger.warning("Не удалось распарсить JSON от LLM для SAM3 промптов")
                return None
        
        return None
    except Exception as e:
        logger.warning(f"Ошибка LLM pre-analysis для SAM3: {e}")
        return None


def sam3_segment(image_path: str, disease_key: str, timeout: int, statuses: List[str], 
                 llm_enhanced_prompts: Optional[Dict[str, str]] = None):
    """
    Вызов SAM3 через fal_client с таймаутом и улучшенными промптами.
    Использует RAG (базу знаний) и опционально LLM-enhanced промпты.
    """
    if not FAL_AVAILABLE or not settings.fal_key:
        statuses.append("❌ SAM3 недоступен (нет fal_client или FAL_KEY)")
        return None
    try:
        # Приоритет: LLM-enhanced промпт > RAG-enhanced > базовый
        if llm_enhanced_prompts and disease_key in llm_enhanced_prompts:
            enhanced_prompt = llm_enhanced_prompts[disease_key]
            logger.info(f"SAM3 использует LLM-enhanced промпт для {disease_key}")
        else:
            base_prompt = SAM3_ENHANCED_PROMPTS.get(disease_key, disease_key)
            enhanced_prompt = generate_rag_enhanced_prompt(disease_key, base_prompt)
            logger.info(f"SAM3 использует RAG-enhanced промпт для {disease_key}")
        
        logger.info(f"SAM3 промпт для {disease_key}: {enhanced_prompt[:150]}...")
        
        def call_fal():
            return fal_client.subscribe(
                "fal-ai/sam-3/image",
                arguments={
                    "image_url": fal_client.upload_file(image_path),
                    "text_prompt": enhanced_prompt
                },
                with_logs=False,
            )

        result, error = run_with_timeout(call_fal, timeout)
        if error:
            if isinstance(error, TimeoutException):
                statuses.append(f"⏱️ ПРОПУЩЕНО (таймаут {timeout}с) для {disease_key}")
            else:
                statuses.append(f"⚠️ Ошибка SAM3 для {disease_key}: {error}")
            return None
        return result
    except Exception as e:
        statuses.append(f"⚠️ Ошибка SAM3 для {disease_key}: {e}")
        return None


def filter_masks_by_coverage(masks: List[Dict], image_width: int, image_height: int, 
                            max_coverage_percent: float = 25.0) -> List[Dict]:
    """
    Фильтрует маски, которые покрывают слишком большой процент изображения.
    """
    if not masks or not NUMPY_AVAILABLE:
        return masks
    
    total_image_pixels = image_width * image_height
    filtered_masks = []
    filtered_count = 0
    
    for mask_data in masks:
        if 'url' not in mask_data:
            filtered_masks.append(mask_data)
            continue
        
        try:
            # Загружаем маску
            mask_response = requests.get(mask_data['url'], timeout=10)
            mask_response.raise_for_status()
            
            mask_img = Image.open(io.BytesIO(mask_response.content))
            if mask_img.mode != 'L':
                mask_img = mask_img.convert('L')
            
            # Масштабируем под размер изображения
            if mask_img.size != (image_width, image_height):
                mask_img = mask_img.resize((image_width, image_height), Image.Resampling.LANCZOS)
            
            # Вычисляем процент покрытия
            mask_array = np.array(mask_img)
            mask_pixels = np.sum(mask_array > 127)  # Пиксели маски (непрозрачные)
            coverage_percent = (mask_pixels / total_image_pixels) * 100
            
            # Фильтруем маски, которые покрывают слишком большую область
            if coverage_percent <= max_coverage_percent:
                filtered_masks.append(mask_data)
                logger.debug(f"Маска принята: покрытие {coverage_percent:.2f}%")
            else:
                filtered_count += 1
                logger.info(f"Маска отфильтрована: покрытие {coverage_percent:.2f}% > {max_coverage_percent}%")
        
        except Exception as e:
            logger.warning(f"Ошибка при фильтрации маски: {e}, добавляем маску без проверки")
            filtered_masks.append(mask_data)
    
    if filtered_count > 0:
        logger.info(f"Отфильтровано {filtered_count} масок с покрытием > {max_coverage_percent}%")
    
    return filtered_masks


def run_sam3_pipeline(image_bytes: bytes, diseases: Dict[str, str], timeout: int = 5, 
                     use_llm_preanalysis: bool = True, max_mask_coverage_percent: float = 25.0) -> Dict:
    """
    Запускает последовательную сегментацию SAM3 по списку заболеваний.
    Использует RAG (базу знаний) и опционально LLM pre-analysis для улучшения промптов.
    Возвращает mask_results и статус-лог.
    """
    statuses = []
    mask_results = {}

    if not FAL_AVAILABLE or not settings.fal_key:
        statuses.append("❌ SAM3 недоступен (нет fal_client или FAL_KEY)")
        return {'statuses': statuses, 'mask_results': {}}

    # LLM pre-analysis для генерации улучшенных промптов (RAG + LLM)
    llm_enhanced_prompts = None
    if use_llm_preanalysis and settings.openrouter_api_key:
        statuses.append("🧠 LLM ПРЕДАНАЛИЗ: генерация улучшенных промптов...")
        try:
            # Конвертируем bytes в base64 для LLM
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            llm_enhanced_prompts = analyze_image_for_sam3_prompts(image_base64)
            if llm_enhanced_prompts:
                statuses.append(f"✅ LLM сгенерировал {len(llm_enhanced_prompts)} улучшенных промптов")
            else:
                statuses.append("ℹ️ LLM pre-analysis недоступен, используем RAG промпты")
        except Exception as e:
            logger.warning(f"Ошибка LLM pre-analysis: {e}")
            statuses.append("ℹ️ LLM pre-analysis пропущен, используем RAG промпты")

    # Сохраняем изображение во временный файл
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
        tmp.write(image_bytes)
        tmp.flush()

        total = len(diseases)
        for idx, (disease_key, disease_name) in enumerate(diseases.items(), 1):
            statuses.append(f"🔍 [{idx}/{total}] {disease_name.upper()}")
            
            # Увеличиваем таймаут для кожных меток и других образований, которые могут быть многочисленными
            current_timeout = timeout
            if disease_key in ["skin tags", "papillomas", "moles", "freckles", "pigmentation"]:
                current_timeout = max(timeout, 10)  # Минимум 10 секунд для многочисленных образований
                logger.info(f"Увеличенный таймаут для {disease_name}: {current_timeout}с")
            
            start = time.time()
            result = sam3_segment(tmp.name, disease_key, current_timeout, statuses, llm_enhanced_prompts)
            elapsed = time.time() - start

            if result and isinstance(result, dict) and result.get('masks'):
                # Получаем размер изображения для фильтрации
                image = Image.open(io.BytesIO(image_bytes))
                img_width, img_height = image.size
                
                # Фильтруем маски по размеру покрытия (точечные изменения, а не большие области)
                original_count = len(result['masks'])
                filtered_masks = filter_masks_by_coverage(
                    result['masks'], 
                    img_width, 
                    img_height, 
                    max_coverage_percent=max_mask_coverage_percent
                )
                
                if filtered_masks:
                    result['masks'] = filtered_masks
                    count = len(filtered_masks)
                    if count < original_count:
                        statuses.append(f"✅ {disease_name}: {count} маск (отфильтровано {original_count - count} больших масок) ({elapsed:.1f}с)")
                    else:
                        statuses.append(f"✅ {disease_name}: {count} маск ({elapsed:.1f}с)")
                    mask_results[disease_key] = result
                else:
                    statuses.append(f"⚪ {disease_name}: все маски отфильтрованы (слишком большие) ({elapsed:.1f}с)")
            else:
                statuses.append(f"⚪ {disease_name}: нет масок ({elapsed:.1f}с)")

    return {'statuses': statuses, 'mask_results': mask_results}


def create_sam3_overlay_image(original_image_bytes: bytes, mask_results: Dict) -> Optional[str]:
    """
    Создаёт изображение с наложенными масками SAM3 на оригинальное фото.
    Создаёт КОПИЮ изображения и накладывает ВСЕ маски на эту копию.
    Возвращает base64 строку готового изображения.
    """
    if not NUMPY_AVAILABLE:
        logger.warning("NumPy/SciPy недоступны, наложение масок пропущено")
        return None
    
    try:
        # Загружаем оригинальное изображение
        original = Image.open(io.BytesIO(original_image_bytes)).convert('RGB')
        width, height = original.size
        
        # СОЗДАЁМ КОПИЮ изображения (не изменяем оригинал!)
        result_img = original.copy().convert('RGBA')
        
        # Затемняем копию для контраста
        result_array = np.array(result_img).astype(float)
        dimmed = (result_array * 0.25).astype(np.uint8)
        result_img = Image.fromarray(dimmed).convert('RGBA')
        
        # Слой для подсветки (начинаем с прозрачного)
        highlight_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Цвета для разных заболеваний
        colors = {
            'acne': (255, 0, 0), 'pimples': (255, 50, 50), 'pustules': (255, 20, 20),
            'papules': (255, 100, 100), 'blackheads': (100, 0, 255), 'whiteheads': (255, 255, 0),
            'comedones': (80, 0, 200), 'redness': (255, 100, 0), 'inflammation': (255, 150, 0),
            'red spots': (255, 80, 80), 'rosacea': (255, 60, 100), 'irritation': (255, 120, 80),
            'pigmentation': (200, 0, 255), 'hyperpigmentation': (180, 0, 200), 'dark spots': (255, 0, 255),
            'age spots': (150, 0, 255), 'melasma': (160, 0, 180), 'sun spots': (140, 0, 200),
            'freckles': (120, 50, 200), 'papillomas': (0, 255, 0), 'warts': (50, 255, 50),
            'moles': (255, 200, 0), 'skin tags': (100, 255, 100), 'growths': (150, 255, 50),
            'wrinkles': (0, 200, 255), 'fine lines': (100, 200, 255), 'deep wrinkles': (0, 150, 255),
            'expression lines': (50, 180, 255), 'skin lesion': (0, 255, 255), 'scars': (255, 150, 255),
            'post-acne marks': (255, 100, 200), 'post acne marks': (255, 100, 200),
            'acne scars': (200, 100, 255), 'blemishes': (255, 120, 180), 'eczema': (255, 180, 100),
            'dermatitis': (255, 120, 60), 'psoriasis': (255, 140, 80), 'dry skin': (200, 200, 100),
            'texture issues': (180, 180, 200), 'enlarged pores': (100, 255, 200),
            'open pores': (120, 255, 220), 'uneven skin tone': (220, 180, 255),
            'discoloration': (200, 150, 255), 'broken capillaries': (255, 0, 100),
            'spider veins': (200, 0, 150), 'sunburn': (255, 40, 0), 'peeling': (255, 220, 180),
        }
        
        total_masks = 0
        mask_centers = []  # Сохраняем центры масок для добавления текста
        
        # Обрабатываем КАЖДОЕ заболевание и КАЖДУЮ маску
        for disease, result in mask_results.items():
            if not result or not isinstance(result, dict):
                continue
            
            if 'masks' not in result or not result['masks']:
                continue
            
            color = colors.get(disease, (255, 255, 255))
            # Получаем русское название болезни
            disease_name_ru = SAM3_DISEASES_DEFAULT.get(disease, disease)
            logger.info(f"Обработка масок для {disease} ({disease_name_ru}): {len(result['masks'])} масок")
            
            for i, mask_data in enumerate(result['masks']):
                if 'url' not in mask_data:
                    continue
                
                try:
                    mask_url = mask_data['url']
                    logger.debug(f"Загрузка маски {disease} #{i+1}: {mask_url}")
                    
                    # Загружаем маску
                    mask_response = requests.get(mask_url, timeout=30)
                    mask_response.raise_for_status()
                    
                    # Пробуем загрузить как grayscale, если не получается - конвертируем
                    mask_img = Image.open(io.BytesIO(mask_response.content))
                    if mask_img.mode != 'L':
                        mask_img = mask_img.convert('L')
                    
                    # Масштабируем под размер оригинала
                    if mask_img.size != (width, height):
                        mask_img = mask_img.resize((width, height), Image.Resampling.LANCZOS)
                    
                    mask_array = np.array(mask_img)
                    
                    # Проверяем, что маска не пустая
                    if np.max(mask_array) == 0:
                        logger.warning(f"Маска {disease} #{i+1} пустая, пропускаем")
                        continue
                    
                    # Основное заполнение цветом
                    mask_binary = (mask_array > 127).astype(np.uint8) * 255
                    
                    # Находим центр маски для добавления текста
                    coords = np.where(mask_binary > 0)
                    if len(coords[0]) > 0:
                        center_y = int(np.mean(coords[0]))
                        center_x = int(np.mean(coords[1]))
                        mask_centers.append((center_x, center_y, disease_name_ru, color))
                    
                    colored_fill = Image.new('RGBA', (width, height), color + (255,))
                    mask_alpha = Image.fromarray(mask_binary).convert('L')
                    
                    fill_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                    fill_layer.paste(colored_fill, (0, 0), mask_alpha)
                    
                    # Толстая белая обводка
                    dilated = ndimage.binary_dilation(mask_binary, iterations=7).astype(np.uint8) * 255
                    eroded = ndimage.binary_erosion(mask_binary, iterations=1).astype(np.uint8) * 255
                    thick_border = dilated - eroded
                    
                    border_layer = Image.new('RGBA', (width, height), (255, 255, 255, 255))
                    border_alpha = Image.fromarray(thick_border).convert('L')
                    border_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                    border_img.paste(border_layer, (0, 0), border_alpha)
                    
                    # Двойное свечение для лучшей видимости
                    glow1 = ndimage.binary_dilation(mask_binary, iterations=15).astype(np.uint8) * 255
                    glow1 = glow1 - mask_binary
                    glow1_img = Image.fromarray(glow1).convert('L').filter(ImageFilter.GaussianBlur(radius=7))
                    glow1_colored = Image.new('RGBA', (width, height), color + (200,))
                    glow1_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                    glow1_layer.paste(glow1_colored, (0, 0), glow1_img)
                    
                    glow2 = ndimage.binary_dilation(mask_binary, iterations=25).astype(np.uint8) * 255
                    glow2 = glow2 - mask_binary
                    glow2_img = Image.fromarray(glow2).convert('L').filter(ImageFilter.GaussianBlur(radius=12))
                    glow2_colored = Image.new('RGBA', (width, height), color + (120,))
                    glow2_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                    glow2_layer.paste(glow2_colored, (0, 0), glow2_img)
                    
                    # НАКЛАДЫВАЕМ все слои на highlight_layer
                    highlight_layer = Image.alpha_composite(highlight_layer, glow2_layer)
                    highlight_layer = Image.alpha_composite(highlight_layer, glow1_layer)
                    highlight_layer = Image.alpha_composite(highlight_layer, fill_layer)
                    highlight_layer = Image.alpha_composite(highlight_layer, border_img)
                    
                    total_masks += 1
                    logger.debug(f"Маска {disease} #{i+1} наложена успешно")
                    
                except Exception as e:
                    logger.warning(f"Ошибка обработки маски {disease} #{i+1}: {e}")
                    continue
        
        if total_masks == 0:
            logger.warning("Не найдено масок для наложения")
            return None
        
        logger.info(f"Всего наложено {total_masks} масок")
        
        # Объединяем затемнённое изображение с подсветкой
        result_img = Image.alpha_composite(result_img, highlight_layer).convert('RGB')
        
        # Добавляем русские названия болезней на изображение
        if mask_centers:
            draw = ImageDraw.Draw(result_img)
            # Пробуем загрузить шрифт, если не получается - используем стандартный
            try:
                font_size = max(20, min(width, height) // 30)
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                except:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            for center_x, center_y, disease_name, color in mask_centers:
                # Рисуем текст с обводкой для лучшей читаемости
                text = disease_name
                # Получаем размер текста (с fallback для старых версий PIL)
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                except AttributeError:
                    # Fallback для старых версий PIL
                    text_width, text_height = draw.textsize(text, font=font)
                
                # Позиция текста (центр маски)
                text_x = center_x - text_width // 2
                text_y = center_y - text_height // 2
                
                # Рисуем обводку (чёрная) для лучшей читаемости
                for adj in [(-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2),
                           (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2),
                           (0, -2), (0, -1), (0, 1), (0, 2),
                           (1, -2), (1, -1), (1, 0), (1, 1), (1, 2),
                           (2, -2), (2, -1), (2, 0), (2, 1), (2, 2)]:
                    draw.text((text_x + adj[0], text_y + adj[1]), text, font=font, fill=(0, 0, 0, 255))
                
                # Рисуем сам текст (белый)
                draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
        
        # Усиление контраста и цвета для лучшей видимости
        enhancer = ImageEnhance.Contrast(result_img)
        result_img = enhancer.enhance(2.2)
        enhancer = ImageEnhance.Color(result_img)
        result_img = enhancer.enhance(2.5)
        enhancer = ImageEnhance.Brightness(result_img)
        result_img = enhancer.enhance(1.3)
        result_img = result_img.filter(ImageFilter.SHARPEN)
        
        # Конвертируем в base64
        output = io.BytesIO()
        result_img.save(output, format='JPEG', quality=95)
        output.seek(0)
        image_base64 = base64.b64encode(output.read()).decode('utf-8')
        
        logger.info(f"✅ Изображение с наложенными масками SAM3 создано успешно ({total_masks} масок)")
        return f"data:image/jpeg;base64,{image_base64}"
        
    except Exception as e:
        logger.error(f"Ошибка создания изображения с масками: {e}", exc_info=True)
        return None

