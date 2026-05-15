#!/usr/bin/env python3
"""Add the 2 missing mushroom species to reach 50 total."""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

path = "knowledge_base/east_asia_subtropical/plants.json"
plants = json.load(open(path, encoding="utf-8"))
existing_ids = {sp["id"] for sp in plants}

new_species = [
    {
        "id": "macrolepiota_procera",
        "scientific_name": "Macrolepiota procera",
        "common_names": {"zh-TW": "高大環柄菇", "en": "Parasol Mushroom"},
        "category": "edible",
        "features": {
            "overall": {
                "growth_form": {"value": "fungus"},
                "height_estimate": {"value": "30-100cm"},
                "latex": {"value": "none"},
                "smell": {"value": "none"},
                "habitat": {"value": "open_field"},
                "water_droplet_test": {"value": "flat"}
            },
            "leaf": {
                "leaf_type": {"value": "simple"},
                "shape": {"value": "round"},
                "edge": {"value": "entire"},
                "tip": {"value": "rounded"},
                "base": {"value": "rounded"},
                "colors": {"value": ["brown"]},
                "color_pattern": {"value": "spotted"},
                "surface_top": {"value": "scaly"},
                "surface_bottom": {"value": "matte"},
                "arrangement": {"value": "clustered"},
                "size": {"value": "large_15-50cm"},
                "venation": {"value": "reticulate"},
                "texture": {"value": "fleshy"},
                "petiole_attach": {"value": "normal"}
            },
            "stem": {
                "type": {"value": "erect"},
                "cross_section": {"value": "round"},
                "surface": {"value": "scaly"},
                "colors": {"value": ["brown"]},
                "interior": {"value": "hollow"},
                "has_thorns": {"value": "no"}
            },
            "flower": None,
            "fruit": {
                "type": {"value": "spore"},
                "colors": {"value": ["brown"]},
                "size": {"value": "tiny_<5mm"},
                "surface": {"value": "smooth"}
            },
            "root": {
                "type": {"value": "fibrous"}
            }
        },
        "usage": {
            "type": ["edible_leaf"],
            "edible_parts": ["菌傘（煎烤最佳）"],
            "preparation": "去除菌柄後煎烤或油炸。味道鮮美。",
            "season": "夏秋雨後",
            "warnings": "極易與有毒綠褶菇混淆！必須確認孢子印為白色。"
        },
        "human_readable": {
            "description_zh": "大型傘菌，菌傘直徑15-30cm，表面有褐色鱗片。菌柄細長，有可滑動的環。",
            "diagnostic_features": [
                "菌傘大型（15-30cm），表面褐色鱗片呈同心圓排列",
                "菌柄細長，有可上下滑動的雙層環",
                "菌褶白色（成熟後也不變色，關鍵！）",
                "孢子印白色（關鍵區分：綠褶菇為灰綠色）",
                "常生長於草地、牧場"
            ]
        },
        "distribution": {
            "altitude_range": [0, 1500],
            "climate_zones": ["subtropical", "temperate"]
        }
    },
    {
        "id": "termitomyces_sp",
        "scientific_name": "Termitomyces sp.",
        "common_names": {"zh-TW": "雞肉絲菇", "en": "Termite Mushroom"},
        "category": "edible",
        "features": {
            "overall": {
                "growth_form": {"value": "fungus"},
                "height_estimate": {"value": "<30cm"},
                "latex": {"value": "none"},
                "smell": {"value": "aromatic"},
                "habitat": {"value": "forest_floor"},
                "water_droplet_test": {"value": "flat"}
            },
            "leaf": {
                "leaf_type": {"value": "simple"},
                "shape": {"value": "round"},
                "edge": {"value": "entire"},
                "tip": {"value": "acute"},
                "base": {"value": "rounded"},
                "colors": {"value": ["brown"]},
                "color_pattern": {"value": "solid"},
                "surface_top": {"value": "matte"},
                "surface_bottom": {"value": "matte"},
                "arrangement": {"value": "clustered"},
                "size": {"value": "medium_5-15cm"},
                "venation": {"value": "reticulate"},
                "texture": {"value": "fleshy"},
                "petiole_attach": {"value": "normal"}
            },
            "stem": {
                "type": {"value": "erect"},
                "cross_section": {"value": "round"},
                "surface": {"value": "smooth"},
                "colors": {"value": ["brown"]},
                "interior": {"value": "solid"},
                "has_thorns": {"value": "no"}
            },
            "flower": None,
            "fruit": {
                "type": {"value": "spore"},
                "colors": {"value": ["brown"]},
                "size": {"value": "tiny_<5mm"},
                "surface": {"value": "smooth"}
            },
            "root": {
                "type": {"value": "fibrous"}
            }
        },
        "usage": {
            "type": ["edible_leaf"],
            "edible_parts": ["全菇"],
            "preparation": "炒食或煮湯。味鮮似雞肉。",
            "season": "夏秋雨季",
            "warnings": "極易與白色毒鵝膏混淆！確認生長在白蟻巢上。菌柄基部無杯狀菌托。"
        },
        "human_readable": {
            "description_zh": "中型菇類，菌傘灰褐色至深褐色，中央常有小突起。味道鮮美似雞肉。",
            "diagnostic_features": [
                "生長在白蟻巢附近（關鍵特徵）",
                "菌傘灰褐色，中央有尖突起",
                "菌柄基部無杯狀菌托（毒鵝膏有！）",
                "菌褶白色至淡粉紅色",
                "味道鮮美似雞肉"
            ]
        },
        "distribution": {
            "altitude_range": [0, 1000],
            "climate_zones": ["subtropical", "tropical"]
        }
    }
]

added = 0
for sp in new_species:
    if sp["id"] not in existing_ids:
        plants.append(sp)
        added += 1
        print("Added: " + sp["id"])

json.dump(plants, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("Total: %d species (%d added)" % (len(plants), added))
