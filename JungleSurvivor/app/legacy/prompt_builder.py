"""
動態 Prompt 組裝器 — 兩階段辨識架構。

Stage 1: 危險物種比對 → 取信心度最高的 3 個
Stage 2: 可食用/藥用物種比對 → 取信心度最高的 3 個

信心度 = 絕對相似度（多少項形態特徵吻合），不是排名。
"""

from context_engine import EnvironmentContext, KnowledgeBase
from config import JSON_START_MARKER, JSON_END_MARKER, THRESHOLDS


# ═══════════════════════════════════════════════════════════════
# 內部格式化工具
# ═══════════════════════════════════════════════════════════════

def _format_toxic_plant(plant: dict) -> str:
    morph = plant.get("morphology", {})
    lines = [f"{plant['common_names']['zh-TW']} ({plant['scientific_name']})"]
    lines.append(f"   毒性：{plant['toxicity']}")

    field_map = {
        "leaf_shape": "葉形", "leaf_surface": "葉面", "leaf_venation": "葉脈",
        "leaf_tip": "葉尖", "petiole": "葉柄", "stem": "莖部",
        "flower": "花", "fruit": "果實",
        "leaf_arrangement": "葉排列",
        "cap": "傘蓋", "gills": "菌褶", "stipe": "菌柄",
        "spore_print": "孢子印", "ring": "菌環", "flesh": "菌肉",
    }
    for key, label in field_map.items():
        if key in morph:
            lines.append(f"   {label}：{morph[key]}")

    lines.append(f"   生長環境：{plant.get('habitat', 'N/A')}")

    if plant.get("confusion_with"):
        names = ", ".join(plant["confusion_with"])
        lines.append(f"   易混淆：{names}")

    return "\n".join(lines)


def _format_dangerous_animal(animal: dict) -> str:
    morph = animal.get("morphology", {})
    lines = [f"{animal['common_names']['zh-TW']} ({animal['scientific_name']})"]
    lines.append(f"   毒性：{animal.get('venom_type', 'N/A')}")

    field_map = {
        "body_color": "體色", "tail": "尾部", "head_shape": "頭形",
        "pupil": "瞳孔", "pit_organ": "頰窩", "body_size": "體型",
        "scales": "鱗片", "hood": "頸部", "dorsal_scales": "背鱗",
    }
    for key, label in field_map.items():
        if key in morph:
            lines.append(f"   {label}：{morph[key]}")

    lines.append(f"   棲地：{animal.get('habitat', 'N/A')}")
    lines.append(f"   行為：{animal.get('behavior', 'N/A')}")

    return "\n".join(lines)


def _format_edible_plant(plant: dict) -> str:
    morph = plant.get("morphology", {})
    lines = [f"{plant['common_names']['zh-TW']} ({plant['scientific_name']})"]
    lines.append(f"   食用部位：{', '.join(plant.get('edible_parts', []))}")

    for key, label in [
        ("leaf_shape", "葉形"), ("leaf_arrangement", "葉排列"),
        ("leaf_surface", "葉面"), ("flower", "花"), ("stem", "莖"),
        ("midrib", "中肋"), ("growth_pattern", "生長方式"),
        ("young_shoot", "嫩芽"), ("shape", "外形"), ("fruit", "果實"),
        ("underground", "地下部"), ("smell", "氣味"),
    ]:
        if key in morph:
            lines.append(f"   {label}：{morph[key]}")

    lines.append(f"   生長環境：{plant.get('habitat', 'N/A')}")

    harvesting = plant.get("harvesting", {})
    if harvesting:
        lines.append(f"   採集方式：{harvesting.get('method', 'N/A')}")

    prep = plant.get("preparation", {})
    if prep:
        lines.append(f"   食用方式：{prep.get('method', 'N/A')}")

    if plant.get("caution"):
        lines.append(f"   ⚠️ 注意：{plant['caution']}")

    if plant.get("medicinal_uses"):
        lines.append(f"   💊 藥用：{plant['medicinal_uses']}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Stage 1：危險物種比對 — 輸出 top 3
# ═══════════════════════════════════════════════════════════════

_CONFIDENCE_INSTRUCTION = """
IMPORTANT — How to calculate "confidence":
Confidence is an ABSOLUTE measure of visual similarity, NOT a ranking.
Count how many morphological features from the reference data match
what you observe in the photo. The more features that match, the higher
the confidence (0-100).
- 0%: No features match at all
- 30%: Only general shape/color roughly matches
- 50%: ~Half of listed features match
- 70%: Most key features match, minor differences remain
- 85%: Nearly all features match, very strong identification
- 95-100%: Every listed feature matches perfectly
If a feature cannot be verified from the photo, do NOT count it as matching.
"""


def build_danger_prompt(
    context: EnvironmentContext,
    kb: KnowledgeBase,
    target_type: str = "plant",
) -> str:
    """Stage 1：比對危險物種，輸出信心度最高的 3 個候選。"""
    header = context.to_prompt_header()

    if target_type == "plant":
        role = "a toxicology expert specializing in field identification of dangerous plants and fungi"
        target_word = "plant/fungus"
        species_list = "\n\n".join(
            f"{i+1}. {_format_toxic_plant(p)}"
            for i, p in enumerate(kb.toxic_plants)
        )
    else:
        role = "a herpetology and zoology expert specializing in identification of dangerous animals"
        target_word = "animal/snake"
        species_list = "\n\n".join(
            f"{i+1}. {_format_dangerous_animal(a)}"
            for i, a in enumerate(kb.dangerous_animals)
        )

    prompt = f"""{header}

You are {role}.
Analyze the {target_word} in the provided photo(s).

{_CONFIDENCE_INSTRUCTION}

Follow these steps:

Step 1: Carefully observe the photo(s). Describe ALL morphological features you can see.

Step 2: Compare your observations against EACH species in the list below.
For each species, count how many listed morphological features match the photo.

Step 3: Rank all species by confidence (absolute feature match count → percentage).
Select the TOP 3 with the highest confidence.

Step 4: For features you cannot determine from the photo, explicitly list them.

=== DANGEROUS SPECIES DATABASE ===

{species_list}

After completing Steps 1-4, output a JSON summary:

{JSON_START_MARKER}
{{
  "reasoning_summary": "用繁體中文簡述分析過程（描述你觀察到什麼、與哪些特徵吻合）",
  "observed_features": ["觀察到的特徵1", "觀察到的特徵2", "..."],
  "candidates": [
    {{
      "rank": 1,
      "common_name_zh": "中文名",
      "common_name_en": "English name",
      "scientific_name": "學名",
      "confidence": 85,
      "category": "dangerous",
      "key_matching_features": ["吻合特徵1", "吻合特徵2"],
      "danger_info": {{
        "toxicity": "毒性描述",
        "symptoms": ["中毒症狀"],
        "first_aid": "急救方式"
      }}
    }},
    {{
      "rank": 2,
      "common_name_zh": "...",
      "common_name_en": "...",
      "scientific_name": "...",
      "confidence": 45,
      "category": "dangerous",
      "key_matching_features": ["..."],
      "danger_info": {{ "toxicity": "...", "symptoms": [], "first_aid": "..." }}
    }},
    {{
      "rank": 3,
      "common_name_zh": "...",
      "common_name_en": "...",
      "scientific_name": "...",
      "confidence": 20,
      "category": "dangerous",
      "key_matching_features": ["..."],
      "danger_info": {{ "toxicity": "...", "symptoms": [], "first_aid": "..." }}
    }}
  ]
}}
{JSON_END_MARKER}

Rules:
- "confidence": integer 0-100, absolute feature-matching score
- "category": always "dangerous" in this stage
- Output exactly 3 candidates, even if confidence is low
- All Chinese text in Traditional Chinese (繁體中文)

First write your full analysis in Traditional Chinese, THEN output the JSON.
請用繁體中文回覆。"""

    return prompt


# ═══════════════════════════════════════════════════════════════
# Stage 2：可食用/藥用物種比對 — 輸出 top 3
# ═══════════════════════════════════════════════════════════════

def build_edible_prompt(
    context: EnvironmentContext,
    kb: KnowledgeBase,
) -> str:
    """Stage 2：比對可食用/藥用物種，輸出信心度最高的 3 個候選。"""
    header = context.to_prompt_header()

    edible_list = "\n\n".join(
        f"{i+1}. {_format_edible_plant(p)}"
        for i, p in enumerate(kb.edible_plants)
    )

    prompt = f"""{header}

You are a field survival botanist helping identify edible and medicinal plants.
Analyze the plant in the provided photo(s).

{_CONFIDENCE_INSTRUCTION}

Follow these steps:

Step 1: Carefully observe the photo(s). Describe ALL morphological features you can see.

Step 2: Compare your observations against EACH edible/medicinal species in the list below.
For each species, count how many listed morphological features match the photo.

Step 3: Rank all species by confidence (absolute feature match count → percentage).
Select the TOP 3 with the highest confidence.

Step 4: For features you cannot determine from the photo, explicitly list them.

=== EDIBLE / MEDICINAL SPECIES DATABASE ===

{edible_list}

After completing Steps 1-4, output a JSON summary:

{JSON_START_MARKER}
{{
  "reasoning_summary": "用繁體中文簡述分析過程",
  "observed_features": ["觀察到的特徵1", "觀察到的特徵2", "..."],
  "candidates": [
    {{
      "rank": 1,
      "common_name_zh": "中文名",
      "common_name_en": "English name",
      "scientific_name": "學名",
      "confidence": 85,
      "category": "edible",
      "key_matching_features": ["吻合特徵1", "吻合特徵2"],
      "danger_info": null
    }},
    {{
      "rank": 2,
      "common_name_zh": "...",
      "common_name_en": "...",
      "scientific_name": "...",
      "confidence": 45,
      "category": "edible",
      "key_matching_features": ["..."],
      "danger_info": null
    }},
    {{
      "rank": 3,
      "common_name_zh": "...",
      "common_name_en": "...",
      "scientific_name": "...",
      "confidence": 20,
      "category": "edible",
      "key_matching_features": ["..."],
      "danger_info": null
    }}
  ]
}}
{JSON_END_MARKER}

Rules:
- "confidence": integer 0-100, absolute feature-matching score
- "category": "edible" or "medicinal" (choose based on primary use)
- Output exactly 3 candidates, even if confidence is low
- All Chinese text in Traditional Chinese (繁體中文)

First write your full analysis in Traditional Chinese, THEN output the JSON.
請用繁體中文回覆。"""

    return prompt


# ═══════════════════════════════════════════════════════════════
# 混淆物種鑑別（保留原有邏輯）
# ═══════════════════════════════════════════════════════════════

def build_confusion_pairs_prompt(
    context: EnvironmentContext,
    pair: dict,
) -> str:
    """建構混淆物種專項鑑別 Prompt。"""
    header = context.to_prompt_header()
    threshold = THRESHOLDS.get("confusion_pairs", 80)

    safe = pair["safe_species"]
    danger = pair["dangerous_species"]

    safe_features = "\n".join(
        f"- {k}：{v}" for k, v in safe["key_features"].items()
    )
    danger_features = "\n".join(
        f"- {k}：{v}" for k, v in danger["key_features"].items()
    )

    comparison_rows = ""
    for row in pair.get("comparison_table", []):
        comparison_rows += f"| {row['feature']} | {row['safe']} | {row['danger']} |\n"

    prompt = f"""{header}

你是一位植物學家，專精於野外求生中的危險植物鑑別。
這張照片中的植物可能是以下兩種之一，它們外觀非常相似，
但一個可食用，一個有毒。誤判可能致命。

【可食用】{safe['common_name_zh']} ({safe['scientific_name']})
{safe_features}

【有毒】{danger['common_name_zh']} ({danger['scientific_name']})
{danger_features}

【關鍵鑑別對照表】
| 特徵 | {safe['common_name_zh']}（可食） | {danger['common_name_zh']}（有毒） |
|------|------|------|
{comparison_rows}

請根據照片中可辨識的特徵，逐項比對上表，判斷：
1. 你觀察到哪些特徵？逐一描述
2. 每個特徵更符合{safe['common_name_zh']}還是{danger['common_name_zh']}？
3. 有哪些特徵無法從照片中判斷？
4. 最終判斷：更可能是哪一種？信心度（0-100%）？

⚠️ 重要規則：
- 如果信心度 < {threshold}%，請標注「無法確定，視為有毒，禁止食用」
- 如果任何關鍵鑑別特徵無法從照片確認，也請標注「無法確定，視為有毒」
- 在求生情境中，誤判比不判更危險

After your analysis, output a JSON summary:

{JSON_START_MARKER}
{{
  "confusion_pair_id": "{pair['id']}",
  "judgment": "safe" or "dangerous" or "uncertain",
  "confidence": 0,
  "safe_species": "{safe['common_name_zh']}",
  "dangerous_species": "{danger['common_name_zh']}",
  "feature_comparison": [
    {{
      "feature": "特徵名",
      "observation": "照片中觀察到的情況",
      "matches": "safe" or "dangerous" or "uncertain"
    }}
  ],
  "unobservable_features": ["無法判斷的特徵"],
  "requires_interactive_test": true,
  "recommended_tests": ["建議的互動測試"],
  "final_message_zh": "給使用者的最終建議（繁體中文）"
}}
{JSON_END_MARKER}

請用繁體中文回覆。"""

    return prompt


def build_interactive_test_guidance(pair: dict) -> str:
    """混淆鑑別無法確定時，引導使用者做實地測試。"""
    safe = pair["safe_species"]
    danger = pair["dangerous_species"]
    tests = pair.get("interactive_tests", [])

    if not tests:
        return f"⚠️ 此植物可能是{safe['common_name_zh']}或{danger['common_name_zh']}，無法確定，請勿食用。"

    lines = [
        f"⚠️ 此植物可能是{safe['common_name_zh']}（可食）或{danger['common_name_zh']}（有毒），",
        "僅靠照片無法區分。請執行以下測試：",
        "",
    ]

    for test in sorted(tests, key=lambda t: t.get("priority", 99)):
        critical = "（最關鍵！）" if test.get("is_critical") else ""
        lines.append(f"🔬 {test['test_name']}{critical}：")
        lines.append(f"   {test['instruction_zh']}")
        lines.append(f"   → {test['safe_result']}")
        lines.append(f"   → {test['danger_result']}")
        lines.append("")

    lines.extend([
        "📷 完成測試後，請拍攝測試結果照片上傳，我將結合新資訊重新判斷。",
        f"⚠️ 在完成測試前，請勿食用此植物。",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 多照片包裝器
# ═══════════════════════════════════════════════════════════════

def build_multi_photo_wrapper(base_prompt: str, num_photos: int) -> str:
    """將任何 Prompt 包裝成多照片版本（多角度可提升信心度）。"""
    photo_instructions = (
        f"I am providing {num_photos} photos of the SAME subject taken from different angles.\n"
        "Analyze ALL photos together to improve identification accuracy.\n"
        "For Step 1, describe features observed in EACH photo separately,\n"
        "then note which features are consistently observed across photos (higher reliability).\n\n"
    )

    return base_prompt.replace(
        "Step 1: Carefully observe the photo(s).",
        photo_instructions + "Step 1: For EACH photo, describe the morphological features you observe.",
    )
