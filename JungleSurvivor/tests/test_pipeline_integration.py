#!/usr/bin/env python3
"""Integration test: full v2 pipeline end-to-end."""

import sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline import JungleSurvivorV2

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        print("  [FAIL] %s: expected %s, got %s" % (name, expected, actual))


def test_full_alocasia_flow():
    """Simulate: Photo → Extract → Identify → Warning."""
    print("Test: Full alocasia identification flow")
    p = JungleSurvivorV2()

    # Photo 1: LLM returns features
    llm_response = '''{
        "growth_form": "herb",
        "height_estimate": "1-2m",
        "habitat": "forest_floor",
        "leaf": {
            "shape": "heart",
            "edge": "entire",
            "colors": ["dark_green"],
            "surface_top": "glossy",
            "size": "very_large_>50cm",
            "arrangement": "clustered",
            "venation": "pinnate",
            "texture": "leathery",
            "petiole_attach": "normal"
        },
        "stem": {
            "type": "erect",
            "colors": ["green"]
        }
    }'''

    result = p.extract_features_from_response(llm_response)
    check("extraction_success", result.success, True)
    check("photo_count_1", p.state.photo_count, 1)

    # Photo 2: flower close-up
    llm_response2 = '''{
        "flower": {
            "arrangement": "spathe_spadix",
            "special_shape": "spathe",
            "colors": ["yellow", "green"]
        }
    }'''
    result2 = p.extract_features_from_response(llm_response2)
    check("extraction2_success", result2.success, True)
    check("photo_count_2", p.state.photo_count, 2)

    # Check merged features
    features = p.get_current_features()
    check("leaf_preserved", features["leaf"]["shape"], "heart")
    check("flower_added", features["flower"]["arrangement"], "spathe_spadix")

    # Identify
    processed = p.identify(top_n=3)
    check("has_results", len(processed.top_results) > 0, True)
    check("top1_is_alocasia", processed.top_results[0].species_id, "alocasia_odora")

    display = p.format_display()
    check("display_has_warning", len(display) > 0, True)
    print("    Top 1:", processed.top_results[0].species_name,
          "confidence:", processed.top_results[0].confidence)


def test_user_override_flow():
    """Simulate: Photo → User adds smell → Identify."""
    print("Test: User override flow")
    p = JungleSurvivorV2()

    llm_response = '''{
        "growth_form": "herb",
        "height_estimate": "<30cm",
        "leaf": {
            "shape": "heart",
            "colors": ["green", "red_underside"],
            "arrangement": "alternate"
        },
        "stem": {
            "colors": ["purple"]
        }
    }'''

    p.extract_features_from_response(llm_response)

    # User manually adds smell (not visible in photo)
    p.set_user_feature("overall", "smell", "fishy")

    features = p.get_current_features()
    check("user_smell_applied", features["overall"]["smell"], "fishy")

    processed = p.identify(top_n=3)
    check("houttuynia_in_results",
          any(r.species_id == "houttuynia_cordata" for r in processed.top_results),
          True)
    print("    Top 1:", processed.top_results[0].species_name,
          "confidence:", processed.top_results[0].confidence)


def test_taro_with_water_test():
    """Simulate: Photo + user water droplet test → must distinguish taro from alocasia."""
    print("Test: Taro vs Alocasia with water test")
    p = JungleSurvivorV2()

    llm_response = '''{
        "growth_form": "herb",
        "leaf": {
            "shape": "heart",
            "colors": ["green"],
            "surface_top": "velvety",
            "petiole_attach": "peltate_shield",
            "size": "large_15-50cm"
        }
    }'''
    p.extract_features_from_response(llm_response)
    p.set_user_feature("overall", "water_droplet_test", "beading")

    processed = p.identify(top_n=3)
    check("top1_is_taro", processed.top_results[0].species_id, "colocasia_esculenta")

    # Check confusion pair detected
    check("confusion_detected", len(processed.confusion_alerts) >= 1, True)
    if processed.confusion_alerts:
        print("    Confusion alert:", processed.confusion_alerts[0].pair_id)

    display = p.format_display()
    check("display_has_confusion", "混淆" in display, True)


def test_reset():
    """Test reset functionality."""
    print("Test: Reset session")
    p = JungleSurvivorV2()
    p.extract_features_from_response('{"growth_form": "herb"}')
    check("has_features", len(p.get_current_features()) > 0, True)

    p.reset()
    check("reset_features", len(p.get_current_features()), 0)
    check("reset_photo_count", p.state.photo_count, 0)


def main():
    global passed, failed
    print("=" * 60)
    print("JungleSurvivor v2 — Integration Tests")
    print("=" * 60)
    print()
    test_full_alocasia_flow()
    test_user_override_flow()
    test_taro_with_water_test()
    test_reset()
    print()
    print("=" * 60)
    print("Results: %d/%d passed, %d failed" % (passed, passed + failed, failed))
    print("=" * 60)
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
