# JungleSurvivor MVP 開發計畫

> **進度更新 (2026-04-29)**：第一~三階段全部完成，現進入第四階段：提交準備。

---

## 目標檔案結構

```
Hackthon/                               ← Hackathon 根目錄（可含多個專案）
└── JungleSurvivor/                     ← 本專案
    ├── docs/                           ← 文件區
    │   ├── FirstThought(發想).md
    │   ├── SystemDesign(系統設計).md
    │   ├── TestLog(測試紀錄).md
    │   └── MVP開發計畫.md              ← 本文件
    │
    ├── app/                            ← MVP 程式碼
    │   ├── main.py                     ← Gradio App 入口
    │   ├── pipeline.py                 ← 四層辨識 Pipeline 核心
    │   ├── prompt_builder.py           ← 動態 Prompt 組裝器
    │   ├── response_parser.py          ← JSON 回覆解析器
    │   ├── context_engine.py           ← 環境上下文引擎
    │   ├── model_loader.py             ← 模型載入（支援 Kaggle / Ollama）
    │   └── config.py                   ← 全域設定（閾值、模型路徑等）
    │
    ├── knowledge_base/                 ← 離線知識庫
    │   ├── regions/
    │   │   └── east_asia_subtropical/  ← 台灣 / 華南 / 日本南部
    │   │       ├── toxic_plants.json       ← 有毒植物 20-30 種
    │   │       ├── confusion_pairs.json    ← 混淆物種對 10-15 對
    │   │       ├── edible_plants.json      ← 可食用植物 50 種
    │   │       ├── medicinal_plants.json   ← 藥用植物 30 種
    │   │       └── dangerous_animals.json  ← 危險動物 15 種
    │   └── emergency/
    │       ├── snakebite_first_aid.json
    │       ├── plant_poisoning_first_aid.json
    │       └── wound_care.json
    │
    ├── tests/                          ← 測試腳本
    │   ├── test_pipeline.py
    │   ├── test_prompt_builder.py
    │   └── test_images/                ← 測試用圖片
    │
    ├── requirements.txt
    └── README.md
```

---

## 開發步驟（建議順序）

### Step 1：知識庫建置 `knowledge_base/` ✅ 已完成

**這是最耗時但最重要的部分。** Prompt 的品質直接取決於知識庫的品質。

#### 1-A. 有毒植物 `toxic_plants.json`

先建 10 種（測試中已用過的 + 最常見的），格式如下：

```json
[
  {
    "id": "alocasia_odora",
    "scientific_name": "Alocasia odora",
    "common_names": { "zh-TW": "姑婆芋", "en": "Giant Elephant Ear" },
    "danger_level": "high",
    "toxicity": "全株有毒，汁液含草酸鈣針晶，誤食致口腔灼傷、腹瀉、喉嚨腫脹",
    "morphology": {
      "leaf_shape": "大型心形或箭形，長 50-90cm，寬 40-60cm",
      "leaf_surface": "光滑發亮，深綠色，水珠不成珠狀（會攤平）",
      "leaf_venation": "明顯的羽狀脈，主脈粗壯突出",
      "leaf_tip": "朝上或水平指向",
      "petiole": "粗壯，長 50-100cm，綠色常帶紫暈，接在葉片邊緣",
      "stem": "粗短直立莖，多汁",
      "flower": "佛焰苞花序",
      "fruit": "紅色漿果"
    },
    "habitat": "林下、溪邊、潮濕陰暗處，海拔 0-1500m",
    "confusion_with": ["colocasia_esculenta"],
    "affected_parts": ["全株", "汁液"],
    "symptoms": ["口腔灼傷", "腹瀉", "喉嚨腫脹"],
    "first_aid": "立即漱口，勿催吐，儘速就醫",
    "distribution": {
      "altitude_range": [0, 1500],
      "climate_zones": ["亞熱帶", "熱帶"]
    }
  }
]
```

**第一批（10 種，從測試中已驗證的開始）：**

1. 姑婆芋 (Alocasia odora)
2. 海檬果 (Cerbera manghas)
3. 曼陀羅 (Datura stramonium)
4. 咬人貓 (Urtica thunbergiana)
5. 咬人狗 (Dendrocnide meyeniana)
6. 綠褶菇 (Chlorophyllum molybdites)
7. 鱗柄白毒鵝膏 (Amanita phalloides)
8. 毒漆樹 (Toxicodendron vernicifluum)
9. 夾竹桃 (Nerium oleander)
10. 蘇鐵 (Cycas revoluta)

#### 1-B. 混淆物種對 `confusion_pairs.json`

```json
[
  {
    "id": "taro_vs_alocasia",
    "safe_species": {
      "id": "colocasia_esculenta",
      "common_name_zh": "芋頭",
      "key_features": {
        "leaf_surface": "有天鵝絨般的微絨毛質感，不太光滑",
        "water_droplet_test": "水珠在葉面呈圓珠狀滾動（荷葉效應）",
        "leaf_tip": "通常朝下垂",
        "petiole_attachment": "接在葉片邊緣內側（盾狀著生）",
        "petiole_color": "綠色，較少紫暈",
        "size": "通常比姑婆芋小，葉長 20-50cm"
      }
    },
    "dangerous_species": {
      "id": "alocasia_odora",
      "common_name_zh": "姑婆芋",
      "key_features": {
        "leaf_surface": "光滑發亮，質地像打了蠟",
        "water_droplet_test": "水珠攤平不成珠狀（不具荷葉效應）",
        "leaf_tip": "朝上或水平指向",
        "petiole_attachment": "接在葉片邊緣（非盾狀）",
        "petiole_color": "綠色常帶紫暈",
        "size": "通常比芋頭大，葉長 50-90cm"
      }
    },
    "lethality": "high",
    "interactive_tests": [
      {
        "test_name": "水珠測試",
        "instruction": "在葉面滴一滴水，觀察水珠的形狀",
        "safe_result": "水珠呈圓珠狀，可以滾動",
        "danger_result": "水珠攤平，不成珠狀",
        "is_critical": true
      },
      {
        "test_name": "葉柄接合處特寫",
        "instruction": "拍攝葉柄與葉片的接合處",
        "safe_result": "葉柄接在葉片邊緣內側（盾狀）",
        "danger_result": "葉柄接在葉片邊緣",
        "is_critical": true
      }
    ]
  }
]
```

#### 1-C. 可食用植物 `edible_plants.json`

先建 10 種常見的：

1. 山蘇 (Asplenium nidus)
2. 過貓 (Diplazium esculentum)
3. 野薑花 (Hedychium coronarium)
4. 車前草 (Plantago major)
5. 龍葵 (Solanum nigrum) — 需標註成熟果實才可食
6. 昭和草 (Crassocephalum crepidioides)
7. 山芹菜 (Oenanthe javanica) — 需標註混淆風險
8. 芋頭 (Colocasia esculenta)
9. 野木耳 (Auricularia auricula-judae)
10. 腎蕨 (Nephrolepis cordifolia)

#### 1-D. 危險動物 `dangerous_animals.json`

先建 5 種蛇（已測試架構）：

1. 赤尾青竹絲 (Trimeresurus stejnegeri)
2. 龜殼花 (Protobothrops mucrosquamatus)
3. 雨傘節 (Bungarus multicinctus)
4. 眼鏡蛇 (Naja atra)
5. 百步蛇 (Deinagkistrodon acutus)

---

### Step 2：Pipeline 程式碼 `app/` ✅ 已完成

#### 2-A. `config.py` — 全域設定

```python
THRESHOLDS = {
    "danger_screening": 60,    # ≥ 60% → 立即警告
    "confusion_pairs": 80,     # ≥ 80% → 判定可食；< 80% → 視為有毒
    "useful_resources": 70,    # ≥ 70% → 顯示用途；< 70% → 不確定
}

MAX_NEW_TOKENS = 4096
MODEL_ID = "google/gemma-4-E2B-it"
KNOWLEDGE_BASE_PATH = "../knowledge_base"
DEFAULT_REGION = "east_asia_subtropical"
```

#### 2-B. `context_engine.py` — 環境上下文引擎

- 輸入：GPS（緯/經）、海拔、月份
- 輸出：region_id、climate_zone、vegetation_zone、season
- 功能：根據 region_id 載入對應的知識庫 JSON 檔

#### 2-C. `prompt_builder.py` — 動態 Prompt 組裝器（最關鍵）

- 讀取知識庫 JSON
- 根據辨識層級（danger / confusion / useful）選擇模板
- 動態填入物種特徵清單
- 組裝完整 Prompt（環境上下文 + CoT 指示 + 特徵清單 + JSON 輸出標記）

#### 2-D. `response_parser.py` — 回覆解析器

- 擷取 `<JSON_START>` ... `<JSON_END>` 之間的內容
- 解析 JSON
- 根據 confidence 和 danger_level 決定安全動作
- 判斷是否需要觸發互動式鑑別

#### 2-E. `pipeline.py` — 四層辨識 Pipeline

```python
def identify(images, context):
    # Layer 0: 載入區域知識庫
    kb = context_engine.load_knowledge_base(context)

    # Layer 1: 危險快篩
    danger_prompt = prompt_builder.build_danger_screening(kb, context)
    danger_result = run_model(images, danger_prompt)
    if danger_result.max_similarity >= 60:
        return DangerWarning(danger_result)

    # Layer 2: 混淆鑑別（如果觸發了混淆物種）
    if danger_result.has_confusion_pair:
        confusion_prompt = prompt_builder.build_confusion_pairs(kb, danger_result)
        confusion_result = run_model(images, confusion_prompt)
        if confusion_result.confidence < 80:
            return InteractiveTest(confusion_result)

    # Layer 3: 有用資源辨識
    useful_prompt = prompt_builder.build_useful_resources(kb, context)
    useful_result = run_model(images, useful_prompt)
    if useful_result.confidence >= 70:
        return UsefulResource(useful_result)

    # Layer 4: 通用描述
    return GeneralDescription(useful_result)
```

#### 2-F. `main.py` — Gradio UI

- 照片上傳區域（支援多張）
- 環境設定（地區、海拔、季節 — 可手動輸入或自動偵測）
- 辨識結果面板（根據危險等級用紅/黃/綠色顯示）
- 互動測試指引區域（當觸發混淆鑑別時出現）
- 歷史紀錄

---

### Step 3：Pipeline 整合測試 ✅ 已完成 (2026-04-29)

- ✅ 自包含 Kaggle Notebook 製作完成（`notebooks/kaggle_integration_test.ipynb`）
- ✅ IT1: 姑婆芋單張 → 危險快篩 + 混淆鑑別觸發
- ✅ IT2: 姑婆芋多張 → 多照片信心度提升
- ✅ IT3: 赤尾青竹絲 → 蛇類辨識 + 急救建議
- ✅ IT4: 山蘇 → 完整三層流程 + 採集指引
- ✅ JSON 解析 100% 穩定
- ⚠️ 注意：此測試驗證 Pipeline 邏輯，不含 Gradio UI

詳細測試紀錄見：`TestLog(測試紀錄).md` IT1-IT4 段落

---

### Step 4：Gradio UI 整合與測試（程式碼完成 ✅ 2026-04-29）

- ✅ 4-A. 將 Gradio UI 嵌入 Kaggle Notebook
 → `notebooks/kaggle_gradio_demo.ipynb`（15 Cells，自包含）
 → 所有模組 + 知識庫 + Gradio UI 嵌入單一 .ipynb
- ✅ 4-C. 補完歷史紀錄功能
 → 表格式紀錄（時間/物種/信心度/層級/模式）
 → `main.py` 和 Notebook 同步更新
- ✅ 4-D. UI/UX 調整
 → 結果使用 HTML 色彩面板（紅/黃/綠/灰）
 → 互動測試引導使用橘色面板
 → 歷史紀錄表格使用對應警告色背景
- ⚠️ 4-B. 待 Kaggle 環境實際運行驗證
 → 模型載入 → 照片上傳 → Pipeline 執行 → 結果顯示

---

### Step 5：提交準備

- 🔲 5-A. 提交用 Notebook 整理 — 加入專案介紹、架構圖、技術亮點
- 🔲 5-B. 錄製 Demo 影片
- 🔲 5-C. 撰寫 README + Write-up（公開文章）
- 🔲 5-D. 最終提交

---

## 開發時間線紀錄

```
第一階段  Prompt 驗證        T1-T15             → 已完成 ✅ (2026-04-17)
第二階段  MVP 核心開發        知識庫+Pipeline+UI碼  → 已完成 ✅ (2026-04-29)
第三階段  Pipeline 整合測試    IT1-IT4            → 已完成 ✅ (2026-04-29)
第四階段  Gradio UI 整合測試  嵌入Notebook+UI完成   → 程式碼完成 ✅ (2026-04-29)
                            ⚠️ 待 Kaggle 環境端對端驗證
第五階段  提交準備            Demo+影片+文件        → 待做 🔲
```

---

## 加分項（時間允許）

- 🔲 擴充知識庫（有毒植物 10 → 30 種，可食用 10 → 50 種等）
- 🔲 多區域知識庫（東南亞、溫帶）
- 🔲 複合草藥處方
- 🔲 互動式鑑別流程完整實作（T16 驗證）
- 🔲 語音輸入/輸出
- 🔲 離線部署 Demo（Ollama）

