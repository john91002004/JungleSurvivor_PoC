#!/usr/bin/env python3
"""
Convert v1 free-text KB to v2 structured format.

Uses keyword matching to map free-text morphology descriptions to enum values.
Produces a best-effort conversion that requires human review for accuracy.
"""

import json
import sys
import io
import re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KB_V1 = Path(__file__).parent.parent / "knowledge_base" / "regions" / "east_asia_subtropical"
KB_V2 = Path(__file__).parent.parent / "knowledge_base" / "east_asia_subtropical"
EXISTING_V2 = KB_V2 / "plants.json"

# ── Keyword mappings for each feature ──

GROWTH_FORM_MAP = {
    "蕨": "fern", "蕨類": "fern", "fern": "fern",
    "草本": "herb", "herb": "herb", "多年生草本": "herb", "一年生草本": "herb",
    "灌木": "shrub", "shrub": "shrub",
    "喬木": "tree", "tree": "tree", "大喬木": "tree",
    "藤": "vine", "攀緣": "vine", "vine": "vine", "藤本": "vine",
    "菇": "fungus", "菌": "fungus", "fungus": "fungus", "木耳": "fungus",
    "禾": "grass", "grass": "grass", "芒": "grass", "竹": "grass",
    "肉質": "succulent", "succulent": "succulent",
    "水生": "aquatic", "aquatic": "aquatic",
    "棕櫚": "palm_like", "蘇鐵": "palm_like",
}

HEIGHT_MAP = {
    "15-40cm": "<30cm", "10-30cm": "<30cm", "10-20cm": "<30cm",
    "30-100cm": "30-100cm", "50-100cm": "30-100cm", "40-80cm": "30-100cm",
    "100-200cm": "1-2m", "1-2m": "1-2m", "150-300cm": "1-2m",
    "2-5m": "2-5m", "3-5m": "2-5m", "200-500cm": "2-5m",
    "5-15m": ">5m", "8-15m": ">5m", "10-20m": ">5m", ">5m": ">5m",
}

LEAF_SHAPE_MAP = {
    "心形": "heart", "心": "heart",
    "箭形": "arrow", "箭": "arrow",
    "卵形": "oval", "卵": "oval", "卵狀": "oval",
    "橢圓": "elliptic",
    "披針": "lanceolate", "長橢圓": "lanceolate", "倒披針": "lanceolate",
    "線形": "linear", "線狀": "linear",
    "針形": "needle", "針狀": "needle",
    "鱗片": "scale",
    "圓形": "round", "圓": "round",
    "匙形": "spatulate",
    "倒卵": "obovate",
    "菱形": "rhombic",
    "扇形": "fan",
    "腎形": "kidney",
    "掌狀": "fan",
}

LEAF_EDGE_MAP = {
    "全緣": "entire", "entire": "entire",
    "鋸齒": "serrated", "齒緣": "serrated", "serrated": "serrated",
    "重鋸齒": "double_serrated",
    "鈍齒": "crenate", "圓齒": "crenate",
    "裂": "lobed", "淺裂": "lobed",
    "深裂": "deeply_lobed",
    "波狀": "wavy", "微波": "wavy",
    "刺": "spiny",
}

LEAF_SURFACE_MAP = {
    "光滑": "glossy", "有光澤": "glossy", "蠟": "waxy", "waxy": "waxy",
    "無光澤": "matte", "matte": "matte",
    "毛": "hairy", "被毛": "hairy", "絨毛": "velvety", "天鵝絨": "velvety",
    "粗糙": "rough", "rough": "rough",
    "蠟質": "waxy",
    "鱗片": "scaly",
}

LEAF_ARRANGEMENT_MAP = {
    "互生": "alternate", "alternate": "alternate",
    "對生": "opposite", "opposite": "opposite",
    "輪生": "whorled", "whorled": "whorled",
    "蓮座": "basal_rosette", "蓮座狀": "basal_rosette", "基生": "basal_rosette",
    "叢生": "clustered", "clustered": "clustered",
    "鳥巢": "bird_nest_radial", "輻射": "bird_nest_radial",
    "螺旋": "spiral",
    "二列": "two_ranked",
}

FLOWER_COLOR_MAP = {
    "白": "white", "white": "white",
    "黃": "yellow", "yellow": "yellow",
    "橙": "orange", "orange": "orange",
    "紅": "red", "red": "red",
    "粉紅": "pink", "pink": "pink", "粉": "pink",
    "紫": "purple", "purple": "purple",
    "藍": "blue", "blue": "blue",
    "綠": "green", "green": "green",
    "褐": "brown", "brown": "brown",
}

FLOWER_ARRANGEMENT_MAP = {
    "單生": "solitary", "solitary": "solitary",
    "總狀": "raceme", "raceme": "raceme",
    "穗狀": "spike", "spike": "spike",
    "繖形": "umbel", "umbel": "umbel",
    "頭狀": "head_composite", "頭花": "head_composite", "菊": "head_composite",
    "圓錐": "panicle", "panicle": "panicle",
    "聚繖": "cyme", "cyme": "cyme",
    "柔荑": "catkin",
    "佛焰苞": "spathe_spadix", "肉穗": "spathe_spadix",
}

FRUIT_TYPE_MAP = {
    "漿果": "berry", "berry": "berry",
    "核果": "drupe", "drupe": "drupe",
    "蒴果": "capsule", "capsule": "capsule",
    "莢果": "pod_legume", "莢": "pod_legume",
    "瘦果": "achene", "achene": "achene",
    "翅果": "samara",
    "堅果": "nut", "nut": "nut",
    "聚合果": "aggregate",
    "孢子": "spore", "spore": "spore",
}

HABITAT_MAP = {
    "路邊": "roadside", "荒地": "roadside", "步道": "roadside",
    "林下": "forest_floor", "林緣": "forest_floor", "森林": "forest_floor",
    "溪邊": "streamside", "溪溝": "streamside", "水邊": "streamside",
    "岩壁": "cliff_rock", "懸崖": "cliff_rock",
    "空地": "open_field", "草地": "open_field", "原野": "open_field",
    "濕地": "wetland", "水田": "wetland", "沼澤": "wetland",
    "附生": "epiphytic", "樹幹": "epiphytic",
    "公園": "urban", "行道樹": "urban", "都市": "urban",
    "海岸": "coastal", "海邊": "coastal", "河口": "coastal",
}


def guess_height(morph_text):
    if not morph_text:
        return "30-100cm"
    nums = re.findall(r'(\d+)\s*(?:cm|m)', morph_text.lower())
    for pattern, val in HEIGHT_MAP.items():
        if pattern in morph_text:
            return val
    for text in ["高可達", "高", "株高"]:
        match = re.search(rf'{text}\s*(?:約\s*)?(\d+)[-~]?(\d*)\s*(cm|m)', morph_text)
        if match:
            h = int(match.group(1))
            unit = match.group(3)
            if unit == "m":
                h *= 100
            if h < 30:
                return "<30cm"
            elif h < 100:
                return "30-100cm"
            elif h < 200:
                return "1-2m"
            elif h < 500:
                return "2-5m"
            else:
                return ">5m"
    return "30-100cm"


def match_first(text, mapping, default=None):
    if not text:
        return default
    for keyword, value in mapping.items():
        if keyword in text:
            return value
    return default


def match_all(text, mapping):
    if not text:
        return []
    found = []
    for keyword, value in mapping.items():
        if keyword in text and value not in found:
            found.append(value)
    return found


def guess_leaf_colors(morph):
    colors = []
    text = morph.get("leaf_surface", "") + morph.get("leaf_shape", "") + str(morph.get("leaves", ""))
    if "深綠" in text or "dark_green" in text:
        colors.append("dark_green")
    elif "淺綠" in text or "黃綠" in text:
        colors.append("yellow_green")
    elif "綠" in text:
        colors.append("green")
    if "紅" in text or "紫" in text:
        if "背" in text or "underside" in text:
            colors.append("red_underside")
        else:
            colors.append("purple")
    if "銀" in text:
        colors.append("silver")
    if "斑" in text:
        colors.append("variegated")
    if not colors:
        colors = ["green"]
    return colors


def convert_species(sp, is_toxic=False):
    """Convert a v1 species entry to v2 format."""
    morph = sp.get("morphology", {})
    morph_text = " ".join(str(v) for v in morph.values())
    habitat_text = sp.get("habitat", "")
    all_text = morph_text + " " + habitat_text

    # Determine category
    if is_toxic:
        category = "dangerous"
    elif sp.get("category") in ("edible_and_medicinal",):
        category = "medicinal"
    elif sp.get("category") == "edible":
        category = "edible"
    elif sp.get("medicinal_uses"):
        category = "medicinal"
    else:
        category = "edible"

    result = {
        "id": sp["id"],
        "scientific_name": sp["scientific_name"],
        "common_names": sp["common_names"],
        "category": category,
    }

    if is_toxic:
        result["danger_level"] = sp.get("danger_level", "high")

    # Build features
    growth_form = match_first(all_text, GROWTH_FORM_MAP, "herb")
    height = guess_height(morph_text)
    habitat = match_first(habitat_text, HABITAT_MAP, "forest_floor")

    latex_val = "none"
    if "乳汁" in all_text or "乳液" in all_text:
        if "白" in all_text:
            latex_val = "yes_white"
        elif "黃" in all_text:
            latex_val = "yes_yellow"
        else:
            latex_val = "yes_white"

    smell_val = match_first(all_text, {
        "腥": "fishy", "臭": "pungent", "香": "aromatic",
        "芳香": "aromatic", "辛辣": "spicy", "薄荷": "minty",
        "甜": "sweet", "惡臭": "rotten",
    }, "none")

    water_test = "flat"
    if "荷葉效應" in all_text or "成珠" in all_text or "圓珠" in all_text:
        water_test = "beading"

    leaf_shape = match_first(morph.get("leaf_shape", "") + morph.get("leaves", ""), LEAF_SHAPE_MAP, "oval")
    leaf_edge = match_first(morph.get("leaf_margin", "") + morph.get("leaf_shape", ""), LEAF_EDGE_MAP, "entire")
    leaf_surface = match_first(morph.get("leaf_surface", "") + str(morph.get("leaves", "")), LEAF_SURFACE_MAP, "matte")
    leaf_arrangement = match_first(
        morph.get("leaf_arrangement", "") + morph.get("growth_pattern", "") + str(morph.get("leaves", "")),
        LEAF_ARRANGEMENT_MAP, "alternate"
    )
    leaf_colors = guess_leaf_colors(morph)

    leaf_size = "medium_5-15cm"
    leaf_text = morph.get("leaf_shape", "") + morph.get("leaves", "")
    size_match = re.search(r'(\d+)[-~](\d+)\s*cm', leaf_text)
    if size_match:
        avg = (int(size_match.group(1)) + int(size_match.group(2))) / 2
        if avg < 2:
            leaf_size = "tiny_<2cm"
        elif avg < 5:
            leaf_size = "small_2-5cm"
        elif avg < 15:
            leaf_size = "medium_5-15cm"
        elif avg < 50:
            leaf_size = "large_15-50cm"
        else:
            leaf_size = "very_large_>50cm"

    leaf_venation = "pinnate"
    if "平行" in all_text:
        leaf_venation = "parallel"
    elif "掌狀脈" in all_text:
        leaf_venation = "palmate"
    elif "網狀" in all_text:
        leaf_venation = "reticulate"
    elif "中肋" in all_text or "中脈" in all_text:
        leaf_venation = "single_midrib"

    leaf_type = "simple"
    if "羽狀複葉" in all_text or "二回羽狀" in all_text:
        leaf_type = "pinnate_compound"
    if "二回" in all_text:
        leaf_type = "bipinnate_compound"
    if "三出" in all_text or "三小葉" in all_text:
        leaf_type = "trifoliate"
    if "掌狀複葉" in all_text:
        leaf_type = "palmate_compound"

    flower_text = morph.get("flower", "") + morph.get("inflorescence", "")
    flower_colors = match_all(flower_text, FLOWER_COLOR_MAP)
    if not flower_colors:
        flower_colors = ["white"]
    flower_arrangement = match_first(flower_text, FLOWER_ARRANGEMENT_MAP, "solitary")
    flower_special = "none"
    if "佛焰苞" in flower_text:
        flower_special = "spathe"
    elif "蝴蝶" in flower_text:
        flower_special = "butterfly_shape"
    elif "唇" in flower_text:
        flower_special = "lip_labellum"
    elif "鐘" in flower_text or "管" in flower_text:
        flower_special = "bell_tubular"
    elif "喇叭" in flower_text or "漏斗" in flower_text:
        flower_special = "trumpet"

    petal_count = "5"
    if "四瓣" in flower_text or "4 枚" in flower_text or "十字" in flower_text:
        petal_count = "4"
    elif "無花瓣" in flower_text or "佛焰苞" in flower_text or "菌" in all_text:
        petal_count = "0"
    elif "六" in flower_text or "6" in flower_text:
        petal_count = "6"
    elif "三" in flower_text:
        petal_count = "3"
    elif "多" in flower_text or "重瓣" in flower_text:
        petal_count = "many"

    fruit_text = morph.get("fruit", "")
    fruit_type = match_first(fruit_text, FRUIT_TYPE_MAP, "capsule")
    fruit_colors = match_all(fruit_text, FLOWER_COLOR_MAP)
    if not fruit_colors:
        fruit_colors = ["green"]

    stem_text = morph.get("stem", "") + morph.get("plant_habit", "")
    stem_type = "erect"
    if "匍匐" in stem_text or "攀" in stem_text:
        stem_type = "creeping"
    if "纏繞" in stem_text:
        stem_type = "twining"
    if "直立" in stem_text:
        stem_type = "erect"

    stem_surface = "smooth"
    if "刺" in stem_text:
        stem_surface = "thorny"
    elif "毛" in stem_text:
        stem_surface = "hairy"
    elif "粗糙" in stem_text:
        stem_surface = "bark_rough"

    stem_colors = ["green"]
    if "褐" in stem_text or "棕" in stem_text:
        stem_colors = ["brown"]
    elif "紫" in stem_text or "紅" in stem_text:
        stem_colors = ["purple"]
    elif "灰" in stem_text:
        stem_colors = ["gray"]

    root_type = "fibrous"
    if "塊莖" in all_text or "tuber" in all_text:
        root_type = "storage_tuber"
    elif "根莖" in all_text or "rhizome" in all_text:
        root_type = "rhizome"
    elif "球莖" in all_text:
        root_type = "corm"
    elif "鱗莖" in all_text:
        root_type = "bulb"
    elif "氣根" in all_text:
        root_type = "aerial_root"

    has_flower = flower_text and "無花" not in flower_text and growth_form != "fungus" and growth_form != "fern"

    features = {
        "overall": {
            "growth_form": {"value": growth_form},
            "height_estimate": {"value": height},
            "latex": {"value": latex_val},
            "smell": {"value": smell_val},
            "habitat": {"value": habitat},
            "water_droplet_test": {"value": water_test},
        },
        "leaf": {
            "leaf_type": {"value": leaf_type},
            "shape": {"value": leaf_shape},
            "edge": {"value": leaf_edge},
            "tip": {"value": "acuminate"},
            "base": {"value": "cuneate"},
            "colors": {"value": leaf_colors},
            "color_pattern": {"value": "solid" if len(leaf_colors) <= 1 else "bicolor"},
            "surface_top": {"value": leaf_surface},
            "surface_bottom": {"value": "matte"},
            "arrangement": {"value": leaf_arrangement},
            "size": {"value": leaf_size},
            "venation": {"value": leaf_venation},
            "texture": {"value": "leathery" if "革質" in all_text else "papery"},
            "petiole_attach": {"value": "normal"},
        },
        "stem": {
            "type": {"value": stem_type},
            "cross_section": {"value": "round"},
            "surface": {"value": stem_surface},
            "colors": {"value": stem_colors},
            "interior": {"value": "solid"},
            "has_thorns": {"value": "yes" if "刺" in stem_text else "no"},
        },
    }

    if has_flower:
        features["flower"] = {
            "colors": {"value": flower_colors},
            "color_pattern": {"value": "solid"},
            "petal_count": {"value": petal_count},
            "symmetry": {"value": "radial"},
            "size": {"value": "medium_15-30mm"},
            "arrangement": {"value": flower_arrangement},
            "position": {"value": "terminal"},
            "orientation": {"value": "upright"},
            "special_shape": {"value": flower_special},
            "fragrant": {"value": "yes" if "香" in flower_text else "no"},
        }
    else:
        features["flower"] = None

    features["fruit"] = {
        "type": {"value": fruit_type},
        "colors": {"value": fruit_colors},
        "size": {"value": "small_5-15mm"},
        "surface": {"value": "smooth"},
    }

    features["root"] = {
        "type": {"value": root_type},
    }

    result["features"] = features

    # Usage for edible/medicinal
    if category in ("edible", "medicinal"):
        usage = {"type": []}
        edible_parts = sp.get("edible_parts", [])
        if edible_parts:
            if any("葉" in p for p in edible_parts):
                usage["type"].append("edible_leaf")
            if any("果" in p or "實" in p for p in edible_parts):
                usage["type"].append("edible_fruit")
            if any("根" in p or "莖" in p or "塊" in p for p in edible_parts):
                usage["type"].append("edible_root")
        medicinal = sp.get("medicinal_uses", [])
        if medicinal:
            med_text = " ".join(medicinal)
            if "傷" in med_text or "止血" in med_text:
                usage["type"].append("wound_care")
            if "炎" in med_text or "消炎" in med_text:
                usage["type"].append("anti_inflammatory")
        if not usage["type"]:
            usage["type"] = ["edible_leaf"]
        usage["edible_parts"] = edible_parts
        prep = sp.get("preparation", {})
        if isinstance(prep, dict):
            usage["preparation"] = prep.get("method", "")
            usage["season"] = sp.get("harvesting", {}).get("season", "")
        else:
            usage["preparation"] = str(prep)
            usage["season"] = ""
        usage["warnings"] = sp.get("caution", "")
        if medicinal:
            usage["medicinal_effects"] = medicinal
        result["usage"] = usage

    # Human readable
    hr = {}
    if is_toxic:
        hr["toxicity"] = sp.get("toxicity", "")
        hr["symptoms"] = sp.get("symptoms", [])
        hr["first_aid"] = sp.get("first_aid", "")
        hr["affected_parts"] = sp.get("affected_parts", [])
    else:
        hr["description_zh"] = sp.get("caution", "")

    hr["diagnostic_features"] = []
    for key, val in morph.items():
        if isinstance(val, str) and len(val) > 5:
            hr["diagnostic_features"].append(val[:60])
    if len(hr["diagnostic_features"]) > 5:
        hr["diagnostic_features"] = hr["diagnostic_features"][:5]
    result["human_readable"] = hr

    # Distribution
    result["distribution"] = sp.get("distribution", {
        "altitude_range": [0, 1500],
        "climate_zones": ["subtropical"]
    })
    if "climate_zones" in result["distribution"]:
        cz = result["distribution"]["climate_zones"]
        mapped = []
        for z in cz:
            if "亞熱帶" in z:
                mapped.append("subtropical")
            elif "熱帶" in z:
                mapped.append("tropical")
            elif "溫帶" in z:
                mapped.append("temperate")
            else:
                mapped.append(z)
        result["distribution"]["climate_zones"] = mapped

    return result


def main():
    with open(KB_V1 / "toxic_plants.json", encoding="utf-8") as f:
        toxic = json.load(f)
    with open(KB_V1 / "edible_plants.json", encoding="utf-8") as f:
        edible = json.load(f)
    with open(EXISTING_V2, encoding="utf-8") as f:
        existing = json.load(f)

    existing_ids = {sp["id"] for sp in existing}
    print(f"V1 toxic: {len(toxic)} species")
    print(f"V1 edible: {len(edible)} species")
    print(f"Existing V2: {len(existing)} species (skipping)")

    converted = list(existing)
    new_count = 0

    for sp in toxic:
        if sp["id"] not in existing_ids:
            v2 = convert_species(sp, is_toxic=True)
            converted.append(v2)
            new_count += 1
            print(f"  Converted (toxic): {sp['id']} -> {v2['category']}")

    for sp in edible:
        if sp["id"] not in existing_ids:
            v2 = convert_species(sp, is_toxic=False)
            converted.append(v2)
            new_count += 1
            print(f"  Converted (edible): {sp['id']} -> {v2['category']}")

    # Add the new species from Plan (section 11) that don't exist in v1
    plan_new_species = [
        {"id": "melia_azedarach", "scientific_name": "Melia azedarach",
         "common_names": {"zh-TW": "苦楝", "en": "Chinaberry"},
         "category": "dangerous", "danger_level": "high",
         "morphology": {"leaf_shape": "二至三回羽狀複葉，小葉卵形至橢圓形，長3-5cm，鋸齒緣",
                        "flower": "淡紫色小花，圓錐花序，有香味",
                        "fruit": "黃褐色核果，球形，直徑1-2cm",
                        "stem": "落葉喬木，高可達15-20m，樹皮灰褐色縱裂"},
         "habitat": "行道樹、平地至低海拔山區，海拔 0-800m",
         "toxicity": "果實有毒，含苦楝素，誤食致嘔吐、腹瀉、呼吸困難",
         "symptoms": ["嘔吐", "腹瀉", "呼吸困難"],
         "first_aid": "催吐後送醫",
         "distribution": {"altitude_range": [0, 800], "climate_zones": ["亞熱帶"]}},
        {"id": "pteridium_aquilinum", "scientific_name": "Pteridium aquilinum",
         "common_names": {"zh-TW": "蕨", "en": "Bracken Fern"},
         "category": "dangerous", "danger_level": "low",
         "morphology": {"leaf_shape": "大型三角形二至三回羽狀複葉，長50-100cm",
                        "stem": "地下根莖粗壯，地上無明顯莖",
                        "leaf_surface": "嫩芽捲曲呈拳頭狀"},
         "habitat": "山坡、林緣、開闊地，海拔 0-2500m",
         "toxicity": "含致癌物 ptaquiloside，生食有害",
         "symptoms": ["長期食用可能致癌"],
         "first_aid": "少量誤食無立即危險，但不建議食用",
         "distribution": {"altitude_range": [0, 2500], "climate_zones": ["亞熱帶", "溫帶"]}},
        {"id": "melastoma_candidum", "scientific_name": "Melastoma candidum",
         "common_names": {"zh-TW": "野牡丹", "en": "Malabar Melastome"},
         "category": "edible", "edible_parts": ["果實（紫黑色漿果）"],
         "morphology": {"leaf_shape": "橢圓形至卵形，長5-10cm，3-5條主脈明顯",
                        "flower": "粉紅至紫色大花，直徑5-7cm，五瓣",
                        "fruit": "壺形漿果，成熟紫黑色",
                        "stem": "灌木，高50-150cm"},
         "habitat": "低海拔步道、草地邊緣，海拔 0-1200m",
         "distribution": {"altitude_range": [0, 1200], "climate_zones": ["亞熱帶"]}},
        {"id": "emilia_sonchifolia", "scientific_name": "Emilia sonchifolia",
         "common_names": {"zh-TW": "紫背草（一點紅）", "en": "Lilac Tasselflower"},
         "category": "edible", "edible_parts": ["嫩莖葉"],
         "morphology": {"leaf_shape": "琴形或卵形，長3-8cm，邊緣不規則齒裂",
                        "flower": "紫紅色頭狀花序，管狀小花",
                        "stem": "草本，高20-50cm"},
         "habitat": "路邊、荒地、農田邊，海拔 0-1000m",
         "distribution": {"altitude_range": [0, 1000], "climate_zones": ["亞熱帶"]}},
        {"id": "pseudognaphalium_affine", "scientific_name": "Pseudognaphalium affine",
         "common_names": {"zh-TW": "鼠麴草", "en": "Cudweed"},
         "category": "edible", "edible_parts": ["嫩莖葉（做草仔粿）"],
         "morphology": {"leaf_shape": "倒披針形至匙形，長3-6cm，全株白色絨毛",
                        "flower": "黃色小頭狀花序，密集排列",
                        "stem": "草本，高15-40cm，全株被白色絨毛"},
         "habitat": "農田、路邊、草地，海拔 0-1500m",
         "distribution": {"altitude_range": [0, 1500], "climate_zones": ["亞熱帶"]}},
        {"id": "centella_asiatica", "scientific_name": "Centella asiatica",
         "common_names": {"zh-TW": "雷公根", "en": "Gotu Kola"},
         "category": "medicinal", "edible_parts": ["全草"],
         "medicinal_uses": ["消炎", "促進傷口癒合", "清熱解毒"],
         "morphology": {"leaf_shape": "腎形至圓形，長2-5cm，邊緣鈍齒",
                        "flower": "繖形花序，小花紫紅色，極小",
                        "stem": "匍匐草本，節上生根"},
         "habitat": "潮濕草地、溝邊、路旁，海拔 0-1500m",
         "distribution": {"altitude_range": [0, 1500], "climate_zones": ["亞熱帶"]}},
        {"id": "momordica_charantia_var", "scientific_name": "Momordica charantia var. abbreviata",
         "common_names": {"zh-TW": "山苦瓜", "en": "Wild Bitter Gourd"},
         "category": "edible", "edible_parts": ["果實", "嫩葉"],
         "morphology": {"leaf_shape": "掌狀深裂，5-7裂片",
                        "flower": "黃色五瓣花",
                        "fruit": "紡錘形，表面有瘤狀突起，成熟橙黃色",
                        "stem": "攀緣藤本，有卷鬚"},
         "habitat": "低海拔山野、林緣，海拔 0-800m",
         "distribution": {"altitude_range": [0, 800], "climate_zones": ["亞熱帶"]}},
        {"id": "cyathea_lepifera", "scientific_name": "Cyathea lepifera",
         "common_names": {"zh-TW": "筆筒樹", "en": "Flying Spider-monkey Tree Fern"},
         "category": "edible", "edible_parts": ["嫩心（樹頂生長點）"],
         "morphology": {"leaf_shape": "大型二回至三回羽狀複葉，長2-3m",
                        "stem": "直立樹幹狀，高可達10-15m，幹面有橢圓形葉痕",
                        "leaf_surface": "嫩芽有金褐色鱗片"},
         "habitat": "中低海拔潮濕森林，海拔 200-1500m",
         "distribution": {"altitude_range": [200, 1500], "climate_zones": ["亞熱帶"]}},
    ]

    for sp in plan_new_species:
        if sp["id"] not in existing_ids and sp["id"] not in {s["id"] for s in converted}:
            is_toxic = sp["category"] == "dangerous"
            v2 = convert_species(sp, is_toxic=is_toxic)
            converted.append(v2)
            new_count += 1
            print(f"  Created (new): {sp['id']} -> {v2['category']}")

    print(f"\nTotal: {len(converted)} species ({new_count} newly converted)")

    with open(EXISTING_V2, "w", encoding="utf-8") as f:
        json.dump(converted, f, indent=2, ensure_ascii=False)
    print(f"Wrote to {EXISTING_V2}")


if __name__ == "__main__":
    main()
