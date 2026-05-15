"""
JungleSurvivor v2 — Gradio UI

Implements Plan Section 13:
  - Iterative photo upload with immediate feedback
  - Editable feature tags
  - Warning-colored result display
  - Confusion pair guidance
"""

from __future__ import annotations
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import gradio as gr
except ImportError:
    print("Gradio not installed. Run: pip install gradio")
    sys.exit(1)

from .pipeline import JungleSurvivorV2

pipeline = JungleSurvivorV2()

# Section name translations for UI
SECTION_NAMES = {
    "overall": "整株特徵",
    "leaf": "葉",
    "stem": "莖",
    "flower": "花",
    "fruit": "果實",
    "root": "根/地下部",
}

ATTR_NAMES = {
    "growth_form": "生長型態",
    "height_estimate": "高度估計",
    "latex": "汁液",
    "smell": "氣味",
    "habitat": "棲地",
    "water_droplet_test": "水珠測試",
    "leaf_type": "葉型",
    "shape": "形狀",
    "edge": "葉緣",
    "tip": "葉尖",
    "base": "葉基",
    "colors": "顏色",
    "color_pattern": "色彩花紋",
    "surface_top": "葉面質感",
    "surface_bottom": "葉背質感",
    "arrangement": "排列",
    "size": "大小",
    "venation": "脈序",
    "texture": "質地",
    "petiole_attach": "葉柄著生",
    "type": "類型",
    "cross_section": "橫截面",
    "surface": "表面",
    "interior": "內部",
    "has_thorns": "有刺",
    "petal_count": "花瓣數",
    "symmetry": "對稱性",
    "position": "位置",
    "orientation": "朝向",
    "special_shape": "特殊形態",
    "fragrant": "有香味",
}


def format_features_display(features: dict) -> str:
    """Format current features as readable markdown."""
    if not features:
        return "尚未萃取任何特徵。請上傳照片或手動輸入特徵。"

    lines = []
    for section_name, section_data in features.items():
        section_label = SECTION_NAMES.get(section_name, section_name)
        lines.append(f"### {section_label}")
        for attr_name, value in section_data.items():
            attr_label = ATTR_NAMES.get(attr_name, attr_name)
            if isinstance(value, list):
                val_str = ", ".join(str(v) for v in value)
            else:
                val_str = str(value)
            lines.append(f"- **{attr_label}**: `{val_str}`")
        lines.append("")

    return "\n".join(lines)


def format_summary_display(summary: dict) -> str:
    """Format feature completeness summary."""
    lines = ["### 特徵完整度"]
    total_filled = 0
    total_all = 0

    for section_name, info in summary.items():
        section_label = SECTION_NAMES.get(section_name, section_name)
        filled = info["filled"]
        total = info["total"]
        total_filled += filled
        total_all += total
        pct = filled / total * 100 if total > 0 else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        lines.append(f"**{section_label}**: {bar} {filled}/{total}")

    overall_pct = total_filled / total_all * 100 if total_all > 0 else 0
    lines.insert(1, f"**整體**: {total_filled}/{total_all} ({overall_pct:.0f}%)")
    lines.insert(2, "")

    return "\n".join(lines)


def process_llm_response(llm_response: str) -> tuple[str, str, str]:
    """Process a simulated LLM response."""
    result = pipeline.extract_features_from_response(llm_response)

    if not result.success:
        return (
            f"❌ 萃取失敗: {result.error}",
            "萃取失敗，無法更新特徵",
            "",
        )

    features = pipeline.get_current_features()
    summary = pipeline.get_feature_summary()

    status = f"✅ 第 {pipeline.state.photo_count} 張照片特徵已合併"
    if result.warnings:
        status += "\n⚠️ 警告:\n" + "\n".join(f"  - {w}" for w in result.warnings)

    return (
        status,
        format_features_display(features),
        format_summary_display(summary),
    )


def run_identification() -> str:
    """Run the identification pipeline."""
    features = pipeline.get_current_features()
    if not features:
        return "請先上傳照片或輸入特徵，再進行辨識。"

    result = pipeline.identify(top_n=3)
    return pipeline.format_display(result)


def add_manual_feature(section: str, attr: str, value: str) -> tuple[str, str]:
    """Add a user manual feature override."""
    if not section or not attr or not value:
        return "請選擇完整的區段、屬性和值", ""

    # Check if it's an array type
    schema_clean = {k: v for k, v in pipeline.schema.items() if not k.startswith("_")}
    attr_def = schema_clean.get(section, {}).get(attr, {})

    if attr_def.get("type") == "array":
        current = pipeline.state.user_overrides.get(section, {}).get(attr, [])
        if isinstance(current, list) and value not in current:
            pipeline.set_user_feature(section, attr, current + [value])
        else:
            pipeline.set_user_feature(section, attr, [value])
    else:
        pipeline.set_user_feature(section, attr, value)

    features = pipeline.get_current_features()
    return (
        f"✅ 已設定 {SECTION_NAMES.get(section, section)}.{ATTR_NAMES.get(attr, attr)} = {value}",
        format_features_display(features),
    )


def reset_session() -> tuple[str, str, str, str]:
    """Reset the pipeline for a new session."""
    pipeline.reset()
    return ("已重置。", "", "", "")


def get_attr_choices(section: str) -> gr.update:
    """Get attribute choices for a given section."""
    schema_clean = {k: v for k, v in pipeline.schema.items() if not k.startswith("_")}
    attrs = schema_clean.get(section, {})
    choices = [(ATTR_NAMES.get(k, k), k) for k in attrs if attrs[k]["type"] != "boolean"]
    return gr.update(choices=choices, value=None)


def get_value_choices(section: str, attr: str) -> gr.update:
    """Get value choices for a given attribute."""
    if not section or not attr:
        return gr.update(choices=[], value=None)
    values = pipeline.get_schema_enums_for_attr(section, attr)
    return gr.update(choices=values, value=None)


def build_ui() -> gr.Blocks:
    """Build the Gradio UI."""
    with gr.Blocks(
        title="JungleSurvivor v2 — 野外植物辨識系統",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown("# 🌿 JungleSurvivor v2 — 野外植物辨識系統")
        gr.Markdown(
            "上傳植物照片 → AI 萃取特徵 → 演算法比對知識庫 → 安全判定\n\n"
            "**流程**: 拍照萃取 → 檢視/修改特徵 → 開始辨識"
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## Phase 1: 特徵萃取")
                llm_input = gr.Textbox(
                    label="LLM 回應 (JSON)",
                    placeholder='貼入 LLM 回傳的 JSON，例如：\n{"growth_form": "herb", "leaf": {"shape": "heart", ...}}',
                    lines=8,
                )
                extract_btn = gr.Button("📷 萃取特徵", variant="primary")
                status_output = gr.Textbox(label="狀態", interactive=False)

                gr.Markdown("---")
                gr.Markdown("## 手動補充特徵")
                section_dd = gr.Dropdown(
                    choices=[(v, k) for k, v in SECTION_NAMES.items()],
                    label="部位",
                )
                attr_dd = gr.Dropdown(choices=[], label="屬性")
                value_dd = gr.Dropdown(choices=[], label="值")
                add_btn = gr.Button("👤 新增/修改", variant="secondary")
                manual_status = gr.Textbox(label="手動輸入狀態", interactive=False)

            with gr.Column(scale=1):
                gr.Markdown("## 目前特徵")
                features_display = gr.Markdown("尚未萃取任何特徵。")
                summary_display = gr.Markdown("")

                gr.Markdown("---")
                with gr.Row():
                    identify_btn = gr.Button("🔍 開始辨識", variant="primary", size="lg")
                    reset_btn = gr.Button("🔄 重新開始", variant="stop")

        gr.Markdown("---")
        gr.Markdown("## 辨識結果")
        result_output = gr.Markdown("等待辨識...")

        # Event handlers
        extract_btn.click(
            fn=process_llm_response,
            inputs=[llm_input],
            outputs=[status_output, features_display, summary_display],
        )

        identify_btn.click(
            fn=run_identification,
            outputs=[result_output],
        )

        reset_btn.click(
            fn=reset_session,
            outputs=[status_output, features_display, summary_display, result_output],
        )

        section_dd.change(
            fn=get_attr_choices,
            inputs=[section_dd],
            outputs=[attr_dd],
        )

        attr_dd.change(
            fn=get_value_choices,
            inputs=[section_dd, attr_dd],
            outputs=[value_dd],
        )

        add_btn.click(
            fn=add_manual_feature,
            inputs=[section_dd, attr_dd, value_dd],
            outputs=[manual_status, features_display],
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(share=False)
