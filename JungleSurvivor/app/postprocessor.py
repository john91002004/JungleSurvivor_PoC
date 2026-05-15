"""
JungleSurvivor v2 — Post-processor

Implements Plan Section 8:
  - 8.1: Warning level determination (strict priority: RED > ORANGE > YELLOW > GREEN > GREY)
  - 8.2: Unknown species handling
  - 8.3: Confusion pair detection and field test guidance
  - 8.4: Top 3 result formatting
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from .scoring import ScoreResult


@dataclass
class WarningInfo:
    level: str  # RED, ORANGE, YELLOW, GREEN, GREY
    color: str  # emoji indicator
    message: str


@dataclass
class ConfusionPairAlert:
    pair_id: str
    species_a_id: str
    species_b_id: str
    lethality: str
    key_differences: list[dict]


@dataclass
class ProcessedResult:
    top_results: list[ScoreResult]
    warning: WarningInfo
    confusion_alerts: list[ConfusionPairAlert] = field(default_factory=list)
    is_unknown: bool = False
    unknown_message: Optional[str] = None


def determine_warning_level(top3: list[ScoreResult]) -> WarningInfo:
    """
    Plan 8.1: Strict priority warning level determination.
    Evaluates from most dangerous to safest; returns on first match.
    """
    if not top3:
        return WarningInfo(
            level="GREY",
            color="",
            message="無法判定，請提供更多資訊。",
        )

    top1 = top3[0]

    # Priority 1: RED — Top 1 is dangerous with high confidence
    if top1.confidence >= 60 and top1.category == "dangerous":
        return WarningInfo(
            level="RED",
            color="🔴",
            message="⚠️ 高度危險！此植物極可能有毒，請勿觸碰或食用。",
        )

    # Priority 2: ORANGE — Top 3 has dangerous species with >= 40% confidence
    dangerous_in_top3 = [
        r for r in top3
        if r.category == "dangerous" and r.confidence >= 40
    ]
    if dangerous_in_top3:
        return WarningInfo(
            level="ORANGE",
            color="🟠",
            message="⚠️ 候選結果中有危險物種，請謹慎對待，建議進一步確認。",
        )

    # Priority 3: YELLOW — handled externally via confusion pair check
    # (will be set after confusion pair detection)

    # Priority 4: GREY — all confidence too low
    if top1.confidence < 40:
        return WarningInfo(
            level="GREY",
            color="⚪",
            message="❓ 無法確定此物種，知識庫中未找到高度匹配的紀錄。建議不要食用或觸碰。",
        )

    # Priority 5: GREEN — Top 1 is safe with high confidence
    if top1.confidence >= 60 and top1.category in ("edible", "medicinal"):
        return WarningInfo(
            level="GREEN",
            color="🟢",
            message="✅ 此植物可能可安全使用，但仍建議確認後再行動。",
        )

    # Priority 6: GREY — medium confidence, uncertain
    return WarningInfo(
        level="GREY",
        color="⚪",
        message="❓ 辨識結果信心度不高，建議補充更多照片或特徵資訊。",
    )


def check_confusion_pairs(
    top3: list[ScoreResult],
    confusion_db: dict,
) -> list[ConfusionPairAlert]:
    """
    Plan 8.3: Check if any Top 3 species are in known confusion pairs.
    Also check if a species' confusion partner isn't in Top 3 — still warn.
    """
    alerts = []
    top3_ids = {r.species_id for r in top3}
    pairs = confusion_db.get("confusion_pairs", [])

    for pair in pairs:
        a_id = pair["species_a"]
        b_id = pair["species_b"]

        if a_id in top3_ids or b_id in top3_ids:
            alerts.append(ConfusionPairAlert(
                pair_id=pair.get("id", ""),
                species_a_id=a_id,
                species_b_id=b_id,
                lethality=pair.get("lethality", "unknown"),
                key_differences=pair.get("key_differences", []),
            ))

    return alerts


def process_results(
    top3: list[ScoreResult],
    confusion_db: dict,
    plants: list[dict],
) -> ProcessedResult:
    """
    Full post-processing pipeline. Plan Section 8.

    1. Determine warning level
    2. Check confusion pairs
    3. If confusion found, may upgrade to YELLOW
    4. Handle unknown species (low confidence)
    """
    # Step 1: Warning level
    warning = determine_warning_level(top3)

    # Step 2: Confusion pairs
    confusion_alerts = check_confusion_pairs(top3, confusion_db)

    # Step 3: If confusion found and current warning < YELLOW, upgrade
    if confusion_alerts and warning.level in ("GREEN", "GREY"):
        has_critical = any(a.lethality in ("critical", "high") for a in confusion_alerts)
        if has_critical:
            warning = WarningInfo(
                level="YELLOW",
                color="🟡",
                message="⚠️ 候選結果中有外觀相似的安全/危險物種對，請仔細比對區分特徵。",
            )
        elif confusion_alerts:
            warning = WarningInfo(
                level="YELLOW",
                color="🟡",
                message="⚠️ 候選結果中存在容易混淆的物種，建議進一步確認。",
            )

    # Step 4: Unknown species check
    is_unknown = False
    unknown_message = None
    if top3 and top3[0].confidence < 60:
        is_unknown = True
        unknown_message = (
            "無法確定此物種。根據觀察到的特徵，"
            "這類植物在此地區的知識庫中未有高度匹配的紀錄。"
            "建議不要食用或觸碰。"
        )

    return ProcessedResult(
        top_results=top3,
        warning=warning,
        confusion_alerts=confusion_alerts,
        is_unknown=is_unknown,
        unknown_message=unknown_message,
    )


def format_result_display(
    processed: ProcessedResult,
    plants: list[dict],
) -> str:
    """
    Plan 8.4: Format Top 3 results for display.
    Returns formatted text string.
    """
    lines = []

    # Warning banner
    lines.append(f"{processed.warning.color} {processed.warning.message}")
    lines.append("")

    # Species lookup
    plants_by_id = {sp["id"]: sp for sp in plants}

    rank_emoji = ["🥇", "🥈", "🥉"]

    for i, result in enumerate(processed.top_results):
        emoji = rank_emoji[i] if i < 3 else f"#{i+1}"
        lines.append(f"{emoji} #{i+1} {result.species_name}（信心度 {result.confidence}%）")

        # Category indicator
        cat_map = {
            "dangerous": "⚠️ 有毒！",
            "edible": "🍃 可食用",
            "medicinal": "💊 藥用",
        }
        lines.append(f"   {cat_map.get(result.category, '❓ 未分類')}")

        # Diagnostic features from KB
        sp_data = plants_by_id.get(result.species_id)
        if sp_data and "human_readable" in sp_data:
            hr = sp_data["human_readable"]
            diag = hr.get("diagnostic_features", [])
            if diag:
                lines.append("")
                lines.append("   【知識庫描述 — 請對照實物確認】")
                for feat in diag[:5]:
                    lines.append(f"   ✦ {feat}")

            if result.category == "dangerous":
                tox = hr.get("toxicity", "")
                if tox:
                    lines.append(f"   🚨 毒性：{tox}")


        # Usage / survival info
        if sp_data and "usage" in sp_data:
            usage = sp_data["usage"]
            lines.append("")
            lines.append("   【生存用途資訊】")
            _type_zh = {"edible_leaf": "可食葉", "edible_root": "可食根莖",
                        "edible_fruit": "可食果實", "wound_care": "傷口處理",
                        "anti_inflammatory": "消炎解毒"}
            u_types = usage.get("type", [])
            if u_types:
                _labels = [_type_zh.get(t, t) for t in u_types]
                lines.append(f"   \U0001f4cb 用途分類：{chr(12289).join(_labels)}")
            if usage.get("edible_parts"):
                lines.append(f"   \U0001f33f 可食部位：{chr(12289).join(usage['edible_parts'])}")
            if usage.get("preparation"):
                lines.append(f"   \U0001f52a 處理方式：{usage['preparation']}")
            if usage.get("medicinal_effects"):
                lines.append(f"   \U0001f48a 藥效：{chr(12289).join(usage['medicinal_effects'])}")
            if usage.get("warnings"):
                lines.append(f"   \u26a0\ufe0f 注意：{usage['warnings']}")
        lines.append("")

    # Confusion pair alerts
    if processed.confusion_alerts:
        for alert in processed.confusion_alerts:
            sp_a = plants_by_id.get(alert.species_a_id)
            sp_b = plants_by_id.get(alert.species_b_id)
            name_a = sp_a["common_names"]["zh-TW"] if sp_a else alert.species_a_id
            name_b = sp_b["common_names"]["zh-TW"] if sp_b else alert.species_b_id

            lines.append(f"⚠️ {name_a} 與 {name_b} 是已知混淆物種對！")
            for diff in alert.key_differences:
                lines.append(f"   🔍 {diff.get('test', '')}")
            lines.append("")

    return "\n".join(lines)