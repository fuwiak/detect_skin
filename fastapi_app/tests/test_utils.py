"""
Unit тесты для утилит
"""
import pytest
from app.utils.parsing import parse_skin_analysis_from_text, parse_report_locations, convert_bbox_to_position
from app.utils.image_utils import segment_face_area


class TestParsing:
    """Тесты для функций парсинга"""
    
    def test_parse_skin_analysis_from_text(self):
        """Тест парсинга анализа из текста"""
        text = """
        acne_score: 25.5
        pigmentation_score: 30.2
        pores_size: 45.8
        wrinkles_grade: 15.3
        skin_tone: 60.0
        texture_score: 55.5
        moisture_level: 70.2
        oiliness: 40.1
        """
        result = parse_skin_analysis_from_text(text)
        
        assert result['acne_score'] == 25.5
        assert result['pigmentation_score'] == 30.2
        assert result['pores_size'] == 45.8
        assert result['wrinkles_grade'] == 15.3
        assert result['skin_tone'] == 60.0
        assert result['texture_score'] == 55.5
        assert result['moisture_level'] == 70.2
        assert result['oiliness'] == 40.1
    
    def test_parse_skin_analysis_empty(self):
        """Тест парсинга пустого текста"""
        result = parse_skin_analysis_from_text("")
        assert all(v == 0.0 for v in result.values())
    
    def test_parse_report_locations(self):
        """Тест парсинга локализации из отчёта"""
        report = """
        Локализация проблем:
        Пигментация обнаружена на щеках.
        Морщины находятся в периорбитальной области и вокруг рта.
        """
        locations = parse_report_locations(report)
        
        assert 'pigmentation' in locations
        assert 'wrinkles' in locations
    
    def test_convert_bbox_to_position(self):
        """Тест конвертации bounding box в позицию"""
        bbox = [100, 200, 300, 400]  # [y_min, x_min, y_max, x_max]
        position = convert_bbox_to_position(bbox)
        
        assert position['x'] == 30.0  # (200 + 400) / 2 / 10
        assert position['y'] == 20.0  # (100 + 300) / 2 / 10
        assert position['width'] == 20.0  # (400 - 200) / 10
        assert position['height'] == 20.0  # (300 - 100) / 10


class TestImageUtils:
    """Тесты для утилит работы с изображениями"""
    
    def test_segment_face_area_acne(self):
        """Тест сегментации зоны для акне"""
        position = segment_face_area('acne', 75.0)
        
        assert 'x' in position
        assert 'y' in position
        assert 'width' in position
        assert 'height' in position
        assert 'zone' in position
    
    def test_segment_face_area_pigmentation(self):
        """Тест сегментации зоны для пигментации"""
        position = segment_face_area('pigmentation', 50.0)
        
        assert position['zone'] in ['left_cheek', 'right_cheek', 'forehead', 't_zone']
    
    def test_segment_face_area_wrinkles(self):
        """Тест сегментации зоны для морщин"""
        position = segment_face_area('wrinkles', 60.0)
        
        assert position['zone'] in ['forehead', 'u_zone', 't_zone']




