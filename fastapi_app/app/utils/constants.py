"""
Константы проекта
"""
# Список заболеваний для SAM3 режима (ключ = prompt, значение = отображаемое имя)
SAM3_DISEASES_DEFAULT = {
    "acne": "Акне",
    "pimples": "Прыщи",
    "pustules": "Пустулы",
    "papules": "Папулы",
    "blackheads": "Черные точки",
    "whiteheads": "Белые угри",
    "comedones": "Комедоны",
    "rosacea": "Розацеа",
    "irritation": "Раздражение",
    "pigmentation": "Пигментация",
    "freckles": "Веснушки",
    "papillomas": "Папилломы",
    "warts": "Бородавки",
    "moles": "Родинки",
    "skin tags": "Кожные выросты",
    "wrinkles": "Морщины",
    "fine lines": "Мелкие морщины",
    "skin lesion": "Повреждения",
    "scars": "Шрамы",
    "post acne marks": "Следы постакне",
    "acne scars": "Шрамы от акне",
}

# База знаний о кожных заболеваниях (RAG-like knowledge base)
SKIN_DISEASE_KNOWLEDGE_BASE = {
    "skin tags": {
        "description": "Skin tags (acrochordons) are small, soft, flesh-colored or slightly darker growths that hang from the skin. They are pedunculated (attached by a stalk), benign, and commonly found on neck, chest, armpits, groin, and under breasts.",
        "characteristics": [
            "Small to medium size (1-5mm typically, can be larger)",
            "Flesh-colored, light brown, or slightly darker than skin",
            "Pedunculated (hanging from a stalk)",
            "Soft texture",
            "Can appear singly or in clusters",
            "Common on neck, chest, body folds",
            "Benign, non-cancerous growths"
        ],
        "few_shot_examples": [
            "Example 1: Multiple small flesh-colored tags clustered on the neck, ranging from 1-3mm, hanging from thin stalks",
            "Example 2: Medium-sized tags (3-5mm) on chest area, slightly darker than surrounding skin, pedunculated",
            "Example 3: Small tags in body folds, soft texture, flesh-colored with some having darker pigmentation"
        ]
    },
    "papillomas": {
        "description": "Papillomas are benign skin growths that can appear as raised bumps or warty growths. They may be caused by HPV or other factors.",
        "characteristics": [
            "Raised bumps on skin",
            "Can be warty in appearance",
            "Benign tumors",
            "Various sizes",
            "May have rough texture"
        ]
    },
    "moles": {
        "description": "Moles (nevi) are pigmented skin lesions that can be flat or raised, dark brown to black in color.",
        "characteristics": [
            "Dark brown or black spots",
            "Can be raised or flat",
            "Pigmented lesions",
            "Various sizes and shapes",
            "Usually benign but should be monitored"
        ]
    },
    "freckles": {
        "description": "Freckles are small, light brown spots that appear on sun-exposed skin, especially in fair-skinned individuals.",
        "characteristics": [
            "Small brown spots",
            "Light brown color",
            "Appear on sun-exposed areas",
            "Flat, not raised",
            "Can be numerous"
        ]
    },
    "pigmentation": {
        "description": "Pigmentation refers to dark spots, hyperpigmentation, age spots, melasma, or uneven skin tone.",
        "characteristics": [
            "Dark spots on skin",
            "Brown or darker than surrounding skin",
            "Can be flat or slightly raised",
            "Various sizes",
            "May appear in patches or scattered"
        ]
    },
    "acne": {
        "description": "Acne includes inflamed red bumps, pimples, pustules, and other acne lesions.",
        "characteristics": [
            "Inflamed red bumps",
            "Raised spots",
            "May have white or yellow centers (pustules)",
            "Can be clustered or scattered",
            "Common on face, chest, back"
        ]
    }
}

# Улучшенные промпты для SAM3 с детальными описаниями (few-shot через описания)
SAM3_ENHANCED_PROMPTS = {
    "acne": "acne, pimples, inflamed red bumps on skin, raised red spots, pustules with white or yellow centers",
    "pimples": "pimples, small raised red bumps on skin, inflamed spots, zits, blemishes",
    "pustules": "pustules, pus-filled bumps, white or yellow-headed pimples, infected acne lesions",
    "papules": "papules, small raised solid bumps on skin, red or pink bumps without pus",
    "blackheads": "blackheads, open comedones, dark spots in pores, clogged pores with dark centers",
    "whiteheads": "whiteheads, closed comedones, small white bumps under skin, milia",
    "comedones": "comedones, clogged pores, blackheads and whiteheads, blocked hair follicles",
    "rosacea": "rosacea, facial redness, red patches on face, visible blood vessels, flushed skin",
    "irritation": "skin irritation, red inflamed areas, rash, sensitive skin patches, redness",
    "pigmentation": "pigmentation, dark spots, hyperpigmentation, brown spots, age spots, melasma, uneven skin tone",
    "freckles": "freckles, small brown spots, ephelides, sun spots, light brown dots on skin",
    "papillomas": "papillomas, small skin growths, raised bumps, benign tumors, warty growths",
    "warts": "warts, rough skin growths, raised bumps with rough texture, viral warts, verruca",
    "moles": "moles, nevi, dark brown or black spots, raised or flat pigmented lesions",
    "skin tags": "skin tags, acrochordons, small fleshy growths hanging from skin, pedunculated skin growths, soft tissue tags, small raised bumps attached by a stalk, flesh-colored or slightly darker growths, multiple small tags clustered together, tags on neck, chest, or body folds, all skin tags including very small ones, tiny tags, medium tags, large tags, tags of any size, every single skin tag visible on the image",
    "wrinkles": "wrinkles, fine lines, creases in skin, age lines, expression lines, deep folds",
    "fine lines": "fine lines, small wrinkles, subtle creases, early signs of aging, delicate lines",
    "skin lesion": "skin lesions, abnormal skin areas, damaged skin, skin abnormalities, skin changes",
    "scars": "scars, healed wound marks, raised or depressed scar tissue, post-surgical scars, injury marks",
    "post acne marks": "post-acne marks, dark spots after acne, hyperpigmentation from acne, acne scars, PIH (post-inflammatory hyperpigmentation)",
    "acne scars": "acne scars, pitted scars, atrophic scars, depressed scars from acne, ice pick scars, boxcar scars",
}

# Настройки моделей по умолчанию
DEFAULT_VISION_MODEL = "google/gemini-2.5-flash"  # Для детекции (поддерживает bounding boxes)
DEFAULT_TEXT_MODEL = "anthropic/claude-3.5-sonnet"  # Для генерации отчёта

# Порядок попыток подключения к API для детекции
DETECTION_FALLBACKS = [
    {"provider": "openrouter", "model": "google/gemini-2.5-flash"},  # Gemini 2.5 Flash - поддержка bounding boxes
    {"provider": "openrouter", "model": "openai/gpt-4o"},  # GPT-4o Vision - поддержка координат
    {"provider": "openrouter", "model": "anthropic/claude-3.5-sonnet"},  # Claude 3.5 Sonnet - баланс качества и стоимости
    {"provider": "openrouter", "model": "google/gemini-1.5-pro"},  # Gemini 1.5 Pro - сильные возможности обработки изображений
    # Бесплатные и бюджетные варианты
    {"provider": "openrouter", "model": "google/gemini-2.0-flash-exp"},  # Gemini 2.0 Flash Experimental (бесплатная)
    {"provider": "openrouter", "model": "qwen/qwen-2-vl-72b-instruct"},  # Qwen2-VL - высокая производительность
    {"provider": "openrouter", "model": "mistralai/pixtral-large"},  # Pixtral Large - 124B параметров
    {"provider": "openrouter", "model": "x-ai/grok-4.1-fast:free"},  # Grok 4.1 Fast (бесплатная)
    {"provider": "openrouter", "model": "google/gemini-2.0-flash-001"}  # Google Gemini 2.0 Flash
]

DEFAULT_CONFIG = {
    "detection_provider": "openrouter",
    "llm_provider": "openrouter",
    "vision_model": DEFAULT_VISION_MODEL,
    "text_model": DEFAULT_TEXT_MODEL,
    "temperature": 0,  # Точность важнее креативности
    "max_tokens": 300  # Краткие и лаконичные ответы
}










