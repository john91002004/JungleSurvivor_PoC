# JungleSurvivor 改善規劃

> **建立日期**：2026-04-30
> **目的**：規劃 MVP 完成後的三大改善方向，在比賽截止（5/18）前盡可能完成。

---

## 一、系統精進計畫（MVP → 完整產品）

### 1-A. 知識庫大幅擴充（比賽前必做）


| 項目     | 現狀       | 目標                   |
| ------ | -------- | -------------------- |
| 有毒植物   | 10 種     | 25+ 種（含台北常見）         |
| 可食用植物  | 10 種     | 25+ 種（含台北常見）         |
| 混淆物種對  | 5 對      | 12+ 對                |
| 危險動物   | 5 種（僅毒蛇） | 15+ 種（毒蛇+虎頭蜂+蜈蚣+蜱蟲等） |
| 急救 SOP | 3 份      | 6+ 份（新增蜂螫、蜈蚣咬傷、蜱蟲叮咬） |


**台北地區重點新增物種：**

有毒植物新增：

- 馬纓丹（Lantana camara）— 台北極常見，未熟果有毒
- 銀膠菊（Parthenium hysterophorus）— 入侵種，嚴重過敏
- 大花曼陀羅（Brugmansia suaveolens）— 公園偶見
- 美洲商陸（Phytolacca americana）— 外形似可食菜
- 海芋（Zantedeschia aethiopica）— 竹子湖大量分布
- 雞母珠（Abrus precatorius）— 種子劇毒
- 蓖麻（Ricinus communis）— 荒地常見
- 烏桕（Triadica sebifera）— 常見行道樹
- 黃金葛（Epipremnum aureum）— 居家/公園極常見
- 毛地黃（Digitalis purpurea）— 陽明山分布

可食植物新增：

- 大花咸豐草（Bidens pilosa）— 台灣最常見可食野草
- 月桃（Alpinia zerumbet）— 低海拔常見
- 構樹（Broussonetia papyrifera）— 果實可食
- 小葉桑（Morus australis）— 桑椹可食
- 野莧菜（Amaranthus viridis）— 常見野菜
- 魚腥草（Houttuynia cordata）— 濕地常見
- 五節芒嫩筍（Miscanthus floridulus）— 嫩筍可食
- 食茱萸（Zanthoxylum ailanthoides）— 嫩葉調味
- 山黃麻（Trema orientalis）— 嫩葉可食
- 鵝仔草（Pterocypsela indica）— 常見野菜

危險動物新增：

- 虎頭蜂 3 種（黃腰虎頭蜂、黑腹虎頭蜂、中華大虎頭蜂）
- 長腳蜂（Polistes）
- 蜈蚣（Scolopendra subspinipes）
- 紅火蟻（Solenopsis invicta）
- 恙蟲（Leptotrombidium）
- 硬蜱（Ixodes granulatus）
- 水蛭（Haemadipsa）
- 赤背寡婦蛛（Latrodectus hasselti）

混淆物種對新增：

- 青蛇 vs 赤尾青竹絲（安全 vs 危險）
- 紅斑蛇 vs 雨傘節（安全 vs 危險）
- 大花咸豐草 vs 銀膠菊（可食 vs 有毒）
- 美洲商陸 vs 野莧菜（有毒 vs 可食）
- 海芋 vs 姑婆芋 vs 芋頭（三方混淆）
- 馬纓丹果 vs 桑椹（有毒 vs 可食）
- 毛地黃 vs 車前草幼株（有毒 vs 可食）

### 1-B. 知識庫分區架構（比賽後）

```
knowledge_base/
├── regions/
│   ├── east_asia_subtropical/   ← 現有（台灣/華南）
│   ├── southeast_asia_tropical/ ← 未來（東南亞）
│   ├── temperate_forest/        ← 未來（溫帶森林）
│   └── ...
├── global_common/               ← 通用知識庫（任何地區都適用）
│   ├── toxic_plants_global.json     ← 全球最危險的 30 種
│   ├── edible_plants_global.json    ← 全球最常見可食 30 種
│   └── dangerous_animals_global.json
└── emergency/                   ← 現有
```

---

## 二、知識庫安全兜底機制（最關鍵的安全改進）

### 問題描述

目前的辨識流程**只在知識庫範圍內比對**。如果一個危險物種不在知識庫裡，系統可能：

1. Layer 1 未匹配危險物種（因為知識庫沒收錄）
2. Layer 3 匹配到相似的可食物種 → **誤判為安全** → 致命錯誤

### 解決方案：三層安全防線

```
┌─────────────────────────────────────────────────────┐
│ 防線 1：知識庫精確比對（現有機制）                        │
│   → 用區域知識庫做精確的特徵比對                         │
│   → 優點：快、準、可解釋                               │
│   → 缺點：只能辨識知識庫中的物種                         │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ 防線 2：模型原生知識交叉驗證（新增）                      │
│   → 不限於知識庫，讓 Gemma 用自身訓練知識額外判斷           │
│   → Prompt：「不要只看上面的清單，根據你所有的知識，         │
│     這個東西有沒有任何可能是有毒或危險的？」                │
│   → 如果模型自身知識認為有毒，即使知識庫說安全 → 以危險為準  │
│   → 優點：覆蓋知識庫外的物種                             │
│   → 缺點：依賴模型訓練資料，可能不夠精確                   │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ 防線 3：明確告知信賴邊界（新增）                          │
│   → 在結果中顯示：「本區域知識庫收錄 N 種危險物種，          │
│     無法排除未收錄的危險物種」                             │
│   → 讓使用者了解系統的能力邊界                            │
│   → 無法確定時，預設結果永遠是「不要碰」                   │
└─────────────────────────────────────────────────────┘
```

### 實作方式

**Pipeline 修改（pipeline.py）：**

```python
# 在 Layer 3（可利用資源辨識）之前，新增模型自由判斷步驟：
def _run_model_native_safety_check(self, images, context):
    """讓模型用自身知識做安全性交叉驗證（不限於知識庫）"""
    prompt = """
    You are a toxicology expert. Look at this photo carefully.
    DO NOT limit yourself to any species list.
    Using ALL your knowledge, is there ANY possibility
    this could be toxic, venomous, or dangerous?
    
    If there is even a small chance of danger, say so.
    When in doubt, classify as potentially dangerous.
    
    Output JSON:
    {
      "might_be_dangerous": true/false,
      "reasoning": "...",
      "possible_species": "...",
      "confidence_safe": 0-100
    }
    """
    response = self.model.generate(prompt, images)
    return parse_safety_check_response(response)
```

**修改後的 Pipeline 流程：**

```
Layer 1: 知識庫危險快篩 → 命中 → 🔴 警告
                         ↓ 未命中
Layer 1.5（新增）: 模型原生安全檢查
    → 模型認為可能危險 → 🟡 注意 + 建議不碰
    → 模型認為安全 → 進入 Layer 3
                         ↓
Layer 3: 知識庫可利用資源辨識 → 命中 → 🟢 + 結果附加信賴邊界聲明
                              ↓ 未命中
Layer 4: 不確定 → ⚪ 建議不碰
```

### 優先級

- **比賽前必做**：防線 2（模型原生知識交叉驗證）+ 防線 3（信賴邊界聲明）
- **比賽後**：建立全球通用知識庫作為區域知識庫的後備

---

## 三、多模態輸入擴展

### 目前狀態

僅支援**照片**輸入（單張或多張）。

### 擴展計畫（按優先順序）

#### 3-A. 照片 + 文字描述（比賽前必做）

**為什麼最優先：**

- 文字描述能提供照片無法傳達的資訊（氣味、觸感、質地）
- 例如：「葉面摸起來有絨毛感」→ 直接幫助判斷芋頭 vs 姑婆芋
- Gemma 4 本身就是多模態模型，技術改動極小

**實作方式：**

```python
# prompt_builder.py 修改
def build_danger_screening_prompt(context, kb, target_type, user_description=None):
    prompt = ...  # 原有 Prompt
    
    if user_description:
        prompt += f"""

The user also provides the following verbal description:
"{user_description}"

Incorporate this information into your analysis.
Verbal descriptions of smell, texture, and touch are especially 
valuable since they cannot be determined from photos alone.
"""
    return prompt
```

**UI 修改：**

- 在照片上傳區域下方新增一個文字輸入框
- 標籤：「📝 補充描述（可選）：描述氣味、觸感、生長環境等照片看不到的資訊」
- 傳入 Pipeline 後附加到 Prompt 中

#### 3-B. 純文字描述辨識（比賽後）

當使用者無法拍照時（太暗、手機壞了），用文字描述做初步辨識。

#### 3-C. 語音輸入（比賽後）

語音 → 文字轉換 → 走文字流程。適合雙手不方便的野外場景。
Gemma 4 支援音訊輸入，技術上可直接傳入語音。

#### 3-D. 語音輸出（比賽後）

將辨識結果和急救指引朗讀出來。在緊急情況下，使用者可能沒辦法看螢幕。

---

## 四、手機端部署規劃（比賽後長期目標）

### AI Edge Gallery

Google AI Edge Gallery 可以在手機上跑 Gemma 4 E2B/E4B 原生模型。
但它只是跑原始模型，**不包含我們的知識庫、Prompt 模板、和安全機制**。

### 完整手機部署需要

```
JungleSurvivor Mobile App
├── Gemma 4 E2B（量化為 INT4，約 1.5-2GB）
│   └── 透過 MediaPipe / AI Edge SDK 載入
├── 知識庫 JSON（約 1-2MB）
│   └── 打包在 App 內
├── Prompt 模板
│   └── 打包在 App 內
├── Pipeline 邏輯（Python → Kotlin/Swift 改寫）
│   └── 四層辨識 + 安全防線
└── 原生 UI
    └── 相機整合、結果顯示、歷史紀錄
```

### 硬體需求


| 等級  | RAM    | 量化        | 推理速度        | 代表機型                                |
| --- | ------ | --------- | ----------- | ----------------------------------- |
| 最低  | 4GB    | INT4      | 3-5 tok/s   | Pixel 6a, Samsung A54               |
| 建議  | 6-8GB  | INT4/INT8 | 8-15 tok/s  | Pixel 8, Samsung S24, iPhone 15 Pro |
| 最佳  | 8-12GB | INT8/BF16 | 15-30 tok/s | Pixel 9 Pro, Samsung S25 Ultra      |


---

## 五、時程規劃

```
現在 → 5/10    知識庫大幅擴充（台北完整版）
               模型原生安全兜底（防線 2+3）
               照片+文字描述輸入
               CUDA OOM 修復 ✅
               
5/10 → 5/15    Kaggle 環境完整驗證
               Write-up 撰寫
               Demo 影片錄製
               
5/15 → 5/18    最終調整
               提交
               
比賽後          多區域知識庫
               語音輸入/輸出
               手機端部署
               Fine-tuning 精調
```

---

## 版本紀錄


| 日期         | 版本   | 內容                |
| ---------- | ---- | ----------------- |
| 2026-04-30 | v1.0 | 建立改善規劃文件，規劃三大改善方向 |


