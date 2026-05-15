"""JungleSurvivor 全域設定"""

from pathlib import Path

# === 路徑設定 ===
# app/ 的 parent 是 JungleSurvivor/，再 parent 不需要
PROJECT_ROOT = Path(__file__).parent.parent
KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "knowledge_base"
REGIONS_PATH = KNOWLEDGE_BASE_PATH / "regions"
EMERGENCY_PATH = KNOWLEDGE_BASE_PATH / "emergency"

# === 模型設定 ===
MODEL_ID = "google/gemma-4-E2B-it"
MAX_NEW_TOKENS = 4096
DEFAULT_DTYPE = "bfloat16"

# === 辨識閾值（經 T8-T15 測試驗證） ===
THRESHOLDS = {
    "danger_screening": 60,     # ≥ 60% → 🔴 立即警告（寧可誤報也不漏報）
    "confusion_pairs": 80,      # ≥ 80% → 判定可食；< 80% → 視為有毒
    "useful_resources": 70,     # ≥ 70% → 🟢 顯示用途；< 70% → 不確定
}

# === 預設區域 ===
DEFAULT_REGION = "east_asia_subtropical"

# === 支援的區域列表 ===
AVAILABLE_REGIONS = {
    "east_asia_subtropical": {
        "name_zh": "東亞亞熱帶（台灣、華南、日本南部）",
        "climate_zone": "亞熱帶",
        "default_altitude": 500,
        "default_vegetation": "低海拔闊葉林",
    },
}

# === JSON 輸出標記 ===
JSON_START_MARKER = "<JSON_START>"
JSON_END_MARKER = "<JSON_END>"

# === 警告等級 ===
WARNING_LEVELS = {
    "RED": {"color": "#FF0000", "label_zh": "🔴 危險", "action": "立即遠離"},
    "YELLOW": {"color": "#FFD700", "label_zh": "🟡 注意", "action": "謹慎處理"},
    "GREEN": {"color": "#00AA00", "label_zh": "🟢 安全", "action": "可安全使用"},
    "GRAY": {"color": "#888888", "label_zh": "⚪ 不確定", "action": "無法判斷，建議不碰"},
}
