"""
JungleSurvivor v2 — Feature Merger

Implements Plan Section 6:
  - 6.1: Multi-photo feature union merge
  - 6.2: User manual input (final override via tag/chip UI)
  - 6.3: Free text fields preserved as-is
"""

from __future__ import annotations
from typing import Any

SKIP_VALUES = frozenset({"not_visible", "uncertain", "not_checkable"})


def _is_skip(val: Any) -> bool:
    return val is None or (isinstance(val, str) and val in SKIP_VALUES)


def merge_single_values(existing: Any, new: Any) -> Any:
    """
    Merge two single-value attributes. Plan 6.1:
      - not_visible + valid → valid
      - uncertain + definite → definite
      - different definite values → convert to array (both kept)
      - same value → keep single
    """
    if _is_skip(existing):
        return new
    if _is_skip(new):
        return existing
    if existing == new:
        return existing
    # Different values → convert to array
    if isinstance(existing, list):
        if new not in existing:
            return existing + [new]
        return existing
    return [existing, new]


def merge_array_values(existing: Any, new: Any) -> list:
    """
    Merge two array-type attributes. Plan 6.1: take union.
    """
    if existing is None or (isinstance(existing, list) and len(existing) == 0):
        return new if isinstance(new, list) else [new] if new else []
    if new is None or (isinstance(new, list) and len(new) == 0):
        return existing if isinstance(existing, list) else [existing]

    ex_list = existing if isinstance(existing, list) else [existing]
    new_list = new if isinstance(new, list) else [new]

    merged = list(ex_list)
    for v in new_list:
        if v not in merged and not _is_skip(v):
            merged.append(v)
    # Remove skip values if any real values exist
    real_vals = [v for v in merged if not _is_skip(v)]
    return real_vals if real_vals else merged


def merge_features(
    existing: dict,
    new_features: dict,
    schema: dict,
) -> dict:
    """
    Merge new photo features into existing accumulated features.
    Plan 6.1: multi-photo union merge.

    Args:
        existing: accumulated features so far (may be empty {})
        new_features: features from the latest photo
        schema: feature_schema.json content

    Returns:
        merged features dict
    """
    schema_clean = {k: v for k, v in schema.items() if not k.startswith("_")}
    merged = {}

    # Collect all section names from both
    all_sections = set()
    all_sections.update(existing.keys())
    all_sections.update(new_features.keys())

    for section_name in all_sections:
        ex_section = existing.get(section_name, {})
        new_section = new_features.get(section_name, {})
        section_schema = schema_clean.get(section_name, {})

        merged_section = {}
        all_attrs = set()
        all_attrs.update(ex_section.keys())
        all_attrs.update(new_section.keys())

        for attr_name in all_attrs:
            ex_val = ex_section.get(attr_name)
            new_val = new_section.get(attr_name)

            attr_def = section_schema.get(attr_name)
            if attr_def and attr_def["type"] == "array":
                merged_section[attr_name] = merge_array_values(ex_val, new_val)
            elif attr_def and attr_def["type"] == "boolean":
                merged_section[attr_name] = new_val if new_val is not None else ex_val
            else:
                if ex_val is None:
                    merged_section[attr_name] = new_val
                elif new_val is None:
                    merged_section[attr_name] = ex_val
                else:
                    merged_section[attr_name] = merge_single_values(ex_val, new_val)

        if merged_section:
            merged[section_name] = merged_section

    return merged


def apply_user_input(
    features: dict,
    user_features: dict,
) -> dict:
    """
    Apply user manual input. Plan 6.2: user values are the final truth.
    The tag/chip UI means what the user sees is what gets used.

    user_features has the same structure as features.
    Any value present in user_features completely replaces the AI value.
    """
    result = {}
    all_sections = set()
    all_sections.update(features.keys())
    all_sections.update(user_features.keys())

    for section_name in all_sections:
        ai_section = features.get(section_name, {})
        user_section = user_features.get(section_name, {})

        merged_section = dict(ai_section)
        for attr_name, user_val in user_section.items():
            if user_val is not None:
                merged_section[attr_name] = user_val

        if merged_section:
            result[section_name] = merged_section

    return result


def get_feature_summary(features: dict, schema: dict) -> dict:
    """
    Generate a summary of filled vs unfilled features for UI display.
    Returns dict with sections and their completion status.
    """
    schema_clean = {k: v for k, v in schema.items() if not k.startswith("_")}
    summary = {}

    for section_name, section_schema in schema_clean.items():
        section = features.get(section_name, {})
        total = 0
        filled = 0
        missing = []

        for attr_name, attr_def in section_schema.items():
            if attr_def["type"] == "boolean":
                continue
            total += 1
            val = section.get(attr_name)
            if val is not None and not _is_skip(val):
                filled += 1
            else:
                missing.append(attr_name)

        summary[section_name] = {
            "total": total,
            "filled": filled,
            "missing": missing,
        }

    return summary
