#!/usr/bin/env python3
"""Patch v2 structured features for edible/medicinal species from v1 text audit."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PLANTS_JSON = PROJECT_ROOT / "knowledge_base" / "east_asia_subtropical" / "plants.json"

# Per-species corrections: only attributes that contradict v1 edible_plants.json (or obvious defaults).
FIXES: dict[str, dict[str, dict[str, object]]] = {
    "asplenium_nidus": {
        "overall": {"height_estimate": "30-100cm"},
        "leaf": {"base": "rounded"},
    },
    "diplazium_esculentum": {
        "leaf": {"shape": "lanceolate"},
        "stem": {"surface": "scaly", "colors": ["brown", "green"]},
        "fruit": {"type": "spore", "colors": ["brown"], "size": "tiny_<5mm"},
    },
    "hedychium_coronarium": {
        "leaf": {"surface_bottom": "hairy", "texture": "leathery"},
        "flower": {"fragrant": "yes"},
    },
    "plantago_major": {
        "leaf": {"size": "large_15-50cm"},
        "overall": {"height_estimate": "30-100cm"},
    },
    "solanum_nigrum": {
        "fruit": {"colors": ["green", "purple"]},
    },
    "crassocephalum_crepidioides": {
        "overall": {"height_estimate": "30-100cm"},
        "stem": {"interior": "hollow"},
    },
    "colocasia_esculenta": {
        "leaf": {"texture": "leathery"},
        "overall": {"height_estimate": "1-2m"},
    },
    "auricularia_auricula_judae": {
        "overall": {
            "growth_form": "fungus",
            "height_estimate": "<30cm",
            "habitat": "forest_floor",
        },
        "leaf": {
            "shape": "oval",
            "tip": "rounded",
            "base": "rounded",
            "colors": ["brown", "dark_green"],
            "surface_top": "hairy",
            "surface_bottom": "glossy",
            "venation": "reticulate",
            "texture": "fleshy",
            "arrangement": "clustered",
        },
        "stem": {"surface": "hairy", "colors": ["brown"]},
        "fruit": {"type": "spore", "colors": ["brown"], "size": "tiny_<5mm"},
    },
    "nephrolepis_cordifolia": {
        "overall": {"growth_form": "fern"},
        "leaf": {"shape": "lanceolate"},
        "stem": {"type": "rhizome", "surface": "scaly", "colors": ["brown"], "interior": "solid"},
        "fruit": {"type": "spore", "colors": ["brown"], "size": "tiny_<5mm"},
    },
    "oenanthe_javanica": {
        "leaf": {"leaf_type": "bipinnate_compound"},
        "stem": {"interior": "hollow"},
    },
    "bidens_pilosa_var_radiata": {
        "leaf": {"edge": "serrated"},
        "stem": {"cross_section": "square"},
        "flower": {"special_shape": "none"},
    },
    "alpinia_zerumbet": {
        "stem": {"type": "erect"},
        "leaf": {"texture": "leathery", "surface_top": "glossy"},
        "overall": {"habitat": "streamside"},
        "flower": {"fragrant": "yes"},
    },
    "broussonetia_papyrifera": {
        "overall": {
            "height_estimate": ">5m",
            "habitat": "roadside",
            "latex": "yes_white",
        },
        "leaf": {"edge": "lobed", "surface_top": "rough"},
        "fruit": {"type": "aggregate"},
    },
    "morus_australis": {
        "overall": {"growth_form": "tree", "height_estimate": "2-5m", "latex": "yes_white"},
        "leaf": {"edge": "serrated", "surface_top": "matte", "texture": "papery"},
        "fruit": {"colors": ["red", "purple"]},
    },
    "amaranthus_viridis": {
        "overall": {"height_estimate": "30-100cm"},
        "stem": {"colors": ["green", "red"]},
    },
    "houttuynia_cordata": {
        "overall": {"height_estimate": "30-100cm"},
        "leaf": {"size": "medium_5-15cm"},
    },
    "miscanthus_floridulus": {
        "overall": {"height_estimate": "2-5m", "habitat": "open_field"},
        "leaf": {"venation": "parallel"},
        "flower": {"arrangement": "panicle"},
        "fruit": {"type": "achene"},
    },
    "zanthoxylum_ailanthoides": {
        "leaf": {"edge": "serrated", "shape": "lanceolate"},
        "stem": {"colors": ["brown", "gray"], "has_thorns": "yes"},
    },
    "trema_orientalis": {
        "leaf": {"edge": "serrated"},
        "fruit": {"size": "tiny_<5mm"},
    },
    "pterocypsela_indica": {
        "leaf": {"edge": "lobed", "shape": "lanceolate"},
        "stem": {"interior": "hollow"},
        "fruit": {"type": "achene", "colors": ["brown"], "size": "tiny_<5mm"},
    },
    "melastoma_candidum": {
        "leaf": {"arrangement": "opposite", "venation": "palmate"},
    },
    "emilia_sonchifolia": {
        "flower": {"colors": ["orange", "red"]},
    },
    "pseudognaphalium_affine": {
        "leaf": {"surface_top": "hairy"},
        "stem": {"surface": "hairy"},
    },
    "centella_asiatica": {
        "leaf": {"venation": "palmate", "tip": "rounded", "arrangement": "clustered"},
        "flower": {"colors": ["pink", "white"], "size": "tiny_<5mm"},
    },
    "momordica_charantia_var": {
        "fruit": {"type": "berry", "size": "large_>30mm"},
    },
    "cyathea_lepifera": {
        "overall": {"growth_form": "fern"},
        "leaf": {
            "arrangement": "clustered",
            "size": "very_large_>50cm",
            "shape": "lanceolate",
        },
        "stem": {"surface": "scaly", "colors": ["brown"]},
        "fruit": {"type": "spore", "colors": ["brown"], "size": "tiny_<5mm"},
    },
    "macrolepiota_procera": {
        "overall": {"growth_form": "fungus", "habitat": "open_field"},
    },
    "termitomyces_sp": {
        "overall": {"growth_form": "fungus", "habitat": "forest_floor"},
        "leaf": {
            "colors": ["brown"],
            "texture": "fleshy",
            "shape": "round",
            "venation": "reticulate",
        },
    },
}


def _norm(v: object) -> object:
    if isinstance(v, list):
        return tuple(v)
    return v


def main() -> None:
    if not PLANTS_JSON.is_file():
        sys.stderr.write("Missing %s\n" % PLANTS_JSON)
        sys.exit(1)
    plants = json.loads(PLANTS_JSON.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in plants}

    for species, sections in FIXES.items():
        plant = by_id.get(species)
        if plant is None:
            print("[skip] %s not in plants.json" % species)
            continue
        buf: list[str] = []

        def _emit(msg: str) -> None:
            buf.append(msg)

        for sec, upd in sections.items():
            feats = plant.get("features") or {}
            block = feats.get(sec)
            if block is None or not isinstance(block, dict):
                continue
            for key, new_val in upd.items():
                if key not in block:
                    continue
                cell = block[key]
                if not isinstance(cell, dict) or "value" not in cell:
                    continue
                old = cell["value"]
                if _norm(old) == _norm(new_val):
                    continue
                _emit("  %s / %s.%s: %r -> %r" % (species, sec, key, old, new_val))
                cell["value"] = new_val

        if buf:
            print("[%s]" % species)
            print("\n".join(buf))

    PLANTS_JSON.write_text(json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nWrote %s" % PLANTS_JSON)


if __name__ == "__main__":
    main()
