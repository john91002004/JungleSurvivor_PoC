#!/usr/bin/env python3
"""
Unit tests for v2 scoring engine and matcher.

Tests Plan sections:
  7.1: Only positive scoring
  7.2: Single value scoring
  7.3: Array scoring with max(|observed|, |kb|) denominator
  7.4: Confidence = score / effective_total
  7.5: Early stopping produces same results as brute force
"""

import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.scoring import (
    score_single,
    score_array,
    score_attribute,
    should_skip,
    score_species,
    compute_effective_total,
)
from app.matcher import load_kb, match_top_n

KB_DIR = PROJECT_ROOT / "knowledge_base" / "east_asia_subtropical"
passed = 0
failed = 0


def check(name, actual, expected, tolerance=0.01):
    global passed, failed
    if isinstance(expected, float):
        ok = abs(actual - expected) < tolerance
    else:
        ok = actual == expected
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed += 1
        print("  [FAIL] %s: expected %s, got %s" % (name, expected, actual))
    else:
        passed += 1


def test_should_skip():
    print("Test: should_skip")
    check("not_visible", should_skip("not_visible"), True)
    check("uncertain", should_skip("uncertain"), True)
    check("not_checkable", should_skip("not_checkable"), True)
    check("None", should_skip(None), True)
    check("empty list", should_skip([]), True)
    check("valid string", should_skip("glossy"), False)
    check("valid list", should_skip(["red", "green"]), False)


def test_score_single():
    print("Test: score_single (Plan 7.2)")
    check("match", score_single("glossy", "glossy", 3), 3.0)
    check("mismatch", score_single("matte", "glossy", 3), 0.0)
    check("not_visible skip", score_single("not_visible", "glossy", 3), 0.0)
    check("uncertain skip", score_single("uncertain", "glossy", 3), 0.0)


def test_score_array():
    print("Test: score_array (Plan 7.3)")

    # Observe 1 of 4, all match -> 1/max(1,4) = 0.25
    check("1_of_4_match",
          score_array(["yellow"], ["yellow", "red", "white", "purple"], 4),
          4 * 1 / 4)  # 1.0

    # Observe 2 of 4, all match -> 2/max(2,4) = 0.5
    check("2_of_4_match",
          score_array(["yellow", "red"], ["yellow", "red", "white", "purple"], 4),
          4 * 2 / 4)  # 2.0

    # Observe 4 of 4, all match -> 4/max(4,4) = 1.0
    check("4_of_4_match",
          score_array(["yellow", "red", "white", "purple"], ["yellow", "red", "white", "purple"], 4),
          4 * 4 / 4)  # 4.0

    # Observe 3, only 2 in KB -> 2/max(3,4) = 0.5
    check("partial_with_extra",
          score_array(["yellow", "red", "blue"], ["yellow", "red", "white", "purple"], 4),
          4 * 2 / 4)  # 2.0

    # Observe 5, only 2 in KB of 2 -> 2/max(5,2) = 0.4
    check("many_extra",
          score_array(["yellow", "red", "blue", "pink", "orange"], ["yellow", "red"], 4),
          4 * 2 / 5)  # 1.6

    # No match -> 0
    check("no_match",
          score_array(["blue", "pink"], ["yellow", "red", "white", "purple"], 4),
          0.0)

    # Empty observed -> skip
    check("empty_observed",
          score_array([], ["yellow", "red"], 4),
          0.0)


def test_no_negative_scoring():
    """Plan 7.1: mismatch should give 0, never negative."""
    print("Test: no_negative_scoring (Plan 7.1)")
    check("single_mismatch_not_negative", score_single("matte", "glossy", 5), 0.0)
    check("array_mismatch_not_negative",
          score_array(["blue"], ["yellow", "red"], 3),
          0.0)


def test_score_species_alocasia():
    """Test scoring against a known species (alocasia_odora / Giant Taro)."""
    print("Test: score_species with alocasia_odora features")
    plants, schema, _ = load_kb(KB_DIR)

    alocasia = next(sp for sp in plants if sp["id"] == "alocasia_odora")

    # Simulate observing features that match alocasia perfectly
    observed = {
        "overall": {
            "growth_form": "herb",
            "height_estimate": "1-2m",
            "habitat": "forest_floor",
            "water_droplet_test": "flat",
        },
        "leaf": {
            "shape": "heart",
            "edge": "entire",
            "colors": ["dark_green"],
            "surface_top": "glossy",
            "size": "very_large_>50cm",
            "arrangement": "clustered",
            "venation": "pinnate",
        },
        "flower": {
            "arrangement": "spathe_spadix",
        },
    }

    result = score_species(observed, alocasia, schema, has_photo=True)
    check("alocasia_score_positive", result.score > 0, True)
    check("alocasia_confidence_reasonable", result.confidence > 30, True)
    check("alocasia_category", result.category, "dangerous")
    print("    Score: %.1f / %.1f = %.1f%%" % (result.score, result.effective_total, result.confidence))


def test_matcher_top3_alocasia():
    """Test that alocasia ranks #1 when observing its exact features."""
    print("Test: matcher top3 with alocasia features")
    plants, schema, _ = load_kb(KB_DIR)

    observed = {
        "overall": {
            "growth_form": "herb",
            "height_estimate": "1-2m",
            "habitat": "forest_floor",
            "water_droplet_test": "flat",
        },
        "leaf": {
            "leaf_type": "simple",
            "shape": "heart",
            "edge": "entire",
            "colors": ["dark_green"],
            "surface_top": "glossy",
            "size": "very_large_>50cm",
            "arrangement": "clustered",
            "venation": "pinnate",
            "texture": "leathery",
            "petiole_attach": "normal",
        },
        "flower": {
            "arrangement": "spathe_spadix",
            "special_shape": "spathe",
        },
    }

    results = match_top_n(observed, plants, schema, has_photo=True, top_n=3)
    check("got_3_results", len(results), 3)
    check("top1_is_alocasia", results[0].species_id, "alocasia_odora")
    check("top1_is_dangerous", results[0].category, "dangerous")

    print("    Top 3:")
    for i, r in enumerate(results):
        print("      #%d %s (%.1f%%) - %s" % (i + 1, r.species_name, r.confidence, r.category))


def test_matcher_taro_with_beading():
    """Test that taro ranks #1 when water_droplet_test=beading is observed."""
    print("Test: matcher top3 with taro features (beading test)")
    plants, schema, _ = load_kb(KB_DIR)

    observed = {
        "overall": {
            "growth_form": "herb",
            "habitat": "wetland",
            "water_droplet_test": "beading",
        },
        "leaf": {
            "shape": "heart",
            "surface_top": "velvety",
            "petiole_attach": "peltate_shield",
        },
    }

    results = match_top_n(observed, plants, schema, has_photo=True, top_n=3)
    check("top1_is_taro", results[0].species_id, "colocasia_esculenta")
    check("top1_is_edible", results[0].category, "edible")

    print("    Top 3:")
    for i, r in enumerate(results):
        print("      #%d %s (%.1f%%) - %s" % (i + 1, r.species_name, r.confidence, r.category))


def test_early_stopping_same_results():
    """Plan 7.5: Early stopping should produce same Top 3 as brute force."""
    print("Test: early_stopping vs brute_force consistency")
    plants, schema, _ = load_kb(KB_DIR)

    observed = {
        "overall": {"growth_form": "herb", "habitat": "forest_floor"},
        "leaf": {"shape": "heart", "colors": ["dark_green"], "surface_top": "glossy"},
    }

    results_es = match_top_n(observed, plants, schema, top_n=3, use_early_stopping=True)
    results_bf = match_top_n(observed, plants, schema, top_n=3, use_early_stopping=False)

    check("same_top1", results_es[0].species_id, results_bf[0].species_id)
    check("same_top2", results_es[1].species_id, results_bf[1].species_id)
    check("same_top3", results_es[2].species_id, results_bf[2].species_id)

    for i in range(3):
        check("same_score_%d" % i, results_es[i].score, results_bf[i].score)


def test_confidence_increases_with_more_features():
    """More matching features should increase confidence."""
    print("Test: confidence increases with more features")
    plants, schema, _ = load_kb(KB_DIR)
    alocasia = next(sp for sp in plants if sp["id"] == "alocasia_odora")

    # Few features
    obs_few = {
        "leaf": {"shape": "heart", "surface_top": "glossy"},
    }
    result_few = score_species(obs_few, alocasia, schema, has_photo=True)

    # Many features
    obs_many = {
        "overall": {"growth_form": "herb", "height_estimate": "1-2m", "habitat": "forest_floor"},
        "leaf": {"shape": "heart", "surface_top": "glossy", "size": "very_large_>50cm",
                 "edge": "entire", "arrangement": "clustered"},
        "flower": {"arrangement": "spathe_spadix"},
    }
    result_many = score_species(obs_many, alocasia, schema, has_photo=True)

    check("more_features_higher_score", result_many.score > result_few.score, True)
    print("    Few features: score=%.1f, conf=%.1f%%" % (result_few.score, result_few.confidence))
    print("    Many features: score=%.1f, conf=%.1f%%" % (result_many.score, result_many.confidence))


def main():
    global passed, failed
    print("=" * 60)
    print("JungleSurvivor v2 Scoring Engine — Unit Tests")
    print("=" * 60)
    print()

    test_should_skip()
    test_score_single()
    test_score_array()
    test_no_negative_scoring()
    test_score_species_alocasia()
    test_matcher_top3_alocasia()
    test_matcher_taro_with_beading()
    test_early_stopping_same_results()
    test_confidence_increases_with_more_features()

    print()
    print("=" * 60)
    total = passed + failed
    print("Results: %d/%d passed, %d failed" % (passed, total, failed))
    print("=" * 60)

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
