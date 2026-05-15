"""
JungleSurvivor v2 — LLM Feature Extractor

Implements Plan Section 5:
  - 5.1: LLM only does "fill in the blanks" from photo
  - 5.2: Per-photo extraction with immediate feedback
  - 5.3: Prompt template auto-generated from KB enums
  - 5.4: JSON validation + error tolerance
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional


SKIP_VALUES = frozenset({"not_visible", "uncertain", "not_checkable"})

_ZH_STRIP_RE = re.compile(r'^([a-zA-Z0-9_<>.\-]+)\(.*\)$')

def _strip_zh_annotation(val: str) -> str:
    """Strip Chinese annotation from values like 'glossy(光滑反光(像打蠟))' → 'glossy'."""
    m = _ZH_STRIP_RE.match(val)
    return m.group(1) if m else val


@dataclass
class ExtractionResult:
    raw_response: str
    features: Optional[dict]
    success: bool
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


def load_prompt_template(kb_root: Path) -> str:
    """Load the auto-generated prompt template from KB."""
    template_path = kb_root / "prompt_template.txt"
    with open(template_path, encoding="utf-8") as f:
        return f.read()


def load_enums(kb_root: Path) -> dict:
    """Load derived enum definitions from KB."""
    enums_path = kb_root / "derived_enums.json"
    with open(enums_path, encoding="utf-8") as f:
        return json.load(f)


def load_schema(kb_root: Path) -> dict:
    """Load feature schema from KB."""
    schema_path = kb_root / "feature_schema.json"
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


# ── JSON Extraction (reusing v1 repair logic) ──

def _extract_json_from_codeblock(text: str) -> Optional[str]:
    m = re.search(r'```(?:json)?\s*\n?([\s\S]*?)```', text)
    if m:
        return m.group(1).strip()
    m = re.search(r'```(?:json)?\s*\n?([\s\S]+)', text)
    if m:
        return m.group(1).strip()
    return None


def _extract_json_fallback(text: str) -> Optional[str]:
    start = text.find('{')
    if start < 0:
        return None
    candidate = text[start:]
    end = candidate.rfind('}')
    if end >= 0:
        return candidate[:end + 1].strip()
    return candidate.strip()


def _repair_truncated_json(json_str: str) -> Optional[str]:
    candidate = json_str.rstrip()
    while candidate.endswith(',') or candidate.endswith(':'):
        candidate = candidate[:-1].rstrip()

    opens = candidate.count('{') - candidate.count('}')
    brackets = candidate.count('[') - candidate.count(']')

    if opens <= 0 and brackets <= 0:
        return None

    candidate += ']' * max(0, brackets) + '}' * max(0, opens)
    return candidate


def _try_parse(json_str: str) -> Optional[dict]:
    clean = json_str.strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    repaired = _repair_truncated_json(clean)
    if repaired:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        cleaned = re.sub(r',\s*([}\]])', r'\1', repaired)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    cleaned = re.sub(r',\s*([}\]])', r'\1', clean)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    return None


def extract_json(text: str) -> Optional[dict]:
    """Extract JSON from LLM response using multiple strategies."""
    for extractor in [_extract_json_from_codeblock, _extract_json_fallback]:
        candidate = extractor(text)
        if candidate:
            result = _try_parse(candidate)
            if result:
                return result
    return None


# ── Feature Validation ──

def validate_and_clean_features(
    raw_features: dict,
    schema: dict,
    enums: dict,
) -> tuple[dict, list[str]]:
    """
    Validate LLM-extracted features against schema.
    Plan 5.4: invalid values → "uncertain", missing sections → skip.
    Returns cleaned features dict and list of warnings.
    """
    cleaned = {}
    warnings = []
    schema_clean = {k: v for k, v in schema.items() if not k.startswith("_")}

    # Top-level overall features may be mixed with nested sections
    overall_raw = {}
    sections_raw = {}
    for key, val in raw_features.items():
        if key in schema_clean and key != "overall":
            if isinstance(val, dict):
                sections_raw[key] = val
            else:
                warnings.append(f"Section '{key}' expected dict, got {type(val).__name__}")
        elif key in schema_clean.get("overall", {}):
            overall_raw[key] = val
        elif key == "overall" and isinstance(val, dict):
            overall_raw.update(val)
        else:
            overall_raw[key] = val

    # Process overall section
    if overall_raw:
        sections_raw["overall"] = overall_raw

    for section_name, section_schema in schema_clean.items():
        raw_section = sections_raw.get(section_name)
        if raw_section is None:
            continue

        cleaned_section = {}
        section_enums = enums.get(section_name, {})

        for attr_name, attr_def in section_schema.items():
            raw_val = raw_section.get(attr_name)
            if raw_val is None:
                continue

            attr_type = attr_def["type"]
            valid_values = section_enums.get(attr_name, attr_def.get("values", []))
            valid_strs = [str(v) for v in valid_values]

            if attr_type == "boolean":
                if isinstance(raw_val, bool):
                    cleaned_section[attr_name] = raw_val
                elif str(raw_val).lower() in ("true", "false"):
                    cleaned_section[attr_name] = str(raw_val).lower() == "true"
            elif attr_type == "array":
                if isinstance(raw_val, str):
                    raw_val = [raw_val]
                if isinstance(raw_val, list):
                    valid_items = []
                    for item in raw_val:
                        s = _strip_zh_annotation(str(item))
                        if s in valid_strs:
                            valid_items.append(s)
                        elif s not in SKIP_VALUES:
                            warnings.append(
                                f"{section_name}.{attr_name}: '{s}' not in enum, dropped"
                            )
                    if valid_items:
                        cleaned_section[attr_name] = valid_items
            else:  # single
                s = _strip_zh_annotation(str(raw_val))
                if s in valid_strs:
                    cleaned_section[attr_name] = s
                elif s in SKIP_VALUES:
                    cleaned_section[attr_name] = s
                else:
                    cleaned_section[attr_name] = "uncertain"
                    warnings.append(
                        f"{section_name}.{attr_name}: '{s}' not in enum, set to 'uncertain'"
                    )

        if cleaned_section:
            cleaned[section_name] = cleaned_section

    # Enforce photo_observable constraints:
    # Attributes that cannot be determined from photos are forced to "not_checkable"
    # regardless of what the LLM outputs. User manual input bypasses this function.
    for section_name, section_schema in schema_clean.items():
        if section_name not in cleaned:
            continue
        for attr_name, attr_def in section_schema.items():
            if attr_def.get("photo_observable", True):
                continue
            if attr_name not in cleaned[section_name]:
                continue
            val = cleaned[section_name][attr_name]
            if val not in ("not_checkable", "not_visible", "uncertain"):
                cleaned[section_name][attr_name] = "not_checkable"
                warnings.append(
                    f"{section_name}.{attr_name}: '{val}' → 'not_checkable' (non-photo attribute)"
                )

    # If a section has visible=false, strip all other attributes from that section.
    # The LLM may hallucinate features for parts it cannot see.
    for section_name in list(cleaned.keys()):
        section = cleaned[section_name]
        if section.get("visible") is False:
            kept = {"visible": False}
            removed = [k for k in section if k != "visible"]
            if removed:
                warnings.append(
                    f"{section_name}: visible=false, removed hallucinated attrs: {removed}"
                )
            cleaned[section_name] = kept

    return cleaned, warnings


def parse_llm_response(
    response: str,
    schema: dict,
    enums: dict,
) -> ExtractionResult:
    """
    Full pipeline: extract JSON → validate → clean features.
    """
    raw_json = extract_json(response)
    if raw_json is None:
        return ExtractionResult(
            raw_response=response,
            features=None,
            success=False,
            error="無法從 LLM 回應中提取 JSON",
        )

    features, warnings = validate_and_clean_features(raw_json, schema, enums)

    if not features:
        return ExtractionResult(
            raw_response=response,
            features=None,
            success=False,
            error="JSON 提取成功但無有效特徵",
            warnings=warnings,
        )

    return ExtractionResult(
        raw_response=response,
        features=features,
        success=True,
        warnings=warnings,
    )
