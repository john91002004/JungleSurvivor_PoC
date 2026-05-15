#!/usr/bin/env python3
"""Unit tests for v2 post-processor."""

import sys, io, json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.scoring import ScoreResult
from app.postprocessor import (
    determine_warning_level,
    check_confusion_pairs,
    process_results,
    format_result_display,
)
from app.matcher import load_kb

KB_DIR = PROJECT_ROOT / "knowledge_base" / "east_asia_subtropical"
plants, schema, confusion_db = load_kb(KB_DIR)

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        print("  [FAIL] %s: expected %s, got %s" % (name, expected, actual))


def make_result(sid, name, cat, conf, danger=None):
    return ScoreResult(
        species_id=sid, species_name=name, category=cat,
        danger_level=danger, score=conf * 0.8, effective_total=80.0,
        confidence=conf,
    )


def test_warning_red():
    """Plan 8.1 Priority 1: Top 1 dangerous + high confidence → RED."""
    print("Test: warning RED")
    top3 = [
        make_result("alocasia_odora", "姑婆芋", "dangerous", 75.0, "high"),
        make_result("colocasia_esculenta", "芋頭", "edible", 60.0),
        make_result("plantago_major", "車前草", "medicinal", 30.0),
    ]
    w = determine_warning_level(top3)
    check("red_level", w.level, "RED")


def test_warning_orange():
    """Plan 8.1 Priority 2: Dangerous in top3 with >= 40%."""
    print("Test: warning ORANGE")
    top3 = [
        make_result("colocasia_esculenta", "芋頭", "edible", 55.0),
        make_result("alocasia_odora", "姑婆芋", "dangerous", 45.0, "high"),
        make_result("plantago_major", "車前草", "medicinal", 30.0),
    ]
    w = determine_warning_level(top3)
    check("orange_level", w.level, "ORANGE")


def test_warning_green():
    """Plan 8.1 Priority 5: Safe top 1 with high confidence."""
    print("Test: warning GREEN")
    top3 = [
        make_result("colocasia_esculenta", "芋頭", "edible", 80.0),
        make_result("asplenium_nidus", "山蘇", "edible", 40.0),
        make_result("plantago_major", "車前草", "medicinal", 20.0),
    ]
    w = determine_warning_level(top3)
    check("green_level", w.level, "GREEN")


def test_warning_grey_low_conf():
    """Plan 8.1 Priority 4: All low confidence → GREY."""
    print("Test: warning GREY low confidence")
    top3 = [
        make_result("colocasia_esculenta", "芋頭", "edible", 25.0),
        make_result("asplenium_nidus", "山蘇", "edible", 20.0),
        make_result("plantago_major", "車前草", "medicinal", 15.0),
    ]
    w = determine_warning_level(top3)
    check("grey_level", w.level, "GREY")


def test_warning_priority_order():
    """RED must take priority over everything else."""
    print("Test: warning priority order")
    top3 = [
        make_result("alocasia_odora", "姑婆芋", "dangerous", 80.0, "high"),
        make_result("colocasia_esculenta", "芋頭", "edible", 70.0),
        make_result("asplenium_nidus", "山蘇", "edible", 60.0),
    ]
    w = determine_warning_level(top3)
    check("priority_red_wins", w.level, "RED")


def test_confusion_detection():
    """Plan 8.3: Detect confusion pairs in top 3."""
    print("Test: confusion pair detection")
    top3 = [
        make_result("alocasia_odora", "姑婆芋", "dangerous", 70.0),
        make_result("colocasia_esculenta", "芋頭", "edible", 60.0),
        make_result("plantago_major", "車前草", "medicinal", 30.0),
    ]
    alerts = check_confusion_pairs(top3, confusion_db)
    check("found_alocasia_taro_pair", len(alerts) >= 1, True)
    if alerts:
        check("pair_species_a", alerts[0].species_a_id, "alocasia_odora")
        check("pair_species_b", alerts[0].species_b_id, "colocasia_esculenta")
        check("pair_has_tests", len(alerts[0].key_differences) >= 2, True)


def test_confusion_upgrades_to_yellow():
    """Plan 8.1 Priority 3: Confusion pair → YELLOW."""
    print("Test: confusion upgrades to YELLOW")
    top3 = [
        make_result("colocasia_esculenta", "芋頭", "edible", 80.0),
        make_result("alocasia_odora", "姑婆芋", "dangerous", 30.0),
        make_result("plantago_major", "車前草", "medicinal", 20.0),
    ]
    result = process_results(top3, confusion_db, plants)
    check("yellow_from_confusion", result.warning.level, "YELLOW")


def test_full_processing():
    """Full pipeline test."""
    print("Test: full processing pipeline")
    top3 = [
        make_result("alocasia_odora", "姑婆芋", "dangerous", 75.0, "high"),
        make_result("colocasia_esculenta", "芋頭", "edible", 60.0),
        make_result("asplenium_nidus", "山蘇", "edible", 30.0),
    ]
    result = process_results(top3, confusion_db, plants)
    check("processing_red", result.warning.level, "RED")
    check("has_confusion_alerts", len(result.confusion_alerts) >= 1, True)

    display = format_result_display(result, plants)
    check("display_has_warning", "危險" in display, True)
    check("display_has_top1", "姑婆芋" in display, True)
    check("display_has_confusion", "混淆" in display, True)
    print()
    print("--- Sample output ---")
    print(display[:600])
    print("--- End sample ---")


def main():
    global passed, failed
    print("=" * 60)
    print("JungleSurvivor v2 Post-processor — Unit Tests")
    print("=" * 60)
    print()
    test_warning_red()
    test_warning_orange()
    test_warning_green()
    test_warning_grey_low_conf()
    test_warning_priority_order()
    test_confusion_detection()
    test_confusion_upgrades_to_yellow()
    test_full_processing()
    print()
    print("=" * 60)
    print("Results: %d/%d passed, %d failed" % (passed, passed + failed, failed))
    print("=" * 60)
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
