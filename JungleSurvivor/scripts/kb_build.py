#!/usr/bin/env python3
"""
Knowledge Base Build Tool — JungleSurvivor v2

功能：
  1. 從 plants.json 收集所有實際使用的 enum 值
  2. 計算每個特徵值的稀有度權重: max(1, round(log2(N / count(value))))
  3. 將權重寫回每個物種的 features
  4. 計算每個物種的 total_weight 和 photo_observable_weight
  5. 生成 LLM prompt 模板
  6. 輸出統計報告
"""

import json
import math
import sys
import io
from pathlib import Path
from collections import defaultdict

KB_ROOT = Path(__file__).parent.parent / "knowledge_base"
PLANTS_FILE = KB_ROOT / "east_asia_subtropical" / "plants.json"
SCHEMA_FILE = KB_ROOT / "feature_schema.json"
OUTPUT_PLANTS = KB_ROOT / "east_asia_subtropical" / "plants.json"
OUTPUT_ENUMS = KB_ROOT / "derived_enums.json"
OUTPUT_WEIGHTS = KB_ROOT / "derived_weights.json"
OUTPUT_PROMPT = KB_ROOT / "prompt_template.txt"

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def load_data():
    with open(PLANTS_FILE, encoding="utf-8") as f:
        plants = json.load(f)
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        schema = json.load(f)
    schema = {k: v for k, v in schema.items() if not k.startswith("_")}
    return plants, schema


def collect_enums(plants, schema):
    """Collect all unique values actually used in KB for each attribute."""
    enums = {}
    for section_name, section_schema in schema.items():
        enums[section_name] = {}
        for attr_name, attr_def in section_schema.items():
            if attr_def["type"] == "boolean":
                continue
            values_in_kb = set()
            for sp in plants:
                feat = sp["features"].get(section_name)
                if feat is None:
                    continue
                attr_obj = feat.get(attr_name)
                if attr_obj is None:
                    continue
                val = attr_obj["value"]
                if isinstance(val, list):
                    values_in_kb.update(val)
                else:
                    values_in_kb.add(val)

            all_values = sorted(values_in_kb)
            if attr_def["type"] in ("single", "array"):
                all_values.append("not_visible")
                all_values.append("uncertain")
            if not attr_def.get("photo_observable", True):
                if "not_checkable" not in all_values:
                    all_values.append("not_checkable")
            enums[section_name][attr_name] = all_values

    return enums


def compute_weights(plants, schema):
    """Compute rarity-based weights: max(1, round(log2(N / count(value))))"""
    N = len(plants)
    if N == 0:
        return {}, {}

    value_counts = {}
    for section_name, section_schema in schema.items():
        value_counts[section_name] = {}
        for attr_name, attr_def in section_schema.items():
            if attr_def["type"] == "boolean":
                continue
            counts = defaultdict(int)
            for sp in plants:
                feat = sp["features"].get(section_name)
                if feat is None:
                    continue
                attr_obj = feat.get(attr_name)
                if attr_obj is None:
                    continue
                val = attr_obj["value"]
                if isinstance(val, list):
                    for v in val:
                        counts[v] += 1
                else:
                    counts[val] += 1
            value_counts[section_name][attr_name] = dict(counts)

    weights = {}
    for section_name, attrs in value_counts.items():
        weights[section_name] = {}
        for attr_name, counts in attrs.items():
            attr_weights = {}
            for value, count in counts.items():
                w = max(1, round(math.log2(N / count)))
                attr_weights[value] = w
            weights[section_name][attr_name] = attr_weights

    return weights, value_counts


def apply_weights_to_plants(plants, weights, schema):
    """Write computed weights back into each plant's features."""
    for sp in plants:
        total_weight = 0
        photo_observable_weight = 0

        for section_name, section_features in sp["features"].items():
            if section_features is None:
                continue
            schema_section = schema.get(section_name, {})
            for attr_name, attr_obj in section_features.items():
                schema_attr = schema_section.get(attr_name)
                if schema_attr is None or schema_attr["type"] == "boolean":
                    continue

                val = attr_obj["value"]
                section_weights = weights.get(section_name, {}).get(attr_name, {})

                if isinstance(val, list):
                    max_w = max((section_weights.get(v, 1) for v in val), default=1)
                    attr_obj["weight"] = max_w
                else:
                    attr_obj["weight"] = section_weights.get(val, 1)

                total_weight += attr_obj["weight"]
                if schema_attr.get("photo_observable", True):
                    photo_observable_weight += attr_obj["weight"]

        sp["total_weight"] = total_weight
        sp["photo_observable_weight"] = photo_observable_weight


VALUE_ZH_DESCRIPTIONS = {
    "growth_form": {"herb": "草本", "shrub": "灌木", "tree": "喬木", "vine": "藤本",
                    "fern": "蕨類", "fungus": "菇菌", "grass": "禾草",
                    "succulent": "多肉", "aquatic": "水生", "moss": "苔蘚", "palm_like": "棕櫚狀"},
    "height_estimate": {"<30cm": "矮於30cm", "30-100cm": "30-100cm", "1-2m": "1-2公尺",
                        "2-5m": "2-5公尺", ">5m": "高於5公尺"},
    "habitat": {"roadside": "路邊", "forest_floor": "林下地面", "streamside": "溪邊",
                "cliff_rock": "岩壁", "open_field": "空曠地", "wetland": "濕地",
                "epiphytic": "附生", "parasitic": "寄生", "urban": "都市", "coastal": "海岸"},
    "leaf_type": {"simple": "單葉", "trifoliate": "三出複葉", "pinnate_compound": "羽狀複葉",
                  "bipinnate_compound": "二回羽狀複葉", "palmate_compound": "掌狀複葉"},
    "shape": {"heart": "心形", "arrow": "箭形", "oval": "卵形", "elliptic": "橢圓形",
              "lanceolate": "披針形", "linear": "線形", "needle": "針形", "scale": "鱗片形",
              "round": "圓形", "spatulate": "匙形", "obovate": "倒卵形",
              "rhombic": "菱形", "fan": "扇形", "kidney": "腎形"},
    "edge": {"entire": "全緣(光滑)", "serrated": "鋸齒", "double_serrated": "重鋸齒",
             "crenate": "圓齒", "lobed": "淺裂", "deeply_lobed": "深裂",
             "wavy": "波狀", "spiny": "刺狀"},
    "tip": {"acute": "銳尖(尖端直接收窄)", "acuminate": "漸尖(尖端拉長如尾巴)",
            "rounded": "圓鈍", "emarginate": "凹缺", "truncate": "截形"},
    "base": {"cordate": "心形基部(有凹口)", "cuneate": "楔形(V字收窄)",
             "rounded": "圓形", "truncate": "截形", "sagittate": "箭形基部",
             "peltate": "盾狀"},
    "surface_top": {"glossy": "光滑反光(像打蠟)", "matte": "霧面(不反光)",
                    "hairy": "有毛", "rough": "粗糙", "waxy": "蠟質層",
                    "velvety": "絨面(如天鵝絨)", "pubescent": "微柔毛", "scaly": "鱗片狀",
                    "sandpaper": "砂紙狀"},
    "surface_bottom": {"glossy": "光滑反光", "matte": "霧面", "hairy": "有毛",
                       "rough": "粗糙", "waxy": "蠟質", "velvety": "絨面",
                       "pubescent": "微柔毛", "scaly": "鱗片狀", "sandpaper": "砂紙狀"},
    "arrangement": {"alternate": "互生", "opposite": "對生", "whorled": "輪生",
                    "rosette": "蓮座狀", "basal_rosette": "基生蓮座",
                    "clustered": "叢生", "spiral": "螺旋", "two_ranked": "二列",
                    "bird_nest_radial": "鳥巢放射狀"},
    "venation": {"parallel": "平行脈", "pinnate": "羽狀脈", "palmate": "掌狀脈",
                 "reticulate": "網狀脈", "single_midrib": "單中脈"},
    "texture": {"papery": "紙質", "leathery": "革質(厚硬)", "fleshy": "肉質",
                "membranous": "膜質", "succulent": "多肉質"},
    "petiole_attach": {"normal": "接在葉片邊緣", "peltate_shield": "盾狀著生(接在葉片內側)",
                       "sheathing": "鞘狀", "sessile": "無柄直接著生"},
    "leaf_size": {"tiny_<2cm": "極小(<2cm)", "small_2-5cm": "小(2-5cm)",
                  "medium_5-15cm": "中(5-15cm)", "large_15-50cm": "大(15-50cm)",
                  "very_large_>50cm": "很大(>50cm)"},
    "color_pattern": {"solid": "純色", "gradient": "漸層", "spotted": "斑點",
                      "striped": "條紋", "bicolor": "雙色", "center_different": "中心異色"},
    "leaf_colors": {"light_green": "淺綠", "green": "綠", "dark_green": "深綠",
                    "yellow_green": "黃綠", "red": "紅", "purple": "紫",
                    "variegated": "斑葉", "silver": "銀", "brown": "棕", "red_underside": "背紅"},
    "stem_type": {"erect": "直立", "creeping": "匍匐", "climbing": "攀緣",
                  "twining": "纏繞", "prostrate": "平臥", "rhizome": "根莖", "pseudostem": "假莖"},
    "stem_surface": {"smooth": "光滑", "hairy": "有毛", "thorny": "有刺",
                     "ridged": "有稜", "waxy": "蠟質", "scaly": "鱗片",
                     "bark_rough": "粗糙樹皮", "bark_smooth": "光滑樹皮"},
    "stem_colors": {"green": "綠", "brown": "棕", "purple": "紫", "red": "紅",
                    "gray": "灰", "white_powdery": "白粉"},
    "flower_colors": {"white": "白", "yellow": "黃", "orange": "橙", "red": "紅",
                      "pink": "粉紅", "purple": "紫", "blue": "藍", "green": "綠", "brown": "棕"},
    "flower_arrangement": {"solitary": "單生", "raceme": "總狀", "spike": "穗狀",
                           "umbel": "繖形", "head_composite": "頭狀(菊科)",
                           "panicle": "圓錐", "cyme": "聚繖", "catkin": "柔荑",
                           "spathe_spadix": "佛焰苞+肉穗(天南星科)"},
    "special_shape": {"none": "無", "lip_labellum": "唇瓣(蘭科)", "spur": "距",
                      "spathe": "佛焰苞", "butterfly_shape": "蝶形(豆科)",
                      "bell_tubular": "鐘形/筒形", "trumpet": "喇叭形"},
    "fruit_type": {"berry": "漿果", "drupe": "核果", "capsule": "蒴果",
                   "pod_legume": "莢果", "achene": "瘦果", "samara": "翅果",
                   "nut": "堅果", "aggregate": "聚合果", "fig": "隱花果",
                   "cone": "毬果", "spore": "孢子"},
    "fruit_colors": {"green": "綠", "yellow": "黃", "orange": "橙", "red": "紅",
                     "purple": "紫", "black": "黑", "brown": "棕", "white_waxy": "白蠟"},
    "fruit_surface": {"smooth": "光滑", "hairy": "有毛", "spiny": "有刺",
                      "warty": "疣狀", "waxy": "蠟質", "hooked_bristles": "鉤刺"},
}

def _annotate_value(val, attr_name, section_name):
    """Add Chinese annotation to an enum value if available."""
    if val in ("not_visible", "uncertain", "not_checkable"):
        return val
    lookup_key = attr_name
    if section_name == "leaf" and attr_name == "size":
        lookup_key = "leaf_size"
    elif section_name == "leaf" and attr_name == "colors":
        lookup_key = "leaf_colors"
    elif section_name == "stem" and attr_name == "type":
        lookup_key = "stem_type"
    elif section_name == "stem" and attr_name == "surface":
        lookup_key = "stem_surface"
    elif section_name == "stem" and attr_name == "colors":
        lookup_key = "stem_colors"
    elif section_name == "flower" and attr_name == "colors":
        lookup_key = "flower_colors"
    elif section_name == "flower" and attr_name == "arrangement":
        lookup_key = "flower_arrangement"
    elif section_name == "fruit" and attr_name == "type":
        lookup_key = "fruit_type"
    elif section_name == "fruit" and attr_name == "colors":
        lookup_key = "fruit_colors"
    elif section_name == "fruit" and attr_name == "surface":
        lookup_key = "fruit_surface"
    desc_dict = VALUE_ZH_DESCRIPTIONS.get(lookup_key, {})
    zh = desc_dict.get(val)
    if zh:
        return f"{val}({zh})"
    return val


def _annotate_values(values, attr_name, section_name):
    """Annotate a list of enum values with Chinese descriptions."""
    return [_annotate_value(v, attr_name, section_name) for v in values]


_FEWSHOT_EXAMPLE = r'''{
  "growth_form": "herb",
  "height_estimate": "30-100cm",
  "latex": "not_checkable",
  "smell": "not_checkable",
  "habitat": "roadside",
  "water_droplet_test": "not_checkable",
  "leaf": {
    "leaf_type": "simple",
    "shape": "oval",
    "edge": "serrated",
    "tip": "acute",
    "base": "rounded",
    "colors": ["green"],
    "color_pattern": "solid",
    "surface_top": "matte",
    "surface_bottom": "hairy",
    "arrangement": "alternate",
    "size": "medium_5-15cm",
    "venation": "pinnate",
    "texture": "papery",
    "petiole_attach": "normal"
  },
  "stem": {
    "type": "erect",
    "cross_section": "round",
    "surface": "hairy",
    "colors": ["green"],
    "interior": "not_checkable",
    "has_thorns": "no"
  },
  "flower": {
    "visible": false
  },
  "fruit": {
    "visible": false
  },
  "root": {
    "visible": false,
    "type": "not_checkable"
  }
}'''


def generate_prompt_template(enums, schema):
    """Generate LLM prompt template with enum choices, Chinese annotations, and few-shot example."""
    non_photo_attrs = []
    for section_name, section_schema in schema.items():
        for attr_name, attr_def in section_schema.items():
            if not attr_def.get("photo_observable", True):
                non_photo_attrs.append((section_name, attr_name))

    lines = []
    lines.append("你是植物特徵辨識器。請仔細觀察照片中的植物，")
    lines.append("只根據你在照片中「實際看到」的視覺特徵填寫 JSON。")
    lines.append("")
    lines.append("【核心規則】")
    lines.append("1. 只根據照片的視覺資訊填寫，不要根據你對植物物種的知識填寫。")
    lines.append("   即使你認出這可能是某種植物，也必須只描述照片中看到的特徵。")
    lines.append('2. 看不到的部位填 "not_visible"，不確定的屬性填 "uncertain"。')
    lines.append("3. 嚴禁猜測看不到的部位。")
    lines.append("4. 輸出純 JSON，不要任何解釋文字。")
    lines.append('5. 如果某個部位（花/果實/根）完全不在照片中，該部位只填 "visible": false，')
    lines.append("   不要填寫該部位的其他任何屬性。範例：\"flower\": {\"visible\": false}")
    lines.append("")
    lines.append("【照片無法判斷的屬性 — 一律填 \"not_checkable\"】")
    lines.append("以下屬性不可能從照片判斷，不論你多有信心，一律填 \"not_checkable\"：")
    desc_map = {
        ("overall", "latex"): "汁液 — 需折斷莖部才能觀察",
        ("overall", "smell"): "氣味 — 需要實際聞到",
        ("overall", "water_droplet_test"): "水珠測試 — 需要現場實測",
        ("stem", "interior"): "莖內部 — 需要切開才能觀察",
        ("flower", "fragrant"): "花香 — 需要實際聞到",
        ("root", "type"): "根型 — 根部通常在地下",
    }
    for sec, attr in non_photo_attrs:
        desc = desc_map.get((sec, attr), attr)
        if sec == "overall":
            lines.append(f"- {attr}（{desc}）")
        else:
            lines.append(f"- {sec}.{attr}（{desc}）")

    lines.append("")
    lines.append("【範例 — 一張路邊草本植物只拍到葉和莖的照片】")
    lines.append(_FEWSHOT_EXAMPLE)

    lines.append("")
    lines.append("【請填寫以下 JSON — 每個值必須從括號內的選項中選擇】")
    lines.append("{")

    section_order = ["overall", "leaf", "stem", "flower", "fruit", "root"]
    for i, section_name in enumerate(section_order):
        section_enums = enums.get(section_name, {})
        section_schema = schema.get(section_name, {})
        if not section_enums:
            continue

        if section_name == "overall":
            for attr_name, values in section_enums.items():
                attr_def = section_schema.get(attr_name, {})
                annotated = _annotate_values(values, attr_name, section_name)
                display = json.dumps(annotated, ensure_ascii=False)
                if attr_def.get("type") == "array":
                    lines.append(f'  "{attr_name}": [從 {display} 中選一到多個],')
                else:
                    lines.append(f'  "{attr_name}": 從 {display} 選,')
        else:
            lines.append(f'  "{section_name}": {{')
            attr_items = list(section_enums.items())
            for j, (attr_name, values) in enumerate(attr_items):
                attr_def = section_schema.get(attr_name, {})
                annotated = _annotate_values(values, attr_name, section_name)
                display = json.dumps(annotated, ensure_ascii=False)
                comma = "," if j < len(attr_items) - 1 else ""
                if attr_def.get("type") == "array":
                    lines.append(f'    "{attr_name}": [從 {display} 中選一到多個]{comma}')
                else:
                    lines.append(f'    "{attr_name}": 從 {display} 選{comma}')
            comma = "," if i < len(section_order) - 1 else ""
            lines.append(f'  }}{comma}')

    lines.append("}")
    return "\n".join(lines)


def print_stats(plants, weights, value_counts):
    """Print statistics report."""
    N = len(plants)
    print(f"\n{'='*60}")
    print(f"Knowledge Base Build Report")
    print(f"{'='*60}")
    print(f"Total species: {N}")
    print(f"Categories: ", end="")
    cats = defaultdict(int)
    for sp in plants:
        cats[sp["category"]] += 1
    print(", ".join(f"{k}={v}" for k, v in sorted(cats.items())))

    print(f"\nPer-species weight summary:")
    for sp in plants:
        name = sp["common_names"].get("zh-TW", sp["id"])
        print(f"  {name:20s} total_weight={sp['total_weight']:3d}  photo_observable={sp['photo_observable_weight']:3d}")

    print(f"\nWeight distribution by section:")
    for section_name, attrs in weights.items():
        all_w = []
        for attr_weights in attrs.values():
            all_w.extend(attr_weights.values())
        if all_w:
            print(f"  {section_name:10s}: min={min(all_w)}, max={max(all_w)}, avg={sum(all_w)/len(all_w):.1f}")

    print(f"\nHigh-weight features (weight >= 3):")
    for section_name, attrs in weights.items():
        for attr_name, attr_weights in attrs.items():
            for value, w in sorted(attr_weights.items(), key=lambda x: -x[1]):
                if w >= 3:
                    count = value_counts[section_name][attr_name][value]
                    print(f"  {section_name}.{attr_name} = {value:25s} weight={w} (appears in {count}/{N} species)")


def main():
    plants, schema = load_data()
    print(f"Loaded {len(plants)} species, {len(schema)} feature sections")

    # Step 1: Collect enums
    enums = collect_enums(plants, schema)
    total_enums = sum(len(v) for attrs in enums.values() for v in attrs.values())
    print(f"Collected {total_enums} unique enum values across all attributes")

    # Step 2: Compute weights
    weights, value_counts = compute_weights(plants, schema)

    # Step 3: Apply weights to plants
    apply_weights_to_plants(plants, weights, schema)

    # Step 4: Generate prompt template
    prompt = generate_prompt_template(enums, schema)

    # Step 5: Save outputs
    with open(OUTPUT_PLANTS, "w", encoding="utf-8") as f:
        json.dump(plants, f, indent=2, ensure_ascii=False)
    print(f"Wrote plants with weights to {OUTPUT_PLANTS.name}")

    with open(OUTPUT_ENUMS, "w", encoding="utf-8") as f:
        json.dump(enums, f, indent=2, ensure_ascii=False)
    print(f"Wrote derived enums to {OUTPUT_ENUMS.name}")

    with open(OUTPUT_WEIGHTS, "w", encoding="utf-8") as f:
        json.dump(weights, f, indent=2, ensure_ascii=False)
    print(f"Wrote derived weights to {OUTPUT_WEIGHTS.name}")

    with open(OUTPUT_PROMPT, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"Wrote prompt template to {OUTPUT_PROMPT.name}")

    # Step 6: Print stats
    print_stats(plants, weights, value_counts)


if __name__ == "__main__":
    main()
