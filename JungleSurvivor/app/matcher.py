"""
JungleSurvivor v2 — Species Matcher with Early Stopping

Implements Plan Section 7.5: Branch-and-bound pruning.
Compares observed features against all KB species and returns Top N.
"""

from __future__ import annotations
import heapq
import json
from pathlib import Path
from typing import Any

from .scoring import ScoreResult, score_species, should_skip, score_attribute, compute_effective_total


def load_kb(kb_dir: str | Path) -> tuple[list[dict], dict, dict]:
    """Load plants, schema, and confusion pairs from KB directory."""
    kb_dir = Path(kb_dir)
    v2_root = kb_dir.parent if kb_dir.name != "v2" else kb_dir

    with open(v2_root / "feature_schema.json", encoding="utf-8") as f:
        schema = json.load(f)

    region_dir = kb_dir if (kb_dir / "plants.json").exists() else kb_dir / "east_asia_subtropical"
    with open(region_dir / "plants.json", encoding="utf-8") as f:
        plants = json.load(f)

    pairs_path = region_dir / "confusion_pairs.json"
    if pairs_path.exists():
        with open(pairs_path, encoding="utf-8") as f:
            confusion = json.load(f)
    else:
        confusion = {"confusion_pairs": []}

    return plants, schema, confusion


def match_top_n(
    observed_features: dict,
    plants: list[dict],
    schema: dict,
    has_photo: bool = True,
    top_n: int = 3,
    use_early_stopping: bool = True,
) -> list[ScoreResult]:
    """
    Match observed features against all species in KB, return Top N.

    Uses Early Stopping (Plan 7.5): if remaining max possible score
    cannot beat current Nth best, skip that species early.
    """
    schema_clean = {k: v for k, v in schema.items() if not k.startswith("_")}

    if not use_early_stopping:
        results = []
        for species in plants:
            result = score_species(observed_features, species, schema, has_photo)
            results.append(result)
        results.sort(key=lambda r: (-r.score, -r.confidence, r.species_id))
        return results[:top_n]

    # Early stopping version
    # min-heap of (score, tiebreak, result) — keeps track of the current top N scores
    # tiebreak uses (-confidence, species_id) to match brute-force sort
    top_heap: list[tuple[float, float, str, ScoreResult]] = []
    min_top_score = 0.0

    for idx, species in enumerate(plants):
        sp_features = species["features"]

        # Collect all scorable attributes and their max possible contribution
        attrs_to_score = []
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

                weight = sp_attr.get("weight", 1)
                attrs_to_score.append((section_name, attr_name, attr_def, sp_attr, obs_value, weight))

        total_possible = sum(a[5] for a in attrs_to_score)

        # If total possible cannot beat current min_top_score, skip entirely
        if len(top_heap) >= top_n and total_possible < min_top_score:
            continue

        # Score with early stopping
        score = 0.0
        compared_weight = 0.0
        pruned = False

        for section_name, attr_name, attr_def, sp_attr, obs_value, weight in attrs_to_score:
            attr_score = score_attribute(obs_value, sp_attr["value"], weight, attr_def["type"])
            score += attr_score
            compared_weight += weight
            remaining_max = total_possible - compared_weight

            if len(top_heap) >= top_n and (score + remaining_max) < min_top_score:
                pruned = True
                break

        if pruned:
            continue

        effective_total = compute_effective_total(schema, observed_features, sp_features, has_photo)
        confidence = (score / effective_total * 100) if effective_total > 0 else 0.0

        result = ScoreResult(
            species_id=species["id"],
            species_name=species.get("common_names", {}).get("zh-TW", species["id"]),
            category=species.get("category", "unknown"),
            danger_level=species.get("danger_level"),
            score=score,
            effective_total=effective_total,
            confidence=round(confidence, 1),
        )

        heap_item = (score, confidence, result.species_id, result)
        if len(top_heap) < top_n:
            heapq.heappush(top_heap, heap_item)
            if len(top_heap) == top_n:
                min_top_score = top_heap[0][0]
        elif score >= min_top_score:
            heapq.heapreplace(top_heap, heap_item)
            min_top_score = top_heap[0][0]

    # Extract results sorted consistently with brute-force
    results = [item[3] for item in sorted(top_heap, key=lambda x: (-x[0], -x[1], x[2]))]
    return results
