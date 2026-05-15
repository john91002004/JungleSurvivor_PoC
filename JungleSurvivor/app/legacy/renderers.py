"""HTML rendering utilities for identification results and history."""

from styles import RESULT_STYLES
from i18n import ui

GUIDE_TITLES = {
    "medical/poultice": "藥用植物敷用法",
    "medical/hemostatic_plants": "止血植物使用法",
    "medical/wound_general": "傷口處理通則",
    "medical/inflammation_checklist": "傷口發炎判斷",
    "medical/burn": "燒燙傷處理",
    "medical/sprain": "扭傷骨折處置",
    "food/blanching": "川燙法",
    "food/boiling": "煮沸法",
    "food/plant_processing": "植物處理方式",
    "food/raw": "生食法",
    "food/fire": "生火方法",
    "food/edibility_test": "通用可食性測試法",
    "tools/cordage": "天然繩索製作",
    "tools/knots": "繩結教學",
    "water/purification": "淨水處理法",
    "water/rainwater": "雨水收集法",
    "water/dew": "露水收集法",
    "water/safety_checklist": "水源安全 Checklist",
}


def make_link(page_id: str, display_text: str = None) -> str:
    anchor = "guide-" + page_id.replace("/", "-")
    label = display_text or GUIDE_TITLES.get(page_id, page_id)
    return f'<a href="#{anchor}" style="color:#0066CC;text-decoration:underline;cursor:pointer;">{label}</a>'


def result_html(result) -> str:
    """渲染辨識結果主面板"""
    s = RESULT_STYLES.get(result.warning_level, RESULT_STYLES["GRAY"])
    wl_labels = {
        "RED": "🔴 危險 DANGER", "YELLOW": "🟡 注意 CAUTION",
        "GREEN": "🟢 安全 SAFE", "GRAY": "⚪ 不確定 UNKNOWN",
    }
    label = wl_labels.get(result.warning_level, "⚪")
    summary = result.summary_zh.replace("\n", "<br>")

    return (
        f'<div class="result-panel" style="border:3px solid {s["bd"]};border-radius:12px;padding:20px;'
        f'background:{s["bg"]};margin:8px 0;">'
        f'<h2 style="color:{s["tx"]};margin:0 0 12px 0;">{label}</h2>'
        f'<div style="font-size:15px;line-height:1.8;color:#333;white-space:pre-line;">{summary}</div>'
        f'</div>'
    )


def detail_md(result) -> str:
    """渲染詳細分析 Markdown"""
    parts = []

    if result.reasoning:
        parts.append(f"### 🧠 AI 分析\n\n{result.reasoning}")

    if result.candidates:
        parts.append("### 📊 候選排名\n")
        for c in result.candidates:
            cat_icon = {"dangerous": "⚠️", "edible": "🍃", "medicinal": "💊"}.get(c.category, "❓")
            parts.append(f"**#{c.rank}** {cat_icon} {c.common_name_zh} (*{c.scientific_name}*) — {c.confidence}%")
            if c.key_matching_features:
                parts.append(f"   匹配特徵：{'、'.join(c.key_matching_features)}")
            if c.danger_info and c.danger_info.get("toxicity"):
                parts.append(f"   ⚠️ 毒性：{c.danger_info['toxicity']}")

    if result.observed_features:
        parts.append(f"\n### 🔍 觀察到的特徵\n\n{'、'.join(result.observed_features)}")

    if hasattr(result, 'confusion_warnings') and result.confusion_warnings:
        parts.append("\n### 🔀 混淆物種對照\n")
        for cw in result.confusion_warnings:
            parts.append(f"**「{cw.candidate_name}」⟷「{cw.confused_with}」**")
            if cw.distinguishing_features:
                parts.append("關鍵區別：")
                for feat in cw.distinguishing_features[:5]:
                    parts.append(f"- {feat}")
            if cw.interactive_tests:
                parts.append(f"🧪 建議測試：{'、'.join(cw.interactive_tests)}")

    return "\n\n".join(parts) if parts else "（無詳細分析）"


def interactive_html(result) -> str:
    """渲染互動測試指引"""
    if not result.interactive_guidance:
        return ""
    g = result.interactive_guidance.replace("\n", "<br>")
    return (
        '<div style="border:3px solid #FF6600;border-radius:12px;padding:20px;'
        'background:#FFF8F0;margin:8px 0;">'
        '<h3 style="color:#CC5500;margin:0 0 10px 0;">🔬 互動測試指引</h3>'
        f'<div style="font-size:14px;line-height:1.8;color:#333;">{g}</div></div>'
    )


def history_html(history: list) -> str:
    if not history:
        return f"<p style='color:#888;text-align:center;'>{ui('no_records')}</p>"
    rows = ""
    for i, h in enumerate(reversed(history)):
        s = RESULT_STYLES.get(h["level"], RESULT_STYLES["GRAY"])
        rows += (
            f'<tr style="background:{s["bg"]};">'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{len(history)-i}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{h["time"]}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{s["emoji"]} {h["species"]}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{h["conf"]}%</td>'
            f'<td style="padding:8px;border-bottom:1px solid #ddd;">{h["mode"]}</td></tr>'
        )
    return (
        '<table style="width:100%;border-collapse:collapse;font-size:14px;">'
        '<thead><tr style="background:#f0f0f0;">'
        f'<th style="padding:8px;text-align:left;">{ui("hist_num")}</th>'
        f'<th style="padding:8px;text-align:left;">{ui("hist_time")}</th>'
        f'<th style="padding:8px;text-align:left;">{ui("hist_result")}</th>'
        f'<th style="padding:8px;text-align:left;">{ui("hist_conf")}</th>'
        f'<th style="padding:8px;text-align:left;">{ui("hist_mode")}</th>'
        '</tr></thead><tbody>' + rows + '</tbody></table>'
    )
