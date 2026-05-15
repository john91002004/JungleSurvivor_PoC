#!/usr/bin/env python3
"""Unit tests for v2 feature merger."""

import sys, io, json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.feature_merger import merge_single_values, merge_array_values, merge_features, apply_user_input
from app.feature_extractor import load_schema

KB_ROOT = PROJECT_ROOT / "knowledge_base"
schema = load_schema(KB_ROOT)

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        print("  [FAIL] %s: expected %s, got %s" % (name, expected, actual))


def test_merge_single():
    print("Test: merge_single_values (Plan 6.1)")
    check("not_visible+valid", merge_single_values("not_visible", "glossy"), "glossy")
    check("valid+not_visible", merge_single_values("glossy", "not_visible"), "glossy")
    check("uncertain+valid", merge_single_values("uncertain", "matte"), "matte")
    check("same_value", merge_single_values("glossy", "glossy"), "glossy")
    check("different_values", merge_single_values("heart", "arrow"), ["heart", "arrow"])
    check("not_visible+not_visible", merge_single_values("not_visible", "not_visible"), "not_visible")
    check("none+valid", merge_single_values(None, "glossy"), "glossy")
    check("valid+none", merge_single_values("glossy", None), "glossy")


def test_merge_array():
    print("Test: merge_array_values (Plan 6.1 union)")
    check("union_basic",
          merge_array_values(["yellow"], ["red", "white"]),
          ["yellow", "red", "white"])
    check("union_overlap",
          merge_array_values(["yellow", "red"], ["red", "white"]),
          ["yellow", "red", "white"])
    check("empty+valid", merge_array_values([], ["red"]), ["red"])
    check("valid+empty", merge_array_values(["red"], []), ["red"])
    check("none+valid", merge_array_values(None, ["red"]), ["red"])


def test_merge_features_two_photos():
    """Plan 6.1: Photo 1 + Photo 2 merge."""
    print("Test: merge_features two photos")
    photo1 = {
        "leaf": {
            "shape": "heart",
            "colors": ["dark_green"],
            "surface_top": "glossy",
        },
        "flower": {
            "colors": ["yellow"],
        },
    }
    photo2 = {
        "leaf": {
            "shape": "heart",
            "colors": ["dark_green", "purple"],
            "arrangement": "clustered",
        },
        "flower": {
            "colors": ["red", "yellow"],
        },
    }
    merged = merge_features(photo1, photo2, schema)
    check("leaf_shape_same", merged["leaf"]["shape"], "heart")
    check("leaf_colors_union", merged["leaf"]["colors"], ["dark_green", "purple"])
    check("leaf_surface_kept", merged["leaf"]["surface_top"], "glossy")
    check("leaf_arrangement_new", merged["leaf"]["arrangement"], "clustered")
    check("flower_colors_union", merged["flower"]["colors"], ["yellow", "red"])


def test_merge_conflicting_single():
    """Plan 6.1: Different single values → array."""
    print("Test: merge conflicting single values")
    photo1 = {"leaf": {"shape": "heart"}}
    photo2 = {"leaf": {"shape": "arrow"}}
    merged = merge_features(photo1, photo2, schema)
    check("conflict_to_array", merged["leaf"]["shape"], ["heart", "arrow"])


def test_merge_not_visible_recovery():
    """Plan 6.1: not_visible + visible → visible."""
    print("Test: merge not_visible recovery")
    photo1 = {"leaf": {"shape": "not_visible"}, "flower": {"colors": ["not_visible"]}}
    photo2 = {"leaf": {"shape": "heart"}, "flower": {"colors": ["white"]}}
    merged = merge_features(photo1, photo2, schema)
    check("not_visible_recovery", merged["leaf"]["shape"], "heart")
    check("flower_color_recovery", merged["flower"]["colors"], ["white"])


def test_apply_user_input():
    """Plan 6.2: User input overrides AI."""
    print("Test: apply_user_input (Plan 6.2)")
    ai_features = {
        "leaf": {
            "shape": "heart",
            "colors": ["dark_green"],
            "surface_top": "glossy",
        },
    }
    user_features = {
        "leaf": {
            "colors": ["dark_green", "purple"],
            "surface_top": "velvety",
        },
        "overall": {
            "smell": "fishy",
        },
    }
    result = apply_user_input(ai_features, user_features)
    check("user_overrides_colors", result["leaf"]["colors"], ["dark_green", "purple"])
    check("user_overrides_surface", result["leaf"]["surface_top"], "velvety")
    check("ai_kept_shape", result["leaf"]["shape"], "heart")
    check("user_adds_smell", result["overall"]["smell"], "fishy")


def main():
    global passed, failed
    print("=" * 60)
    print("JungleSurvivor v2 Feature Merger — Unit Tests")
    print("=" * 60)
    print()
    test_merge_single()
    test_merge_array()
    test_merge_features_two_photos()
    test_merge_conflicting_single()
    test_merge_not_visible_recovery()
    test_apply_user_input()
    print()
    print("=" * 60)
    print("Results: %d/%d passed, %d failed" % (passed, passed + failed, failed))
    print("=" * 60)
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
