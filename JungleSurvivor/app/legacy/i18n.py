"""Internationalization — bilingual text lookup for UI and dynamic content."""

_current_lang = "zh"


def set_lang(lang: str):
    global _current_lang
    _current_lang = lang


def get_lang() -> str:
    return _current_lang


def t(zh: str, en: str) -> str:
    return en if _current_lang == "en" else zh


UI = {
    "app_title": ("🌿 JungleSurvivor — 叢林求生離線 AI 助手",
                  "🌿 JungleSurvivor — Jungle Survival AI Assistant"),
    "app_subtitle": ("AI 辨識 + 離線生存指南 | 安全第一",
                     "AI Identification + Offline Survival Guide | Safety First"),
    "load_model": ("🚀 載入模型", "🚀 Load Model"),
    "night_mode": ("🌙 夜間模式", "🌙 Night Mode"),
    "status": ("狀態", "Status"),
    "lang_label": ("🌐 語言", "🌐 Language"),

    "tab_identify": ("🔍 AI 辨識", "🔍 AI Identify"),
    "tab_guide": ("📖 生存指南", "📖 Survival Guide"),
    "tab_scan": ("📍 區域掃描", "📍 Area Scan"),
    "tab_history": ("📜 歷史紀錄", "📜 History"),

    "tab_water": ("💧 水", "💧 Water"),
    "tab_food": ("🍃 食", "🍃 Food"),
    "tab_medical": ("🏥 醫", "🏥 Medical"),
    "tab_shelter": ("🏕️ 住", "🏕️ Shelter"),
    "tab_navigation": ("🧭 行", "🧭 Navigation"),
    "tab_tools": ("🔧 工具", "🔧 Tools"),

    "photo_tips_title": ("📸 拍照建議：", "📸 Photo Tips:"),
    "tip_angles": ("至少 2 張不同角度", "At least 2 different angles"),
    "tip_light": ("光線明亮", "Good lighting"),
    "tip_parts": ("拍葉片正反面、莖部、花果", "Capture leaves (both sides), stem, flowers/fruit"),
    "tip_scale": ("放手指當比例尺", "Include finger for scale reference"),
    "tip_desc": ("📝 文字描述大幅提升準確率：觸感、氣味、環境、高度",
                 "📝 Text description greatly improves accuracy: texture, smell, environment, height"),

    "photos_label": ("📷 照片", "📷 Photos"),
    "desc_label": ("📝 文字描述（可選）", "📝 Description (optional)"),
    "desc_placeholder": ("例：葉面光滑、搓揉有刺鼻味、溪邊陰暗處、高30cm...",
                         "e.g.: Smooth leaves, pungent smell when crushed, shady streamside, 30cm tall..."),
    "mode_label": ("辨識模式", "Identification Mode"),
    "mode_auto": ("自動（完整流程）", "Auto (full pipeline)"),
    "mode_toxic": ("這個有毒嗎？", "Is this toxic?"),
    "mode_edible": ("這個能吃嗎？", "Can I eat this?"),
    "mode_animal": ("動物辨識", "Animal ID"),
    "mode_medicinal": ("藥用植物", "Medicinal Plant"),
    "location_label": ("📍 地點", "📍 Location"),
    "start_btn": ("🔍 開始辨識", "🔍 Start Identification"),
    "result_label": ("結果", "Result"),
    "detail_label": ("📋 詳細分析", "📋 Detailed Analysis"),
    "interactive_label": ("🔬 互動測試", "🔬 Interactive Test"),

    "guide_static": ("靜態內容，零算力", "Static content, zero compute"),
    "scan_hint": ("不需 AI，查詢知識庫", "No AI needed, KB query only"),
    "scan_btn": ("🔍 掃描", "🔍 Scan"),
    "no_records": ("尚無紀錄", "No records yet"),

    "load_first": ("❌ 請先載入模型", "❌ Please load model first"),
    "upload_photos": ("❌ 請上傳照片", "❌ Please upload photos"),
    "model_loaded": ("✅ 模型載入成功！", "✅ Model loaded!"),
    "model_already": ("✅ 模型已載入", "✅ Model already loaded"),
    "model_fail": ("❌ 載入失敗", "❌ Load failed"),

    "scan_title": ("📍 區域資源總覽", "📍 Area Resources Overview"),
    "scan_location": ("地點", "Location"),
    "scan_tw_only": ("知識庫目前僅涵蓋台灣物種。其他地區結果僅供參考。",
                     "KB currently covers Taiwan species only. Results for other regions are approximate."),
    "scan_edible": ("🍃 可食植物", "🍃 Edible Plants"),
    "scan_medicinal": ("💊 藥用", "💊 Medicinal"),
    "scan_toxic": ("⚠️ 危險植物", "⚠️ Toxic Plants"),
    "scan_animal": ("🐍 危險動物", "🐍 Dangerous Animals"),
    "scan_water": ("💧 水源建議", "💧 Water Advice"),
    "scan_water_text": ("建議收集雨水/露水或尋找溪流。", "Collect rainwater/dew or find streams."),
    "species_count": ("種", "species"),

    "hist_num": ("#", "#"),
    "hist_time": ("時間", "Time"),
    "hist_result": ("結果", "Result"),
    "hist_conf": ("信心度", "Confidence"),
    "hist_mode": ("模式", "Mode"),
}


def ui(key: str) -> str:
    pair = UI.get(key)
    if not pair:
        return key
    return pair[1] if _current_lang == "en" else pair[0]
