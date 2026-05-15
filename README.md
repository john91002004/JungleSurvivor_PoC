# 🌿 JungleSurvivor — Offline Plant Identification & Wilderness Survival Assistant

> **Kaggle Gemma "4 Good" Hackathon Submission**

---

## 1. Motivation & The Problem We Solve

Imagine being stranded in a subtropical jungle — no cell signal, no internet, battery draining fast. You're hungry, possibly injured, surrounded by lush vegetation. **Can you eat that plant, or will it kill you?**

Every year, hikers, soldiers, and outdoor adventurers face life-threatening situations where identifying a single plant correctly could mean the difference between survival and tragedy. Existing plant identification apps require internet connectivity and powerful cloud-based models — exactly the resources unavailable in an emergency.

**JungleSurvivor** is an offline-first, edge-deployable AI assistant that identifies plants and provides actionable survival guidance — all running locally on a mobile device with zero internet dependency.

### Target Use Cases

- **Hikers & mountaineers** caught in unexpected overnight situations or lost on trails
- **Military personnel** operating in jungle environments where foraging knowledge is mission-critical
- **Search-and-rescue teams** advising survivors on safe food sources during extended rescue operations
- **Rural communities** in areas with limited internet access who interact with wild plants daily

### The Scenario

You're lost in the mountains of Taiwan. It's been 18 hours since your last meal. You spot a large-leafed plant — it could be edible **Taro** (*Colocasia esculenta*), or it could be the highly toxic **Giant Elephant Ear** (*Alocasia odora*). They look nearly identical. One wrong bite could mean severe poisoning.

With JungleSurvivor, you:

1. Take 3 photos of the plant (whole plant, leaf top-down, flower close-up)
2. The on-device Gemma 4 model extracts visual features
3. You manually add what you can observe (e.g., smell, stem sap color)
4. The algorithmic engine matches against 50 known species
5. The app **warns you** that Taro and Giant Elephant Ear are a known confusion pair, and provides a **field test**: *"Drop water on the leaf — if it beads up, it's Taro (safe); if it spreads flat, it's Alocasia (toxic)"*
6. Once identified, the built-in **Survival Guide** tells you exactly how to prepare it safely

---

## 2. Our Journey: From v1 to v2

### v1: The Monolithic LLM Approach (What Didn't Work)

Our first version treated Gemma 4 as an all-in-one oracle:

- **One prompt** asked the LLM to identify the image, determine the species, assess toxicity, provide preparation instructions, and compare with similar species
- **Result**: Each identification took **~5 minutes** on a T4 GPU
- Confidence scores were inconsistent and irreproducible
- The prompt grew enormous (8,000+ tokens) trying to embed the entire knowledge base
- On edge devices, this approach was simply **infeasible**

### v2: The "Eyes & Brain" Architecture (What Works)

The breakthrough insight: **separate perception from reasoning**.

- **Gemma 4 = Eyes** — Its only job is to look at the photo and fill out a structured feature form (JSON). Like a botanist noting "heart-shaped leaf, glossy surface, pinnate venation" — nothing more.
- **Algorithm = Brain** — A deterministic scoring engine compares extracted features against a structured knowledge base. Zero LLM compute needed. Instant results.

**Impact on performance:**


| Metric                       | v1                            | v2                                 |
| ---------------------------- | ----------------------------- | ---------------------------------- |
| LLM inference time per photo | ~5 min                        | ~30 sec                            |
| LLM calls per identification | 1 (massive)                   | 1 per photo (lightweight)          |
| Matching & ranking           | LLM (slow, non-deterministic) | Algorithm (instant, deterministic) |
| Reproducibility              | Low                           | 100% for same features             |
| Edge feasibility             | ❌                             | ✅                                  |


---

## 3. Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    JungleSurvivor v2                         │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  📸 Photo    │  Phase 1: LLM Feature Extraction             │
│  Input       │  Gemma 4 → Structured JSON                   │
│              │  (constrained enum values only)               │
│              │                                              │
├──────────────┤  Phase 2: Feature Merging                    │
│              │  Multi-photo union + user overrides            │
│  ✏️ Manual   │  (user observations take priority)            │
│  Input       │                                              │
│              ├──────────────────────────────────────────────┤
│              │                                              │
│              │  Phase 3: Deterministic Scoring               │
│              │  Additive scoring + early stopping            │
│              │  Rarity-weighted feature matching             │
│              │  Confidence = score / effective_total         │
│              │                                              │
│              ├──────────────────────────────────────────────┤
│              │                                              │
│              │  Phase 4: Post-processing                    │
│              │  Warning levels (RED→ORANGE→YELLOW→GREEN)     │
│              │  Confusion pair detection + field tests       │
│              │  Usage info (edible parts, preparation)       │
│              │                                              │
├──────────────┴──────────────────────────────────────────────┤
│                                                             │
│  📚 Knowledge Base          │  🌿 Survival Guide            │
│  50 species (Taiwan)        │  6 categories:                │
│  Structured features        │  Food / Water / Medical       │
│  12 confusion pairs         │  Shelter / Tools / Navigation │
│  Rarity-based weights       │                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Phase 1: LLM as a "Visual Feature Extractor"

The LLM receives a prompt template that instructs it to act as a **pure perception layer**:

- Output **only** what is **visible** in the photo as structured JSON
- Choose from **predefined enum values** (e.g., leaf shape: `heart`, `oval`, `lanceolate`, ...)
- Use `not_visible` for features not seen, `uncertain` when unsure
- **Never** attempt species identification — no botanical knowledge needed
- Attributes that cannot be determined from photos (smell, sap taste, etc.) are marked `not_checkable`

### Phase 2: Multi-Photo Merging

Users upload multiple photos (recommended 3+). Features are merged via **union**:

- Photo 1 shows leaves → leaf features extracted
- Photo 2 shows flowers → flower features added
- Photo 3 shows the whole plant → overall features added
- User manually adds smell, habitat observations → highest priority overrides

### Phase 3: Scoring Engine

A deterministic, additive scoring algorithm:

- **Single-value match**: Full weight if value matches, 0 otherwise
- **Array match**: `weight × |intersection| / max(|observed|, |KB|)`
- **Weights**: Pre-computed from **rarity** across all 50 species — rare features are more diagnostic
- **Confidence**: `score / effective_total × 100` — where `effective_total` only counts attributes the user actually provided
- **Early stopping**: Branch-and-bound pruning skips species that can't reach the current top-3

### Phase 4: Safety Post-processing

- **Warning levels**: RED (toxic, high confidence) → ORANGE (toxic in candidates) → YELLOW (confusion pair detected) → GREEN (safe) → GREY (uncertain)
- **Confusion pair alerts**: 12 curated pairs (e.g., Taro vs. Alocasia) with **actionable field tests**
- **Usage information**: Edible parts, preparation methods, medicinal effects displayed inline

---

## 4. How to Use the App

### Step 1: Take Photos 📸

Take **3 or more** frontal photos of different plant features:

- ① **Whole plant** (must clearly show the stem)
- ② **Leaf from directly above** (to show shape, venation, margin)
- ③ **Flower or fruit close-up** (if present)

### Step 2: Upload & Extract Features 🔍

Upload photos one by one. After each upload, click "AI Extract Features". The system will:

- Call Gemma 4 to extract structured features (~30 seconds per photo)
- Automatically merge features from multiple photos
- Display results in interactive dropdown menus

### Step 3: Manual Correction ✏️

Review the feature dropdowns. Correct any AI mistakes:

- Change leaf shape if misidentified
- Add observations the camera can't capture (smell, sap color, texture feel)
- The more accurate features you provide, the better the identification

### Step 4: Identify & Verify 🔎

Click "Start Identification". The app returns:

- **Top 3 candidate species** with confidence scores
- **Warning level** (color-coded safety indicator)
- **Confusion pair alerts** with field tests you can perform on the spot
- **Usage information** (edible parts, preparation, medicinal effects)

### Step 5: Survival Guide 📖

Scroll down to the **Jungle Survival Guide** with 6 tabs:

- 🍃 **Food**: Plant processing methods (blanching, boiling, detox soaking), edibility testing, fire-making, cooking
- 💧 **Water**: Finding water sources, rain/dew collection, purification
- 🏥 **Medical**: Wound care, infection checklist, sprains, plant poultice, burns, snakebite
- 🏕️ **Shelter**: Site selection, lean-to / A-frame construction, warmth
- 🔧 **Tools**: Knot tying, stone knife, containers, cordage
- 🧭 **Navigation**: Direction finding (shadow method, Polaris), rescue signals

---

## 5. Strengths & Limitations

### ✅ Strengths

1. **Fully offline** — No internet required after model download. Critical for real wilderness scenarios.
2. **Deterministic matching** — Same features always produce the same result. No LLM hallucination in the matching phase.
3. **Human-in-the-loop** — Users can correct AI mistakes before identification, dramatically improving accuracy.
4. **Safety-first design** — Confusion pair warnings with field tests; multi-level warning system; never says "definitely safe" — always recommends verification.
5. **Comprehensive survival guide** — Goes beyond identification: teaches users how to process, cook, and use medicinal plants.
6. **Efficient on-device inference** — LLM only does feature extraction (~~30 sec), not full reasoning (~~5 min). Feasible on mobile GPUs.
7. **Extensible architecture** — Adding new species only requires adding entries to the knowledge base JSON. No model retraining needed.

### ⚠️ Limitations & Honest Disclaimers

1. **Proof of Concept (PoC)** — This is an experimental prototype. **Do NOT rely on it for actual survival situations** without additional verification.
2. **Limited species coverage** — Currently only **50 common Taiwan plants**. Future versions should expand to hundreds of species across multiple regions, with region-based filtering.
3. **Model size trade-off** — The demo uses Gemma 4 **E4B** (4 billion parameters). On mobile devices, **E2B** (2 billion) would be necessary, resulting in **lower extraction accuracy**. However, the human-in-the-loop design and reference photo comparison help compensate.
4. **Feature terminology** — Many botanical terms (e.g., "cuneate base", "acuminate tip", "pinnate venation") are **not intuitive for non-botanists**. Future versions need more accessible descriptions and visual examples.
5. **AI-generated survival guide** — The survival guide content was **generated by AI and has not been fully verified** by wilderness survival experts. It should be cross-referenced with established survival literature.
6. **Plants only** — Currently limited to plant identification. Future versions should include **animal identification** (edible insects, dangerous snakes, etc.) to be a comprehensive survival tool.
7. **No GPS/region awareness** — The current version does not use location data to narrow down likely species. Adding GPS-based regional filtering would significantly improve accuracy.
8. **Image quality dependency** — The LLM's feature extraction quality depends heavily on photo quality. Blurry, poorly lit, or partially obscured photos will produce inaccurate features.

---

## 6. Future Vision

If fully developed, JungleSurvivor could become:

### 🏔️ Essential App for Mountain Hikers

Pre-loaded with regional plant databases, providing instant identification and foraging guidance when cell signal is lost. Integrated with trail maps and emergency contact procedures.

### 🎖️ Military Jungle Survival Tool

Deployed on ruggedized devices for soldiers operating in dense vegetation. Combined with animal identification, water source assessment, and medical triage. Could be pre-loaded with theater-specific botanical databases.

### Roadmap

- **Expand knowledge base** to 500+ species across East Asia, Southeast Asia, and other regions
- **Add animal identification** (snakes, insects, edible fauna)
- **GPS-based region filtering** to narrow down candidate species
- **Expert-verified survival guide** with peer review from wilderness survival professionals
- **Multilingual support** (English, Japanese, Thai, Malay, etc.)
- **Offline map integration** with marked water sources and dangerous terrain
- **Community contribution** platform for adding new species observations
- **Smaller model optimization** (INT4/INT8 quantization) for broader device support

---

## 7. Technical Stack


| Component         | Technology                                                         |
| ----------------- | ------------------------------------------------------------------ |
| LLM               | Google Gemma 4 E4B-it (multimodal)                                 |
| Framework         | PyTorch + Transformers (HuggingFace)                               |
| UI                | Gradio                                                             |
| Inference         | BFloat16, `device_map="auto"` (multi-GPU)                          |
| Knowledge Base    | Structured JSON (50 species, 6 feature groups, 12 confusion pairs) |
| Scoring           | Custom Python (additive scoring, early stopping, rarity-weighted)  |
| Survival Guide    | Pre-rendered HTML from structured JSON (6 categories, 30+ pages)   |
| Deployment Target | Kaggle Notebook (T4 x2 GPU) / Mobile (future)                      |


---

## 8. Conclusion

JungleSurvivor demonstrates that **splitting LLM perception from algorithmic reasoning** can make edge-deployed AI both practical and reliable. By constraining the LLM to structured feature extraction and delegating matching to deterministic algorithms, we achieve:

- **10× faster inference** compared to monolithic LLM approaches
- **Reproducible, auditable results** — no hidden LLM reasoning
- **Human-correctable outputs** — users are part of the pipeline, not just consumers
- **Safety-conscious design** — confusion pair warnings, multi-level alerts, and field tests

While still a proof of concept, JungleSurvivor points toward a future where AI-powered survival tools can genuinely save lives — even when the nearest cell tower is 50 kilometers away.

> *"In the jungle, knowledge is the ultimate survival tool. JungleSurvivor puts that knowledge in your pocket — no signal required."*

---

**Team**: John Huang  
**Competition**: Kaggle Gemma "4 Good" Hackathon  
**Model**: Google Gemma 4 (E4B-it / E2B-it)
