"""
JungleSurvivor — 叢林求生離線 AI 助手
Gradio UI 入口（含歷史紀錄、警告色彩、互動測試面板）
"""

import gradio as gr
from PIL import Image
from typing import Optional
from datetime import datetime

from config import THRESHOLDS, WARNING_LEVELS, AVAILABLE_REGIONS
from context_engine import create_context, get_vegetation_zone
from model_loader import load_model
from pipeline import JungleSurvivorPipeline, PipelineResult

pipeline: Optional[JungleSurvivorPipeline] = None
model_loaded = False


def init_model(mode: str = "auto"):
    global pipeline, model_loaded
    if model_loaded and pipeline is not None:
        return "✅ 模型已載入，無需重複載入。"
    try:
        model = load_model(mode=mode)
        pipeline = JungleSurvivorPipeline(model)
        model_loaded = True
        return "✅ 模型載入成功！可以開始辨識。"
    except Exception as e:
        model_loaded = False
        return f"❌ 模型載入失敗：{e}"


_STYLE = {
    "RED":    {"bg": "#FFF0F0", "border": "#FF0000", "text": "#CC0000", "emoji": "🔴"},
    "YELLOW": {"bg": "#FFFBE6", "border": "#FFD700", "text": "#996600", "emoji": "🟡"},
    "GREEN":  {"bg": "#F0FFF4", "border": "#00AA00", "text": "#006600", "emoji": "🟢"},
    "GRAY":   {"bg": "#F5F5F5", "border": "#888888", "text": "#555555", "emoji": "⚪"},
}


def _result_html(result: PipelineResult) -> str:
    s = _STYLE.get(result.warning_level, _STYLE["GRAY"])
    label = WARNING_LEVELS.get(result.warning_level, {}).get("label_zh", "⚪ 不確定")
    summary = result.summary_zh.replace("\n", "<br>")

    return f"""
<div style="border:3px solid {s['border']}; border-radius:12px; padding:20px;
            background:{s['bg']}; margin:8px 0;">
  <h2 style="color:{s['text']}; margin:0 0 12px 0;">{label}</h2>
  <div style="font-size:15px; line-height:1.8; color:#333;">{summary}</div>
</div>"""


def _detail_md(result: PipelineResult) -> str:
    parts = []
    if result.danger_result and result.danger_result.analysis_text:
        parts.append("### 🔍 危險快篩分析\n\n" + result.danger_result.analysis_text)
    if result.confusion_result and result.confusion_result.raw_response:
        parts.append("### 🔬 混淆鑑別分析\n\n" + result.confusion_result.raw_response)
    if result.useful_result and result.useful_result.analysis_text:
        parts.append("### 🌿 可利用資源分析\n\n" + result.useful_result.analysis_text)
    return "\n\n---\n\n".join(parts) if parts else "（無詳細分析）"


def _interactive_html(result: PipelineResult) -> str:
    if not result.interactive_guidance:
        return "<p style='color:#888;'>（不需要互動測試）</p>"

    guidance = result.interactive_guidance.replace("\n", "<br>")
    return f"""
<div style="border:3px solid #FF6600; border-radius:12px; padding:20px;
            background:#FFF8F0; margin:8px 0;">
  <h3 style="color:#CC5500; margin:0 0 10px 0;">🔬 需要互動式測試</h3>
  <div style="font-size:14px; line-height:1.8; color:#333;">{guidance}</div>
</div>"""


def _history_html(history: list) -> str:
    if not history:
        return "<p style='color:#888; text-align:center;'>尚無辨識紀錄</p>"

    rows = ""
    for i, h in enumerate(reversed(history)):
        s = _STYLE.get(h["level"], _STYLE["GRAY"])
        rows += f"""
<tr style="background:{s['bg']};">
  <td style="padding:8px; border-bottom:1px solid #ddd;">{len(history)-i}</td>
  <td style="padding:8px; border-bottom:1px solid #ddd;">{h['time']}</td>
  <td style="padding:8px; border-bottom:1px solid #ddd;">{s['emoji']} {h['species']}</td>
  <td style="padding:8px; border-bottom:1px solid #ddd;">{h['confidence']}%</td>
  <td style="padding:8px; border-bottom:1px solid #ddd;">{h['layer']}</td>
  <td style="padding:8px; border-bottom:1px solid #ddd;">{h['mode']}</td>
</tr>"""

    return f"""
<table style="width:100%; border-collapse:collapse; font-size:14px;">
<thead>
<tr style="background:#f0f0f0;">
  <th style="padding:8px; text-align:left;">#</th>
  <th style="padding:8px; text-align:left;">時間</th>
  <th style="padding:8px; text-align:left;">辨識結果</th>
  <th style="padding:8px; text-align:left;">信心度</th>
  <th style="padding:8px; text-align:left;">到達層級</th>
  <th style="padding:8px; text-align:left;">模式</th>
</tr>
</thead>
<tbody>{rows}</tbody>
</table>"""


def identify_species(images, country, altitude, vegetation_zone, mode, history_state):
    if not model_loaded or pipeline is None:
        return (
            "<p style='color:red;'>❌ 請先載入模型</p>",
            "", "", _history_html(history_state), history_state,
        )

    if images is None or len(images) == 0:
        return (
            "<p style='color:red;'>❌ 請上傳至少一張照片</p>",
            "", "", _history_html(history_state), history_state,
        )

    pil_images = []
    for img in images:
        if isinstance(img, str):
            pil_images.append(Image.open(img).convert("RGB"))
        elif isinstance(img, Image.Image):
            pil_images.append(img.convert("RGB"))
        else:
            pil_images.append(Image.open(img).convert("RGB"))

    context = create_context(
        country=country,
        altitude=int(altitude),
        vegetation_zone=vegetation_zone,
    )

    mode_map = {
        "自動（完整流程）": "auto",
        "這個有毒嗎？（危險快篩）": "danger_only",
        "這個能吃嗎？（食物辨識）": "auto",
        "這是什麼動物？（動物辨識）": "animal",
    }
    pipeline_mode = mode_map.get(mode, "auto")

    try:
        result = pipeline.identify(pil_images, context, mode=pipeline_mode)

        species = "未知"
        confidence = 0
        if result.danger_result and result.danger_result.json_data:
            species = result.danger_result.primary_match_name
            confidence = result.danger_result.confidence
        if result.useful_result and result.useful_result.json_data:
            if result.useful_result.confidence > confidence:
                species = result.useful_result.primary_match_name
                confidence = result.useful_result.confidence

        layer_names = {1: "L1 危險快篩", 2: "L2 混淆鑑別", 3: "L3 可利用資源", 4: "L4 通用描述"}
        history_state.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "species": species,
            "confidence": confidence,
            "level": result.warning_level,
            "layer": layer_names.get(result.layer_reached, "?"),
            "mode": mode,
        })

        return (
            _result_html(result),
            _detail_md(result),
            _interactive_html(result),
            _history_html(history_state),
            history_state,
        )
    except Exception as e:
        return (
            f"<p style='color:red;'>❌ 辨識過程發生錯誤：{e}</p>",
            "", "", _history_html(history_state), history_state,
        )


def on_altitude_change(altitude):
    return get_vegetation_zone(int(altitude))


def create_ui():
    with gr.Blocks(
        title="JungleSurvivor — 叢林求生 AI 助手",
        theme=gr.themes.Soft(),
        css="""
        .main-title { text-align: center; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #666; font-size: 14px; margin-bottom: 15px; }
        """
    ) as app:

        history_state = gr.State([])

        gr.HTML("""
        <div class="main-title">
          <h1>🌿 JungleSurvivor — 叢林求生離線 AI 助手</h1>
        </div>
        <div class="subtitle">
          拍攝照片，AI 幫你辨識危險物種、可食植物、毒蛇，並提供求生建議。<br>
          <b>安全第一</b> — 寧可誤報也不漏報。無法確定時一律視為危險。
        </div>
        """)

        with gr.Row():
            model_mode = gr.Dropdown(
                choices=["auto", "kaggle", "ollama"], value="auto",
                label="模型載入模式", scale=1,
            )
            load_btn = gr.Button("🚀 載入模型", variant="primary", scale=1)
            load_status = gr.Textbox(label="載入狀態", interactive=False, scale=3)
        load_btn.click(fn=init_model, inputs=[model_mode], outputs=[load_status])

        gr.HTML("<hr>")

        with gr.Row():
            with gr.Column(scale=1):
                images_input = gr.Gallery(
                    label="📷 上傳照片（可多張，不同角度提升準確度）",
                    type="filepath", columns=3, height=280,
                )
                mode_selector = gr.Dropdown(
                    choices=[
                        "自動（完整流程）",
                        "這個有毒嗎？（危險快篩）",
                        "這個能吃嗎？（食物辨識）",
                        "這是什麼動物？（動物辨識）",
                    ],
                    value="自動（完整流程）", label="辨識模式",
                )
                gr.Markdown("#### 🌏 環境設定")
                country_input = gr.Textbox(value="台灣", label="地點")
                altitude_input = gr.Slider(
                    minimum=0, maximum=4000, value=500, step=100,
                    label="海拔（公尺）",
                )
                vegetation_input = gr.Dropdown(
                    choices=[
                        "低海拔闊葉林", "中海拔闊葉林",
                        "中高海拔針闊混合林", "高海拔針葉林",
                        "高山草原", "海岸地帶", "溪邊濕地",
                    ],
                    value="低海拔闊葉林", label="植被帶",
                )
                altitude_input.change(
                    fn=on_altitude_change, inputs=[altitude_input], outputs=[vegetation_input],
                )
                identify_btn = gr.Button("🔍 開始辨識", variant="primary", size="lg")

            with gr.Column(scale=1):
                main_result = gr.HTML(label="辨識結果")
                with gr.Accordion("🔬 互動測試指引", open=True):
                    interactive_result = gr.HTML()
                with gr.Accordion("📋 詳細分析（Chain of Thought）", open=False):
                    detail_result = gr.Markdown()

        gr.HTML("<hr>")

        with gr.Accordion("📜 歷史紀錄", open=True):
            history_display = gr.HTML(value="<p style='color:#888; text-align:center;'>尚無辨識紀錄</p>")

        identify_btn.click(
            fn=identify_species,
            inputs=[
                images_input, country_input, altitude_input,
                vegetation_input, mode_selector, history_state,
            ],
            outputs=[
                main_result, detail_result, interactive_result,
                history_display, history_state,
            ],
        )

        gr.HTML(f"""
        <hr>
        <div style="text-align:center; color:#888; font-size:13px;">
          <b>閾值設定</b> |
          危險快篩：≥{THRESHOLDS['danger_screening']}% 觸發警告 |
          混淆鑑別：≥{THRESHOLDS['confusion_pairs']}% 才判定安全 |
          可用資源：≥{THRESHOLDS['useful_resources']}% 顯示用途
          <br>
          <b>免責聲明</b>：本工具僅供參考，不能取代專業鑑定。
          在野外遇到不確定的物種，請遵循「不碰、不吃、不觸摸」原則。
        </div>
        """)

    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch(share=True)
