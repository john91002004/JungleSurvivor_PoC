"""
動態 Prompt 組裝器 — 單次推論合併架構。

設計原則：
- 一次 AI 呼叫同時比對所有物種（危險 + 可食 + 藥用）
- 輸出前 3 名候選，跨類別排名
- 程式端後處理混淆物種，不需二次 AI 呼叫
- JSON 關鍵欄位在前，reasoning 在後
"""


def _format_toxic_plant(plant: dict, idx: int) -> str:
    morph = plant.get("morphology", {})
    lines = [f"{idx}. [⚠️危險] {plant['common_names']['zh-TW']} ({plant['scientific_name']})"]
    lines.append(f"   毒性：{plant['toxicity']}")

    priority_keys = ["leaf_shape", "leaf_surface", "leaf_venation", "leaf_arrangement",
                     "flower", "fruit", "stem", "petiole",
                     "cap", "gills", "stipe", "ring"]
    for key in priority_keys:
        if key in morph:
            lines.append(f"   {key}：{morph[key]}")

    lines.append(f"   habitat：{plant.get('habitat', 'N/A')}")
    if plant.get("confusion_with"):
        lines.append(f"   易混淆：{', '.join(plant['confusion_with'])}")
    return "\n".join(lines)


def _format_edible_plant(plant: dict, idx: int) -> str:
    morph = plant.get("morphology", {})
    is_med = bool(plant.get("medicinal_uses"))
    tag = "[🍃可食+💊藥用]" if is_med else "[🍃可食]"
    lines = [f"{idx}. {tag} {plant['common_names']['zh-TW']} ({plant['scientific_name']})"]
    lines.append(f"   edible_parts：{', '.join(plant.get('edible_parts', []))}")

    if is_med:
        lines.append(f"   medicinal：{', '.join(plant.get('medicinal_uses', []))}")

    priority_keys = ["leaf_shape", "leaf_surface", "leaf_venation", "leaf_arrangement",
                     "flower", "stem", "fruit", "growth_pattern", "smell",
                     "midrib", "underground", "petiole"]
    for key in priority_keys:
        if key in morph:
            lines.append(f"   {key}：{morph[key]}")

    lines.append(f"   habitat：{plant.get('habitat', 'N/A')}")
    return "\n".join(lines)


def _format_dangerous_animal(animal: dict, idx: int) -> str:
    morph = animal.get("morphology", {})
    lines = [f"{idx}. [⚠️危險] {animal['common_names']['zh-TW']} ({animal['scientific_name']})"]
    lines.append(f"   venom：{animal.get('venom_type', 'N/A')}")

    priority_keys = ["body_color", "head_shape", "body_size", "pupil",
                     "scales", "hood", "tail", "dorsal_scales"]
    for key in priority_keys:
        if key in morph:
            lines.append(f"   {key}：{morph[key]}")

    lines.append(f"   habitat：{animal.get('habitat', 'N/A')}")
    lines.append(f"   behavior：{animal.get('behavior', 'N/A')}")
    return "\n".join(lines)


def _append_user_description(prompt: str, user_description: str | None) -> str:
    if not user_description or not user_description.strip():
        return prompt
    return prompt + f"""

IMPORTANT — The user also provides the following verbal description of the subject:
\"{user_description.strip()}\"

Incorporate this information into your analysis. Verbal descriptions of smell, texture,
touch, and growth environment are especially valuable since they cannot be determined
from photos alone. Give extra weight to these observations.
"""


def _json_template() -> str:
    return f"""OUTPUT: Respond with ONLY the JSON below. No other text before or after the JSON markers.

{JSON_START_MARKER}
{{
  "candidates": [
    {{
      "rank": 1,
      "common_name_zh": "中文名",
      "common_name_en": "English name",
      "scientific_name": "學名",
      "confidence": 85,
      "category": "dangerous|edible|medicinal",
      "key_matching_features": ["匹配特徵1", "匹配特徵2"],
      "danger_info": {{"is_dangerous": true, "toxicity": "毒性描述", "warning": "警告"}}
    }},
    {{"rank": 2, "common_name_zh": "名", "common_name_en": "name", "scientific_name": "學名", "confidence": 45, "category": "edible", "key_matching_features": ["特徵"], "danger_info": null}},
    {{"rank": 3, "common_name_zh": "名", "common_name_en": "name", "scientific_name": "學名", "confidence": 20, "category": "edible", "key_matching_features": ["特徵"], "danger_info": null}}
  ],
  "observed_features": ["特徵1", "特徵2", "特徵3"],
  "reasoning_summary": "判斷依據"
}}
{JSON_END_MARKER}"""


def _rules_section() -> str:
    return f"""RULES:
- confidence: 0-100 (based on how many features match)
- category: "dangerous" if species is toxic/venomous, "edible" if safe to eat, "medicinal" if has medicinal uses
- danger_info: fill ONLY for dangerous species, set null for safe species
- If the subject does NOT match any species well, still provide 3 candidates but with LOW confidence (<30)
- Use Traditional Chinese for names and descriptions
- Always provide exactly 3 candidates"""


def build_unified_prompt(
    context: EnvironmentContext,
    kb: KnowledgeBase,
    target_type: str = "plant",
    user_description: str | None = None,
) -> str:
    """
    合併式辨識 prompt：一次呼叫比對所有物種，輸出前 3 名候選。
    """
    header = context.to_prompt_header()

    if target_type == "animal":
        role = "a herpetology and zoology expert"
        species_list = "\n\n".join(
            _format_dangerous_animal(a, i + 1)
            for i, a in enumerate(kb.dangerous_animals)
        )
        prompt = f"""{header}

You are {role}. Identify the animal in the photo(s).

=== SPECIES DATABASE ({len(kb.dangerous_animals)} species) ===
{species_list}

TASK:
1. Carefully observe the morphological features in the photo(s).
2. Compare with ALL species in the database above.
3. Select the TOP 3 most similar species, ranked by confidence.
4. If NONE match well, set all confidence values below 30.

{_json_template()}

{_rules_section()}"""
    else:
        idx = 1
        all_species_parts = []

        for p in kb.toxic_plants:
            all_species_parts.append(_format_toxic_plant(p, idx))
            idx += 1

        for p in kb.edible_plants:
            all_species_parts.append(_format_edible_plant(p, idx))
            idx += 1

        species_list = "\n\n".join(all_species_parts)
        total = len(kb.toxic_plants) + len(kb.edible_plants)

        prompt = f"""{header}

You are a botanist expert in field identification. Identify the plant in the photo(s).

=== SPECIES DATABASE ({total} species: {len(kb.toxic_plants)} dangerous + {len(kb.edible_plants)} edible/medicinal) ===
{species_list}

TASK:
1. Carefully observe the morphological features in the photo(s): leaf shape, venation, surface texture, arrangement, stem, flowers, fruits, growth habit.
2. Compare with ALL species in the database above.
3. Select the TOP 3 most similar species, ranked by confidence (0-100%).
4. If NONE match well, set all confidence values below 30.
5. Mark each candidate's category: "dangerous", "edible", or "medicinal".

{_json_template()}

{_rules_section()}"""

    prompt = _append_user_description(prompt, user_description)
    return prompt


def build_confusion_pairs_prompt(
    context: EnvironmentContext,
    pair: dict,
) -> str:
    """
    混淆物種專項鑑別 prompt（備用，當需要進一步確認時使用）。
    """
    header = context.to_prompt_header()
    threshold = THRESHOLDS["confusion_pairs"]

    safe = pair["safe_species"]
    danger = pair["dangerous_species"]

    safe_features = "\n".join(f"- {k}：{v}" for k, v in safe["key_features"].items())
    danger_features = "\n".join(f"- {k}：{v}" for k, v in danger["key_features"].items())

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

請根據照片中可辨識的特徵，判斷更可能是哪一種。

{JSON_START_MARKER}
{{
  "confusion_pair_id": "{pair['id']}",
  "judgment": "safe|dangerous|uncertain",
  "confidence": 0,
  "observed_features": ["觀察到的特徵"],
  "matching_safe": ["符合可食特徵"],
  "matching_danger": ["符合有毒特徵"],
  "unobservable_features": ["無法判斷的特徵"],
  "requires_interactive_test": true,
  "final_message_zh": "給使用者的最終建議（繁體中文）"
}}
{JSON_END_MARKER}

⚠️ 重要：如果信心度 < {threshold}%，judgment 必須設為 "uncertain"。
在無法確定時，一律視為有毒。請用繁體中文回覆。"""

    return prompt


def build_interactive_test_guidance(pair: dict) -> str:
    """產生互動式測試的引導文字。"""
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
        "⚠️ 在完成測試前，請勿食用此植物。",
    ])

    return "\n".join(lines)


def build_multi_photo_wrapper(base_prompt: str, num_photos: int) -> str:
    """將 prompt 包裝成多照片版本。"""
    insert = (
        f"\nI am providing {num_photos} photos of the SAME subject taken from different angles.\n"
        "Analyze ALL photos together. Features consistently observed across multiple photos have higher reliability.\n\n"
    )
    if "TASK:" in base_prompt:
        return base_prompt.replace("TASK:", insert + "TASK:", 1)
    return insert + base_prompt
