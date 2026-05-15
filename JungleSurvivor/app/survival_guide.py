"""
JungleSurvivor v2 — Region-Aware Survival Guide

Implements Plan Section 18:
  - Dynamic survival guide pages that pull edible/medicinal plants from KB
  - Filtered by usage type (wound_care, edible_leaf, edible_fruit, etc.)
  - Deep linking to plant identification
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GuidePlant:
    species_id: str
    name_zh: str
    name_en: str
    usage_types: list[str]
    edible_parts: list[str]
    preparation: str
    medicinal_effects: list[str]
    warnings: str
    diagnostic_features: list[str]


@dataclass
class GuideSection:
    title: str
    description: str
    usage_filter: list[str]
    plants: list[GuidePlant] = field(default_factory=list)


# Guide section definitions
GUIDE_SECTIONS = [
    GuideSection(
        title="🩹 傷口處理 — 可用藥草",
        description="以下植物在本地區常見，傳統上用於傷口處理。搗碎鮮葉外敷或水煎清洗。\n⚠️ 嚴重傷口請優先使用急救包。",
        usage_filter=["wound_care"],
    ),
    GuideSection(
        title="🍃 可食葉類 — 野菜",
        description="以下植物的嫩葉可食用。採集時注意避免與有毒植物混淆。",
        usage_filter=["edible_leaf"],
    ),
    GuideSection(
        title="🫐 可食果實",
        description="以下植物的果實可食用。注意成熟度和正確辨識。",
        usage_filter=["edible_fruit"],
    ),
    GuideSection(
        title="🥔 可食根莖",
        description="以下植物的地下部分可食用。多數需要煮熟。",
        usage_filter=["edible_root"],
    ),
    GuideSection(
        title="💊 消炎/解毒",
        description="以下植物傳統上用於消炎解毒。民俗用法，非醫學建議。",
        usage_filter=["anti_inflammatory"],
    ),
]


def build_guide_from_kb(plants: list[dict]) -> list[GuideSection]:
    """
    Build survival guide sections from KB species data.
    Plan 18: dynamically pull plants based on usage tags.
    """
    sections = []

    for template in GUIDE_SECTIONS:
        section = GuideSection(
            title=template.title,
            description=template.description,
            usage_filter=template.usage_filter,
        )

        for sp in plants:
            usage = sp.get("usage")
            if not usage:
                continue

            usage_types = usage.get("type", [])
            if not any(ut in usage_types for ut in template.usage_filter):
                continue

            hr = sp.get("human_readable", {})
            section.plants.append(GuidePlant(
                species_id=sp["id"],
                name_zh=sp["common_names"].get("zh-TW", sp["id"]),
                name_en=sp["common_names"].get("en", ""),
                usage_types=usage_types,
                edible_parts=usage.get("edible_parts", []),
                preparation=usage.get("preparation", ""),
                medicinal_effects=usage.get("medicinal_effects", []),
                warnings=usage.get("warnings", ""),
                diagnostic_features=hr.get("diagnostic_features", []),
            ))

        if section.plants:
            sections.append(section)

    return sections


def format_guide_markdown(sections: list[GuideSection]) -> str:
    """Format guide sections as markdown for display."""
    lines = ["# 🌿 區域生存指南 — 台灣亞熱帶", ""]

    for section in sections:
        lines.append(f"## {section.title}")
        lines.append(f"_{section.description}_")
        lines.append("")

        for plant in section.plants:
            lines.append(f"### {plant.name_zh} ({plant.name_en})")

            if plant.edible_parts:
                lines.append(f"**可用部位**: {', '.join(plant.edible_parts)}")
            if plant.medicinal_effects:
                lines.append(f"**藥效**: {', '.join(plant.medicinal_effects)}")
            if plant.preparation:
                lines.append(f"**處理方式**: {plant.preparation}")

            if plant.diagnostic_features:
                lines.append("**辨識要點**:")
                for feat in plant.diagnostic_features[:3]:
                    lines.append(f"  - {feat}")

            if plant.warnings:
                lines.append(f"⚠️ **注意**: {plant.warnings}")

            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
