#!/usr/bin/env python3
"""Assemble kaggle_gradio_demo.ipynb from app sources and knowledge_base JSON files."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
KB_REGION = ROOT / "knowledge_base" / "regions" / "east_asia_subtropical"
KB_EM = ROOT / "knowledge_base" / "emergency"
OUT = Path(__file__).resolve().parent / "kaggle_gradio_demo.ipynb"


def nb_source(s: str) -> list:
    if not s.endswith("\n"):
        s += "\n"
    parts = s.split("\n")
    return [p + "\n" for p in parts]


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def embed_kb_assign(name: str, data) -> str:
    inner = json.dumps(json.dumps(data, ensure_ascii=False))
    return f"{name} = json.loads({inner})\n"


def build_context_engine() -> str:
    src = read_text(APP / "context_engine.py")
    src = src.replace("import json\n", "")
    src = src.replace("from pathlib import Path\n", "")
    src = src.replace(
        "from config import REGIONS_PATH, EMERGENCY_PATH, AVAILABLE_REGIONS, DEFAULT_REGION\n",
        "",
    )
    src = re.sub(
        r"\ndef _load_json\(path: Path\) -> list \| dict:[\s\S]*?\n\n(?=def load_knowledge_base)",
        "\n",
        src,
        count=1,
    )
    start = src.index("def load_knowledge_base")
    end = src.index("\ndef create_context", start)
    new_lb = """def load_knowledge_base(region_id: str = DEFAULT_REGION) -> KnowledgeBase:
    \"\"\"直接從嵌入的知識庫資料載入\"\"\"
    return KnowledgeBase(
        toxic_plants=_KB_TOXIC_PLANTS,
        confusion_pairs=_KB_CONFUSION_PAIRS,
        edible_plants=_KB_EDIBLE_PLANTS,
        dangerous_animals=_KB_DANGEROUS_ANIMALS,
        snakebite_first_aid=_KB_SNAKEBITE_FIRST_AID,
        plant_poisoning_first_aid=_KB_PLANT_POISONING,
        wound_care=_KB_WOUND_CARE,
    )

"""
    src = src[:start] + new_lb + src[end:]
    return src.strip() + "\n"


def build_prompt_builder() -> str:
    src = read_text(APP / "prompt_builder.py")
    for line in (
        "from context_engine import EnvironmentContext, KnowledgeBase\n",
        "from config import JSON_START_MARKER, JSON_END_MARKER, THRESHOLDS\n",
    ):
        src = src.replace(line, "")
    return src.strip() + "\n"


def build_response_parser() -> str:
    src = read_text(APP / "response_parser.py")
    src = src.replace(
        "from config import JSON_START_MARKER, JSON_END_MARKER\n",
        "",
    )
    return src.strip() + "\n"


def build_model_loader() -> str:
    src = read_text(APP / "model_loader.py")
    m = re.search(
        r"(class GemmaModel:[\s\S]*?)(?:\n\nclass OllamaModel:)",
        src,
    )
    if not m:
        raise RuntimeError("Could not extract GemmaModel class")
    block = m.group(1).strip() + "\n"
    block = block.replace(
        "from config import MODEL_ID, MAX_NEW_TOKENS, DEFAULT_DTYPE\n",
        "",
    )
    block = block.replace("from PIL import Image\n", "")
    return block


def build_pipeline() -> str:
    src = read_text(APP / "pipeline.py")
    src = src.replace("\r\n", "\n")
    src = re.sub(r"^from config import THRESHOLDS\n", "", src, flags=re.M)
    src = re.sub(
        r"^from context_engine import .*\n",
        "",
        src,
        flags=re.M,
    )
    src = re.sub(
        r"^from prompt_builder import \(\n(?:^    .*\n)*^\)\n",
        "",
        src,
        flags=re.M,
    )
    src = re.sub(
        r"^from response_parser import \(\n(?:^    .*\n)*^\)\n",
        "",
        src,
        flags=re.M,
    )
    return src.strip() + "\n"


def kb_embed_cell() -> str:
    toxic = json.loads(read_text(KB_REGION / "toxic_plants.json"))
    edible = json.loads(read_text(KB_REGION / "edible_plants.json"))
    danger = json.loads(read_text(KB_REGION / "dangerous_animals.json"))
    conf = json.loads(read_text(KB_REGION / "confusion_pairs.json"))
    sn = json.loads(read_text(KB_EM / "snakebite_first_aid.json"))
    pp = json.loads(read_text(KB_EM / "plant_poisoning_first_aid.json"))
    wc = json.loads(read_text(KB_EM / "wound_care.json"))
    bee = json.loads(read_text(KB_EM / "bee_sting_first_aid.json"))
    arth = json.loads(read_text(KB_EM / "arthropod_bite_first_aid.json"))

    lines = ["import json\n", "\n"]
    lines.append(embed_kb_assign("_KB_TOXIC_PLANTS", toxic))
    lines.append("\n")
    lines.append(embed_kb_assign("_KB_EDIBLE_PLANTS", edible))
    lines.append("\n")
    lines.append(embed_kb_assign("_KB_DANGEROUS_ANIMALS", danger))
    lines.append("\n")
    lines.append(embed_kb_assign("_KB_CONFUSION_PAIRS", conf))
    lines.append("\n")
    lines.append(embed_kb_assign("_KB_SNAKEBITE_FIRST_AID", sn))
    lines.append("\n")
    lines.append(embed_kb_assign("_KB_PLANT_POISONING", pp))
    lines.append("\n")
    lines.append(embed_kb_assign("_KB_WOUND_CARE", wc))
    lines.append("\n")
    lines.append(embed_kb_assign("_KB_BEE_STING", bee))
    lines.append("\n")
    lines.append(embed_kb_assign("_KB_ARTHROPOD_BITE", arth))
    lines.append("\n")
    lines.append(
        'print(f"✅ 知識庫載入完成：")\n'
        'print(f"   有毒植物：{len(_KB_TOXIC_PLANTS)} 種")\n'
        'print(f"   可食植物：{len(_KB_EDIBLE_PLANTS)} 種")\n'
        'print(f"   危險動物：{len(_KB_DANGEROUS_ANIMALS)} 種")\n'
        'print(f"   混淆物種對：{len(_KB_CONFUSION_PAIRS)} 組")\n'
        'print(f"   急救 SOP：5 份")\n'
    )
    return "".join(lines)


GRADIO_CELL = r'''import gradio as gr
from datetime import datetime as _dt

_pipeline = None
_model_loaded = False

def _init_model():
    global _pipeline, _model_loaded
    if _model_loaded and _pipeline is not None:
        return "✅ 模型已載入，無需重複載入。"
    try:
        if '_demo_model' in dir():
            model = _demo_model
        elif '_demo_model' in globals():
            model = globals()['_demo_model']
        else:
            model = GemmaModel()
        _pipeline = JungleSurvivorPipeline(model)
        _model_loaded = True
        return "✅ 模型載入成功！可以開始辨識。"
    except Exception as e:
        _model_loaded = False
        return f"❌ 模型載入失敗：{e}"

_S = {
    "RED":    {"bg":"#FFF0F0","bd":"#FF0000","tx":"#CC0000","em":"🔴"},
    "YELLOW": {"bg":"#FFFBE6","bd":"#FFD700","tx":"#996600","em":"🟡"},
    "GREEN":  {"bg":"#F0FFF4","bd":"#00AA00","tx":"#006600","em":"🟢"},
    "GRAY":   {"bg":"#F5F5F5","bd":"#888888","tx":"#555555","em":"⚪"},
}
_WL = {"RED":"🔴 危險","YELLOW":"🟡 注意","GREEN":"🟢 安全","GRAY":"⚪ 不確定"}

def _result_html(r):
    s = _S.get(r.warning_level, _S["GRAY"])
    lbl = _WL.get(r.warning_level, "⚪ 不確定")
    sm = r.summary_zh.replace("\n", "<br>")
    return (
        f'<div style="border:3px solid {s["bd"]};border-radius:12px;padding:20px;'
        f'background:{s["bg"]};margin:8px 0;">'
        f'<h2 style="color:{s["tx"]};margin:0 0 12px 0;">{lbl}</h2>'
        f'<div style="font-size:15px;line-height:1.8;color:#333;white-space:pre-line;">{sm}</div></div>'
    )

def _detail_md(r):
    parts = []
    if r.reasoning:
        parts.append("### 🧠 AI 分析\n\n" + r.reasoning)
    if r.candidates:
        parts.append("### 📊 候選排名\n")
        for c in r.candidates:
            cat_icon = {"dangerous": "⚠️", "edible": "🍃", "medicinal": "💊"}.get(c.category, "❓")
            parts.append(f"**#{c.rank}** {cat_icon} {c.common_name_zh} (*{c.scientific_name}*) — {c.confidence}%")
            if c.key_matching_features:
                parts.append(f"   匹配特徵：{'、'.join(c.key_matching_features)}")
            if c.danger_info and c.danger_info.get("toxicity"):
                parts.append(f"   ⚠️ 毒性：{c.danger_info['toxicity']}")
    if r.observed_features:
        parts.append("\n### 🔍 觀察到的特徵\n\n" + "、".join(r.observed_features))
    if hasattr(r, 'confusion_warnings') and r.confusion_warnings:
        parts.append("\n### 🔀 混淆物種對照\n")
        for cw in r.confusion_warnings:
            parts.append(f"**「{cw.candidate_name}」⟷「{cw.confused_with}」**")
            if cw.distinguishing_features:
                parts.append("關鍵區別：")
                for feat in cw.distinguishing_features[:5]:
                    parts.append(f"- {feat}")
            if cw.interactive_tests:
                parts.append(f"🧪 建議測試：{'、'.join(cw.interactive_tests)}")
    return "\n\n".join(parts) if parts else "（無詳細分析）"

def _inter_html(r):
    if not r.interactive_guidance:
        return "<p style='color:#888;'>（不需要互動測試）</p>"
    g = r.interactive_guidance.replace("\n", "<br>")
    return (
        '<div style="border:3px solid #FF6600;border-radius:12px;padding:20px;'
        'background:#FFF8F0;margin:8px 0;">'
        '<h3 style="color:#CC5500;margin:0 0 10px 0;">🔬 互動測試指引</h3>'
        f'<div style="font-size:14px;line-height:1.8;color:#333;">{g}</div></div>'
    )

def _hist_html(h):
    if not h:
        return "<p style='color:#888;text-align:center;'>尚無辨識紀錄</p>"
    rows = ""
    for i, x in enumerate(reversed(h)):
        s = _S.get(x["level"], _S["GRAY"])
        rows += (
            f'<tr style="background:{s["bg"]};">'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{len(h)-i}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{x["time"]}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{s["em"]} {x["species"]}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{x["conf"]}%</td>'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{x["mode"]}</td></tr>'
        )
    return (
        '<table style="width:100%;border-collapse:collapse;font-size:14px;">'
        '<thead><tr style="background:#f0f0f0;">'
        '<th style="padding:8px;text-align:left;">#</th>'
        '<th style="padding:8px;text-align:left;">時間</th>'
        '<th style="padding:8px;text-align:left;">辨識結果</th>'
        '<th style="padding:8px;text-align:left;">信心度</th>'
        '<th style="padding:8px;text-align:left;">模式</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
    )

def _open_image(im):
    from PIL import Image as _Img
    if isinstance(im, _Img.Image):
        return im.convert("RGB")
    if isinstance(im, tuple):
        return _Img.open(im[0]).convert("RGB")
    if isinstance(im, dict):
        path = im.get("name") or im.get("path") or im.get("image", {}).get("path", "")
        if isinstance(path, dict):
            path = path.get("path", "")
        return _Img.open(path).convert("RGB")
    if isinstance(im, str):
        return _Img.open(im).convert("RGB")
    return _Img.open(str(im)).convert("RGB")

def _identify(images, desc, country, alt, veg, mode, hist):
    if not _model_loaded or _pipeline is None:
        return "<p style='color:red;'>❌ 請先載入模型</p>", "", "", _hist_html(hist), hist
    if images is None or len(images) == 0:
        return "<p style='color:red;'>❌ 請上傳至少一張照片</p>", "", "", _hist_html(hist), hist

    pil = []
    for im in images:
        try:
            pil.append(_open_image(im))
        except Exception as img_err:
            return (
                f"<p style='color:red;'>❌ 照片載入失敗：{img_err}<br>type={type(im)}, value={repr(im)[:200]}</p>",
                "", "", _hist_html(hist), hist,
            )

    ctx = create_context(country=country, altitude=int(alt), vegetation_zone=veg)
    _mm = {
        "自動（兩階段辨識）": "auto",
        "這個有毒嗎？（危險快篩）": "auto",
        "這個能吃嗎？（食物辨識）": "auto",
        "這是什麼動物？（動物辨識）": "animal",
    }
    pm = _mm.get(mode, "auto")
    d = desc.strip() if desc and desc.strip() else None

    try:
        res = _pipeline.identify(pil, ctx, mode=pm, description=d)
        sp = res.candidates[0].common_name_zh if res.candidates else "未知"
        conf = res.candidates[0].confidence if res.candidates else 0
        hist.append({
            "time": _dt.now().strftime("%H:%M:%S"),
            "species": sp, "conf": conf,
            "level": res.warning_level,
            "mode": mode.split("（")[0],
        })
        return _result_html(res), _detail_md(res), _inter_html(res), _hist_html(hist), hist
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"<p style='color:red;'>❌ 辨識過程發生錯誤：{e}</p>", "", "", _hist_html(hist), hist

with gr.Blocks(title="JungleSurvivor", theme=gr.themes.Soft()) as demo:
    hist_state = gr.State([])
    gr.HTML(
        '<div style="text-align:center;">'
        '<h1>🌿 JungleSurvivor — 叢林求生離線 AI 助手</h1>'
        '<p style="color:#666;">拍攝照片，AI 比對危險物種與可食物種，取信心度最高的前三名候選。<br>'
        '信心度 = 形態特徵吻合度（絕對值，越多特徵符合分數越高）<br>'
        '<b>安全第一</b> — 寧可誤報也不漏報。無法確定時一律視為危險。</p></div>'
    )

    with gr.Row():
        load_btn = gr.Button("🚀 載入模型", variant="primary", scale=1)
        load_st = gr.Textbox(label="載入狀態", interactive=False, scale=3)
    load_btn.click(fn=_init_model, inputs=[], outputs=[load_st])
    gr.HTML("<hr>")

    with gr.Row():
        with gr.Column(scale=1):
            img_in = gr.Gallery(label="📷 上傳照片（可多張，多角度可提升信心度）", type="filepath", columns=3, height=280)
            desc_in = gr.Textbox(label="📝 補充描述（選填）", placeholder="例如：葉子搓碎有辛辣味、莖切開有白色乳汁...", lines=2)
            mode_sel = gr.Dropdown(
                choices=["自動（兩階段辨識）", "這個有毒嗎？（危險快篩）",
                         "這個能吃嗎？（食物辨識）", "這是什麼動物？（動物辨識）"],
                value="自動（兩階段辨識）", label="辨識模式")
            gr.Markdown("#### 🌏 環境設定")
            country_in = gr.Textbox(value="台灣", label="地點")
            alt_in = gr.Slider(minimum=0, maximum=4000, value=500, step=100, label="海拔（公尺）")
            veg_in = gr.Dropdown(
                choices=["低海拔闊葉林", "中海拔闊葉林", "中高海拔針闊混合林",
                         "高海拔針葉林", "高山草原", "海岸地帶", "溪邊濕地"],
                value="低海拔闊葉林", label="植被帶")
            alt_in.change(fn=get_vegetation_zone, inputs=[alt_in], outputs=[veg_in])
            id_btn = gr.Button("🔍 開始辨識", variant="primary", size="lg")

        with gr.Column(scale=1):
            main_out = gr.HTML(label="辨識結果")
            with gr.Accordion("🔬 混淆物種 & 互動測試指引", open=True):
                inter_out = gr.HTML()
            with gr.Accordion("📋 詳細分析（Chain of Thought）", open=False):
                detail_out = gr.Markdown()

    gr.HTML("<hr>")
    with gr.Accordion("📜 歷史紀錄", open=True):
        hist_disp = gr.HTML(value="<p style='color:#888;text-align:center;'>尚無辨識紀錄</p>")

    id_btn.click(
        fn=_identify,
        inputs=[img_in, desc_in, country_in, alt_in, veg_in, mode_sel, hist_state],
        outputs=[main_out, detail_out, inter_out, hist_disp, hist_state],
    )

    gr.HTML(
        '<hr><div style="text-align:center;color:#888;font-size:13px;">'
        f'<b>辨識流程</b> | Stage 1：危險物種比對（Top 3）→ Stage 2：可食/藥用比對（Top 3）→ 合併取 Top 3<br>'
        f'<b>信心度</b> = 特徵吻合的絕對值（越多特徵符合分數越高，與排名無關）<br>'
        '<b>免責聲明</b>：本工具僅供參考，不能取代專業鑑定。在野外，寧可不吃也不誤食。</div>'
    )

demo.launch(share=True, debug=True)
'''

CELL0 = r"""# 🌿 JungleSurvivor — Kaggle Gradio Demo

**叢林求生離線 AI 助手 — 互動式 Demo**

上傳植物/動物照片，AI 辨識危險物種、可食植物、毒蛇，並提供求生建議。

**環境需求：** Kaggle Notebook + GPU T4 x2 + Gemma 4 E2B

**功能：**
1. 兩階段辨識系統（Stage 1 危險物種 → Stage 2 可食/藥用物種 → 合併取 Top 3）
2. 混淆物種自動偵測 + 互動式測試引導
3. 絕對信心度評估（特徵吻合越多 → 分數越高）
4. 進一步觀察指引（多角度拍攝、野外可食性測試）
5. 歷史紀錄追蹤
6. 多照片支援

**知識庫：** 有毒植物 20 種 | 可食植物 20 種 | 危險動物 13 種 | 混淆對 12 組 | 急救 SOP 5 份
"""

CELL1 = r"""!pip install -q --upgrade transformers accelerate gradio

import json, re, os, torch, requests
from io import BytesIO
from PIL import Image
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from transformers import AutoProcessor, AutoModelForImageTextToText

print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU count: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        mem = torch.cuda.get_device_properties(i).total_memory / 1024**3
        print(f"         VRAM: {mem:.1f} GB")
"""

CELL2 = r"""# === 模型設定 ===
MODEL_ID = "google/gemma-4-E2B-it"
MAX_NEW_TOKENS = 4096
DEFAULT_DTYPE = "bfloat16"

# === 辨識閾值 ===
THRESHOLDS = {
    "danger_screening": 60,
    "confusion_pairs": 80,
    "useful_resources": 70,
}

DEFAULT_REGION = "east_asia_subtropical"

AVAILABLE_REGIONS = {
    "east_asia_subtropical": {
        "name_zh": "東亞亞熱帶（台灣、華南、日本南部）",
        "climate_zone": "亞熱帶",
        "default_altitude": 500,
        "default_vegetation": "低海拔闊葉林",
    },
}

JSON_START_MARKER = "<JSON_START>"
JSON_END_MARKER = "<JSON_END>"

WARNING_LEVELS = {
    "RED": {"color": "#FF0000", "label_zh": "🔴 危險", "action": "立即遠離"},
    "YELLOW": {"color": "#FFD700", "label_zh": "🟡 注意", "action": "謹慎處理"},
    "GREEN": {"color": "#00AA00", "label_zh": "🟢 安全", "action": "可安全使用"},
    "GRAY": {"color": "#888888", "label_zh": "⚪ 不確定", "action": "無法判斷，建議不碰"},
}
"""

CELL3 = r"""## 📚 知識庫嵌入

以下 Cell 包含完整的離線知識庫資料（20 種有毒植物、20 種可食植物、13 種危險動物、12 組混淆對、5 份急救 SOP）。
"""

CELL5 = r"""## 🧠 核心辨識模組
"""

CELL11 = r"""## 🚀 載入模型

執行此 Cell 載入 Gemma 4 模型（約需 1-2 分鐘）。
"""

CELL12 = r"""print("正在載入 Gemma 4 E2B 模型...")
_demo_model = GemmaModel()
print("✅ 模型載入完成！")
print(f"   模型：{_demo_model.model_id}")
print(f"   裝置：{_demo_model._device}")
"""

CELL13 = r"""## 🎮 Gradio 互動介面

執行下方 Cell 啟動互動介面。介面啟動後會產生一個公開 URL，可在瀏覽器中開啟。

**使用方式：**
1. 點擊「載入模型」（如果上方已載入則會直接使用）
2. 上傳照片（支援多張）
3. 選擇辨識模式和環境設定
4. 點擊「開始辨識」
"""


def main():
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": nb_source(CELL0), "id": "title"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(CELL1), "execution_count": None, "outputs": [], "id": "imports"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(CELL2), "execution_count": None, "outputs": [], "id": "config"},
        {"cell_type": "markdown", "metadata": {}, "source": nb_source(CELL3), "id": "md-kb"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(kb_embed_cell()), "execution_count": None, "outputs": [], "id": "kb-embed"},
        {"cell_type": "markdown", "metadata": {}, "source": nb_source(CELL5), "id": "md-core"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(build_context_engine()), "execution_count": None, "outputs": [], "id": "context-engine"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(build_prompt_builder()), "execution_count": None, "outputs": [], "id": "prompt-builder"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(build_response_parser()), "execution_count": None, "outputs": [], "id": "response-parser"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(build_model_loader()), "execution_count": None, "outputs": [], "id": "model-loader"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(build_pipeline()), "execution_count": None, "outputs": [], "id": "pipeline"},
        {"cell_type": "markdown", "metadata": {}, "source": nb_source(CELL11), "id": "md-load-model"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(CELL12), "execution_count": None, "outputs": [], "id": "load-model"},
        {"cell_type": "markdown", "metadata": {}, "source": nb_source(CELL13), "id": "md-gradio"},
        {"cell_type": "code", "metadata": {}, "source": nb_source(GRADIO_CELL), "execution_count": None, "outputs": [], "id": "gradio-ui"},
    ]

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }

    with OUT.open("w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=2)

    sz = OUT.stat().st_size
    (OUT.parent / ".rebuild_notebook_bytes.txt").write_text(str(sz), encoding="utf-8")
    print(f"Wrote {OUT} ({sz} bytes)")


if __name__ == "__main__":
    main()
