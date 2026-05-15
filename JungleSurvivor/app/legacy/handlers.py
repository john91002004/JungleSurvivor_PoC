"""Event handlers: model loading, identification, language switch, area scan."""

from typing import Optional
from datetime import datetime
from PIL import Image

from config import THRESHOLDS
from context_engine import create_context, load_knowledge_base
from model_loader import load_model
from pipeline import JungleSurvivorPipeline, PipelineResult
from renderers import result_html, detail_md, interactive_html, history_html, make_link
from i18n import set_lang, get_lang, ui

pipeline: Optional[JungleSurvivorPipeline] = None
model_loaded = False


def init_model():
    global pipeline, model_loaded
    if model_loaded and pipeline is not None:
        return ui("model_already")
    try:
        model = load_model(mode="auto")
        pipeline = JungleSurvivorPipeline(model)
        model_loaded = True
        return ui("model_loaded")
    except Exception as e:
        model_loaded = False
        return f"{ui('model_fail')}: {e}"


def switch_language(lang_choice):
    lang = "en" if "English" in lang_choice else "zh"
    set_lang(lang)
    if lang == "en":
        return "Switched to English"
    return "已切換為中文"


def identify_species(images, description, country, mode, lang, hist):
    lang_code = "en" if "English" in lang else "zh"
    set_lang(lang_code)

    if not model_loaded or pipeline is None:
        return f"<p style='color:red;'>{ui('load_first')}</p>", "", "", history_html(hist), hist
    if images is None or len(images) == 0:
        return f"<p style='color:red;'>{ui('upload_photos')}</p>", "", "", history_html(hist), hist

    pil = []
    for im in images:
        try:
            if isinstance(im, Image.Image):
                pil.append(im.convert("RGB"))
            elif isinstance(im, tuple):
                pil.append(Image.open(im[0]).convert("RGB"))
            elif isinstance(im, dict):
                path = im.get("name") or im.get("path") or im.get("image", {}).get("path", "")
                if isinstance(path, dict):
                    path = path.get("path", "")
                pil.append(Image.open(path).convert("RGB"))
            elif isinstance(im, str):
                pil.append(Image.open(im).convert("RGB"))
            else:
                pil.append(Image.open(str(im)).convert("RGB"))
        except Exception as img_err:
            return (
                f"<p style='color:red;'>❌ 照片載入失敗：{img_err}<br>type={type(im)}</p>",
                "", "", history_html(hist), hist
            )

    ctx = create_context(country=country, altitude=500, vegetation_zone="低海拔闊葉林")

    mode_map = {
        ui("mode_auto"): "auto",
        ui("mode_toxic"): "auto",
        ui("mode_edible"): "auto",
        ui("mode_animal"): "animal",
        ui("mode_medicinal"): "auto",
    }
    pm = mode_map.get(mode, "auto")

    desc_parts = []
    if lang_code == "en":
        desc_parts.append("[Respond in English]")
    if description and description.strip():
        desc_parts.append(description.strip())
    desc = " ".join(desc_parts) if desc_parts else None

    try:
        res = pipeline.identify(pil, ctx, mode=pm, description=desc)

        sp = res.candidates[0].common_name_zh if res.candidates else "未知"
        conf = res.candidates[0].confidence if res.candidates else 0

        hist.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "species": sp, "conf": conf,
            "level": res.warning_level,
            "mode": mode.split("（")[0].split("(")[0].strip(),
        })
        return result_html(res), detail_md(res), interactive_html(res), history_html(hist), hist
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"<p style='color:red;'>❌ Error: {e}</p>", "", "", history_html(hist), hist


def area_scan(country):
    kb = load_knowledge_base()
    is_taiwan = any(kw in country for kw in ["台灣", "Taiwan", "台北", "Taipei"])

    edible_names = [p["common_names"]["zh-TW"] for p in kb.edible_plants]
    toxic_names = [p["common_names"]["zh-TW"] for p in kb.toxic_plants]
    animal_names = [a["common_names"]["zh-TW"] for a in kb.dangerous_animals]
    med_names = [p["common_names"]["zh-TW"] for p in kb.edible_plants if p.get("medicinal_uses")]

    html = '<div style="padding:16px;">'
    html += f'<h3>{ui("scan_title")}</h3>'
    html += f'<p style="color:#666;">{ui("scan_location")}：{country}</p>'

    if not is_taiwan:
        html += (
            '<div style="margin:8px 0;padding:10px;background:#FFFBE6;border-radius:8px;border-left:4px solid #FFD700;">'
            f'<b>⚠️</b> {ui("scan_tw_only")}'
            '</div>'
        )

    html += f'<div style="margin:12px 0;padding:12px;background:#F0FFF4;border-radius:8px;">'
    html += f'<b>{ui("scan_edible")}（{len(edible_names)} {ui("species_count")}）：</b><br>' + '、'.join(edible_names) + '</div>'

    if med_names:
        html += f'<div style="margin:12px 0;padding:12px;background:#F0F8FF;border-radius:8px;">'
        html += f'<b>{ui("scan_medicinal")}（{len(med_names)} {ui("species_count")}）：</b><br>' + '、'.join(med_names) + '</div>'

    html += f'<div style="margin:12px 0;padding:12px;background:#FFF0F0;border-radius:8px;">'
    html += f'<b>{ui("scan_toxic")}（{len(toxic_names)} {ui("species_count")}）：</b><br>' + '、'.join(toxic_names) + '</div>'

    html += f'<div style="margin:12px 0;padding:12px;background:#FFF8F0;border-radius:8px;">'
    html += f'<b>{ui("scan_animal")}（{len(animal_names)} {ui("species_count")}）：</b><br>' + '、'.join(animal_names) + '</div>'

    html += f'<div style="margin:12px 0;padding:12px;background:#F5F5FF;border-radius:8px;">'
    html += f'<b>{ui("scan_water")}：</b><br>{ui("scan_water_text")}'
    html += f'<br>{make_link("water/safety_checklist")} | {make_link("water/purification")}'
    html += '</div></div>'
    return html
