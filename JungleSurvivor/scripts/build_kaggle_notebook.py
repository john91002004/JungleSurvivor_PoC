#!/usr/bin/env python3
"""
Build a self-contained Kaggle notebook for JungleSurvivor v2.

Reads all source modules and KB data, embeds them into a single .ipynb file.
"""
import json
import uuid
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
KB_ROOT = PROJECT / "knowledge_base"
APP_DIR = PROJECT / "app"
OUT_PATH = PROJECT / "notebooks" / "jungle_survivor_v2_kaggle.ipynb"


def uid():
    return uuid.uuid4().hex[:8]


def md_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.split("\n"), "id": uid()}


def code_cell(source: str) -> dict:
    lines = source.split("\n")
    src = [line + "\n" for line in lines[:-1]]
    if lines:
        src.append(lines[-1])
    return {
        "cell_type": "code",
        "metadata": {},
        "source": src,
        "execution_count": None,
        "outputs": [],
        "id": uid(),
    }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def strip_relative_imports(code: str) -> str:
    """Remove lines like 'from .scoring import ...' since everything is in one namespace."""
    lines = code.split("\n")
    cleaned = []
    skip_continuation = False
    for line in lines:
        if skip_continuation:
            if line.strip().endswith(")"):
                skip_continuation = False
            continue
        if line.strip().startswith("from ."):
            if "(" in line and ")" not in line:
                skip_continuation = True
            continue
        cleaned.append(line)
    return "\n".join(cleaned)



def _read_guide_cell_source():
    """Read pre-built survival guide cell source."""
    p = KB_ROOT / "_guide_cell_source.py.txt"
    return p.read_text(encoding="utf-8")


def build_notebook():
    cells = []

    # ── Cell: Title ──
    cells.append(md_cell(
        "# 🌿 JungleSurvivor v2 — Kaggle 完整 Notebook\n"
        "\n"
        "**叢林求生離線 AI 助手 — 結構化特徵辨識 Pipeline**\n"
        "\n"
        "### 架構\n"
        "- **Gemma 4** 只做「看圖填表」— 從照片萃取結構化植物特徵 (JSON)\n"
        "- **演算法引擎** 做比對、計分、排序 — 確定性結果，零 LLM 算力\n"
        "- **50 種台灣常見植物** 知識庫，含危險/可食/藥用分類\n"
        "- **混淆物種警告** + 野外實測指引\n"
        "\n"
        "### 測試項目\n"
        "1. 單張照片辨識\n"
        "2. 多張照片特徵合併\n"
        "3. 使用者手動修正特徵\n"
        "4. 危險物種警告 + 混淆對提示\n"
        "5. Gradio 互動介面"
    ))

    # ── Cell: Install ──
    cells.append(code_cell(
        "# Cell 1: 安裝依賴\n"
        "# Pillow 不要升級 — Kaggle 預裝版本與 torchvision 相容\n"
        "!pip install -q --upgrade transformers accelerate gradio\n"
        "\n"
        "import json, re, os, sys, time, torch\n"
        "import requests\n"
        "from io import BytesIO\n"
        "from pathlib import Path\n"
        "from PIL import Image\n"
        "from dataclasses import dataclass, field\n"
        "from typing import Any, Optional, Callable\n"
        "import heapq\n"
        "\n"
        'print(f"PyTorch: {torch.__version__}")\n'
        'print(f"CUDA available: {torch.cuda.is_available()}")\n'
        "if torch.cuda.is_available():\n"
        '    print(f"GPU: {torch.cuda.get_device_name(0)}")\n'
        '    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")'
    ))

    # ── Cell: Config ──
    cells.append(code_cell(
        "# Cell 2: 全域設定\n"
        '\n'
        'MODEL_ID = "google/gemma-4-E4B-it"\n'
        "MAX_NEW_TOKENS = 4096\n"
        'DTYPE = torch.bfloat16 if torch.cuda.is_available() else torch.float32\n'
        '\n'
        'print(f"✅ Model: {MODEL_ID}")\n'
        'print(f"✅ Dtype: {DTYPE}")'
    ))

    # ── Cell: Scoring Engine ──
    cells.append(md_cell(
        "## 🧮 核心引擎 — Scoring & Matching\n"
        "\n"
        "確定性演算法：特徵比對、加權計分、Top-N 排序、Early Stopping 剪枝。"
    ))

    scoring_code = read_text(APP_DIR / "scoring.py")
    scoring_code = strip_relative_imports(scoring_code)
    scoring_code = scoring_code.replace("from __future__ import annotations\n", "")
    cells.append(code_cell("# Cell 3: Scoring Engine\n" + scoring_code))

    # ── Cell: Feature Extractor ──
    cells.append(md_cell(
        "## 🔍 LLM 特徵萃取器\n"
        "\n"
        "從 LLM 回應中提取 JSON → 驗證 → 清理，容錯截斷修復。"
    ))

    extractor_code = read_text(APP_DIR / "feature_extractor.py")
    extractor_code = strip_relative_imports(extractor_code)
    extractor_code = extractor_code.replace("from __future__ import annotations\n", "")
    # Remove file-loading functions (we'll embed data directly)
    lines = extractor_code.split("\n")
    filtered = []
    skip_func = False
    for line in lines:
        if line.startswith("def load_prompt_template(") or line.startswith("def load_enums(") or line.startswith("def load_schema("):
            skip_func = True
            continue
        if skip_func:
            if line and not line.startswith(" ") and not line.startswith("\t"):
                skip_func = False
            else:
                continue
        if not skip_func:
            filtered.append(line)
    extractor_code = "\n".join(filtered)
    cells.append(code_cell("# Cell 4: Feature Extractor\n" + extractor_code))

    # ── Cell: Feature Merger ──
    cells.append(md_cell(
        "## 🔀 多照片特徵合併 + 使用者輸入覆蓋"
    ))
    merger_code = read_text(APP_DIR / "feature_merger.py")
    merger_code = strip_relative_imports(merger_code)
    merger_code = merger_code.replace("from __future__ import annotations\n", "")
    cells.append(code_cell("# Cell 5: Feature Merger\n" + merger_code))

    # ── Cell: Matcher ──
    cells.append(md_cell(
        "## 🎯 Species Matcher (Early Stopping)\n"
        "\n"
        "Branch-and-bound 剪枝，效率比暴力搜尋高 2-3 倍。"
    ))
    matcher_code = read_text(APP_DIR / "matcher.py")
    matcher_code = strip_relative_imports(matcher_code)
    matcher_code = matcher_code.replace("from __future__ import annotations\n", "")
    # Remove load_kb function (we'll define our own)
    lines = matcher_code.split("\n")
    filtered = []
    skip_func = False
    for line in lines:
        if line.startswith("def load_kb("):
            skip_func = True
            continue
        if skip_func:
            if line and not line.startswith(" ") and not line.startswith("\t"):
                skip_func = False
            else:
                continue
        if not skip_func:
            filtered.append(line)
    matcher_code = "\n".join(filtered)
    cells.append(code_cell("# Cell 6: Matcher\n" + matcher_code))

    # ── Cell: Postprocessor ──
    cells.append(md_cell(
        "## ⚠️ 後處理 — 警告等級 & 混淆物種\n"
        "\n"
        "嚴格優先順序：RED > ORANGE > YELLOW > GREEN > GREY"
    ))
    post_code = read_text(APP_DIR / "postprocessor.py")
    post_code = strip_relative_imports(post_code)
    post_code = post_code.replace("from __future__ import annotations\n", "")
    cells.append(code_cell("# Cell 7: Postprocessor\n" + post_code))

    # ── Cell: Knowledge Base ──
    cells.append(md_cell(
        "## 📚 知識庫 (嵌入式)\n"
        "\n"
        "50 種台灣常見植物 + 完整結構化特徵 + 混淆物種對。\n"
        "所有資料內嵌於 Notebook 中，不需要外部檔案。"
    ))

    schema = read_json(KB_ROOT / "feature_schema.json")
    enums = read_json(KB_ROOT / "derived_enums.json")
    weights = read_json(KB_ROOT / "derived_weights.json")
    confusion = read_json(KB_ROOT / "east_asia_subtropical" / "confusion_pairs.json")
    prompt_tpl = read_text(KB_ROOT / "prompt_template.txt")
    plants = read_json(KB_ROOT / "east_asia_subtropical" / "plants.json")

    kb_code = "# Cell 8: 知識庫資料 (嵌入)\n\n"
    kb_code += f"FEATURE_SCHEMA = json.loads(r'''{json.dumps(schema, ensure_ascii=False)}''')\n\n"
    kb_code += f"DERIVED_ENUMS = json.loads(r'''{json.dumps(enums, ensure_ascii=False)}''')\n\n"
    kb_code += f"DERIVED_WEIGHTS = json.loads(r'''{json.dumps(weights, ensure_ascii=False)}''')\n\n"
    kb_code += f"CONFUSION_DB = json.loads(r'''{json.dumps(confusion, ensure_ascii=False)}''')\n\n"
    kb_code += f"PROMPT_TEMPLATE = r'''{prompt_tpl}'''\n\n"
    kb_code += 'print(f"✅ Schema sections: {list(k for k in FEATURE_SCHEMA if not k.startswith(\'_\'))}")\n'
    kb_code += 'print(f"✅ Confusion pairs: {len(CONFUSION_DB.get(\'confusion_pairs\', []))}")\n'
    kb_code += 'print(f"✅ Prompt template: {len(PROMPT_TEMPLATE)} chars")'
    cells.append(code_cell(kb_code))

    # Plants data in separate cell (large)
    plants_compact = json.dumps(plants, ensure_ascii=False, separators=(",", ":"))
    plants_code = "# Cell 9: 植物知識庫 (50 species)\n\n"
    plants_code += f"PLANTS_DB = json.loads(r'''{plants_compact}''')\n\n"
    plants_code += 'print(f"✅ Loaded {len(PLANTS_DB)} species")\n'
    plants_code += "cats = {}\n"
    plants_code += "for sp in PLANTS_DB:\n"
    plants_code += "    c = sp.get('category', 'unknown')\n"
    plants_code += "    cats[c] = cats.get(c, 0) + 1\n"
    plants_code += 'print(f"   Categories: {cats}")'
    cells.append(code_cell(plants_code))


    # ── Cell: Survival Guide (pre-rendered HTML) ──
    cells.append(md_cell(
        "## \U0001f33f 叢林生存指南資料\n"
        "\n"
        "6 大分類（食/水/醫/住/工具/行），build 時預先渲染為 HTML。"
    ))
    cells.append(code_cell(_read_guide_cell_source()))

    # ── Cell: Pipeline ──
    cells.append(md_cell(
        "## 🔄 Pipeline — 完整辨識流程\n"
        "\n"
        "Phase 0: 載入 KB → Phase 1: LLM 特徵萃取 → Phase 2: 特徵合併 → Phase 3: 比對計分 → Phase 4: 後處理"
    ))

    pipeline_code = '''# Cell 10: Pipeline (Notebook 版)

class PipelineState:
    """Tracks state across iterative photo sessions."""
    def __init__(self):
        self.accumulated_features = {}
        self.photo_count = 0
        self.user_overrides = {}
        self.extraction_logs = []
        self.identification_logs = []
        self.latest_result = None


class JungleSurvivorV2:
    """Main v2 pipeline controller — Notebook version (no file I/O)."""

    def __init__(self):
        self.plants = PLANTS_DB
        self.schema = FEATURE_SCHEMA
        self.confusion_db = CONFUSION_DB
        self.enums = DERIVED_ENUMS
        self.prompt_template = PROMPT_TEMPLATE
        self.state = PipelineState()
        self._plants_by_id = {sp["id"]: sp for sp in self.plants}

    def reset(self):
        self.state = PipelineState()

    def get_prompt(self) -> str:
        return self.prompt_template

    # ── Phase 1: Feature Extraction ──

    def extract_features_from_response(self, llm_response: str) -> ExtractionResult:
        result = parse_llm_response(llm_response, self.schema, self.enums)
        if result.success and result.features:
            self.state.accumulated_features = merge_features(
                self.state.accumulated_features,
                result.features,
                self.schema,
            )
            self.state.photo_count += 1
        return result

    def log_extraction(self, llm_time_sec, response_len, result):
        feat_count = 0
        if result.success and result.features:
            for sec, data in result.features.items():
                feat_count += len(data) if isinstance(data, dict) else 1
        self.state.extraction_logs.append({
            "photo_num": self.state.photo_count,
            "time_sec": llm_time_sec,
            "success": result.success,
            "resp_len": response_len,
            "feature_count": feat_count,
            "warning_count": len(result.warnings),
        })

    # ── Phase 2: Feature Management ──

    def get_current_features(self) -> dict:
        if self.state.user_overrides:
            return apply_user_input(
                self.state.accumulated_features,
                self.state.user_overrides,
            )
        return self.state.accumulated_features

    def get_feature_summary(self) -> dict:
        features = self.get_current_features()
        return get_feature_summary(features, self.schema)

    def set_user_feature(self, section: str, attr: str, value):
        if section not in self.state.user_overrides:
            self.state.user_overrides[section] = {}
        self.state.user_overrides[section][attr] = value

    def remove_user_override(self, section: str, attr: str):
        if section in self.state.user_overrides:
            self.state.user_overrides[section].pop(attr, None)
            if not self.state.user_overrides[section]:
                del self.state.user_overrides[section]

    def get_override_list(self):
        items = []
        for sec, attrs in self.state.user_overrides.items():
            for attr, val in attrs.items():
                items.append((sec, attr, val))
        return items

    # ── Phase 3 + 4: Identify ──

    def identify(self, top_n: int = 3) -> ProcessedResult:
        features = self.get_current_features()
        has_photo = self.state.photo_count > 0
        top_results = match_top_n(features, self.plants, self.schema, has_photo=has_photo, top_n=top_n)
        result = process_results(top_results, self.confusion_db, self.plants)
        self.state.latest_result = result
        return result

    def log_identification(self, time_sec, processed):
        top1 = ""
        top1_score = ""
        warning_level = ""
        if processed.top_results:
            r0 = processed.top_results[0]
            sp = self._plants_by_id.get(r0.species_id, {})
            top1 = sp.get("common_names", {}).get("zh-TW", r0.species_name)
            top1_score = f"{r0.confidence:.1f}%"
        warning_level = processed.warning.level if processed.warning else ""
        ovr_count = sum(len(v) for v in self.state.user_overrides.values())
        self.state.identification_logs.append({
            "time_sec": time_sec,
            "photo_count": self.state.photo_count,
            "override_count": ovr_count,
            "top1": top1,
            "top1_score": top1_score,
            "warning_level": warning_level,
        })

    def format_display(self, result=None) -> str:
        r = result or self.state.latest_result
        if r is None:
            return "尚未進行辨識。請先上傳照片。"
        return format_result_display(r, self.plants)

    def get_species_info(self, species_id: str):
        return self._plants_by_id.get(species_id)

    def get_schema_enums_for_attr(self, section: str, attr: str) -> list:
        return self.enums.get(section, {}).get(attr, [])


pipeline = JungleSurvivorV2()
print(f"\\u2705 Pipeline 初始化完成 — {len(pipeline.plants)} species loaded")'''
    cells.append(code_cell(pipeline_code))

    # ── Cell: Load Model ──
    cells.append(md_cell(
        "## 🤖 Gemma 4 模型載入\n"
        "\n"
        "使用 `google/gemma-4-E4B-it` 多模態模型，專門用於看照片萃取結構化特徵。"
    ))

    model_code = '''# Cell 11: 載入 Gemma 4 多模態模型
from transformers import AutoProcessor, AutoModelForImageTextToText

processor = AutoProcessor.from_pretrained(MODEL_ID)
processor.image_seq_length = 560  # 280(預設)→560: 圖片細節更豐富，利於辨識葉面質感等

# E4B BF16 ~16GB，超過單張 T4 (14.56 GiB)，需要 device_map="auto" 分散到兩張 GPU
# transformers 會自動在前向傳遞時處理跨 GPU 的 tensor 搬移
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID,
    dtype=DTYPE,
    device_map="auto",
)
print(f"\\u2705 Model loaded: {MODEL_ID}")
print(f"   Device map: {model.hf_device_map}")
print(f"   Dtype: {model.dtype}")
for i in range(torch.cuda.device_count()):
    print(f"   GPU {i} Memory: {torch.cuda.memory_allocated(i) / 1024**3:.1f} GB used")'''
    cells.append(code_cell(model_code))

    # ── Cell: Identify Function ──
    cells.append(md_cell(
        "## 📸 辨識函式 — 從照片到結果\n"
        "\n"
        "1. 將 prompt_template + 照片送入 Gemma 4\n"
        "2. LLM 回傳結構化 JSON 特徵\n"
        "3. 特徵萃取 + 驗證 + 合併\n"
        "4. 演算法比對 KB → Top 3 結果\n"
        "5. 後處理：警告等級 + 混淆物種"
    ))

    identify_code = '''# Cell 12: 辨識函式

IMG_MAX_SIDE = 1600
IMG_MIN_SIDE = 256

def preprocess_image(image: Image.Image) -> Image.Image:
    """Resize image so the long side is at most IMG_MAX_SIDE pixels (LANCZOS)."""
    w, h = image.size
    if max(w, h) <= IMG_MAX_SIDE and min(w, h) >= IMG_MIN_SIDE:
        return image
    if max(w, h) > IMG_MAX_SIDE:
        ratio = IMG_MAX_SIDE / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        image = image.resize(new_size, Image.LANCZOS)
    return image


def _get_input_device():
    """Get the device for the model's first parameter (for multi-GPU device_map='auto')."""
    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cuda:0")

def call_gemma(image: Image.Image, prompt: str) -> str:
    """Send image + prompt to Gemma 4, return raw text response."""
    image = preprocess_image(image)
    content = [{"type": "image", "image": image}, {"type": "text", "text": prompt}]
    messages = [{"role": "user", "content": content}]

    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
    ).to(_get_input_device())

    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)

    input_len = inputs["input_ids"].shape[1]
    response = processor.decode(output_ids[0][input_len:], skip_special_tokens=True)
    return response


def identify_from_image(image: Image.Image, session_pipeline=None) -> str:
    """Full pipeline: image → Gemma 4 → features → matching → result display."""
    if session_pipeline is None:
        session_pipeline = pipeline

    prompt = session_pipeline.get_prompt()
    print("📸 正在呼叫 Gemma 4 萃取特徵...")
    llm_response = call_gemma(image, prompt)
    print(f"   LLM 回應長度: {len(llm_response)} chars")

    result = session_pipeline.extract_features_from_response(llm_response)
    if not result.success:
        return f"❌ 特徵萃取失敗: {result.error}\\n\\n原始回應:\\n{llm_response[:500]}"

    features = session_pipeline.get_current_features()
    feature_count = sum(
        len(v) if isinstance(v, dict) else 1
        for v in features.values()
    )
    print(f"   ✅ 萃取成功 — {feature_count} attributes across {len(features)} sections")
    if result.warnings:
        for w in result.warnings:
            print(f"   ⚠️ {w}")

    processed = session_pipeline.identify(top_n=3)
    display = session_pipeline.format_display(processed)
    return display


def identify_from_url(url: str) -> str:
    """Download image from URL and identify."""
    response = requests.get(url, timeout=30)
    image = Image.open(BytesIO(response.content)).convert("RGB")
    return identify_from_image(image)


print("✅ 辨識函式就緒")'''
    cells.append(code_cell(identify_code))

    # ── Cell: Demo ──
    cells.append(md_cell(
        "## 🧪 Demo 測試\n"
        "\n"
        "### 測試 1: 純演算法測試（不需要 GPU）\n"
        "模擬 LLM 已萃取好的特徵，直接測試計分引擎。"
    ))

    demo_code = '''# Cell 13: 演算法測試 — 模擬已萃取的特徵

test_pipeline = JungleSurvivorV2()

# 模擬姑婆芋特徵 (LLM 萃取結果)
alocasia_features = {
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
        "texture": "leathery"
    },
    "stem": {
        "type": "erect",
        "colors": ["green"],
        "surface": "smooth"
    },
    "flower": {
        "special_shape": "spathe",
        "arrangement": "spathe_spadix",
        "colors": ["green", "yellow"]
    }
}

mock_response = json.dumps(alocasia_features, ensure_ascii=False)
result = test_pipeline.extract_features_from_response(mock_response)
print(f"特徵萃取: {'✅ 成功' if result.success else '❌ 失敗'}")
if result.warnings:
    for w in result.warnings:
        print(f"  ⚠️ {w}")

processed = test_pipeline.identify(top_n=3)
print()
print(test_pipeline.format_display(processed))
print()
print("=" * 60)

# 測試 2: 模擬魚腥草特徵
test_pipeline.reset()
houttuynia_features = {
    "growth_form": "herb",
    "height_estimate": "<30cm",
    "smell": "fishy",
    "habitat": "streamside",
    "leaf": {
        "shape": "heart",
        "edge": "entire",
        "colors": ["green", "red_underside"],
        "surface_top": "matte",
        "arrangement": "alternate",
        "size": "medium_5-15cm"
    },
    "stem": {
        "type": "creeping",
        "colors": ["purple"]
    },
    "flower": {
        "colors": ["white"],
        "petal_count": "4",
        "arrangement": "spike"
    }
}

mock_response2 = json.dumps(houttuynia_features, ensure_ascii=False)
result2 = test_pipeline.extract_features_from_response(mock_response2)
print(f"特徵萃取: {'✅ 成功' if result2.success else '❌ 失敗'}")
processed2 = test_pipeline.identify(top_n=3)
print()
print(test_pipeline.format_display(processed2))'''
    cells.append(code_cell(demo_code))

    # ── Cell: Real Image Test ──
    cells.append(md_cell(
        "### 測試 2: 真實照片辨識（需要 GPU + Gemma 4）\n"
        "\n"
        "上傳照片或貼入 URL 進行測試。"
    ))

    real_test_code = '''# Cell 14: 真實照片辨識（取消註解並替換 URL 即可使用）

# pipeline.reset()
# result = identify_from_url("https://upload.wikimedia.org/wikipedia/commons/thumb/X/XX/example.jpg/800px-example.jpg")
# print(result)

# 或使用本機上傳：
# from google.colab import files  # Colab
# uploaded = files.upload()
# for name, data in uploaded.items():
#     img = Image.open(BytesIO(data)).convert("RGB")
#     pipeline.reset()
#     print(identify_from_image(img))

print("💡 取消上方註解並替換為實際圖片 URL 來測試真實照片辨識")'''
    cells.append(code_cell(real_test_code))

    # ── Cell: Multi-photo Test ──
    cells.append(md_cell(
        "### 測試 3: 多照片特徵合併"
    ))

    multi_code = '''# Cell 15: 多照片特徵合併測試

test_multi = JungleSurvivorV2()

# 第一張照片 — 只看到葉子
photo1 = json.dumps({
    "growth_form": "herb",
    "height_estimate": "1-2m",
    "leaf": {
        "shape": "heart",
        "edge": "entire",
        "colors": ["dark_green"],
        "surface_top": "glossy",
        "size": "very_large_>50cm",
        "venation": "pinnate"
    },
    "stem": {"type": "not_visible"},
    "flower": {"colors": "not_visible"}
})

r1 = test_multi.extract_features_from_response(photo1)
print(f"📸 Photo 1: {'✅' if r1.success else '❌'} — {test_multi.state.photo_count} photo(s)")

# 第二張照片 — 看到花和莖
photo2 = json.dumps({
    "flower": {
        "special_shape": "spathe",
        "arrangement": "spathe_spadix",
        "colors": ["green", "yellow"]
    },
    "stem": {
        "type": "erect",
        "colors": ["green"],
        "surface": "smooth"
    }
})

r2 = test_multi.extract_features_from_response(photo2)
print(f"📸 Photo 2: {'✅' if r2.success else '❌'} — {test_multi.state.photo_count} photo(s)")

# 合併結果
features = test_multi.get_current_features()
summary = test_multi.get_feature_summary()
print(f"\\n📊 特徵完整度:")
for section, info in summary.items():
    print(f"   {section}: {info['filled']}/{info['total']}")

processed = test_multi.identify(top_n=3)
print()
print(test_multi.format_display(processed))'''
    cells.append(code_cell(multi_code))

    # ── Cell: Gradio UI ──
    cells.append(md_cell(
        "## 🎨 Gradio 互動介面\n"
        "\n"
        "提供完整的互動式植物辨識介面：\n"
        "- 上傳照片 → AI 自動萃取特徵\n"
        "- Tab 分頁顯示每個特徵的下拉選單，可直接編輯\n"
        "- 多照片特徵自動聯集合併至下拉選單\n"
        "- 一鍵辨識 → 安全警告 + Top 3 結果"
    ))

    gradio_code = '''# Cell 16: Gradio 互動介面
import gradio as gr

SECTION_NAMES = {
    "overall": "整株特徵", "leaf": "葉", "stem": "莖",
    "flower": "花", "fruit": "果實", "root": "根/地下部",
}
SECTION_ORDER = ["overall", "leaf", "stem", "flower", "fruit", "root"]

ATTR_NAMES = {
    "growth_form": "生長型態", "height_estimate": "高度估計",
    "latex": "汁液", "smell": "氣味", "habitat": "棲地",
    "water_droplet_test": "水珠測試", "leaf_type": "葉型",
    "shape": "形狀", "edge": "葉緣", "tip": "葉尖", "base": "葉基",
    "colors": "顏色", "color_pattern": "色彩花紋",
    "surface_top": "葉面質感", "surface_bottom": "葉背質感",
    "arrangement": "排列", "size": "大小", "venation": "脈序",
    "texture": "質地", "petiole_attach": "葉柄著生",
    "type": "類型", "cross_section": "橫截面", "surface": "表面",
    "interior": "內部", "has_thorns": "有刺",
    "petal_count": "花瓣數", "symmetry": "對稱性",
    "position": "位置", "orientation": "朝向",
    "special_shape": "特殊形態", "fragrant": "有香味",
}

VALUE_ZH = {
    "herb": "草本", "shrub": "灌木", "tree": "喬木", "vine": "藤蔓",
    "fern": "蕨類", "fungus": "菇菌類", "grass": "禾草", "succulent": "多肉",
    "aquatic": "水生", "moss": "苔蘚", "palm_like": "棕櫚狀",
    "<30cm": "< 30cm", "30-100cm": "30-100cm", "1-2m": "1-2m",
    "2-5m": "2-5m", ">5m": "> 5m",
    "none": "無", "yes_white": "有（白色乳汁）", "yes_yellow": "有（黃色）",
    "yes_red": "有（紅色）", "yes_clear": "有（透明）",
    "aromatic": "芳香", "pungent": "刺鼻", "fishy": "魚腥味",
    "minty": "薄荷味", "spicy": "辛辣味", "rotten": "腐臭", "sweet": "甜香",
    "roadside": "路邊", "forest_floor": "林下", "streamside": "溪邊",
    "cliff_rock": "岩壁", "open_field": "空曠地", "wetland": "濕地",
    "epiphytic": "附生", "parasitic": "寄生", "urban": "都市", "coastal": "海岸",
    "beading": "水珠成珠", "flat": "水珠攤平",
    "simple": "單葉", "trifoliate": "三出複葉",
    "pinnate_compound": "羽狀複葉", "bipinnate_compound": "二回羽狀複葉",
    "palmate_compound": "掌狀複葉",
    "heart": "心形", "arrow": "箭形", "oval": "卵形", "elliptic": "橢圓",
    "lanceolate": "披針形", "linear": "線形", "needle": "針形",
    "scale": "鱗片狀", "round": "圓形", "spatulate": "匙形",
    "obovate": "倒卵形", "rhombic": "菱形", "fan": "扇形", "kidney": "腎形",
    "entire": "全緣", "serrated": "鋸齒", "double_serrated": "重鋸齒",
    "crenate": "圓齒", "lobed": "裂片", "deeply_lobed": "深裂",
    "wavy": "波狀", "spiny": "刺狀",
    "acute": "銳尖", "acuminate": "漸尖", "rounded": "圓鈍",
    "emarginate": "凹缺", "truncate": "截形",
    "cordate": "心形基", "cuneate": "楔形基", "sagittate": "箭形基",
    "peltate": "盾狀基",
    "light_green": "淺綠", "green": "綠色", "dark_green": "深綠",
    "yellow_green": "黃綠", "red": "紅色", "purple": "紫色",
    "variegated": "斑葉", "silver": "銀色", "brown": "褐色",
    "red_underside": "葉背紅", "white": "白色", "yellow": "黃色",
    "orange": "橘色", "pink": "粉紅", "blue": "藍色",
    "gray": "灰色", "white_powdery": "白粉狀", "black": "黑色",
    "white_waxy": "白蠟質",
    "solid": "單色", "gradient": "漸層", "spotted": "斑點",
    "striped": "條紋", "bicolor": "雙色", "center_different": "花心異色",
    "glossy": "光滑亮澤", "matte": "霧面", "hairy": "有毛",
    "rough": "粗糙", "waxy": "蠟質", "velvety": "天鵝絨",
    "pubescent": "柔毛", "scaly": "鱗片狀", "sandpaper": "砂紙狀",
    "alternate": "互生", "opposite": "對生", "whorled": "輪生",
    "rosette": "蓮座", "basal_rosette": "基生蓮座", "clustered": "叢生",
    "spiral": "螺旋", "two_ranked": "二列", "bird_nest_radial": "鳥巢放射狀",
    "tiny_<2cm": "極小 (< 2cm)", "small_2-5cm": "小 (2-5cm)",
    "medium_5-15cm": "中 (5-15cm)", "large_15-50cm": "大 (15-50cm)",
    "very_large_>50cm": "特大 (> 50cm)",
    "parallel": "平行脈", "pinnate": "羽狀脈", "palmate": "掌狀脈",
    "reticulate": "網狀脈", "single_midrib": "單主脈",
    "papery": "紙質", "leathery": "革質", "fleshy": "肉質",
    "membranous": "膜質",
    "normal": "一般著生", "peltate_shield": "盾狀",
    "sheathing": "鞘狀", "sessile": "無柄",
    "erect": "直立", "creeping": "匍匐", "climbing": "攀緣",
    "twining": "纏繞", "prostrate": "伏地", "rhizome": "根莖",
    "pseudostem": "假莖",
    "square": "方形", "triangular": "三角形",
    "flattened": "扁平", "ridged": "有稜",
    "smooth": "光滑", "thorny": "有刺", "bark_rough": "樹皮粗糙",
    "bark_smooth": "樹皮光滑",
    "hollow": "中空", "pithy": "有髓",
    "yes": "是", "no": "否",
    "0": "無花瓣", "3": "3 瓣", "4": "4 瓣", "5": "5 瓣",
    "6": "6 瓣", "many": "多瓣", "fused_tubular": "合瓣筒狀",
    "radial": "輻射對稱", "bilateral": "兩側對稱", "irregular": "不規則",
    "tiny_<5mm": "極小 (< 5mm)", "small_5-15mm": "小 (5-15mm)",
    "medium_15-30mm": "中 (15-30mm)", "large_30-60mm": "大 (30-60mm)",
    "very_large_>60mm": "特大 (> 60mm)",
    "solitary": "單生", "raceme": "總狀", "spike": "穗狀",
    "umbel": "繖形", "head_composite": "頭狀/菊科", "panicle": "圓錐",
    "cyme": "聚繖", "catkin": "柔荑", "spathe_spadix": "佛焰苞+肉穗",
    "terminal": "頂生", "axillary": "腋生", "basal": "基生",
    "cauliflorous": "莖生花",
    "upright": "向上", "horizontal": "水平", "drooping": "下垂",
    "lip_labellum": "唇瓣", "spur": "距", "spathe": "佛焰苞",
    "butterfly_shape": "蝶形", "bell_tubular": "鐘形/筒狀", "trumpet": "喇叭形",
    "berry": "漿果", "drupe": "核果", "capsule": "蒴果",
    "pod_legume": "莢果", "achene": "瘦果", "samara": "翅果",
    "nut": "堅果", "aggregate": "聚合果", "fig": "隱花果",
    "cone": "毬果", "spore": "孢子",
    "large_>30mm": "大 (> 30mm)", "medium_15-30mm": "中 (15-30mm)",
    "small_5-15mm": "小 (5-15mm)", "tiny_<5mm": "極小 (< 5mm)",
    "warty": "疣狀", "hooked_bristles": "鉤刺",
    "fibrous": "鬚根", "taproot": "主根", "tuberous": "塊根",
    "bulb": "鱗莖", "corm": "球莖", "aerial_root": "氣生根",
    "storage_tuber": "儲藏塊莖",
    "not_visible": "看不到", "uncertain": "不確定", "not_checkable": "無法檢查",
}


def val_to_zh(v):
    return VALUE_ZH.get(v, v)


ui_pipeline = JungleSurvivorV2()

# Build ordered attribute list from schema (used to map dropdowns ↔ features)
_schema_clean = {k: v for k, v in FEATURE_SCHEMA.items() if not k.startswith("_")}
ATTR_ORDER = []
for _s in SECTION_ORDER:
    for _a, _d in _schema_clean.get(_s, {}).items():
        if _d["type"] != "boolean":
            ATTR_ORDER.append((_s, _a, _d))
N_ATTRS = len(ATTR_ORDER)


def _no_change():
    """Return gr.update() for every dropdown (no visual change)."""
    return tuple(gr.update() for _ in range(N_ATTRS))


def _get_dropdown_updates():
    """Return gr.update(value=...) for every dropdown from current features."""
    features = ui_pipeline.get_current_features()
    updates = []
    for sec, attr, adef in ATTR_ORDER:
        val = features.get(sec, {}).get(attr)
        if val is None:
            updates.append(gr.update(value=[] if adef["type"] == "array" else None))
        else:
            updates.append(gr.update(value=val))
    return tuple(updates)


def _clear_dropdowns():
    return tuple(
        gr.update(value=[] if ad["type"] == "array" else None)
        for _, _, ad in ATTR_ORDER
    )


def _sync_overrides(dd_vals):
    """Compare dropdown values with AI accumulated features; differences become overrides."""
    if not ui_pipeline.state.accumulated_features:
        return
    for i, (sec, attr, adef) in enumerate(ATTR_ORDER):
        val = dd_vals[i]
        ai_val = ui_pipeline.state.accumulated_features.get(sec, {}).get(attr)
        if adef["type"] == "array":
            v_list = val if isinstance(val, list) else ([] if val is None else [val])
            a_list = ai_val if isinstance(ai_val, list) else ([] if ai_val is None else [ai_val])
            if sorted(str(x) for x in v_list) != sorted(str(x) for x in a_list):
                if v_list:
                    ui_pipeline.set_user_feature(sec, attr, v_list)
                else:
                    ui_pipeline.remove_user_override(sec, attr)
            else:
                ui_pipeline.remove_user_override(sec, attr)
        else:
            if val != ai_val and val is not None:
                ui_pipeline.set_user_feature(sec, attr, val)
            else:
                ui_pipeline.remove_user_override(sec, attr)


def format_history_md():
    ext = ui_pipeline.state.extraction_logs
    ids = ui_pipeline.state.identification_logs
    lines = []
    if ext:
        lines.append("### LLM 特徵萃取紀錄")
        lines.append("| # | 耗時 | 結果 | 回應長度 | 特徵數 | 警告 |")
        lines.append("|---|------|------|----------|--------|------|")
        for i, log in enumerate(ext, 1):
            st = "\\u2705" if log["success"] else "\\u274c"
            lines.append(
                f"| {i} | {log['time_sec']:.1f}s | {st} "
                f"| {log['resp_len']} | {log['feature_count']} | {log['warning_count']} |"
            )
        lines.append("")
    if ids:
        lines.append("### 辨識紀錄")
        lines.append("| # | 耗時 | 照片 | Top 1 | 信心度 | 警告等級 |")
        lines.append("|---|------|------|-------|--------|----------|")
        for i, log in enumerate(ids, 1):
            lines.append(
                f"| {i} | {log['time_sec']:.2f}s | {log['photo_count']} "
                f"| {log['top1']} | {log['top1_score']} | {log['warning_level']} |"
            )
        lines.append("")
    if not lines:
        return "尚無紀錄。"
    return "\\n".join(lines)


def _get_final_features_json():
    """Return the merged features (accumulated + overrides) for the JSON display."""
    features = ui_pipeline.get_current_features()
    return features if features else {}

# ── Event Handlers ──

def on_upload_photo(image, *dd_vals):
    _sync_overrides(dd_vals)
    if image is None:
        yield ("請上傳照片",) + _no_change() + (gr.update(), gr.update())
        return
    yield ("\\u23f3 AI 正在萃取特徵...",) + _no_change() + (gr.update(), gr.update())
    pil_image = Image.fromarray(image).convert("RGB")
    prompt = ui_pipeline.get_prompt()
    try:
        t0 = time.time()
        llm_response = call_gemma(pil_image, prompt)
        llm_time = time.time() - t0
        result = ui_pipeline.extract_features_from_response(llm_response)
        ui_pipeline.log_extraction(llm_time, len(llm_response), result)
        if not result.success:
            yield (f"\\u274c 萃取失敗: {result.error}",) + _no_change() + (format_history_md(), _get_final_features_json())
            return
        status = f"\\u2705 第 {ui_pipeline.state.photo_count} 張照片（{llm_time:.1f}s）"
        if result.warnings:
            status += "\\n" + "\\n".join(f"\\u26a0\\ufe0f {w}" for w in result.warnings)
        yield (status,) + _get_dropdown_updates() + (format_history_md(), _get_final_features_json())
    except Exception as e:
        yield (f"\\u274c 錯誤: {str(e)}",) + _no_change() + (format_history_md(), _get_final_features_json())


def on_paste_json(json_text, *dd_vals):
    _sync_overrides(dd_vals)
    if not json_text.strip():
        return ("請貼入 JSON",) + _no_change() + (gr.update(), gr.update())
    t0 = time.time()
    result = ui_pipeline.extract_features_from_response(json_text)
    parse_time = time.time() - t0
    ui_pipeline.log_extraction(parse_time, len(json_text), result)
    if not result.success:
        return (f"\\u274c 萃取失敗: {result.error}",) + _no_change() + (format_history_md(), _get_final_features_json())
    status = f"\\u2705 第 {ui_pipeline.state.photo_count} 張（{parse_time:.2f}s）"
    if result.warnings:
        status += "\\n" + "\\n".join(f"\\u26a0\\ufe0f {w}" for w in result.warnings)
    return (status,) + _get_dropdown_updates() + (format_history_md(), _get_final_features_json())


def on_identify(*dd_vals):
    _sync_overrides(dd_vals)
    features = ui_pipeline.get_current_features()
    if not features:
        return "請先上傳照片或輸入特徵。", format_history_md(), _get_final_features_json()
    t0 = time.time()
    processed = ui_pipeline.identify(top_n=3)
    id_time = time.time() - t0
    ui_pipeline.log_identification(id_time, processed)
    display = ui_pipeline.format_display(processed)
    display = display.replace("<", "&lt;")
    return display, format_history_md(), _get_final_features_json()


def on_reset():
    old_ext = ui_pipeline.state.extraction_logs
    old_ids = ui_pipeline.state.identification_logs
    ui_pipeline.reset()
    ui_pipeline.state.extraction_logs = old_ext
    ui_pipeline.state.identification_logs = old_ids
    return ("\\u2705 已重置",) + _clear_dropdowns() + ("等待辨識...", format_history_md(), {})


# ── Build Gradio UI ──

with gr.Blocks(title="JungleSurvivor v2", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# \\U0001f33f JungleSurvivor v2 — 野外植物辨識系統")
    gr.Markdown(
        "### \\U0001f4f7 拍攝與使用指南\\n"
        "1. **拍照**：對準植物拍攝 **3 張或以上**不同特徵的正面照片：\\n"
        "   - \\u2460 整株植物全貌（須清楚拍到莖部）\\n"
        "   - \\u2461 葉子正上方特寫（展示葉形、葉脈、葉緣）\\n"
        "   - \\u2462 花朵或果實正面特寫（若有的話）\\n"
        "2. **上傳** \\u2192 逐張點選「AI 萃取特徵」，每上傳一張會自動合併\\n"
        "3. **手動修正**：查看下方特徵選單，修正 AI 判斷有誤的項目\\n"
        "4. **辨識** \\u2192 查看結果中的生存用途資訊 \\u2192 翻閱下方「叢林生存指南」\\n\\n"
        "> \\U0001f4a1 手動輸入越多正確特徵，辨識結果越準確。"
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## \\U0001f4f8 輸入")
            image_input = gr.Image(label="上傳植物照片", type="numpy")
            upload_btn = gr.Button("\\U0001f4f7 AI 萃取特徵", variant="primary")
            status_output = gr.Textbox(label="萃取狀態", interactive=False, lines=4)

            with gr.Accordion("\\U0001f4cb JSON 測試", open=False):
                json_input = gr.Textbox(label="JSON 特徵", lines=4,
                    placeholder='{"growth_form":"herb","leaf":{"shape":"heart",...}}')
                json_btn = gr.Button("\\U0001f4cb 載入 JSON")

        with gr.Column(scale=2):
            gr.Markdown("## \\U0001f4cb 特徵（直接編輯下拉選單即可覆蓋）")

            dropdowns = []
            with gr.Tabs():
                for _sec in SECTION_ORDER:
                    _sec_schema = _schema_clean.get(_sec, {})
                    _sec_attrs = [(_a, _d) for _a, _d in _sec_schema.items() if _d["type"] != "boolean"]
                    if not _sec_attrs:
                        continue
                    with gr.TabItem(SECTION_NAMES.get(_sec, _sec)):
                        for _a, _d in _sec_attrs:
                            _is_multi = _d["type"] == "array"
                            _enum_vals = DERIVED_ENUMS.get(_sec, {}).get(_a, [])
                            _choices = [(val_to_zh(v), v) for v in _enum_vals]
                            _dd = gr.Dropdown(
                                choices=_choices,
                                multiselect=_is_multi,
                                label=ATTR_NAMES.get(_a, _a),
                                interactive=True,
                            )
                            dropdowns.append(_dd)

            with gr.Row():
                identify_btn = gr.Button("\\U0001f50d 開始辨識", variant="primary", size="lg")
                reset_btn = gr.Button("\\U0001f504 重新開始", variant="stop")

            gr.Markdown("## 結果")
            result_output = gr.Markdown("等待辨識...")

            with gr.Accordion("\\U0001f4ca 歷史紀錄", open=False):
                history_display = gr.Markdown("尚無紀錄。")

            with gr.Accordion("\\U0001f50d 目前特徵 JSON", open=False):
                feature_json_display = gr.JSON(label="合併後特徵（AI + 使用者覆蓋）")

    gr.Markdown("---")
    gr.Markdown("## \\U0001f33f 叢林生存指南")
    gr.Markdown("辨識植物後，可在此查詢烹調處理方式、藥用方法、求生技巧等實用資訊。")
    with gr.Tabs():
        for _gcat in GUIDE_ORDER:
            _ginfo = GUIDE_RENDERED.get(_gcat, {})
            if _ginfo:
                _gt = f'{_ginfo.get("icon","")} {_ginfo.get("title", _gcat)}'
                with gr.TabItem(_gt):
                    gr.HTML(_ginfo.get("html", ""))

    # ── Event Bindings ──
    _up_outs = [status_output] + dropdowns + [history_display, feature_json_display]
    upload_btn.click(on_upload_photo, [image_input] + dropdowns, _up_outs)
    json_btn.click(on_paste_json, [json_input] + dropdowns, _up_outs)
    identify_btn.click(on_identify, dropdowns, [result_output, history_display, feature_json_display])
    _rst_outs = [status_output] + dropdowns + [result_output, history_display, feature_json_display]
    reset_btn.click(on_reset, [], _rst_outs)

demo.launch(share=True, debug=True)'''
    cells.append(code_cell(gradio_code))

    # ── Assemble Notebook ──
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10.0",
            },
            "kaggle": {
                "accelerator": "gpu",
                "dataSources": [],
                "isGpuEnabled": True,
                "isInternetEnabled": True,
            },
        },
        "cells": cells,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(notebook, f, ensure_ascii=False, indent=2)

    print(f"Notebook written to: {OUT_PATH}")
    print(f"Total cells: {len(cells)}")
    print(f"File size: {OUT_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build_notebook()