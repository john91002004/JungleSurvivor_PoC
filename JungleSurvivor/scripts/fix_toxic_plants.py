#!/usr/bin/env python3
"""Fix v2 structured features for toxic species based on thorough v1 audit."""
import io, json, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PLANTS = Path(__file__).resolve().parent.parent / "knowledge_base" / "east_asia_subtropical" / "plants.json"

FIXES = {
    "urtica_thunbergiana": {
        "overall": {},
        "leaf": {
            "tip": "acute",
            "base": "cordate",
            "arrangement": "opposite",
            "venation": "palmate",
        },
        "stem": {
            "cross_section": "square",
        },
        "flower": {
            "petal_count": "0",
            "size": "tiny_<5mm",
        },
    },
    "datura_stramonium": {
        "overall": {"height_estimate": "1-2m"},
        "leaf": {
            "tip": "acute",
            "colors": ["dark_green"],
            "size": "large_15-50cm",
        },
        "stem": {"colors": ["green", "purple"]},
        "flower": {
            "petal_count": "5",
            "size": "very_large_>60mm",
        },
        "fruit": {
            "surface": "spiny",
            "size": "large_>30mm",
        },
    },
    "epipremnum_aureum": {
        "leaf": {
            "surface_top": "glossy",
            "base": "cordate",
        },
        "stem": {"type": "climbing"},
    },
    "abrus_precatorius": {
        "leaf": {
            "tip": "rounded",
            "shape": "elliptic",
            "size": "tiny_<2cm",
        },
        "stem": {"type": "twining"},
        "flower": {
            "symmetry": "bilateral",
            "size": "small_5-15mm",
            "special_shape": "butterfly_shape",
        },
        "fruit": {
            "colors": ["red", "black"],
            "surface": "smooth",
        },
    },
    "ricinus_communis": {
        "leaf": {
            "shape": "round",
            "edge": "deeply_lobed",
            "venation": "palmate",
            "surface_top": "glossy",
        },
        "stem": {
            "colors": ["green", "purple"],
            "interior": "pithy",
        },
        "fruit": {
            "surface": "spiny",
            "size": "medium_15-30mm",
            "colors": ["green", "brown"],
        },
    },
    "nerium_oleander": {
        "overall": {
            "height_estimate": "2-5m",
            "latex": "yes_white",
        },
        "leaf": {"size": "medium_5-15cm"},
    },
    "digitalis_purpurea": {
        "overall": {"height_estimate": "1-2m"},
        "leaf": {
            "surface_top": "hairy",
            "surface_bottom": "hairy",
            "edge": "crenate",
            "arrangement": "basal_rosette",
            "size": "large_15-50cm",
        },
    },
    "chlorophyllum_molybdites": {
        "leaf": {
            "colors": ["white_waxy", "brown"],
            "size": "large_15-50cm",
            "surface_top": "scaly",
            "texture": "fleshy",
            "arrangement": "clustered",
            "tip": "rounded",
            "base": "rounded",
            "edge": "entire",
            "venation": "reticulate",
        },
        "stem": {
            "colors": ["white_powdery"],
            "surface": "smooth",
        },
        "fruit": {"type": "spore", "colors": ["green"], "size": "tiny_<5mm"},
    },
    "amanita_phalloides": {
        "overall": {"height_estimate": "<30cm"},
        "leaf": {
            "colors": ["white_waxy", "green", "yellow"],
            "texture": "fleshy",
            "surface_top": "glossy",
            "size": "medium_5-15cm",
            "arrangement": "clustered",
            "tip": "rounded",
            "base": "rounded",
            "edge": "entire",
            "venation": "reticulate",
        },
        "stem": {
            "colors": ["white_powdery"],
            "surface": "smooth",
        },
        "fruit": {"type": "spore", "colors": ["white_waxy"], "size": "tiny_<5mm"},
    },
    "brugmansia_suaveolens": {
        "flower": {
            "size": "very_large_>60mm",
            "orientation": "drooping",
        },
    },
    "phytolacca_americana": {
        "overall": {"height_estimate": "1-2m"},
        "stem": {"interior": "pithy"},
        "root": {"type": "taproot"},
    },
    "cycas_revoluta": {
        "stem": {
            "has_thorns": "yes",
            "surface": "scaly",
            "colors": ["brown", "gray"],
        },
        "fruit": {"size": "large_>30mm"},
    },
    "zantedeschia_aethiopica": {
        "leaf": {
            "base": "cordate",
            "arrangement": "clustered",
            "texture": "leathery",
            "shape": "arrow",
        },
    },
    "dendrocnide_meyeniana": {
        "overall": {"height_estimate": "2-5m"},
        "leaf": {
            "leaf_type": "simple",
            "venation": "palmate",
            "tip": "acute",
            "surface_bottom": "hairy",
        },
    },
    "toxicodendron_vernicifluum": {
        "overall": {"latex": "yes_white"},
        "leaf": {"colors": ["green"]},
    },
    "triadica_sebifera": {
        "overall": {"latex": "yes_white"},
        "leaf": {
            "shape": "rhombic",
            "colors": ["dark_green"],
        },
        "stem": {
            "surface": "bark_rough",
            "colors": ["brown", "gray"],
        },
        "fruit": {"colors": ["black", "white_waxy"]},
    },
    "parthenium_hysterophorus": {
        "leaf": {"surface_top": "hairy"},
        "fruit": {"type": "achene"},
    },
    "melia_azedarach": {
        "leaf": {"leaf_type": "bipinnate_compound"},
    },
    "pteridium_aquilinum": {
        "overall": {"growth_form": "fern"},
        "leaf": {"leaf_type": "bipinnate_compound"},
        "fruit": {"type": "spore", "colors": ["brown"], "size": "tiny_<5mm"},
    },
    "lantana_camara": {
        "stem": {"cross_section": "square"},
        "flower": {"arrangement": "umbel"},
    },
}


def main():
    plants = json.loads(PLANTS.read_text("utf-8"))
    by_id = {p["id"]: p for p in plants}
    total = 0

    for species, sections in FIXES.items():
        plant = by_id.get(species)
        if not plant:
            print("[skip] %s not found" % species)
            continue
        msgs = []
        for sec, upd in sections.items():
            block = plant.get("features", {}).get(sec)
            if block is None or not isinstance(block, dict):
                continue
            for key, new_val in upd.items():
                cell = block.get(key)
                if cell is None or not isinstance(cell, dict) or "value" not in cell:
                    continue
                old = cell["value"]
                if isinstance(new_val, list):
                    if sorted(old) if isinstance(old, list) else old == sorted(new_val):
                        continue
                elif old == new_val:
                    continue
                msgs.append("  %s.%s: %r -> %r" % (sec, key, old, new_val))
                cell["value"] = new_val
                total += 1
        if msgs:
            print("[%s]" % species)
            for m in msgs:
                print(m)

    PLANTS.write_text(json.dumps(plants, ensure_ascii=False, indent=2), "utf-8")
    print("\nTotal fixes applied: %d" % total)


if __name__ == "__main__":
    main()
