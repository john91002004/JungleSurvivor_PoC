#!/usr/bin/env python3
"""Validate v2 knowledge base plants against feature schema."""

import json
import sys
from pathlib import Path

KB_ROOT = Path(__file__).parent.parent / "knowledge_base"
PLANTS_FILE = KB_ROOT / "east_asia_subtropical" / "plants.json"
SCHEMA_FILE = KB_ROOT / "feature_schema.json"


def main():
    with open(PLANTS_FILE, encoding="utf-8") as f:
        plants = json.load(f)
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        schema = json.load(f)

    # Remove meta keys from schema
    schema_sections = {k: v for k, v in schema.items() if not k.startswith("_")}

    print(f"Loaded {len(plants)} species from {PLANTS_FILE.name}")
    print(f"Schema sections: {list(schema_sections.keys())}")
    print()

    for sp in plants:
        sid = sp["id"]
        cat = sp["category"]
        sections = list(sp["features"].keys())
        has_usage = "usage" in sp
        print(f"  {sid:30s} cat={cat:12s} sections={sections} usage={has_usage}")
    print()

    errors = []
    warnings = []

    for sp in plants:
        sid = sp["id"]

        # Check required top-level fields
        for req in ("id", "scientific_name", "common_names", "category", "features", "human_readable"):
            if req not in sp:
                errors.append(f"{sid}: missing required field '{req}'")

        # Check dangerous species have danger_level
        if sp.get("category") == "dangerous" and "danger_level" not in sp:
            errors.append(f"{sid}: dangerous species missing 'danger_level'")

        # Check edible/medicinal species have usage
        if sp.get("category") in ("edible", "medicinal") and "usage" not in sp:
            warnings.append(f"{sid}: edible/medicinal species missing 'usage' field")

        # Validate features against schema
        for section_name, section_features in sp["features"].items():
            if section_features is None:
                continue

            schema_section = schema_sections.get(section_name)
            if not schema_section:
                errors.append(f"{sid}/{section_name}: section not in schema")
                continue

            for attr_name, attr_obj in section_features.items():
                schema_attr = schema_section.get(attr_name)
                if not schema_attr:
                    errors.append(f"{sid}/{section_name}.{attr_name}: attribute not in schema")
                    continue

                val = attr_obj.get("value")
                if val is None:
                    errors.append(f"{sid}/{section_name}.{attr_name}: missing 'value'")
                    continue

                allowed = [str(v) for v in schema_attr["values"]]
                attr_type = schema_attr["type"]

                if attr_type == "array":
                    if not isinstance(val, list):
                        errors.append(f"{sid}/{section_name}.{attr_name}: expected array, got {type(val).__name__}")
                    else:
                        for v in val:
                            if str(v) not in allowed:
                                errors.append(f"{sid}/{section_name}.{attr_name}: value '{v}' not in allowed {allowed}")
                elif attr_type == "boolean":
                    if not isinstance(val, bool):
                        errors.append(f"{sid}/{section_name}.{attr_name}: expected boolean, got {type(val).__name__}")
                else:
                    if str(val) not in allowed:
                        errors.append(f"{sid}/{section_name}.{attr_name}: value '{val}' not in allowed {allowed}")

            # Check for missing schema attributes
            for schema_attr_name in schema_section:
                if schema_attr_name not in section_features:
                    if schema_attr_name != "visible":
                        warnings.append(f"{sid}/{section_name}.{schema_attr_name}: attribute in schema but not in plant data")

    # Report
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
    else:
        print("✓ No validation errors!")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠ {w}")

    print()
    print(f"Summary: {len(plants)} species, {len(errors)} errors, {len(warnings)} warnings")

    return 1 if errors else 0


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
