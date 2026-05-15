#!/usr/bin/env python3
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

plants = json.loads(open("knowledge_base/east_asia_subtropical/plants.json", encoding="utf-8").read())
by_id = {p["id"]: p for p in plants}

check = [
    "urtica_thunbergiana", "alocasia_odora", "datura_stramonium",
    "epipremnum_aureum", "abrus_precatorius", "ricinus_communis",
    "nerium_oleander", "lantana_camara", "digitalis_purpurea",
    "chlorophyllum_molybdites", "amanita_phalloides",
    "brugmansia_suaveolens", "phytolacca_americana",
    "cycas_revoluta", "zantedeschia_aethiopica",
    "dendrocnide_meyeniana", "cerbera_manghas",
    "toxicodendron_vernicifluum", "triadica_sebifera",
    "parthenium_hysterophorus",
    "melia_azedarach", "pteridium_aquilinum",
]

for sid in check:
    p = by_id.get(sid)
    if not p:
        print("MISSING: " + sid)
        continue
    f = p["features"]
    ov = {k: v.get("value") for k, v in f.get("overall", {}).items()}
    leaf = {k: v.get("value") for k, v in (f.get("leaf") or {}).items()}
    stem = {k: v.get("value") for k, v in (f.get("stem") or {}).items()}
    flower = {k: v.get("value") for k, v in (f.get("flower") or {}).items()}
    fruit = {k: v.get("value") for k, v in (f.get("fruit") or {}).items()}
    root = {k: v.get("value") for k, v in (f.get("root") or {}).items()}
    cn = p["common_names"]["zh-TW"]
    print("=== %s (%s) ===" % (sid, cn))
    print("  overall: growth=%s, h=%s, lat=%s, smell=%s, hab=%s, water=%s" % (
        ov.get("growth_form"), ov.get("height_estimate"), ov.get("latex"),
        ov.get("smell"), ov.get("habitat"), ov.get("water_droplet_test")))
    print("  leaf: type=%s, shape=%s, edge=%s, tip=%s, base=%s, arr=%s, sz=%s" % (
        leaf.get("leaf_type"), leaf.get("shape"), leaf.get("edge"),
        leaf.get("tip"), leaf.get("base"), leaf.get("arrangement"), leaf.get("size")))
    print("        ven=%s, tex=%s, surT=%s, surB=%s, col=%s, pat=%s, pet=%s" % (
        leaf.get("venation"), leaf.get("texture"), leaf.get("surface_top"),
        leaf.get("surface_bottom"), leaf.get("colors"), leaf.get("color_pattern"),
        leaf.get("petiole_attach")))
    print("  stem: type=%s, xsec=%s, col=%s, int=%s, thorn=%s, sur=%s" % (
        stem.get("type"), stem.get("cross_section"), stem.get("colors"),
        stem.get("interior"), stem.get("has_thorns"), stem.get("surface")))
    print("  flower: col=%s, arr=%s, pet=%s, shape=%s, frag=%s, sym=%s, sz=%s" % (
        flower.get("colors"), flower.get("arrangement"), flower.get("petal_count"),
        flower.get("special_shape"), flower.get("fragrant"), flower.get("symmetry"),
        flower.get("size")))
    print("  fruit: type=%s, col=%s, sz=%s, sur=%s" % (
        fruit.get("type"), fruit.get("colors"), fruit.get("size"), fruit.get("surface")))
    print("  root: type=%s" % root.get("type"))
    print()
