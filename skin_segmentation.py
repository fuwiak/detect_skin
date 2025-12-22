#!/usr/bin/env python3
"""
Легкая модель сегментации для морщин, веснушек и пигментации
Использует MobileNetV2 + UNet decoder для быстрой сегментации
"""
import numpy as np
from PIL import Image
import io
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Попытка импорта библиотек для глубокого обучения
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torchvision import transforms, models
    TORCH_AVAILABLE = True
    logger.info("PyTorch доступен для сегментации")
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch не установлен, будет использована упрощенная сегментация")


class MobileUNet(nn.Module):
    """
    Легкая модель сегментации на основе MobileNetV2 + UNet decoder
    Классы: фон, морщины, веснушки/пигментация
    """
    def __init__(self, num_classes=3):
        super(MobileUNet, self).__init__()
        
        # Encoder: MobileNetV2 (легкий backbone)
        mobilenet = models.mobilenet_v2(pretrained=True)
        self.encoder = mobilenet.features
        
        # Decoder: простой UNet decoder
        self.decoder = nn.Sequential(
            # Upsampling блоки
            nn.ConvTranspose2d(1280, 512, 2, stride=2),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            
            nn.ConvTranspose2d(512, 256, 2, stride=2),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            
            nn.ConvTranspose2d(256, 128, 2, stride=2),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            
            nn.ConvTranspose2d(128, 64, 2, stride=2),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            
            # Финальный слой
            nn.Conv2d(64, num_classes, 1)
        )
    
    def forward(self, x):
        # Encoder
        features = self.encoder(x)
        
        # Decoder
        output = self.decoder(features)
        
        # Upsample до исходного размера
        output = F.interpolate(output, size=x.shape[2:], mode='bilinear', align_corners=False)
        
        return output


class LightweightSkinSegmenter:
    """
    Легкий сегментатор кожи для морщин, веснушек и пигментации
    """
    
    def __init__(self):
        self.model = None
        self.device = None
        self.transform = None
        
        if TORCH_AVAILABLE:
            try:
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                logger.info(f"Используется устройство: {self.device}")
                
                # Создаем модель
                self.model = MobileUNet(num_classes=3).to(self.device)
                self.model.eval()
                
                # Трансформации для изображения
                self.transform = transforms.Compose([
                    transforms.Resize((256, 256)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                      std=[0.229, 0.224, 0.225])
                ])
                
                logger.info("Модель сегментации инициализирована")
            except Exception as e:
                logger.warning(f"Не удалось инициализировать модель: {e}")
                self.model = None
    
    def segment_image(self, image_bytes: bytes) -> Optional[Dict]:
        """
        Сегментирует изображение на морщины, веснушки/пигментацию и фон
        
        Args:
            image_bytes: Байты изображения
            
        Returns:
            Dict с масками и координатами:
            {
                'wrinkles': [{'bbox': [x, y, w, h], 'confidence': float}, ...],
                'pigmentation': [{'bbox': [x, y, w, h], 'confidence': float}, ...],
                'mask': numpy array с маской
            }
        """
        if not self.model or not TORCH_AVAILABLE:
            # Fallback на простую эвристическую сегментацию
            return self._heuristic_segmentation(image_bytes)
        
        try:
            # Загружаем изображение
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            original_size = image.size
            
            # Подготавливаем изображение для модели
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # Предсказание
            with torch.no_grad():
                output = self.model(input_tensor)
                probs = F.softmax(output, dim=1)
                predictions = torch.argmax(probs, dim=1).cpu().numpy()[0]
            
            # Масштабируем маску до исходного размера
            mask = Image.fromarray(predictions.astype(np.uint8))
            mask = mask.resize(original_size, Image.NEAREST)
            mask_array = np.array(mask)
            
            # Извлекаем области
            wrinkles = self._extract_regions(mask_array, class_id=1, min_area=50)
            pigmentation = self._extract_regions(mask_array, class_id=2, min_area=20)
            
            return {
                'wrinkles': wrinkles,
                'pigmentation': pigmentation,
                'mask': mask_array,
                'original_size': original_size
            }
            
        except Exception as e:
            logger.error(f"Ошибка сегментации: {e}")
            return self._heuristic_segmentation(image_bytes)
    
    def _extract_regions(self, mask: np.ndarray, class_id: int, min_area: int = 20) -> List[Dict]:
        """
        Извлекает области из маски
        
        Args:
            mask: Маска сегментации
            class_id: ID класса (1 - морщины, 2 - пигментация)
            min_area: Минимальная площадь области
            
        Returns:
            Список областей с bounding boxes
        """
        regions = []
        
        # Находим области заданного класса
        binary_mask = (mask == class_id).astype(np.uint8)
        
        # Используем простой алгоритм поиска связанных компонентов
        from scipy import ndimage
        try:
            labeled, num_features = ndimage.label(binary_mask)
            
            for i in range(1, num_features + 1):
                # Находим координаты области
                coords = np.where(labeled == i)
                if len(coords[0]) < min_area:
                    continue
                
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()
                
                # Нормализуем координаты к 0-1000 (как в bounding boxes)
                height, width = mask.shape
                bbox = [
                    int((y_min / height) * 1000),  # y_min
                    int((x_min / width) * 1000),    # x_min
                    int((y_max / height) * 1000),   # y_max
                    int((x_max / width) * 1000)    # x_max
                ]
                
                # Вычисляем уверенность (площадь области)
                area = len(coords[0])
                confidence = min(1.0, area / (width * height * 0.01))
                
                regions.append({
                    'bbox': bbox,
                    'confidence': confidence,
                    'area': area
                })
        except ImportError:
            # Если scipy не установлен, используем простой метод
            logger.warning("scipy не установлен, используется упрощенная сегментация")
            # Простой поиск прямоугольных областей
            rows = np.any(binary_mask, axis=1)
            cols = np.any(binary_mask, axis=0)
            if rows.any() and cols.any():
                y_min, y_max = np.where(rows)[0][[0, -1]]
                x_min, x_max = np.where(cols)[0][[0, -1]]
                
                height, width = mask.shape
                bbox = [
                    int((y_min / height) * 1000),
                    int((x_min / width) * 1000),
                    int((y_max / height) * 1000),
                    int((x_max / width) * 1000)
                ]
                
                regions.append({
                    'bbox': bbox,
                    'confidence': 0.5,
                    'area': (y_max - y_min) * (x_max - x_min)
                })
        
        return regions
    
    def _heuristic_segmentation(self, image_bytes: bytes) -> Dict:
        """
        Простая эвристическая сегментация на основе анализа цвета и текстуры
        Используется как fallback, если модель недоступна
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            img_array = np.array(image)
            height, width = img_array.shape[:2]
            
            # Простая сегментация на основе анализа яркости и контраста
            gray = np.mean(img_array, axis=2)
            
            # Находим темные области (пигментация)
            dark_threshold = np.percentile(gray, 20)
            dark_mask = gray < dark_threshold
            
            # Находим области с высокой вариацией (морщины)
            from scipy import ndimage
            try:
                # Вычисляем градиент для поиска морщин
                sobel_x = ndimage.sobel(gray, axis=1)
                sobel_y = ndimage.sobel(gray, axis=0)
                gradient = np.sqrt(sobel_x**2 + sobel_y**2)
                
                wrinkle_threshold = np.percentile(gradient, 80)
                wrinkle_mask = gradient > wrinkle_threshold
            except ImportError:
                # Если scipy недоступен, используем простой метод
                wrinkle_mask = np.zeros_like(gray, dtype=bool)
            
            # Извлекаем области
            pigmentation = self._extract_regions_simple(dark_mask, width, height, min_area=20)
            wrinkles = self._extract_regions_simple(wrinkle_mask, width, height, min_area=50)
            
            return {
                'wrinkles': wrinkles,
                'pigmentation': pigmentation,
                'mask': None,
                'original_size': (width, height)
            }
        except Exception as e:
            logger.error(f"Ошибка эвристической сегментации: {e}")
            return {
                'wrinkles': [],
                'pigmentation': [],
                'mask': None,
                'original_size': None
            }
    
    def _extract_regions_simple(self, mask: np.ndarray, width: int, height: int, min_area: int = 20) -> List[Dict]:
        """Простое извлечение областей без scipy"""
        regions = []
        
        # Находим границы
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        
        if rows.any() and cols.any():
            y_min, y_max = np.where(rows)[0][[0, -1]]
            x_min, x_max = np.where(cols)[0][[0, -1]]
            
            area = (y_max - y_min) * (x_max - x_min)
            if area >= min_area:
                bbox = [
                    int((y_min / height) * 1000),
                    int((x_min / width) * 1000),
                    int((y_max / height) * 1000),
                    int((x_max / width) * 1000)
                ]
                
                regions.append({
                    'bbox': bbox,
                    'confidence': min(1.0, area / (width * height * 0.01)),
                    'area': area
                })
        
        return regions


# Глобальный экземпляр сегментатора
_segmenter = None

def get_segmenter() -> LightweightSkinSegmenter:
    """Получить глобальный экземпляр сегментатора (lazy initialization)"""
    global _segmenter
    if _segmenter is None:
        _segmenter = LightweightSkinSegmenter()
    return _segmenter













