# JungleSurvivor v2 — 邏輯流程規劃書

> **版本**：v2.1（架構重構 — 計分/信心度/UI 修訂）
> **日期**：2026-05-08（v2.0）→ 2026-05-08（v2.1 修訂）
> **核心改變**：LLM 只做特徵萃取（看圖填表），比對排序完全由傳統演算法處理。
>
> **v2.1 修訂摘要**：
>
> - 陣列型計分公式改為 `|交集| / max(|觀察|, |KB|)`
> - 信心度公式改為 `得分 / 物種有效總權重`（含 photo_observable 區分）
> - 使用者輸入改為 tag/chip 完整編輯控制（不再區分覆蓋/追加）
> - 警告等級判定加入嚴格優先順序邏輯
> - 新增「區域感知生存指南」章節

---

## 一、背景與動機

### 1.1 比賽資訊

- **比賽**：Kaggle — The Gemma 4 Good Hackathon
- **獎金**：$200,000 USD
- **截止**：2026-05-18 (11:59 PM UTC)
- **要求**：必須使用至少一個 Gemma 4 模型
- **評分**：Impact & Vision (40%) / Video Pitch & Storytelling (30%) / Technical Depth (30%)
- **強調**：邊緣部署 (edge-based deployment)、離線優先 (offline-first)

### 1.2 v1 架構的問題


| 問題            | 說明                                        |
| ------------- | ----------------------------------------- |
| **太慢**        | LLM 要做辨識 + 比對 + 排名 + 解釋，每次需要 2-3 次 LLM 呼叫 |
| **不準**        | LLM 自行判斷信心度，每次結果不同，不具可重現性                 |
| **Prompt 太長** | 把整個知識庫塞進 Prompt，token 消耗巨大                |
| **手機跑不動**     | 算力需求太高，無法在行動裝置上即時運算                       |
| **功能過雜**      | 同時處理動物、植物、海拔推算，模型算力分散                     |


### 1.3 v2 設計哲學

> **LLM 當「眼睛」（看圖萃取特徵），演算法當「大腦」（比對排序決策）。**

- LLM 只做一件事：看照片，填寫結構化的特徵表格（JSON）
- 比對、排序、剪枝、信心度計算全部用傳統演算法
- 同樣的特徵輸入 → 永遠得到同樣的排名結果（確定性）
- 只辨識植物，不做動物辨識（算力集中）
- 去掉海拔推算等雜項功能

---

## 二、Gemini 回饋評估

### 2.1 Gemini 正確的觀點


| 觀點                 | 說明                                          |
| ------------------ | ------------------------------------------- |
| **聯集而非交集**         | 多張照片的特徵應取聯集（互補），不是交集（會變空集合）                 |
| **不需要向量比對**        | 用結構化 JSON 輸出 + 字串/布林匹配，不需要 embedding 或餘弦相似度 |
| **Early Stopping** | 分支界限法剪枝，不可能超越第 3 名就提前停止比對                   |
| **GPS 地理圍欄**       | 用 GPS 自動選擇區域知識庫，縮小搜尋空間                      |
| **文字描述優先**         | 人類對氣味、觸感的判斷比 AI 看圖猜更可靠                      |


### 2.2 Gemini 需要修正的觀點


| 觀點          | 問題                | 修正                            |
| ----------- | ----------------- | ----------------------------- |
| 「其他」權重 3    | 模糊特徵給高權重可能導致誤判    | 改為**從 KB 自動計算稀有度權重**（預計算，非動態） |
| TF-IDF 動態計算 | 手機上即時算 TF-IDF 不實際 | 權重在**建構知識庫時預先計算好**，執行時只查表     |


### 2.3 Gemini 沒提到但很重要的點


| 補充項目                    | 說明                                           |
| ----------------------- | -------------------------------------------- |
| **LLM 輸出可控性**           | 小模型 JSON 輸出容易格式錯誤，需強制選擇題式 prompt + schema 驗證 |
| `**not_visible` 是合法選項** | 防止模型對看不到的部位亂猜                                |
| **不扣分策略**               | 照片不清楚可能導致誤判扣分，只加分不扣分更安全                      |


---

## 三、系統架構總覽

```
┌─────────────────────────────────────────────────────────────┐
│                     使用者輸入層                              │
│  📷 照片(逐張) + 📝 結構化表單(可選) + 📍 GPS/地區(可選)       │
│  📝 自由文字觀察(可選，不比對，純展示)                          │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 0：預處理（零 AI 成本）                                │
│  ① GPS/使用者選擇 → 決定地區 → 載入該區知識庫（≤50 個物種）     │
│  ② 圖片預處理（縮放、壓縮）                                   │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1：特徵萃取（✦ 唯一使用 LLM 的步驟 ✦）                │
│  輸入：單張照片 + 強制選擇題式 prompt                          │
│  輸出：結構化 JSON（每個部位 × 每個屬性 = enum 值）             │
│  ※ 逐張萃取，每張完成後即時顯示給使用者                         │
│  ※ 使用者可決定是否繼續補拍                                    │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2：特徵合併（零 AI 成本）                              │
│  ① 合併多張照片特徵（聯集）                                   │
│  ② 合併使用者手動填入的特徵（使用者值覆蓋照片值）                │
│  ③ 所有屬性最終都可能是陣列型（因聯集）                         │
│  ④ 產出：完整的未知植物特徵檔案                                │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3：比對排序（零 AI 成本，純演算法）                     │
│  ① 逐物種比對特徵 → 正規化加分 × 權重（不扣分）                │
│  ② Early Stopping 剪枝                                      │
│  ③ 取 Top 3 + 信心度百分比                                   │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4：後處理與輸出（零 AI 成本）                          │
│  ① 信心度 < 60% → 標記為未登錄物種                            │
│  ② 查找混淆物種對 → 附加區分指引 + 互動測試                    │
│  ③ 展示 KB 的診斷性特徵讓使用者自行比對                        │
│  ④ 生成結果摘要 + 危險警告                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、Phase 0：預處理（零 AI 成本）

### 4.1 地區決定


| 來源     | 方法                          |
| ------ | --------------------------- |
| GPS 座標 | 座標 → 行政區查表 → region_id      |
| 使用者手選  | App 設定 UI 直接選擇地區            |
| 預設     | `east_asia_subtropical`（台灣） |


### 4.2 載入知識庫

根據 `region_id` 載入該地區的結構化物種知識庫（JSON 檔案）。
目前只建置 `east_asia_subtropical`（台灣），包含 50 個物種。

### 4.3 圖片預處理

- Resize 到模型可接受的尺寸
- JPEG 壓縮降低記憶體佔用
- 在手機端，這一步可以利用原生 API 完成

---

## 五、Phase 1：特徵萃取（唯一使用 LLM 的步驟）

### 5.1 核心原則

- **LLM 只做「看圖填選擇題」**，不做辨識、不做比對、不做排名
- **不把知識庫內容塞進 Prompt** → 大幅縮短 prompt，省 token 省算力
- **逐張照片萃取** → 每張完成即時顯示，使用者可自行決定是否補拍
- **強制 enum 選擇** → 輸出可預測，方便後續字串比對

### 5.2 逐張迭代流程

```
拍照 1 → LLM 萃取 → UI 顯示特徵表（已填/未填一目瞭然）
  → 使用者看到「花：not_visible」→ 決定補拍花
拍照 2 → LLM 萃取 → 聯集合併 → UI 更新特徵表
  → 使用者覺得夠了 → 按「開始辨識」
→ 進入 Phase 2 + Phase 3
```

好處：

- 手機一次只處理一張圖，記憶體峰值低
- 使用者得到即時回饋
- 系統可引導使用者：「目前缺少花的資訊，建議補拍花的特寫」

### 5.3 LLM Prompt 設計

```
你是植物特徵辨識器。請觀察照片中的植物，針對每個可見部位，
從預定義選項中選擇最符合的答案。

【規則】
- 只選你確實在照片中看到的。看不到的部位填 "not_visible"。
- 不確定的屬性填 "uncertain"。
- 嚴禁猜測看不到的部位。
- 輸出純 JSON，不要任何解釋文字。

【請填寫以下 JSON】
{
  "growth_form": 從 [<enum 選項>] 選,
  "height_estimate": 從 [<enum 選項>] 選,
  "leaf": {
    "visible": true/false,
    "shape": 從 [<enum 選項>] 選,
    "edge": 從 [<enum 選項>] 選,
    "colors": [從 <顏色 enum> 中選一到多個],
    "color_pattern": 從 [<enum 選項>] 選,
    "surface_top": 從 [<enum 選項>] 選,
    "surface_bottom": 從 [<enum 選項>] 選,
    "arrangement": 從 [<enum 選項>] 選,
    "size": 從 [<enum 選項>] 選,
    "venation": 從 [<enum 選項>] 選,
    ...更多屬性
    "other_observations": "自由文字，只填上述選項無法涵蓋的重要特徵"
  },
  "stem": { ...同樣格式... },
  "flower": { ...同樣格式... },
  "fruit": { ...同樣格式... },
  "root": { ...同樣格式... },
  "overall": {
    "latex": 從 [<enum 選項>] 選,
    "smell": "not_checkable",
    "water_droplet_test": 從 [<enum 選項>] 選,
    "notable_features": "自由文字，只填最顯著的 1-2 個特殊特徵"
  }
}
```

**Prompt 中的 enum 選項列表是從知識庫自動生成的**（見第九章）。

### 5.4 JSON 輸出驗證

LLM 輸出的 JSON 需要經過嚴格驗證：

1. **格式驗證**：JSON 是否合法？（復用現有 `response_parser.py` 的修復邏輯）
2. **Schema 驗證**：每個欄位是否存在？值是否在合法 enum 內？
3. **容錯處理**：
  - 值不在 enum 內 → 標記為 `uncertain`
  - JSON 完全壞掉 → 重試一次，或回傳「萃取失敗，請重新拍攝」
4. `**not_visible` 不算錯** → 是合法的預期輸出

---

## 六、Phase 2：特徵合併（零 AI 成本）

### 6.1 多張照片合併規則

所有屬性最終都可能因聯集而成為**陣列型**。

#### 陣列型屬性（如 colors）

直接取聯集：

```
照片 1: flower.colors = ["yellow"]
照片 2: flower.colors = ["red", "white"]

合併: flower.colors = ["yellow", "red", "white"]
```

#### 單值型屬性（如 shape、edge）

- 多張照片值相同 → 保留單值
- 多張照片值不同 → 轉為陣列（都保留，代表不確定）

```
照片 1: leaf.shape = "heart"
照片 2: leaf.shape = "arrow"

合併: leaf.shape = ["heart", "arrow"]  ← 兩個都保留
```

#### `not_visible` 和 `uncertain` 的處理

- `not_visible` + 任何有效值 → 取有效值（照片互補）
- `uncertain` + 明確值 → 取明確值
- `not_visible` + `not_visible` → 保持 `not_visible`

### 6.2 使用者手動輸入的合併規則

#### 可編輯 Tag/Chip 介面

每個特徵欄位都呈現為**可編輯的 tag/chip 列表**，使用者擁有完整控制權：

```
┌─ 花朵顏色 ──────────────────────────────────┐
│  [yellow ×] [red ×]  [+ 新增 ▼]            │
│   ↑ AI 萃取                                 │
│  點 × 可刪除，點 [+ 新增] 可從 enum 清單中加入 │
└─────────────────────────────────────────────┘

┌─ 葉面質感 ──────────────────────────────────┐
│  [glossy ×]  [+ 新增 ▼]                     │
│   ↑ AI 萃取，使用者可直接刪掉改成 rough       │
└─────────────────────────────────────────────┘
```

**規則：**

- **不再區分「覆蓋」vs「追加」** — 使用者看到的就是最終值，可自由增刪
- 每個 tag 標示來源（🤖 AI 萃取 / 👤 使用者輸入），方便識別
- 使用者修改的欄位用不同顏色/圖示標記，可一鍵恢復 AI 原始值
- 所有欄位在「確認並辨識」之前都可隨時調整
- 候選值來自 KB 自動衍生的 enum 清單，確保輸入合法

```
範例操作流程：

1. AI 萃取完成後，花朵顏色顯示: [yellow 🤖 ×] [red 🤖 ×]
2. 使用者認為不是 red → 點擊 × 刪除 → [yellow 🤖 ×]
3. 使用者看到花上有 purple → 點 [+ 新增] 選 purple → [yellow 🤖 ×] [purple 👤 ×]
4. 最終送入比對的值: flower.colors = ["yellow", "purple"]
```

**優點：**

- 消除「覆蓋 vs 追加」的歧義 — 所見即所得
- 使用者對最終輸入有完全掌控感
- 可隨時恢復 AI 原始值，降低誤操作風險

### 6.3 自由文字欄位

- `other_observations` 和 `notable_features` 是自由文字
- **不餵給 LLM 做結構化萃取**
- **不參與 Phase 3 的演算法比對**
- 原樣保存，Phase 4 展示在結果頁讓使用者自行參考

### 6.4 使用者文字描述

使用者想補充特徵 → 用**結構化 dropdown 表單**（和 enum 候選值一致）
使用者想寫無法歸類的觀察 → 用**自由文字欄位**，純展示用途

**不讓 LLM 處理使用者的自由文字**，理由：

1. 多一次 LLM 呼叫 = 多一倍延遲和算力
2. LLM 可能誤解文字，覆蓋掉照片原本正確的分析值
3. 使用者直接用 dropdown 選更快更準

---

## 七、Phase 3：比對排序演算法（零 AI 成本）

### 7.1 計分規則：只加分，不扣分


| 情況                 | 處理          |
| ------------------ | ----------- |
| 觀察值與 KB 值吻合        | +weight（加分） |
| 觀察值與 KB 值不同        | 0（不加分，也不扣分） |
| 觀察值為 `not_visible` | 跳過，不計入分母    |
| 觀察值為 `uncertain`   | 跳過，不計入分母    |


**為什麼不扣分：**

- 照片不清楚或角度不佳，LLM 可能誤判特徵值
- 如果扣分，正確的物種反而可能因為一個誤判特徵被排到後面
- 不扣分的情況下，Early Stopping 剪枝依然有效（透過「機會成本」而非「負分」）

### 7.2 單值屬性計分

```
if observed_value in ("not_visible", "uncertain"):
    score_contribution = 0      # 跳過，不計入
elif observed_value == kb_value:
    score_contribution = weight  # 完全吻合
else:
    score_contribution = 0       # 不吻合但不扣分
```

### 7.3 陣列型屬性計分（正規化版本）

```
observed_set = {"yellow", "red"}                # 觀察到的值
kb_set = {"yellow", "red", "white", "purple"}   # KB 中的值
intersection = observed_set ∩ kb_set            # 交集 = {"yellow", "red"}

denominator = max( |observed_set|, |kb_set| )   # max(2, 4) = 4

score_contribution = weight × ( |intersection| / denominator )
                   = weight × ( 2 / 4 )
                   = weight × 0.5
```

**分母使用 `max(|observed_set|, |kb_set|)` 的設計考量：**

v2.0 原先用 `|observed_set|` 作分母，會出現一個問題：
若某物種有 4 種顏色，觀察到 1 種且吻合 → `1/1 = 1.0×w`（滿分），
觀察到 4 種且全部吻合 → `4/4 = 1.0×w`（也是滿分）。
**觀察了更多匹配的證據，卻沒有得到更高的回報 — 不合理。**

使用 `max(|observed|, |kb|)` 同時解決兩個方向的問題：

1. **觀察較少時（|observed| < |kb|）**：分母 = |kb|，只確認了部分特徵 → 得分成比例降低
2. **觀察較多時（|observed| > |kb|）**：分母 = |observed|，多出來的值不在 KB → 稀釋匹配比率


| 情境        | observed                          | KB                           | 交集  | 分母         | 得分           | 合理性                |
| --------- | --------------------------------- | ---------------------------- | --- | ---------- | ------------ | ------------------ |
| 觀察到 1 種吻合 | [yellow]                          | [yellow, red, white, purple] | 1   | max(1,4)=4 | 1/4 = 0.25×w | ✅ 只確認了 25%，分數偏低但合理 |
| 觀察到 2 種吻合 | [yellow, red]                     | [yellow, red, white, purple] | 2   | max(2,4)=4 | 2/4 = 0.50×w | ✅ 確認了一半            |
| 全部吻合      | [yellow, red, white, purple]      | 同左                           | 4   | max(4,4)=4 | 4/4 = 1.00×w | ✅ 完美匹配，滿分          |
| 部分吻合+多餘   | [yellow, red, blue]               | [yellow, red, white, purple] | 2   | max(3,4)=4 | 2/4 = 0.50×w | ✅ blue 不在 KB，不影響分母 |
| 多餘超過 KB   | [yellow, red, blue, pink, orange] | [yellow, red]                | 2   | max(5,2)=5 | 2/5 = 0.40×w | ✅ 大量不匹配值稀釋得分       |
| 完全不符      | [blue, pink]                      | [yellow, red, white, purple] | 0   | max(2,4)=4 | 0/4 = 0      | ✅ 完全不匹配            |


**此公式的核心語義：**「觀察到的特徵和 KB 的特徵之間，最大涵蓋範圍內有多少是吻合的？」

- 觀察越多且吻合越多 → 分數越高（回報遞增）
- 觀察越多但不吻合越多 → 分數越低（隱式負面訊號）
- 每個屬性的得分仍然上限為 `weight`（當完美匹配時）

### 7.4 信心度計算

#### 兩種候選方案的比較


| 方案         | 公式                              | 分母定義           | 語義              |
| ---------- | ------------------------------- | -------------- | --------------- |
| A（v2.0 原版） | score / Σ(已觀察屬性的 weight)        | 只看使用者實際提供了值的欄位 | 「我提供的東西匹配了多少？」  |
| B（v2.1 採用） | score / species_effective_total | 物種所有理論上可觀察的欄位  | 「這個物種整體上匹配了多少？」 |


**方案 A 的缺陷：**

- 觀察到 2 個特徵、全部吻合 → 信心度 100%，但這只是基於很少的證據
- 會給使用者「很有信心」的錯覺，實際上只驗證了冰山一角
- 不鼓勵使用者多觀察 — 反正少觀察就能 100%

**選擇方案 B 的原因：**

- 信心度真正反映了「這個物種在所有可驗證的維度上吻合了多少」
- 自然鼓勵使用者觀察更多特徵 → 信心度才會上升 → 更安全
- 對於有毒植物辨識場景，偏保守（不輕易給高信心度）更安全

#### 公式定義

```
species_score = Σ (每個屬性的 score_contribution)

species_effective_total = Σ (所有「理論上可從當前輸入取得」的屬性的 max_weight)
                       = Σ (photo_observable 屬性的 weight)      ← 只要有上傳照片
                       + Σ (使用者手動填入的非照片屬性的 weight)   ← smell, touch 等

confidence = species_score / species_effective_total × 100%
```

#### photo_observable 的區分

KB 中的每個屬性標記 `photo_observable: true/false`：


| 屬性                   | photo_observable | 說明             |
| -------------------- | ---------------- | -------------- |
| leaf.shape           | true             | 照片可見           |
| leaf.colors          | true             | 照片可見           |
| flower.arrangement   | true             | 照片可見           |
| stem.surface_texture | true             | 照片有時可見         |
| smell                | false            | 照片看不到，需要使用者實地聞 |
| taste                | false            | 照片看不到，且不建議嘗試   |
| sap.latex_test       | false            | 需要實地折斷莖觀察      |
| root.type            | false            | 通常在地下，照片看不到    |


#### 計算範例

```
假設某物種有 17 個特徵欄位：
  - 12 個 photo_observable = true  (weight 合計 = 38)
  - 5 個 photo_observable = false (weight 合計 = 15)

場景 1：使用者只上傳了照片，沒有手動輸入
  species_effective_total = 38（只算 photo_observable 部分）
  假設 species_score = 25
  confidence = 25 / 38 × 100% = 65.8%

場景 2：使用者上傳了照片，還手動輸入了 smell
  species_effective_total = 38 + weight(smell) = 38 + 3 = 41
  假設 species_score = 25 + 3 = 28（smell 也吻合）
  confidence = 28 / 41 × 100% = 68.3%

場景 3：使用者上傳照片 + 手動輸入 smell + sap.latex_test
  species_effective_total = 38 + 3 + 4 = 45
  假設 species_score = 28 + 4 = 32
  confidence = 32 / 45 × 100% = 71.1%
```

#### UI 顯示

在信心度旁邊標示觀察完整度，讓使用者知道可信程度：

```
信心度: 65.8%（基於 12/17 項可觀察特徵）
💡 試著補充 氣味、汁液測試 等資訊，可提高辨識信心度
```

#### 對 not_visible / uncertain 的處理

- 如果某個 photo_observable 屬性的 LLM 萃取結果為 `not_visible`：
  - **仍計入 effective_total**（因為理論上照片應該能看到）
  - score_contribution = 0（因為無法比對）
  - 結果：信心度會被拉低 → 鼓勵使用者拍更好的照片或多角度拍攝
- 如果使用者手動將一個本來 `not_visible` 的值改為具體值：
  - 該屬性正常參與計分

### 7.5 Early Stopping 剪枝

```python
top3 = MinHeap(size=3)

effective_total = compute_effective_total(observed, has_photo=True)

for species in kb_species:
    score = 0

    comparable_attrs = [attr for attr in species.features
                        if attr.photo_observable or observed[attr] is not None]
    species_max = sum(attr.weight for attr in comparable_attrs)
    compared_weight = 0

    for attr in comparable_attrs:
        score += compute_score(observed[attr], species[attr], attr.weight)
        compared_weight += attr.weight
        remaining_max = species_max - compared_weight

        # ★ 剪枝：剩餘全部滿分也不可能超越當前第 3 名 → 跳過
        if score + remaining_max < top3.min_score:
            break

    confidence = score / effective_total * 100
    top3.try_insert(species, score, confidence)

return top3.sorted_descending()
```

Early Stopping 的剪枝仍然基於原始分數（score）而非信心度，因為信心度的分母（effective_total）對所有物種都相同。

### 7.6 權重設計

**權重從知識庫自動計算，不人為指定。**

計算公式（預計算，存在 KB 裡）：

```
weight(feature, value) = max(1, round(log2(N / count(value))))

N = 知識庫總物種數
count(value) = 有多少物種的該欄位等於此值
```

範例（假設 N=50）：


| 特徵值                                 | 出現次數 | 計算                | 權重  |
| ----------------------------------- | ---- | ----------------- | --- |
| leaf.colors = green                 | 40   | log2(50/40) ≈ 0.3 | 1   |
| leaf.arrangement = alternate        | 18   | log2(50/18) ≈ 1.5 | 2   |
| flower.arrangement = spathe_spadix  | 3    | log2(50/3) ≈ 4.1  | 4   |
| leaf.arrangement = bird_nest_radial | 1    | log2(50/1) ≈ 5.6  | 6   |


越稀有的特徵值 → 權重越高 → 鑑別力越強。

---

## 八、Phase 4：後處理與輸出（零 AI 成本）

### 8.1 警告等級判定

#### 嚴格優先順序（由高到低，命中即返回）

警告等級的判定必須按照**嚴格的優先順序**，從最危險的情況開始評估，一旦命中就立即返回，不再往下檢查。這確保安全性永遠最優先。

```python
def determine_warning_level(top3_results):
    """
    嚴格優先順序判定警告等級。
    top3_results: [(species, confidence, category), ...] 按信心度降序排列
    """
    top1 = top3_results[0]
    top1_conf = top1.confidence
    top1_cat = top1.category

    # ── 優先級 1：最高危 ─────────────────────────────
    # Top 1 是危險物種且信心度高 → 紅色警報
    if top1_conf >= 60 and top1_cat == "dangerous":
        return "RED", "⚠️ 高度危險！此植物極可能有毒，請勿觸碰或食用。"

    # ── 優先級 2：高危 ───────────────────────────────
    # Top 1 信心度不足，但 Top 3 中有危險物種且信心度 ≥ 40%
    dangerous_in_top3 = [r for r in top3_results if r.category == "dangerous" and r.confidence >= 40]
    if dangerous_in_top3:
        return "ORANGE", "⚠️ 候選結果中有危險物種，請謹慎對待，建議進一步確認。"

    # ── 優先級 3：混淆警告 ──────────────────────────
    # Top 3 中存在已知混淆物種對（一安全一危險）
    has_confusion = check_confusion_pairs(top3_results)
    if has_confusion:
        return "YELLOW", "⚠️ 候選結果中有外觀相似的安全/危險物種對，請仔細比對區分特徵。"

    # ── 優先級 4：信心度不足 ─────────────────────────
    # 所有 Top 3 信心度都很低
    if top1_conf < 40:
        return "GREY", "❓ 無法確定此物種，知識庫中未找到高度匹配的紀錄。建議不要食用或觸碰。"

    # ── 優先級 5：安全 ──────────────────────────────
    # Top 1 是安全物種且信心度高
    if top1_conf >= 60 and top1_cat in ("edible", "medicinal"):
        return "GREEN", "✅ 此植物可能可安全使用，但仍建議確認後再行動。"

    # ── 優先級 6：一般不確定 ─────────────────────────
    # 信心度中等，非危險非安全
    return "GREY", "❓ 辨識結果信心度不高，建議補充更多照片或特徵資訊。"
```

#### 等級說明表


| 等級     | 顏色  | 觸發條件                           | 語義             |
| ------ | --- | ------------------------------ | -------------- |
| RED    | 🔴  | Top 1 ≥ 60% 且 dangerous        | 幾乎確定是危險植物      |
| ORANGE | 🟠  | Top 3 中有 dangerous 且 ≥ 40%     | 候選中有危險物種，需小心   |
| YELLOW | 🟡  | Top 3 有已知混淆物種對                 | 存在容易混淆的安全/危險物種 |
| GREEN  | 🟢  | Top 1 ≥ 60% 且 edible/medicinal | 可能安全，但仍需確認     |
| GREY   | ⚪   | 其他情況                           | 不確定，建議不碰       |


**設計原則：安全第一。** 只要有任何危險跡象，就先報危險。只有在排除所有危險可能性之後，才會給出 GREEN。

### 8.2 未登錄物種處理

當 Top 1 信心度 < 60%：

> 「無法確定此物種。根據觀察到的特徵：[列出已萃取的特徵]，
> 這類植物在此地區的知識庫中未有高度匹配的紀錄。
> 建議不要食用或觸碰。」

### 8.3 混淆物種對處理

#### 混淆物種在 KB 中的定位

混淆物種（如姑婆芋 vs 芋頭）**本身就是 KB 中的一般物種條目**，它們各自擁有完整的結構化特徵、權重、和 category 標記。

`confusion_pairs.json` 是一個**獨立的關係表**，不儲存物種特徵，只記錄：

- 哪些物種之間容易混淆
- 關鍵區分特徵有哪些
- 互動測試指引（如水珠測試、折莖觀察汁液等）

```json
{
  "confusion_pairs": [
    {
      "species_a": "giant_taro",        // 姑婆芋（dangerous）
      "species_b": "taro",              // 芋頭（edible）
      "key_differences": [
        {
          "feature": "leaf.surface_top",
          "species_a_value": "glossy",
          "species_b_value": "velvety",
          "test": "用手指摸葉面，光滑發亮 = 姑婆芋，有天鵝絨般絨毛 = 芋頭"
        },
        {
          "feature": "water_drop_test",
          "species_a_value": "spreads_flat",
          "species_b_value": "beads_up",
          "test": "在葉面滴水，水珠攤平 = 姑婆芋，水珠成珠滾動 = 芋頭"
        }
      ]
    }
  ]
}
```

#### 查找邏輯

```python
def check_confusion_pairs(top3_results, confusion_db):
    top3_ids = {r.species_id for r in top3_results}
    matched_pairs = []

    for pair in confusion_db:
        if pair.species_a in top3_ids and pair.species_b in top3_ids:
            matched_pairs.append(pair)
        elif pair.species_a in top3_ids or pair.species_b in top3_ids:
            # 即使只有一方在 Top 3 中，如果另一方信心度差距很小，也觸發提醒
            matched_pairs.append(pair)

    return matched_pairs
```

- 如果 Top 3 中有已知的混淆物種對 → 附加比較表 + 互動測試指引
- 顯示混淆物種的關鍵區分特徵，引導使用者做實地測試
- 即使混淆物種的另一方不在 Top 3 中，只要一方在，也主動提醒「注意此物種容易與 XXX 混淆」

### 8.4 Top 3 結果展示

對每個候選物種，從 KB 取出診斷性特徵展示給使用者自行比對：

```
🥇 #1 姑婆芋（信心度 78%）
   ⚠️ 有毒！

   【知識庫描述 — 請對照實物確認】
   ✦ 葉面：光滑發亮，像打了蠟
   ✦ 水珠測試：水珠會攤平（不成珠狀）
   ✦ 葉尖：朝上或水平指向
   ✦ 特殊特徵：汁液含草酸鈣針晶，觸碰皮膚會灼傷

🥈 #2 芋頭（信心度 65%）
   🍃 可食用（須煮熟）

   【知識庫描述 — 請對照實物確認】
   ✦ 葉面：有天鵝絨般微絨毛，不光滑
   ✦ 水珠測試：水珠呈圓珠狀滾動
   ✦ 葉尖：通常朝下垂
   ✦ 特殊特徵：地下有圓形塊莖

   ⚠️ #1 與 #2 是已知混淆物種對！請做水珠測試進一步區分。
```

---

## 九、知識庫重構設計

### 9.1 新的結構化格式

從自由文字描述改為結構化 enum + 預計算權重：

```json
{
  "id": "alocasia_odora",
  "scientific_name": "Alocasia odora",
  "common_names": { "zh-TW": "姑婆芋", "en": "Giant Elephant Ear" },
  "category": "dangerous",
  "danger_level": "high",

  "features": {
    "growth_form":    { "value": "herb", "weight": 1 },
    "height_estimate": { "value": "1-2m", "weight": 1 },

    "leaf": {
      "shape":          { "value": "heart",              "weight": 1 },
      "edge":           { "value": "entire",             "weight": 1 },
      "colors":         { "value": ["dark_green"],       "weight": 1 },
      "surface_top":    { "value": "glossy",             "weight": 3 },
      "size":           { "value": "very_large_>50cm",   "weight": 2 },
      "arrangement":    { "value": "clustered",          "weight": 1 },
      "venation":       { "value": "pinnate",            "weight": 1 },
      "tip_direction":  { "value": "upward",             "weight": 3 }
    },
    "stem": {
      "type":   { "value": "thick_succulent", "weight": 2 },
      "colors": { "value": ["green"],         "weight": 1 },
      "latex":  { "value": "yes_white",       "weight": 3 }
    },
    "flower": {
      "arrangement": { "value": "spathe_spadix",   "weight": 4 },
      "colors":      { "value": ["yellow_green"],  "weight": 2 }
    },
    "fruit": {
      "type":   { "value": "berry_cluster", "weight": 2 },
      "colors": { "value": ["red"],         "weight": 2 }
    },
    "overall": {
      "water_droplet_test": { "value": "flat",                       "weight": 5 },
      "habitat":            { "value": "forest_understory_moist",    "weight": 2 }
    }
  },

  "total_weight": 32,

  "human_readable": {
    "toxicity": "全株有毒，汁液含草酸鈣針晶，誤食致口腔灼傷、腹瀉、喉嚨腫脹",
    "symptoms": ["口腔灼傷", "舌頭麻痺", "腹瀉", "喉嚨腫脹", "嘔吐"],
    "first_aid": "立即用大量清水漱口，勿催吐，儘速就醫。",
    "description_zh": "姑婆芋的詳細文字描述（用於最終顯示給使用者看）",
    "diagnostic_features": [
      "葉面光滑發亮，像打了蠟",
      "水珠在葉面攤平不成珠狀",
      "葉尖朝上或水平指向",
      "葉柄接在葉片邊緣（非盾狀著生）"
    ]
  }
}
```

### 9.2 Enum 的來源：從 KB 自動衍生

**Enum 選項不是人為設計的，而是從知識庫反推的。**

```
Step 1: 建構知識庫 → 為每個物種填入結構化特徵值
Step 2: 掃描 KB 所有物種的所有特徵值 → 收集所有出現過的值
Step 3: 加上 not_visible、uncertain、other 作為安全網 → 形成完整 enum
Step 4: 自動計算每個值的出現頻率 → 算出稀有度權重
Step 5: 自動生成 LLM prompt 的 enum 選項列表
```

這保證了：

- KB 裡有的值，LLM 一定選得到
- 不會出現「LLM 想選的值不在 enum 裡」的情況
- 新增物種 → 自動擴展 enum → 自動更新 prompt

### 9.3 知識庫建構流程

1. **以現有 KB 為基礎**：現有 40 種植物的自由文字描述已經很詳細
2. **用雲端大模型格式轉換**：用 Gemini/GPT-4 批次將自由文字轉為結構化 JSON（離線一次性工作）
3. **人工校驗**：有毒植物的關鍵特徵絕不能寫錯
4. **補充新增物種**：查閱台灣植物誌等專業資料
5. **自動計算衍生資料**：腳本收集 enum + 計算權重 + 計算 total_weight

---

## 十、完整特徵分類表（Feature Taxonomy）

以下列出所有植物部位的所有屬性及候選值方向。
**最終版的候選值必須從知識庫反推（見 9.2），這裡是初步框架。**

### 10.1 整株 (overall)


| 屬性                 | 候選值                                                                                                                    | 類型  |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------- | --- |
| growth_form        | herb, shrub, tree, vine, fern, fungus, grass, succulent, aquatic, moss, palm_like                                      | 單值  |
| height_estimate    | <30cm, 30-100cm, 1-2m, 2-5m, >5m, not_visible                                                                          | 單值  |
| latex              | none, yes_white, yes_yellow, yes_red, yes_clear, not_visible                                                           | 單值  |
| smell              | none, aromatic, pungent, fishy, minty, spicy, rotten, sweet, not_checkable                                             | 單值  |
| habitat            | roadside, forest_floor, streamside, cliff_rock, open_field, wetland, epiphytic, parasitic, urban, coastal, not_visible | 單值  |
| water_droplet_test | beading, flat, not_checkable                                                                                           | 單值  |


### 10.2 葉 (leaf)


| 屬性                 | 候選值                                                                                                                                  | 類型       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| visible            | true, false                                                                                                                          | 布林       |
| leaf_type          | simple, trifoliate, pinnate_compound, bipinnate_compound, palmate_compound, not_visible                                              | 單值       |
| shape              | heart, arrow, oval, elliptic, lanceolate, linear, needle, scale, round, spatulate, obovate, rhombic, fan, kidney, not_visible, other | 單值       |
| edge               | entire, serrated, double_serrated, crenate, lobed, deeply_lobed, wavy, spiny, not_visible                                            | 單值       |
| tip                | acute, acuminate, rounded, emarginate, truncate, not_visible                                                                         | 單值       |
| base               | cordate, cuneate, rounded, truncate, sagittate, peltate, not_visible                                                                 | 單值       |
| colors             | light_green, green, dark_green, yellow_green, red, purple, variegated, silver, brown, red_underside                                  | **多值陣列** |
| color_pattern      | solid, gradient, spotted, striped, bicolor, not_visible                                                                              | 單值       |
| surface_top        | glossy, matte, hairy, rough, waxy, velvety, pubescent, scaly, sandpaper, not_visible                                                 | 單值       |
| surface_bottom     | (同 surface_top)                                                                                                                      | 單值       |
| arrangement        | alternate, opposite, whorled, rosette, basal_rosette, clustered, spiral, two_ranked, bird_nest_radial, not_visible                   | 單值       |
| size               | tiny_<2cm, small_2-5cm, medium_5-15cm, large_15-50cm, very_large_>50cm, not_visible                                                  | 單值       |
| venation           | parallel, pinnate, palmate, reticulate, single_midrib, not_visible                                                                   | 單值       |
| texture            | papery, leathery, fleshy, membranous, succulent, not_visible                                                                         | 單值       |
| petiole_attach     | normal, peltate_shield, sheathing, sessile, not_visible                                                                              | 單值       |
| other_observations | 自由文字                                                                                                                                 | 文字       |


### 10.3 莖 (stem)


| 屬性                 | 候選值                                                                              | 類型       |
| ------------------ | -------------------------------------------------------------------------------- | -------- |
| visible            | true, false                                                                      | 布林       |
| type               | erect, creeping, climbing, twining, prostrate, rhizome, pseudostem, not_visible  | 單值       |
| cross_section      | round, square, triangular, flattened, ridged, not_visible                        | 單值       |
| surface            | smooth, hairy, thorny, ridged, waxy, scaly, bark_rough, bark_smooth, not_visible | 單值       |
| colors             | green, brown, purple, red, gray, white_powdery                                   | **多值陣列** |
| interior           | solid, hollow, pithy, not_visible                                                | 單值       |
| has_thorns         | yes, no, not_visible                                                             | 單值       |
| other_observations | 自由文字                                                                             | 文字       |


### 10.4 花 (flower)


| 屬性                 | 候選值                                                                                               | 類型       |
| ------------------ | ------------------------------------------------------------------------------------------------- | -------- |
| visible            | true, false                                                                                       | 布林       |
| colors             | white, yellow, orange, red, pink, purple, blue, green, brown                                      | **多值陣列** |
| color_pattern      | solid, gradient, spotted, striped, center_different, bicolor, not_visible                         | 單值       |
| petal_count        | 0, 3, 4, 5, 6, many, fused_tubular, not_visible                                                   | 單值       |
| symmetry           | radial, bilateral, irregular, not_visible                                                         | 單值       |
| size               | tiny_<5mm, small_5-15mm, medium_15-30mm, large_30-60mm, very_large_>60mm, not_visible             | 單值       |
| arrangement        | solitary, raceme, spike, umbel, head_composite, panicle, cyme, catkin, spathe_spadix, not_visible | 單值       |
| position           | terminal, axillary, basal, cauliflorous, not_visible                                              | 單值       |
| orientation        | upright, horizontal, drooping, not_visible                                                        | 單值       |
| special_shape      | none, lip_labellum, spur, spathe, butterfly_shape, bell_tubular, trumpet, not_visible             | 單值       |
| fragrant           | yes, no, not_checkable                                                                            | 單值       |
| other_observations | 自由文字                                                                                              | 文字       |


### 10.5 果實 (fruit)


| 屬性                 | 候選值                                                                                              | 類型       |
| ------------------ | ------------------------------------------------------------------------------------------------ | -------- |
| visible            | true, false                                                                                      | 布林       |
| type               | berry, drupe, capsule, pod_legume, achene, samara, nut, aggregate, fig, cone, spore, not_visible | 單值       |
| colors             | green, yellow, orange, red, purple, black, brown, white_waxy                                     | **多值陣列** |
| size               | tiny_<5mm, small_5-15mm, medium_15-30mm, large_>30mm, not_visible                                | 單值       |
| surface            | smooth, hairy, spiny, warty, waxy, hooked_bristles, not_visible                                  | 單值       |
| other_observations | 自由文字                                                                                             | 文字       |


### 10.6 根/地下部 (root)

> 多數照片看不到，主要靠使用者手動填入。


| 屬性                 | 候選值                                                                                      | 類型  |
| ------------------ | ---------------------------------------------------------------------------------------- | --- |
| visible            | true, false                                                                              | 布林  |
| type               | fibrous, taproot, tuberous, rhizome, bulb, corm, aerial_root, storage_tuber, not_visible | 單值  |
| other_observations | 自由文字                                                                                     | 文字  |


---

## 十一、50 種台灣植物清單

### 11.1 有毒/危險植物（22 種）


| #   | 中文名    | 學名                           | 來源     | 常見混淆對象    |
| --- | ------ | ---------------------------- | ------ | --------- |
| 1   | 姑婆芋    | *Alocasia odora*             | 現有     | 芋頭、海芋     |
| 2   | 海檬果    | *Cerbera manghas*            | 現有     | —         |
| 3   | 曼陀羅    | *Datura stramonium*          | 現有     | 大花曼陀羅     |
| 4   | 咬人貓    | *Urtica thunbergiana*        | 現有     | —         |
| 5   | 咬人狗    | *Dendrocnide meyeniana*      | 現有     | —         |
| 6   | 綠褶菇    | *Chlorophyllum molybdites*   | 現有     | 高大環柄菇     |
| 7   | 鱗柄白毒鵝膏 | *Amanita phalloides* 近似種     | 現有     | 雞肉絲菇      |
| 8   | 漆樹     | *Toxicodendron vernicifluum* | 現有     | —         |
| 9   | 夾竹桃    | *Nerium oleander*            | 現有     | —         |
| 10  | 蘇鐵     | *Cycas revoluta*             | 現有     | —         |
| 11  | 馬纓丹    | *Lantana camara*             | 現有     | 小葉桑（果實）   |
| 12  | 銀膠菊    | *Parthenium hysterophorus*   | 現有     | 大花咸豐草、鼠麴草 |
| 13  | 大花曼陀羅  | *Brugmansia suaveolens*      | 現有     | 曼陀羅       |
| 14  | 美洲商陸   | *Phytolacca americana*       | 現有     | 野莧菜       |
| 15  | 海芋     | *Zantedeschia aethiopica*    | 現有     | 芋頭、姑婆芋    |
| 16  | 雞母珠    | *Abrus precatorius*          | 現有     | —         |
| 17  | 蓖麻     | *Ricinus communis*           | 現有     | —         |
| 18  | 烏桕     | *Triadica sebifera*          | 現有     | —         |
| 19  | 黃金葛    | *Epipremnum aureum*          | 現有     | —         |
| 20  | 毛地黃    | *Digitalis purpurea*         | 現有     | 車前草（蓮座期）  |
| 21  | **苦楝** | *Melia azedarach*            | **新增** | 食茱萸（羽狀複葉） |
| 22  | **蕨**  | *Pteridium aquilinum*        | **新增** | 過貓（嫩芽捲曲）  |


> #22 取代原本混淆物種對裡的「有毒蕨類（泛指）」。蕨是台灣最常見蕨類之一，生食含致癌物 ptaquiloside，常被誤認為過貓。

### 11.2 可食用/藥用植物（28 種）


| #   | 中文名          | 學名                            | 來源     | 常見混淆對象   |
| --- | ------------ | ----------------------------- | ------ | -------- |
| 23  | 山蘇           | *Asplenium nidus*             | 現有     | 其他蕨類     |
| 24  | 過貓           | *Diplazium esculentum*        | 現有     | 蕨（#22）   |
| 25  | 野薑花          | *Hedychium coronarium*        | 現有     | 有毒薑科植物   |
| 26  | 車前草          | *Plantago major*              | 現有     | 毛地黃（蓮座期） |
| 27  | 龍葵           | *Solanum nigrum*              | 現有     | —        |
| 28  | 昭和草          | *Crassocephalum crepidioides* | 現有     | —        |
| 29  | 芋頭           | *Colocasia esculenta*         | 現有     | 姑婆芋、海芋   |
| 30  | 木耳           | *Auricularia auricula-judae*  | 現有     | —        |
| 31  | 腎蕨           | *Nephrolepis cordifolia*      | 現有     | —        |
| 32  | 山芹菜          | *Oenanthe javanica*           | 現有     | 毒水芹      |
| 33  | 大花咸豐草        | *Bidens pilosa var. radiata*  | 現有     | 銀膠菊      |
| 34  | 月桃           | *Alpinia zerumbet*            | 現有     | —        |
| 35  | 構樹           | *Broussonetia papyrifera*     | 現有     | —        |
| 36  | 小葉桑          | *Morus australis*             | 現有     | 馬纓丹（果實）  |
| 37  | 野莧菜          | *Amaranthus viridis*          | 現有     | 美洲商陸     |
| 38  | 魚腥草          | *Houttuynia cordata*          | 現有     | —        |
| 39  | 五節芒          | *Miscanthus floridulus*       | 現有     | —        |
| 40  | 食茱萸          | *Zanthoxylum ailanthoides*    | 現有     | 苦楝（#21）  |
| 41  | 山黃麻          | *Trema orientalis*            | 現有     | —        |
| 42  | 鵝仔草          | *Pterocypsela indica*         | 現有     | —        |
| 43  | 高大環柄菇        | *Macrolepiota procera*        | 混淆對    | 綠褶菇      |
| 44  | 雞肉絲菇         | *Termitomyces* sp.            | 混淆對    | 白色毒鵝膏    |
| 45  | **野牡丹**      | *Melastoma candidum*          | **新增** | —        |
| 46  | **紫背草（一點紅）** | *Emilia sonchifolia*          | **新增** | —        |
| 47  | **鼠麴草**      | *Pseudognaphalium affine*     | **新增** | 銀膠菊      |
| 48  | **雷公根**      | *Centella asiatica*           | **新增** | —        |
| 49  | **山苦瓜**      | *Momordica charantia* var.    | **新增** | —        |
| 50  | **筆筒樹**      | *Cyathea lepifera*            | **新增** | —        |


### 11.3 新增物種選擇理由


| 新增物種      | 理由                                |
| --------- | --------------------------------- |
| 苦楝 (#21)  | 台灣極常見行道樹，果實像漿果但有毒。羽狀複葉易與食茱萸混淆     |
| 蕨 (#22)   | 取代泛稱「有毒蕨類」。台灣山區最常見蕨類，生食致癌。和過貓嫩芽相似 |
| 野牡丹 (#45) | 低海拔步道邊極常見，紫色漿果可食，好辨認的野果           |
| 紫背草 (#46) | 路邊空地極常見的菊科野菜，嫩葉可食                 |
| 鼠麴草 (#47) | 做草仔粿的傳統野草，白色花序可能和銀膠菊混淆            |
| 雷公根 (#48) | 台灣潮濕地面極常見，藥食兩用，辨識特徵明確             |
| 山苦瓜 (#49) | 野外常見攀緣植物，果實可食，求生場景有實用價值           |
| 筆筒樹 (#50) | 台灣代表性蕨類，嫩心可食，體型巨大辨識明確             |


---

## 十二、混淆物種對（更新版，移除動物）


| ID                              | 安全種     | 危險種    | 致命性 | 關鍵區分           | 狀態     |
| ------------------------------- | ------- | ------ | --- | -------------- | ------ |
| taro_vs_alocasia                | 芋頭      | 姑婆芋    | 高   | 水珠測試、葉面質感、葉尖方向 | 保留     |
| parasol_vs_green_spored         | 高大環柄菇   | 綠褶菇    | 中   | 菌褶成熟後變綠、孢子印顏色  | 保留     |
| birds_nest_fern_vs_bracken      | 山蘇      | **蕨**  | 低   | 單葉vs複葉、鳥巢狀排列   | **更新** |
| wild_ginger_vs_toxic_ginger     | 野薑花     | 有毒薑科   | 中   | 花色、根莖薑味        | 保留     |
| termite_mushroom_vs_white_toxic | 雞肉絲菇    | 白色毒鵝膏  | 極高  | 菌柄基部、生長在白蟻巢上   | 保留     |
| bidens_vs_parthenium            | 大花咸豐草   | 銀膠菊    | 低   | 花朵大小、莖形、氣味     | 保留     |
| pokeweed_vs_amaranth            | 野莧菜     | 美洲商陸   | 高   | 莖粗細與顏色、果實      | 保留     |
| calla_vs_taro                   | 芋頭      | 海芋     | 中   | 白色佛焰苞、葉形       | 保留     |
| lantana_vs_mulberry             | 小葉桑     | 馬纓丹    | 中   | 果實形狀、葉排列、氣味    | 保留     |
| foxglove_vs_plantain            | 車前草     | 毛地黃    | 極高  | 葉面質感、葉脈、葉緣     | 保留     |
| vegetable_fern_vs_bracken       | 過貓      | **蕨**  | 低   | 嫩芽形態、生長環境      | **新增** |
| prickly_ash_vs_chinaberry       | 食茱萸     | **苦楝** | 中   | 搓葉氣味（花椒味vs無）   | **新增** |
| cudweed_vs_parthenium           | **鼠麴草** | 銀膠菊    | 低   | 葉形、花序大小        | **新增** |


已移除的動物混淆對：`green_snake_vs_bamboo_viper`、`red_banded_vs_krait`

---

## 十三、UI 設計要點

### 13.1 逐張拍攝 + 即時回饋

```
┌────────────────────────────────────────────┐
│ 📷 拍攝第 1 張照片                           │
│ [拍照] [從相簿選取]                          │
└────────────────────────────────────────────┘
          │ 拍攝完成
          ▼
┌────────────────────────────────────────────┐
│ ✅ 特徵萃取完成！                             │
│                                            │
│ 已辨識的特徵：                               │
│   葉形: heart ✅                             │
│   葉色: [dark_green] ✅                      │
│   葉面: glossy ✅                            │
│   花:   not_visible ❌ ← 建議補拍             │
│   果實: not_visible ❌ ← 建議補拍             │
│   莖:   not_visible ❌                       │
│                                            │
│ [📷 繼續拍攝] [🔍 開始辨識] [✏️ 手動補充]     │
└────────────────────────────────────────────┘
```

### 13.2 使用者手動補充/修正（可編輯 Tag/Chip 介面）

每個特徵欄位都呈現為 tag/chip 列表，使用者擁有完整控制權（增、刪、改），
不再區分「覆蓋」vs「追加」，所見即所得。

```
┌────────────────────────────────────────────┐
│ ✏️ 特徵編輯                                 │
│                                            │
│ 🔎 照片可觀察的特徵（AI 萃取 + 使用者可編輯）  │
│                                            │
│ 葉形:    [heart 🤖 ×]  [+ 新增 ▼]          │
│ 葉色:    [dark_green 🤖 ×]  [+ 新增 ▼]     │
│ 葉面:    [glossy 🤖 ×]  [+ 新增 ▼]         │
│ 花色:    [yellow 🤖 ×] [red 🤖 ×]  [+ ▼]  │
│                                            │
│ 🤚 需要現場確認的特徵（AI 無法判斷）           │
│                                            │
│ 氣味:     [未填]  [+ 新增 ▼]               │
│ 水珠測試: [未填]  [+ 新增 ▼]               │
│ 汁液顏色: [未填]  [+ 新增 ▼]               │
│                                            │
│ 💡 補充氣味、水珠測試等資訊可大幅提升信心度    │
│                                            │
│ 📝 其他觀察: [_______________] 自由文字       │
│                                            │
│ [確認並開始辨識]                              │
└────────────────────────────────────────────┘
```

- 🤖 表示 AI 萃取的值，👤 表示使用者手動輸入的值
- 點 × 可刪除任何 tag，點 [+ 新增] 從 enum 清單中挑選值加入
- 被使用者修改過的欄位用不同底色標記，可一鍵恢復 AI 原始值
- 非照片可觀察的欄位預設為「未填」，鼓勵使用者現場補充

---

## 十四、與 v1 架構的關鍵差異


| 面向        | v1（現有）                             | v2（新架構）               |
| --------- | ---------------------------------- | --------------------- |
| LLM 呼叫次數  | 2-3 次（danger + edible + confusion） | **1 次/張照片**（只做特徵萃取）   |
| Prompt 長度 | 極長（塞入整個知識庫）                        | **極短**（只有選擇題模板）       |
| LLM 任務    | 辨識 + 比對 + 排名 + 解釋                  | **只看圖填表**             |
| 比對邏輯      | LLM 自己判斷                           | **確定性演算法**（加分 × 權重）   |
| 知識庫格式     | 自由文字 morphology                    | **結構化 enum + 預算權重**   |
| 可重現性      | 低（每次結果可能不同）                        | **高**（同特徵 → 同結果）      |
| 手機可行性     | 困難（太慢太耗算力）                         | **可行**（LLM 只生成短 JSON） |
| 物種範圍      | 植物 + 動物                            | **只有植物**（算力集中）        |
| 照片輸入      | 一次批量多張                             | **逐張迭代 + 即時回饋**       |
| 使用者輸入     | 自由文字描述                             | **結構化 dropdown 表單**   |


---

## 十五、關鍵設計決策摘要


| #   | 決策項目                       | 結論                                                         | 理由                           |
| --- | -------------------------- | ---------------------------------------------------------- | ---------------------------- |
| 1   | 照片輸入方式                     | 逐張迭代，即時顯示，使用者決定何時辨識                                        | 手機算力友善 + 即時回饋 UX             |
| 2   | 不符合特徵                      | 不扣分，只不加分 (0)                                               | 避免照片品質差導致正確物種被誤扣             |
| 3   | 顏色等多值屬性                    | 陣列型（允許多值）                                                  | 花可以是黃紅白紫漸層                   |
| 4   | **陣列型計分**                  | **weight × (                                               | 交集                           |
| 5   | Enum 來源                    | 從 KB 自動衍生                                                  | 保證 KB 有的值 LLM 一定選得到          |
| 6   | 權重來源                       | 從 KB 自動計算（稀有度公式）                                           | max(1, round(log2(N/count))) |
| 7   | 自由文字處理                     | 不餵 LLM，不比對，原樣保存展示                                          | 避免 LLM 誤解覆蓋正確值               |
| 8   | **使用者輸入 UI**               | **可編輯 tag/chip 列表（增刪改自由）**                                 | **所見即所得，消除覆蓋/追加歧義**          |
| 9   | 使用者輸入優先級                   | 最高，使用者的修改即最終值                                              | 人類對觸感/氣味判斷更可靠                |
| 10  | other_observations         | 展示 KB 診斷性特徵讓使用者自行比對                                        | 引導使用者進一步確認                   |
| 11  | 多照片合併                      | 全部聯集（含單值屬性衝突時也保留為陣列）                                       | 安全，不丟失任何資訊                   |
| 12  | 物種範圍                       | 只有植物，去掉動物                                                  | 算力集中，提升植物辨識準確度               |
| 13  | `colors` 與 `color_pattern` | colors 只放純顏色值，color_pattern 描述組合方式                         | 職責分離，不冗餘                     |
| 14  | **信心度計算**                  | **score / species_effective_total（含 photo_observable 區分）** | **不高估少量證據，鼓勵多觀察，偏保守更安全**     |
| 15  | **警告等級**                   | **嚴格優先順序：RED → ORANGE → YELLOW → GREEN → GREY**            | **安全第一，危險訊號永遠優先**            |
| 16  | 信心度不足                      | < 40% → 未登錄物種                                              | 利用已萃取特徵生成描述句                 |
| 17  | **混淆物種**                   | **混淆物種是一般 KB 條目 + confusion_pairs 關係表**                    | **不重複儲存特徵，只記錄「哪些物種容易混淆」**    |
| 18  | **生存指南**                   | **區域感知，從地區 KB 動態查詢在地植物**                                   | **因地制宜，使用者知道去找什麼植物**         |


---

## 十六、實作優先順序

```
=== Step 1：知識庫重構 ===
  □ 將現有 40 種植物從自由文字轉為結構化 JSON 格式
  □ 新增 10 種植物的結構化資料
  □ 更新混淆物種對（移除動物，新增 3 對植物）
  □ 寫腳本自動收集 enum + 計算權重 + 生成 prompt 模板

=== Step 2：Phase 1 — LLM 特徵萃取 ===
  □ 設計「選擇題式」prompt 模板（enum 選項從 KB 自動生成）
  □ 實作 JSON schema 驗證 + 容錯處理
  □ 測試 Gemma 4 是否能穩定輸出合規 JSON

=== Step 3：Phase 3 — 比對演算法 ===
  □ 實作正規化計分邏輯（單值 + 陣列型）
  □ 實作 Early Stopping 剪枝
  □ 實作信心度計算
  □ 單元測試（已知物種照片 → 期望排名）

=== Step 4：Phase 2 — 特徵合併 ===
  □ 實作多照片聯集邏輯
  □ 實作使用者手動輸入覆蓋邏輯

=== Step 5：Phase 4 — 後處理 ===
  □ 警告等級判定（嚴格優先順序邏輯）
  □ 混淆物種對查找 + 展示
  □ Top 3 診斷性特徵展示
  □ 復用現有 confusion_pairs 互動測試指引

=== Step 6：UI 整合 ===
  □ Gradio 介面重構（去掉動物選項、海拔等）
  □ 逐張拍攝 + 即時特徵顯示
  □ 可編輯 tag/chip 使用者輸入介面
  □ 信心度 + 觀察完整度顯示

=== Step 7：區域感知生存指南 ===
  □ KB 物種新增 usage 欄位（edible/medicinal 物種）
  □ 生存指南章節定義查詢標籤
  □ 動態查詢邏輯：指南章節 → KB 查詢 → 在地植物卡片
  □ 「查看辨識特徵」深度連結到物種詳情

=== Step 8：Kaggle 提交準備 ===
  □ 整合為 Kaggle Notebook
  □ 錄製 Demo 影片（3 分鐘）
  □ 撰寫 Write-up
```

---

## 十八、區域感知生存指南

### 18.1 核心概念

生存指南不應是靜態的通用手冊，而應該**根據使用者所在地區的知識庫，動態填入在地化的植物資訊**。

例如：使用者在台灣，開啟「傷口急救」指南頁面時，不只看到通用的止血步驟，還會看到：

- 「在你的地區，可用 **車前草** 搗碎敷傷口消炎」（從台灣 KB 中 category=medicinal 的物種提取）
- 「在你的地區，**魚腥草** 有抗菌消炎功效」

### 18.2 資料來源

從區域 KB 中，根據物種的 `category` 和 `usage` 欄位動態查詢：

```json
// KB 中每個物種已有的欄位：
{
  "species_id": "plantago_major",
  "common_name": "車前草",
  "category": "medicinal",
  "usage": {
    "type": ["wound_care", "anti_inflammatory"],
    "description": "搗碎鮮葉敷於傷口可消炎止血",
    "preparation": "摘取新鮮葉片，洗淨後搗碎成泥狀敷用",
    "warnings": "僅限外用，確認辨識正確後再使用"
  }
}
```

### 18.3 生存指南與 KB 的關聯

```
┌──────────────────────┐     ┌──────────────────────┐
│  survival_guide/     │     │  regions/             │
│  medical.json        │     │  east_asia_subtropical│
│                      │     │  /plants.json         │
│  "wound_care": {     │     │                       │
│    "steps": [...],   │────▶│  query: category in   │
│    "plant_remedies": │     │  [medicinal] AND      │
│    "→ 動態查詢 KB"   │     │  usage.type includes  │
│  }                   │     │  "wound_care"         │
└──────────────────────┘     └──────────────────────┘
```

每個生存指南章節定義**需要哪些類型的植物資訊**（query tag），系統在載入時從地區 KB 動態查詢匹配的物種。

### 18.4 指南章節與查詢標籤對應


| 生存指南章節 | 查詢標籤 (usage.type)                            | 說明             |
| ------ | -------------------------------------------- | -------------- |
| 傷口急救   | `wound_care`, `anti_inflammatory`            | 可用於消炎止血的藥草     |
| 食物來源   | `edible_leaf`, `edible_fruit`, `edible_root` | 該地區可食用的野生植物    |
| 飲水淨化   | `water_purification`                         | 可用於淨化水質的植物（如有） |
| 驅蟲防蛇   | `insect_repellent`, `snake_repellent`        | 具有驅蟲效果的植物      |
| 繩索材料   | `fiber_material`                             | 纖維可做繩索的植物      |
| 生火引燃   | `tinder_material`                            | 乾燥後易燃的植物材料     |


### 18.5 UI 呈現

```
┌────────────────────────────────────────────┐
│ 📖 生存指南 — 傷口急救                        │
│                                            │
│ 📍 地區：台灣亞熱帶                          │
│                                            │
│ ── 通用步驟 ──                              │
│ 1. 用清水沖洗傷口                           │
│ 2. 移除異物                                │
│ 3. 施壓止血                                │
│ ...                                        │
│                                            │
│ ── 🌿 在地藥用植物 ──                        │
│                                            │
│ ┌─────────────────────────────────────┐    │
│ │ 🌱 車前草 (Plantago major)           │    │
│ │ 功效：消炎止血                        │    │
│ │ 用法：摘新鮮葉片洗淨搗碎敷於傷口       │    │
│ │ ⚠️ 僅限外用，確認辨識正確後再使用      │    │
│ │ [📷 查看辨識特徵]                     │    │
│ └─────────────────────────────────────┘    │
│                                            │
│ ┌─────────────────────────────────────┐    │
│ │ 🌱 魚腥草 (Houttuynia cordata)       │    │
│ │ 功效：抗菌消炎                        │    │
│ │ 用法：鮮葉搗汁外敷或水煎內服          │    │
│ │ ⚠️ 味道強烈但無毒                     │    │
│ │ [📷 查看辨識特徵]                     │    │
│ └─────────────────────────────────────┘    │
│                                            │
│ ── 🍽️ 在地可食植物 ──                       │
│ （點擊展開 → 連結到食物來源頁面）             │
│                                            │
└────────────────────────────────────────────┘
```

### 18.6 「查看辨識特徵」的深度連結

每個植物卡片上的 **[📷 查看辨識特徵]** 按鈕，連結到該物種在 KB 中的完整特徵頁面，
讓使用者在實際尋找藥草時，可以準確辨識目標植物：

```
使用者流程：
1. 閱讀生存指南 → 知道「車前草可以止血」
2. 點擊 [📷 查看辨識特徵] → 看到車前草的葉形、葉脈、花穗等特徵
3. 帶著這些特徵去野外尋找 → 找到疑似植物
4. 拍照上傳 → 用辨識功能確認是否真的是車前草
5. 信心度 ≥ 60% → 安心使用
```

### 18.7 離線支援

- 生存指南的靜態內容（通用步驟）在 App 安裝時即內建
- 區域 KB 在使用者選擇/偵測到地區後一次性載入（~0.3 MB）
- 動態查詢在本地端完成，**無需網路連線**
- 使用者可預先下載多個地區的 KB 以備不同旅行目的地

### 18.8 KB usage 欄位擴充

為支援此功能，KB 物種條目需新增 `usage` 欄位：

```json
{
  "species_id": "houttuynia_cordata",
  "common_name": "魚腥草",
  "category": "medicinal",
  "features": { ... },
  "usage": {
    "type": ["wound_care", "anti_inflammatory", "edible_leaf"],
    "edible_parts": ["leaf"],
    "medicinal_effects": ["抗菌", "消炎", "利尿"],
    "preparation": "鮮葉搗汁外敷或水煎內服",
    "season": "全年可採",
    "warnings": "味道強烈但安全無毒"
  }
}
```

**只有 `category` 為 `edible` 或 `medicinal` 的物種**需要填寫 `usage` 欄位，
`dangerous` 類別的物種不會被查詢到生存指南中。

---

## 十九、風險與待決事項


| 風險                     | 影響              | 緩解策略                           |
| ---------------------- | --------------- | ------------------------------ |
| Gemma 4 小模型 JSON 輸出不穩定 | 特徵萃取失敗率高        | 嚴格 schema 驗證 + 重試機制 + fallback |
| Enum 覆蓋度不足             | LLM 選了「最像但不對」的值 | Enum 從 KB 反推，加 `other` 安全網     |
| 知識庫轉換品質                | 有毒植物特徵填錯 → 安全風險 | 人工校驗所有有毒植物                     |
| 50 種物種不夠涵蓋             | 使用者遇到的植物不在 KB 裡 | < 60% 信心度 → 標記未登錄 + 安全提示       |
| 比賽截止日緊迫 (5/18)         | 來不及完成所有功能       | 按優先順序實作，Step 1-3 是最低可用版本       |
| 生存指南 usage 資料不完整       | 部分物種無法連結到指南     | 優先填寫高實用價值物種（車前草、魚腥草等）          |


