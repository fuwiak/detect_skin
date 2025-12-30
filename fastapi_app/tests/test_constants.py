"""
Unit тесты для констант
"""
import pytest
from app.utils.constants import (
    SAM3_DISEASES_DEFAULT,
    SKIN_DISEASE_KNOWLEDGE_BASE,
    SAM3_ENHANCED_PROMPTS,
    DETECTION_FALLBACKS,
    DEFAULT_CONFIG,
    DEFAULT_VISION_MODEL,
    DEFAULT_TEXT_MODEL
)


class TestConstants:
    """Тесты для констант"""
    
    def test_sam3_diseases_default(self):
        """Тест наличия заболеваний для SAM3"""
        assert len(SAM3_DISEASES_DEFAULT) > 0
        assert 'acne' in SAM3_DISEASES_DEFAULT
        assert 'pigmentation' in SAM3_DISEASES_DEFAULT
        assert SAM3_DISEASES_DEFAULT['acne'] == 'Акне'
    
    def test_skin_disease_knowledge_base(self):
        """Тест базы знаний о заболеваниях"""
        assert 'skin tags' in SKIN_DISEASE_KNOWLEDGE_BASE
        assert 'papillomas' in SKIN_DISEASE_KNOWLEDGE_BASE
        assert 'description' in SKIN_DISEASE_KNOWLEDGE_BASE['skin tags']
        assert 'characteristics' in SKIN_DISEASE_KNOWLEDGE_BASE['skin tags']
    
    def test_sam3_enhanced_prompts(self):
        """Тест улучшенных промптов для SAM3"""
        assert 'acne' in SAM3_ENHANCED_PROMPTS
        assert 'skin tags' in SAM3_ENHANCED_PROMPTS
        assert len(SAM3_ENHANCED_PROMPTS['skin tags']) > 0
    
    def test_detection_fallbacks(self):
        """Тест списка fallback моделей"""
        assert len(DETECTION_FALLBACKS) > 0
        assert all('provider' in fb for fb in DETECTION_FALLBACKS)
        assert all('model' in fb for fb in DETECTION_FALLBACKS)
    
    def test_default_config(self):
        """Тест конфигурации по умолчанию"""
        assert 'detection_provider' in DEFAULT_CONFIG
        assert 'llm_provider' in DEFAULT_CONFIG
        assert 'vision_model' in DEFAULT_CONFIG
        assert DEFAULT_CONFIG['vision_model'] == DEFAULT_VISION_MODEL
        assert DEFAULT_CONFIG['text_model'] == DEFAULT_TEXT_MODEL










