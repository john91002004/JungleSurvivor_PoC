"""Dark Mode CSS for Gradio 6"""

DARK_CSS = """
.dark-mode, .dark-mode .gradio-container { background-color: #121212 !important; color: #E8E8E8 !important; }
.dark-mode div, .dark-mode section, .dark-mode article, .dark-mode main,
.dark-mode aside, .dark-mode header, .dark-mode footer,
.dark-mode .contain, .dark-mode .tabs, .dark-mode .tabitem,
.dark-mode .panel, .dark-mode .form, .dark-mode .block, .dark-mode .wrap,
.dark-mode .gallery, .dark-mode .svelte-1ed2p3z,
.dark-mode [class*="container"], .dark-mode [class*="wrapper"],
.dark-mode [class*="panel"], .dark-mode [class*="block"] {
  background-color: #121212 !important; color: #E8E8E8 !important;
}
.dark-mode input, .dark-mode textarea, .dark-mode select,
.dark-mode [data-testid], .dark-mode .secondary-wrap,
.dark-mode .border, .dark-mode label span {
  background-color: #1E1E1E !important; color: #E8E8E8 !important; border-color: #444 !important;
}
.dark-mode button { background-color: #2A2A2A !important; color: #E8E8E8 !important; border-color: #555 !important; }
.dark-mode button.primary, .dark-mode button[variant="primary"],
.dark-mode .primary { background-color: #1B4D3E !important; color: #00FF88 !important; border-color: #00FF88 !important; }
.dark-mode .tab-nav button, .dark-mode button[role="tab"] {
  background-color: #1E1E1E !important; color: #BBB !important; border-color: #333 !important;
}
.dark-mode .tab-nav button.selected, .dark-mode button[role="tab"][aria-selected="true"] {
  background-color: #2A2A2A !important; color: #00D2FF !important; border-bottom-color: #00D2FF !important;
}
.dark-mode h1, .dark-mode h2, .dark-mode h3, .dark-mode h4, .dark-mode h5,
.dark-mode p, .dark-mode span, .dark-mode label, .dark-mode li, .dark-mode td,
.dark-mode th, .dark-mode b, .dark-mode strong, .dark-mode a, .dark-mode ol,
.dark-mode ul, .dark-mode summary, .dark-mode details {
  color: #E8E8E8 !important;
}
.dark-mode details, .dark-mode .accordion, .dark-mode summary {
  background-color: #1E1E1E !important; border-color: #333 !important;
}
.dark-mode .guide-page { background-color: #1A1A2E !important; border-color: #333 !important; }
.dark-mode table { border-color: #444 !important; }
.dark-mode th { background-color: #1A1A2E !important; }
.dark-mode td { background-color: #1E1E1E !important; border-color: #333 !important; }
.dark-mode a { color: #66BBFF !important; }
.dark-mode .result-panel, .dark-mode div[style*="border:3px"] { background-color: #1E1E1E !important; }
.dark-mode div[style*="background:#E8F4FD"] { background-color: #0E2A3A !important; }
.dark-mode div[style*="background:#F0FFF4"] { background-color: #0A2E14 !important; }
.dark-mode div[style*="background:#FFF0F0"] { background-color: #2E0A0A !important; }
.dark-mode div[style*="background:#FFFBE6"] { background-color: #2E2A0A !important; }
.dark-mode div[style*="background:#F5F5F5"], .dark-mode div[style*="background:#FAFAFA"] { background-color: #1E1E1E !important; }
.dark-mode div[style*="background:#FFF3F3"] { background-color: #2E1515 !important; }
.dark-mode div[style*="background:#FFF8F0"] { background-color: #2E1E0A !important; }
.dark-mode div[style*="background:#F0F8FF"] { background-color: #0E1E2E !important; }
.dark-mode div[style*="background:#F5F5FF"] { background-color: #15152E !important; }
.dark-mode ::-webkit-scrollbar { background: #1E1E1E; }
.dark-mode ::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }
"""

NAV_JS = """
() => {
  var CAT_TO_SUBTAB = {
    'water':'subtab-water', 'food':'subtab-food', 'medical':'subtab-medical',
    'shelter':'subtab-shelter', 'navigation':'subtab-navigation', 'tools':'subtab-tools'
  };
  function clickTabById(elemId) {
    var panel = document.getElementById(elemId);
    if (!panel) return false;
    var tabId = panel.getAttribute('aria-labelledby');
    if (tabId) {
      var btn = document.getElementById(tabId);
      if (btn) { btn.click(); return true; }
    }
    var tabs = panel.parentElement
      ? panel.parentElement.querySelectorAll(':scope > [role="tabpanel"]')
      : [];
    var idx = Array.prototype.indexOf.call(tabs, panel);
    if (idx < 0) return false;
    var nav = panel.parentElement.previousElementSibling;
    if (!nav) return false;
    var btns = nav.querySelectorAll('button[role="tab"]');
    if (btns[idx]) { btns[idx].click(); return true; }
    return false;
  }
  document.addEventListener('click', function(e) {
    var link = e.target.closest('a[href*="#guide-"]');
    if (!link) return;
    e.preventDefault();
    var anchor = link.getAttribute('href').split('#')[1];
    var rest = anchor.replace('guide-','');
    var cat = rest.split('-')[0];
    clickTabById('maintab-guide');
    var subId = CAT_TO_SUBTAB[cat];
    setTimeout(function() {
      if (subId) clickTabById(subId);
      setTimeout(function() {
        var el = document.getElementById(anchor);
        if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
      }, 350);
    }, 350);
  });
}
"""

LANG_JS = """
(lang) => {
  var isEn = (typeof lang === 'string' && lang.indexOf('English') >= 0);
  var T = {
    '🌿 JungleSurvivor — 叢林求生離線 AI 助手': '🌿 JungleSurvivor — Jungle Survival AI Assistant',
    'AI 辨識 + 離線生存指南 | 安全第一': 'AI Identification + Offline Survival Guide | Safety First',
    '🚀 載入模型': '🚀 Load Model',
    '🌙 夜間模式': '🌙 Night Mode',
    '📸 拍照建議：': '📸 Photo Tips:',
    '至少 2 張不同角度': 'At least 2 different angles',
    '光線明亮': 'Good lighting',
    '拍葉片正反面、莖部、花果': 'Capture leaves (both sides), stem, flowers/fruit',
    '放手指當比例尺': 'Include finger for scale reference',
    '📝 文字描述大幅提升準確率：觸感、氣味、環境、高度': '📝 Text description greatly improves accuracy: texture, smell, environment, height',
    '🔍 開始辨識': '🔍 Start Identification',
    '靜態內容，零算力': 'Static content, zero compute',
    '不需 AI，查詢知識庫': 'No AI needed, KB query only',
    '🔍 掃描': '🔍 Scan',
    '尚無紀錄': 'No records yet'
  };
  var R = {};
  Object.keys(T).forEach(function(k){ R[T[k]] = k; });
  var map = isEn ? T : R;
  function replaceText(node) {
    if (node.nodeType === 3) {
      var txt = node.textContent;
      Object.keys(map).forEach(function(k) {
        if (txt.indexOf(k) >= 0) { txt = txt.split(k).join(map[k]); }
      });
      node.textContent = txt;
    } else if (node.nodeType === 1 && node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE') {
      for (var i = 0; i < node.childNodes.length; i++) { replaceText(node.childNodes[i]); }
    }
  }
  var container = document.querySelector('.gradio-container');
  if (container) replaceText(container);
  var tabBtns = document.querySelectorAll('button[role="tab"]');
  var tabMap = isEn ? {
    '🔍 AI 辨識': '🔍 AI Identify',
    '📖 生存指南': '📖 Survival Guide',
    '📍 區域掃描': '📍 Area Scan',
    '📜 歷史紀錄': '📜 History',
    '💧 水': '💧 Water',
    '🍃 食': '🍃 Food',
    '🏥 醫': '🏥 Medical',
    '🏕️ 住': '🏕️ Shelter',
    '🧭 行': '🧭 Navigation',
    '🔧 工具': '🔧 Tools'
  } : {
    '🔍 AI Identify': '🔍 AI 辨識',
    '📖 Survival Guide': '📖 生存指南',
    '📍 Area Scan': '📍 區域掃描',
    '📜 History': '📜 歷史紀錄',
    '💧 Water': '💧 水',
    '🍃 Food': '🍃 食',
    '🏥 Medical': '🏥 醫',
    '🏕️ Shelter': '🏕️ 住',
    '🧭 Navigation': '🧭 行',
    '🔧 Tools': '🔧 工具'
  };
  tabBtns.forEach(function(btn) {
    var t = btn.textContent.trim();
    if (tabMap[t]) btn.textContent = tabMap[t];
  });
  return lang;
}
"""

RESULT_STYLES = {
    "RED":    {"bg": "#FFF0F0", "bd": "#FF0000", "tx": "#CC0000", "emoji": "🔴"},
    "YELLOW": {"bg": "#FFFBE6", "bd": "#FFD700", "tx": "#996600", "emoji": "🟡"},
    "GREEN":  {"bg": "#F0FFF4", "bd": "#00AA00", "tx": "#006600", "emoji": "🟢"},
    "GRAY":   {"bg": "#F5F5F5", "bd": "#888888", "tx": "#555555", "emoji": "⚪"},
}
