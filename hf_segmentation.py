#!/usr/bin/env python3
"""
Модуль для сегментации кожи с использованием моделей Hugging Face
Поддерживает акне, морщины, папилломы и пигментацию
"""
import os
import numpy as np
from PIL import Image
import io
from typing import Dict, List, Tuple, Optional
import logging
import cv2

logger = logging.getLogger(__name__)

# Попытка импорта библиотек для Hugging Face
try:
    from transformers import AutoImageProcessor, AutoModelForImageSegmentation
    from transformers import pipeline
    import torch
    HF_AVAILABLE = True
    logger.info("Transformers доступен для Hugging Face сегментации")
except ImportError:
    HF_AVAILABLE = False
    logger.warning("Transformers не установлен, Hugging Face сегментация недоступна")

# Попытка импорта scikit-image для контуров
try:
    from skimage import measure
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False
    logger.warning("scikit-image не установлен, будут использованы cv2 контуры")


class HFSkinSegmenter:
    """
    Сегментатор кожи с использованием моделей Hugging Face
    Использует несколько моделей для разных типов дефектов
    """
    
    def __init__(self, hf_token: Optional[str] = None):
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.device = "cuda" if torch.cuda.is_available() and HF_AVAILABLE else "cpu"
        
        self.models = {}
        self.processors = {}
        
        if not HF_AVAILABLE:
            logger.warning("Hugging Face недоступен, сегментация будет упрощённой")
            return
        
        try:
            # Инициализируем модели по требованию (lazy loading)
            logger.info(f"Инициализация Hugging Face сегментатора на {self.device}")
        except Exception as e:
            logger.warning(f"Ошибка инициализации Hugging Face: {e}")
    
    def _load_model(self, model_name: str, task: str = "image-segmentation"):
        """Загружает модель Hugging Face по требованию"""
        if model_name in self.models:
            return self.models[model_name], self.processors.get(model_name)
        
        try:
            logger.info(f"Загрузка модели {model_name}...")
            pipe = pipeline(
                task,
                model=model_name,
                token=self.hf_token,
                device=0 if self.device == "cuda" else -1
            )
            self.models[model_name] = pipe
            logger.info(f"Модель {model_name} загружена успешно")
            return pipe, None
        except Exception as e:
            logger.warning(f"Не удалось загрузить модель {model_name}: {e}")
            return None, None
    
    def _segment_acne(self, image: Image.Image) -> Optional[np.ndarray]:
        """Сегментация акне с использованием SegFormer"""
        try:
            # Пробуем специализированную модель для акне
            model_name = "akhaliq/segformer-b0-finetuned-ade-640-640"
            pipe, _ = self._load_model(model_name)
            
            if pipe is None:
                # Fallback на общую модель сегментации
                model_name = "nvidia/segformer-b0-finetuned-ade-512-512"
                pipe, _ = self._load_model(model_name)
            
            if pipe is None:
                return None
            
            # Выполняем сегментацию
            results = pipe(image)
            
            # Извлекаем маску для акне (нужно адаптировать под конкретную модель)
            # Для SegFormer результаты - это словарь с 'mask' и 'label'
            mask = None
            for result in results:
                if isinstance(result, dict) and 'mask' in result:
                    # Ищем класс акне (может быть разным в зависимости от модели)
                    label = result.get('label', '').lower()
                    if 'acne' in label or 'pimple' in label or 'skin' in label:
                        mask_array = np.array(result['mask'])
                        if mask is None:
                            mask = mask_array
                        else:
                            mask = np.maximum(mask, mask_array)
            
            return mask
        except Exception as e:
            logger.warning(f"Ошибка сегментации акне: {e}")
            return None
    
    def _segment_pigmentation(self, image: Image.Image) -> Optional[np.ndarray]:
        """Сегментация пигментации/веснушек"""
        try:
            # Пробуем модель для веснушек/пигментации
            model_name = "akhaliq/segformer-b0-finetuned-ade-640-640"
            pipe, _ = self._load_model(model_name)
            
            if pipe is None:
                return None
            
            results = pipe(image)
            
            mask = None
            for result in results:
                if isinstance(result, dict) and 'mask' in result:
                    label = result.get('label', '').lower()
                    if 'freckle' in label or 'pigment' in label or 'spot' in label or 'skin' in label:
                        mask_array = np.array(result['mask'])
                        if mask is None:
                            mask = mask_array
                        else:
                            mask = np.maximum(mask, mask_array)
            
            return mask
        except Exception as e:
            logger.warning(f"Ошибка сегментации пигментации: {e}")
            return None
    
    def _segment_face_parsing(self, image: Image.Image) -> Optional[Dict[str, np.ndarray]]:
        """Face parsing для базовой сегментации лица"""
        try:
            # Используем face parsing для определения зон лица
            # Модель может быть разной, пробуем доступные
            model_name = "briaai/RMBG-1.4"  # Универсальная модель для удаления фона
            pipe, _ = self._load_model(model_name, task="image-segmentation")
            
            if pipe is None:
                return None
            
            results = pipe(image)
            
            # Извлекаем маски для разных частей лица
            face_masks = {}
            for result in results:
                if isinstance(result, dict) and 'mask' in result:
                    label = result.get('label', '').lower()
                    mask_array = np.array(result['mask'])
                    
                    # Категоризируем по зонам
                    if 'forehead' in label or 'head' in label:
                        face_masks['forehead'] = mask_array
                    elif 'cheek' in label:
                        face_masks['cheek'] = mask_array
                    elif 'nose' in label:
                        face_masks['nose'] = mask_array
                    elif 'chin' in label:
                        face_masks['chin'] = mask_array
                    elif 'skin' in label:
                        face_masks['skin'] = mask_array
            
            return face_masks if face_masks else None
        except Exception as e:
            logger.warning(f"Ошибка face parsing: {e}")
            return None
    
    def _detect_wrinkles(self, image: Image.Image, face_masks: Optional[Dict] = None) -> Optional[np.ndarray]:
        """Обнаружение морщин через анализ текстуры на зонах лица"""
        try:
            # Конвертируем PIL в numpy
            img_array = np.array(image.convert('RGB'))
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if len(img_array.shape) == 3 else img_array
            
            # Применяем фильтры для обнаружения морщин (линий)
            # Используем детектор краёв Canny и морфологические операции
            edges = cv2.Canny(gray, 50, 150)
            
            # Морфологические операции для соединения линий
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(edges, kernel, iterations=2)
            
            # Если есть маски лица, применяем только к зонам с морщинами
            if face_masks:
                # Объединяем маски лба и периорбитальной зоны
                forehead_mask = face_masks.get('forehead', np.ones_like(gray) * 255)
                # Применяем маску
                dilated = cv2.bitwise_and(dilated, forehead_mask.astype(np.uint8))
            
            return dilated
        except Exception as e:
            logger.warning(f"Ошибка обнаружения морщин: {e}")
            return None
    
    def _detect_papillomas(self, image: Image.Image) -> Optional[np.ndarray]:
        """Обнаружение папиллом через анализ текстуры и формы"""
        try:
            img_array = np.array(image.convert('RGB'))
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if len(img_array.shape) == 3 else img_array
            
            # Применяем Gaussian blur для сглаживания
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Адаптивная пороговая обработка для обнаружения тёмных областей
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Морфологические операции для соединения близких областей
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Фильтруем по размеру (папилломы обычно маленькие)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            mask = np.zeros_like(gray)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                # Папилломы обычно от 10 до 500 пикселей
                if 10 < area < 500:
                    cv2.fillPoly(mask, [contour], 255)
            
            return mask
        except Exception as e:
            logger.warning(f"Ошибка обнаружения папиллом: {e}")
            return None
    
    def _mask_to_contours(self, mask: np.ndarray, smooth: bool = True) -> List[Dict]:
        """
        Конвертирует маску в список контуров (SVG paths)
        
        Args:
            mask: Бинарная маска (0-255)
            smooth: Применить сглаживание контуров
            
        Returns:
            Список словарей с контурами:
            [{
                'points': [[x1, y1], [x2, y2], ...],
                'svg_path': 'M x1 y1 L x2 y2 ... Z',
                'bbox': [x, y, width, height]
            }, ...]
        """
        if mask is None or mask.size == 0:
            return []
        
        # Бинаризуем маску
        if mask.max() > 1:
            binary = (mask > 127).astype(np.uint8) * 255
        else:
            binary = (mask > 0.5).astype(np.uint8) * 255
        
        contours_list = []
        
        try:
            if SKIMAGE_AVAILABLE:
                # Используем scikit-image для более точных контуров
                contours = measure.find_contours(binary, 0.5)
                for contour in contours:
                    # Конвертируем координаты (scikit-image использует (row, col))
                    points = [[int(p[1]), int(p[0])] for p in contour]
                    
                    if len(points) < 3:
                        continue
                    
                    # Сглаживание через Douglas-Peucker
                    if smooth:
                        epsilon = 0.02 * cv2.arcLength(np.array(points, dtype=np.int32), True)
                        approx = cv2.approxPolyDP(np.array(points, dtype=np.int32), epsilon, True)
                        points = approx.tolist()
                    
                    # Создаём SVG path
                    if len(points) > 0:
                        svg_path = f"M {points[0][0]} {points[0][1]}"
                        for point in points[1:]:
                            svg_path += f" L {point[0]} {point[1]}"
                        svg_path += " Z"
                        
                        # Вычисляем bounding box
                        xs = [p[0] for p in points]
                        ys = [p[1] for p in points]
                        bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
                        
                        contours_list.append({
                            'points': points,
                            'svg_path': svg_path,
                            'bbox': bbox
                        })
            else:
                # Используем OpenCV
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    if len(contour) < 3:
                        continue
                    
                    # Сглаживание
                    if smooth:
                        epsilon = 0.02 * cv2.arcLength(contour, True)
                        approx = cv2.approxPolyDP(contour, epsilon, True)
                        points = approx.reshape(-1, 2).tolist()
                    else:
                        points = contour.reshape(-1, 2).tolist()
                    
                    if len(points) > 0:
                        # Создаём SVG path
                        svg_path = f"M {points[0][0]} {points[0][1]}"
                        for point in points[1:]:
                            svg_path += f" L {point[0]} {point[1]}"
                        svg_path += " Z"
                        
                        # Bounding box
                        xs = [p[0] for p in points]
                        ys = [p[1] for p in points]
                        bbox = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
                        
                        contours_list.append({
                            'points': points,
                            'svg_path': svg_path,
                            'bbox': bbox
                        })
        except Exception as e:
            logger.warning(f"Ошибка конвертации маски в контуры: {e}")
        
        return contours_list
    
    def _contours_to_markers(self, contours: List[Dict], image_size: Tuple[int, int], 
                            concern_type: str, value: float) -> List[Dict]:
        """
        Конвертирует контуры в маркеры для фронтенда
        
        Args:
            contours: Список контуров из _mask_to_contours
            image_size: (width, height) исходного изображения
            concern_type: Тип проблемы (acne, pigmentation, wrinkles, papillomas)
            value: Значение проблемы (0-100)
            
        Returns:
            Список маркеров в формате для фронтенда
        """
        markers = []
        img_width, img_height = image_size
        
        for contour in contours:
            bbox = contour['bbox']
            svg_path = contour['svg_path']
            
            # Конвертируем координаты в проценты
            x_percent = (bbox[0] / img_width) * 100
            y_percent = (bbox[1] / img_height) * 100
            width_percent = (bbox[2] / img_width) * 100
            height_percent = (bbox[3] / img_height) * 100
            
            # Определяем форму на основе типа проблемы
            if concern_type == 'pigmentation':
                shape = 'dot'  # Пигментация - точки
            elif concern_type == 'wrinkles':
                shape = 'wrinkle'  # Морщины - специальная форма
            elif concern_type == 'papillomas':
                shape = 'ellipse'  # Папилломы - эллипсы
            else:  # acne
                shape = 'polygon'  # Акне - многоугольники из контуров
            
            markers.append({
                'x': x_percent,
                'y': y_percent,
                'width': width_percent,
                'height': height_percent,
                'shape': shape,
                'svg_path': svg_path,  # Для точного отображения
                'points': contour['points'],  # Для альтернативного отображения
                'type': concern_type,
                'value': value
            })
        
        return markers
    
    def segment_image(self, image_bytes: bytes) -> Dict:
        """
        Выполняет полную сегментацию изображения
        
        Args:
            image_bytes: Байты изображения
            
        Returns:
            Словарь с маркерами для разных типов дефектов:
            {
                'acne': [markers...],
                'pigmentation': [markers...],
                'wrinkles': [markers...],
                'papillomas': [markers...],
                'method': 'hf_segmentation' | 'simplified'
            }
        """
        if not HF_AVAILABLE:
            return {
                'acne': [],
                'pigmentation': [],
                'wrinkles': [],
                'papillomas': [],
                'method': 'unavailable'
            }
        
        try:
            # Загружаем изображение
            image = Image.open(io.BytesIO(image_bytes))
            image = image.convert('RGB')
            img_width, img_height = image.size
            
            results = {
                'acne': [],
                'pigmentation': [],
                'wrinkles': [],
                'papillomas': [],
                'method': 'hf_segmentation'
            }
            
            # 1. Face parsing для базовой сегментации
            face_masks = self._segment_face_parsing(image)
            
            # 2. Сегментация акне
            acne_mask = self._segment_acne(image)
            if acne_mask is not None:
                acne_contours = self._mask_to_contours(acne_mask)
                # Используем значение по умолчанию (будет переопределено в generate_heuristic_analysis)
                results['acne'] = self._contours_to_markers(acne_contours, (img_width, img_height), 'acne', 50)
            
            # 3. Сегментация пигментации
            pigmentation_mask = self._segment_pigmentation(image)
            if pigmentation_mask is not None:
                pigmentation_contours = self._mask_to_contours(pigmentation_mask)
                results['pigmentation'] = self._contours_to_markers(
                    pigmentation_contours, (img_width, img_height), 'pigmentation', 50
                )
            
            # 4. Обнаружение морщин
            wrinkles_mask = self._detect_wrinkles(image, face_masks)
            if wrinkles_mask is not None:
                wrinkles_contours = self._mask_to_contours(wrinkles_mask)
                results['wrinkles'] = self._contours_to_markers(
                    wrinkles_contours, (img_width, img_height), 'wrinkles', 50
                )
            
            # 5. Обнаружение папиллом
            papillomas_mask = self._detect_papillomas(image)
            if papillomas_mask is not None:
                papillomas_contours = self._mask_to_contours(papillomas_mask)
                results['papillomas'] = self._contours_to_markers(
                    papillomas_contours, (img_width, img_height), 'papillomas', 50
                )
            
            logger.info(f"HF сегментация завершена: акне={len(results['acne'])}, "
                       f"пигментация={len(results['pigmentation'])}, "
                       f"морщины={len(results['wrinkles'])}, "
                       f"папилломы={len(results['papillomas'])}")
            
            return results
            
        except Exception as e:
            logger.warning(f"Ошибка HF сегментации: {e}")
            return {
                'acne': [],
                'pigmentation': [],
                'wrinkles': [],
                'papillomas': [],
                'method': 'error'
            }


# Глобальный экземпляр сегментатора (lazy initialization)
_hf_segmenter = None


def get_hf_segmenter(hf_token: Optional[str] = None) -> HFSkinSegmenter:
    """Получает глобальный экземпляр HF сегментатора"""
    global _hf_segmenter
    if _hf_segmenter is None:
        _hf_segmenter = HFSkinSegmenter(hf_token)
    return _hf_segmenter

