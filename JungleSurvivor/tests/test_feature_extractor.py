#!/usr/bin/env python3
"""Unit tests for v2 feature extractor."""

import sys, io, json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.feature_extractor import (
    extract_json,
    validate_and_clean_features,
    parse_llm_response,
    load_schema,
    load_enums,
)

KB_ROOT = PROJECT_ROOT / "knowledge_base"
schema = load_schema(KB_ROOT)
enums = load_enums(KB_ROOT)

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        print("  [FAIL] %s: expected %s, got %s" % (name, expected, actual))


def test_extract_json():
    print("Test: extract_json")
    check("valid_json", extract_json('{"growth_form": "herb"}'), {"growth_form": "herb"})
    check("codeblock", extract_json('```json\n{"growth_form": "herb"}\n```'), {"growth_form": "herb"})
    check("with_text", extract_json('Here is: {"growth_form": "herb"} done'), {"growth_form": "herb"})
    check("no_json", extract_json("no json here"), None)


def test_validate_valid_features():
    print("Test: validate valid features")
    raw = {
        "growth_form": "herb",
        "height_estimate": "1-2m",
        "leaf": {
            "shape": "heart",
            "colors": ["dark_green"],
            "surface_top": "glossy",
        }
    }
    cleaned, warnings = validate_and_clean_features(raw, schema, enums)
    check("has_overall", "overall" in cleaned, True)
    check("has_leaf", "leaf" in cleaned, True)
    check("growth_form", cleaned["overall"]["growth_form"], "herb")
    check("leaf_shape", cleaned["leaf"]["shape"], "heart")
    check("leaf_colors", cleaned["leaf"]["colors"], ["dark_green"])
    check("no_warnings", len(warnings), 0)


def test_validate_invalid_enum():
    print("Test: validate invalid enum value -> uncertain")
    raw = {
        "growth_form": "dinosaur_plant",
        "leaf": {"shape": "star_shape"},
    }
    cleaned, warnings = validate_and_clean_features(raw, schema, enums)
    check("invalid_growth_form", cleaned["overall"]["growth_form"], "uncertain")
    check("invalid_leaf_shape", cleaned["leaf"]["shape"], "uncertain")
    check("has_warnings", len(warnings) >= 2, True)


def test_validate_not_visible():
    print("Test: validate not_visible passthrough")
    raw = {
        "growth_form": "herb",
        "leaf": {"shape": "not_visible", "edge": "uncertain"},
        "flower": {"colors": "not_visible"},
    }
    cleaned, warnings = validate_and_clean_features(raw, schema, enums)
    check("not_visible_passes", cleaned["leaf"]["shape"], "not_visible")
    check("uncertain_passes", cleaned["leaf"]["edge"], "uncertain")


def test_parse_full_llm_response():
    print("Test: parse_llm_response full pipeline")
    response = '''```json
{
  "growth_form": "herb",
  "height_estimate": "<30cm",
  "leaf": {
    "shape": "heart",
    "edge": "entire",
    "colors": ["green", "red_underside"],
    "surface_top": "matte",
    "arrangement": "alternate"
  },
  "stem": {
    "type": "erect",
    "colors": ["purple"]
  },
  "flower": {
    "colors": ["white"],
    "arrangement": "spike"
  }
}
```'''
    result = parse_llm_response(response, schema, enums)
    check("success", result.success, True)
    check("has_features", result.features is not None, True)
    check("leaf_colors", result.features["leaf"]["colors"], ["green", "red_underside"])
    check("stem_colors", result.features["stem"]["colors"], ["purple"])


def test_parse_broken_json():
    print("Test: parse_llm_response with broken JSON")
    response = '{"growth_form": "herb", "leaf": {"shape": "heart"'
    result = parse_llm_response(response, schema, enums)
    check("broken_recovered", result.success, True)
    check("broken_has_leaf", "leaf" in result.features, True)


def main():
    global passed, failed
    print("=" * 60)
    print("JungleSurvivor v2 Feature Extractor — Unit Tests")
    print("=" * 60)
    print()
    test_extract_json()
    test_validate_valid_features()
    test_validate_invalid_enum()
    test_validate_not_visible()
    test_parse_full_llm_response()
    test_parse_broken_json()
    print()
    print("=" * 60)
    print("Results: %d/%d passed, %d failed" % (passed, passed + failed, failed))
    print("=" * 60)
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
