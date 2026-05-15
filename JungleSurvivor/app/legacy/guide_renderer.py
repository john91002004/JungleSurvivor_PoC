"""Survival guide static page rendering with anchor IDs and bilingual support."""

import json
from pathlib import Path
from i18n import get_lang, t

SURVIVAL_GUIDE_PATH = Path(__file__).parent.parent / "knowledge_base" / "survival_guide"


def _load_guide(filename: str) -> dict:
    path = SURVIVAL_GUIDE_PATH / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"pages": []}


def _g(obj, key_zh, fallback=""):
    """Pick zh or en value from a dict based on current language."""
    if get_lang() == "en":
        en_key = key_zh.replace("_zh", "_en")
        val = obj.get(en_key)
        if val:
            return val
    return obj.get(key_zh, fallback)


def _gl(page, key_zh):
    """Pick zh or en list (e.g. warnings / warnings_en)."""
    if get_lang() == "en":
        en_key = key_zh + "_en" if not key_zh.endswith("_zh") else key_zh.replace("_zh", "_en")
        val = page.get(en_key)
        if val:
            return val
    return page.get(key_zh, [])


def _gc(item, key):
    """Pick zh or en for checklist plain keys like 'item', 'safe', 'warning', 'danger'."""
    if get_lang() == "en":
        val = item.get(key + "_en")
        if val:
            return val
    return item.get(key, "")


def _render_guide_page(page: dict) -> str:
    page_id = page.get("id", "unknown")
    anchor_id = "guide-" + page_id.replace("/", "-")
    en = get_lang() == "en"

    html = f'<div id="{anchor_id}" class="guide-page" style="border:1px solid #ddd;border-radius:8px;padding:16px;margin:10px 0;background:#FAFAFA;">'
    html += f'<h3 style="margin:0 0 8px 0;">{_g(page, "title_zh", page_id)}</h3>'

    sit = _g(page, "situation_zh")
    if sit:
        lbl = "Scenario:" if en else "適用情境："
        html += f'<p style="color:#666;font-size:13px;"><b>{lbl}</b>{sit}</p>'
    mat = _g(page, "materials_zh")
    if mat:
        lbl = "Materials:" if en else "所需材料："
        html += f'<p style="color:#666;font-size:13px;"><b>{lbl}</b>{mat}</p>'
    prep = _g(page, "preparation_zh")
    if prep:
        html += f'<p style="font-size:13px;">{prep.replace(chr(10), "<br>")}</p>'

    if page.get("steps"):
        html += '<ol style="line-height:2;">'
        for step in page["steps"]:
            html += f'<li><b>{_g(step, "action_zh")}</b>'
            detail = _g(step, "detail_zh")
            if detail:
                html += f'<br><span style="color:#666;font-size:13px;">{detail}</span>'
            html += '</li>'
        html += '</ol>'

    if page.get("methods"):
        for m in page["methods"]:
            name = _g(m, "name_zh", m.get("id", ""))
            inst = _g(m, "instruction_zh", "").replace("\n", "<br>")
            html += '<div style="margin:8px 0;padding:10px;background:#F0F8FF;border-radius:6px;border-left:4px solid #4488CC;">'
            html += f'<b>{name}</b>'
            if m.get("difficulty"):
                html += f' <span style="font-size:12px;color:#888;">[{m["difficulty"]}]</span>'
            html += f'<br>{inst}'
            caution = _g(m, "caution_zh")
            if caution:
                html += f'<br><span style="color:#CC6600;">⚠️ {caution}</span>'
            notes = _g(m, "notes_zh")
            if notes:
                html += f'<br><span style="color:#666;font-size:12px;">💡 {notes}</span>'
            html += '</div>'

    if page.get("knots"):
        for k in page["knots"]:
            html += '<div style="margin:8px 0;padding:10px;background:#F0F8FF;border-radius:6px;border-left:4px solid #4488CC;">'
            html += f'<b>{_g(k, "name_zh")}</b> — {_g(k, "use_zh")}'
            html += f'<br>{_g(k, "instruction_zh").replace(chr(10), "<br>")}</div>'

    if page.get("edible_insects"):
        h_bug = "Insect" if en else "昆蟲"
        h_nut = "Nutrition" if en else "營養"
        h_prep = "Preparation" if en else "處理"
        h_find = "Location" if en else "地點"
        html += '<table style="width:100%;border-collapse:collapse;font-size:13px;margin:8px 0;">'
        html += f'<tr style="background:#f0f0f0;"><th style="padding:6px;">{h_bug}</th><th>{h_nut}</th><th>{h_prep}</th><th>{h_find}</th></tr>'
        for ins in page["edible_insects"]:
            html += f'<tr><td style="padding:6px;border:1px solid #ddd;"><b>{_g(ins, "name_zh")}</b></td>'
            html += f'<td style="padding:6px;border:1px solid #ddd;">{_g(ins, "nutrition_zh")}</td>'
            html += f'<td style="padding:6px;border:1px solid #ddd;">{_g(ins, "preparation_zh")}</td>'
            html += f'<td style="padding:6px;border:1px solid #ddd;">{_g(ins, "find_zh")}</td></tr>'
        html += '</table>'
        avoid = _gl(page, "avoid") if en else page.get("avoid", [])
        if avoid:
            lbl = "❌ Avoid:" if en else "❌ 避免："
            html += f'<p style="color:#CC0000;font-size:13px;"><b>{lbl}</b>{"、".join(avoid)}</p>'

    if page.get("checklist"):
        items = page["checklist"]
        has_three = "danger" in items[0] if items else False
        if has_three:
            h = [("Item","項目"), ("✅ Safe","✅ 安全"), ("⚠️ Caution","⚠️ 注意"), ("❌ Danger","❌ 危險")]
            headers = [x[0] if en else x[1] for x in h]
            html += '<table style="width:100%;border-collapse:collapse;font-size:13px;margin:8px 0;">'
            html += f'<tr style="background:#f0f0f0;">{"".join(f"<th style=padding:6px;>{h}</th>" for h in headers)}</tr>'
            for item in items:
                html += f'<tr><td style="padding:6px;border:1px solid #ddd;"><b>{_gc(item,"item")}</b></td>'
                html += f'<td style="padding:6px;border:1px solid #ddd;background:#F0FFF4;">{_gc(item,"safe")}</td>'
                html += f'<td style="padding:6px;border:1px solid #ddd;background:#FFFBE6;">{_gc(item,"warning")}</td>'
                html += f'<td style="padding:6px;border:1px solid #ddd;background:#FFF0F0;">{_gc(item,"danger")}</td></tr>'
            html += '</table>'
        else:
            h = [("Check Item","檢查項目"), ("✅ Normal","✅ 正常"), ("⚠️ Abnormal","⚠️ 異常（可能感染）")]
            headers = [x[0] if en else x[1] for x in h]
            html += '<table style="width:100%;border-collapse:collapse;font-size:13px;margin:8px 0;">'
            html += f'<tr style="background:#f0f0f0;">{"".join(f"<th style=padding:6px;>{h}</th>" for h in headers)}</tr>'
            for item in items:
                q = _g(item, "question_zh") if item.get("question_zh") else ""
                html += f'<tr><td style="padding:8px;border:1px solid #ddd;"><b>{_gc(item,"item")}</b>'
                if q:
                    html += f'<br><span style="font-size:12px;color:#666;">{q}</span>'
                html += '</td>'
                html += f'<td style="padding:8px;border:1px solid #ddd;background:#F0FFF4;">{_gc(item,"normal")}</td>'
                html += f'<td style="padding:8px;border:1px solid #ddd;background:#FFF0F0;">{_gc(item,"warning")}</td></tr>'
            html += '</table>'

        if page.get("conclusion_rules"):
            sev_colors = {"normal": "#F0FFF4", "mild": "#FFFBE6", "moderate": "#FFF0F0",
                          "severe": "#FF0000", "GREEN": "#F0FFF4", "YELLOW": "#FFFBE6", "RED": "#FFF0F0"}
            for rule in page["conclusion_rules"]:
                bg = sev_colors.get(rule.get("severity") or rule.get("color", ""), "#F5F5F5")
                cond = _gc(rule, "condition")
                res = _gc(rule, "result")
                html += f'<div style="padding:8px;margin:4px 0;background:{bg};border-radius:4px;border-left:4px solid #888;">'
                html += f'<b>{cond}</b> → {res}'
                act = _g(rule, "action_zh")
                if act:
                    html += f'<br><span style="font-size:13px;">👉 {act}</span>'
                html += '</div>'

    if page.get("principles"):
        html += '<ol style="line-height:2;">'
        for p in page["principles"]:
            html += f'<li><b>{_g(p, "rule_zh")}</b>'
            detail = _g(p, "detail_zh")
            if detail:
                html += f'<br><span style="color:#666;font-size:13px;">{detail}</span>'
            html += '</li>'
        html += '</ol>'

    if page.get("danger_terrains"):
        lbl = "⚠️ Dangerous Terrain:" if en else "⚠️ 危險地形："
        h_t = "Terrain" if en else "地形"
        h_a = "Action" if en else "應對"
        html += f'<div style="margin-top:8px;"><b>{lbl}</b></div>'
        html += '<table style="width:100%;border-collapse:collapse;font-size:13px;margin:4px 0;">'
        html += f'<tr style="background:#FFF0F0;"><th style="padding:6px;">{h_t}</th><th>{h_a}</th></tr>'
        for dt in page["danger_terrains"]:
            html += f'<tr><td style="padding:6px;border:1px solid #ddd;"><b>{_g(dt, "terrain_zh")}</b></td>'
            html += f'<td style="padding:6px;border:1px solid #ddd;">{_g(dt, "action_zh")}</td></tr>'
        html += '</table>'

    splint = _g(page, "splint_zh")
    if splint:
        lbl = "🦴 Splint:" if en else "🦴 夾板固定："
        html += f'<div style="margin:8px 0;padding:10px;background:#F0F8FF;border-radius:6px;">'
        html += f'<b>{lbl}</b><br>{splint.replace(chr(10), "<br>")}</div>'

    warns = _gl(page, "warnings")
    if warns:
        lbl = "⚠️ Warnings:" if en else "⚠️ 注意事項："
        html += '<div style="margin-top:8px;padding:8px;background:#FFF3F3;border-radius:4px;">'
        html += f'<b>{lbl}</b><ul style="margin:4px 0;">'
        for w in warns:
            html += f'<li style="color:#CC0000;">{w}</li>'
        html += '</ul></div>'

    html += '</div>'
    return html


def render_guide_category(category: str) -> str:
    guide = _load_guide(f"{category}.json")
    if not guide.get("pages"):
        lbl = "(No content)" if get_lang() == "en" else "（尚無內容）"
        return f"<p>{lbl}</p>"
    return "".join(_render_guide_page(page) for page in guide["pages"])
