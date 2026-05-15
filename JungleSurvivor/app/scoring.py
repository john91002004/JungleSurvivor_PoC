"""
JungleSurvivor v2 — Scoring Engine

Implements the deterministic scoring algorithm from Plan Section 7:
  - 7.1: Only positive scoring (match → +weight, mismatch → 0)
  - 7.2: Single-value scoring
  - 7.3: Array scoring with max(|observed|, |kb|) denominator
  - 7.4: Confidence = score / effective_total
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


SKIP_VALUES = frozenset({"not_visible", "uncertain", "not_checkable"})


@dataclass
class ScoreResult:
    species_id: str
    species_name: str
    category: str
    danger_level: str | None
    score: float
    effective_total: float
    confidence: float  # 0-100
    matched_features: list[dict] = field(default_factory=list)


def should_skip(value: Any) -> bool:
    """Check if an observed value should be skipped (not_visible, uncertain, etc.)."""
    if value is None:
        return True
    if isinstance(value, str) and value in SKIP_VALUES:
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def score_single(observed_value: str, kb_value: str, weight: int) -> float:
    """Score a single-value attribute. Plan 7.2."""
    if should_skip(observed_value):
        return 0.0
    if observed_value == kb_value:
        return float(weight)
    return 0.0


def score_array(observed_values: list[str], kb_values: list[str], weight: int) -> float:
    """
    Score an array-type attribute. Plan 7.3.
    Formula: weight * |intersection| / max(|observed|, |kb|)
    """
    if should_skip(observed_values) or not kb_values:
        return 0.0

    obs_set = set(observed_values)
    kb_set = set(kb_values)
    intersection = obs_set & kb_set
    denominator = max(len(obs_set), len(kb_set))

    if denominator == 0:
        return 0.0

    return weight * len(intersection) / denominator


def score_attribute(observed_value: Any, kb_value: Any, weight: int, attr_type: str) -> float:
    """Score a single attribute based on its type."""
    if attr_type == "array":
        obs = observed_value if isinstance(observed_value, list) else [observed_value]
        kb = kb_value if isinstance(kb_value, list) else [kb_value]
        return score_array(obs, kb, weight)
    elif attr_type == "boolean":
        return 0.0
    else:
        return score_single(str(observed_value), str(kb_value), weight)


def compute_effective_total(
    schema: dict,
    observed_features: dict,
    species_features: dict,
    has_photo: bool = True,
) -> float:
    """
    Compute effective_total for confidence calculation. Plan 7.4.

    effective_total = sum of weights for:
      - All photo_observable attributes (if photo uploaded)
      - All non-photo attributes that user manually provided
    """
    total = 0.0
    schema_clean = {k: v for k, v in schema.items() if not k.startswith("_")}

    for section_name, section_schema in schema_clean.items():
        sp_section = species_features.get(section_name)
        if sp_section is None:
            continue

        obs_section = observed_features.get(section_name, {})

        for attr_name, attr_def in section_schema.items():
            if attr_def["type"] == "boolean":
                continue

            sp_attr = sp_section.get(attr_name)
            if sp_attr is None:
                continue

            is_photo_obs = attr_def.get("photo_observable", True)
            obs_value = obs_section.get(attr_name)

            if is_photo_obs and has_photo:
                total += sp_attr.get("weight", 1)
            elif not is_photo_obs and obs_value is not None and not should_skip(obs_value):
                total += sp_attr.get("weight", 1)

    return total


def score_species(
    observed_features: dict,
    species: dict,
    schema: dict,
    has_photo: bool = True,
) -> ScoreResult:
    """
    Score a single species against observed features.
    Returns ScoreResult with score, effective_total, and confidence.
    """
    sp_features = species["features"]
    schema_clean = {k: v for k, v in schema.items() if not k.startswith("_")}

    score = 0.0
    matched = []

    for section_name, section_schema in schema_clean.items():
        sp_section = sp_features.get(section_name)
        if sp_section is None:
            continue

        obs_section = observed_features.get(section_name, {})

        for attr_name, attr_def in section_schema.items():
            if attr_def["type"] == "boolean":
                continue

            sp_attr = sp_section.get(attr_name)
            if sp_attr is None:
                continue

            obs_value = obs_section.get(attr_name)
            if should_skip(obs_value):
                continue

            kb_value = sp_attr["value"]
            weight = sp_attr.get("weight", 1)

            attr_score = score_attribute(obs_value, kb_value, weight, attr_def["type"])
            score += attr_score

            if attr_score > 0:
                matched.append({
                    "section": section_name,
                    "attribute": attr_name,
                    "observed": obs_value,
                    "kb_value": kb_value,
                    "score": attr_score,
                    "weight": weight,
                })

    effective_total = compute_effective_total(schema, observed_features, sp_features, has_photo)
    confidence = (score / effective_total * 100) if effective_total > 0 else 0.0

    return ScoreResult(
        species_id=species["id"],
        species_name=species.get("common_names", {}).get("zh-TW", species["id"]),
        category=species.get("category", "unknown"),
        danger_level=species.get("danger_level"),
        score=score,
        effective_total=effective_total,
        confidence=round(confidence, 1),
        matched_features=matched,
    )
