#!/usr/bin/env python3
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

path = "knowledge_base/east_asia_subtropical/plants.json"
plants = json.load(open(path, encoding="utf-8"))
for sp in plants:
    fruit = sp["features"].get("fruit")
    if fruit and "colors" in fruit:
        colors = fruit["colors"]["value"]
        if "white" in colors:
            idx = colors.index("white")
            colors[idx] = "white_waxy"
            print("Fixed " + sp["id"] + ": white -> white_waxy")
json.dump(plants, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("Done")
