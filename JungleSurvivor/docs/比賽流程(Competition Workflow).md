# JungleSurvivor — 比賽前完整流程

> **最後更新**：2026-05-01  
> **比賽截止**：2026-05-18  
> **剩餘時間**：約 17 天

---

## 整體進度一覽

```
✅ 已完成（底層已就緒）
├── 四層辨識 Pipeline（危險快篩→混淆鑑別→可利用資源→通用描述）
├── 知識庫大幅擴充（有毒20+可食20+動物13+混淆12+急救5）
├── Gradio UI（歷史紀錄、色彩警告、互動測試引導）
├── CUDA OOM 修復（模型不重複載入）
├── Kaggle Notebook 自含式封裝（325KB，所有資料嵌入）
└── 改善規劃文件

⬜ 接下來要做的
├── [Phase A] Kaggle 環境驗證（1-2 天）
├── [Phase B] 安全兜底機制 — Layer 1.5（2-3 天）
├── [Phase C] 文字描述輸入（1-2 天）
├── [Phase D] 端對端測試 + 修 Bug（2-3 天）
├── [Phase E] Write-up 撰寫（2-3 天）
└── [Phase F] 最終提交（1 天）
```

---

## Phase A — Kaggle 環境驗證（5/1 → 5/3）

### 目標

確認 Notebook 能在 Kaggle 環境完整跑起來。

### 步驟


| #   | 動作                                               | 預期結果              |
| --- | ------------------------------------------------ | ----------------- |
| A-1 | 上傳 `kaggle_gradio_demo.ipynb` 到 Kaggle           | 成功上傳              |
| A-2 | 設定環境：GPU T4 x2、Internet On、加入 Gemma model access | 環境正確              |
| A-3 | 執行 Cell 1-4（安裝+知識庫載入）                            | ✅ 知識庫 20/20/13/12 |
| A-4 | 執行 Cell 5-10（核心模組）                               | 無 import error    |
| A-5 | 執行 Cell 12（載入模型）                                 | ✅ 模型載入完成，不 OOM    |
| A-6 | 執行 Cell 14（Gradio UI）                            | 產生 public URL     |
| A-7 | 打開 URL，上傳測試照片，執行辨識                               | 能產出結果             |
| A-8 | 點擊「載入模型」按鈕                                       | 顯示「已載入」而非重複載入     |


### 測試照片建議

- 姑婆芋（應觸發 🔴 + 混淆鑑別）
- 大花咸豐草（應觸發 🟢 可食）
- 赤尾青竹絲（動物模式 → 🔴）
- 一張普通花朵（應 ⚪ 不確定）

### 如果失敗

- OOM → 檢查是否有其他 Cell 也載入了模型
- Import Error → 檢查模組順序
- Gradio URL 不通 → 確認 `share=True`

---

## Phase B — 安全兜底機制 Layer 1.5（5/3 → 5/6）

### 目標

在 Layer 1（知識庫比對）和 Layer 3（可利用資源）之間，加入「模型原生知識交叉驗證」，防止知識庫盲區。

### 實作內容

1. **修改 `pipeline.py`**：在 Layer 1 未命中後、Layer 3 前，新增：
  ```python
   def _run_native_safety_check(self, images, context):
       prompt = """Look at this carefully. Using ALL your botanical/zoological knowledge 
       (not limited to any list), is there ANY possibility this could be toxic or dangerous?
       If unsure, say potentially dangerous. Output JSON..."""
       response = self.model.generate(prompt, images)
       return parse_native_safety(response)
  ```
2. **修改 `response_parser.py`**：新增 `parse_native_safety()` 函數
3. **Pipeline 邏輯**：
  - 模型認為可能危險 → 🟡 注意，建議不碰
  - 模型認為安全 → 進入 Layer 3
4. **在結果中加入信賴邊界聲明**：
  ```
   ℹ️ 本區域知識庫收錄 20 種有毒植物。
   無法排除未收錄的危險物種。如有疑慮，請勿接觸。
  ```
5. **更新 Notebook**（重新產生 or 手動修改相關 Cell）

---

## Phase C — 文字描述輸入（5/6 → 5/8）

### 目標

讓使用者可以在上傳照片的同時，補充文字描述（氣味、觸感等），提高辨識準確度。

### 實作內容

1. **修改 `prompt_builder.py`**：
  - `build_danger_screening_prompt()` 新增 `user_description` 參數
  - 如有描述，附加到 Prompt 中
2. **修改 `pipeline.py`**：
  - `identify()` 新增 `description` 參數
  - 傳遞給各層 Prompt builder
3. **修改 Gradio UI**：
  - 在照片上傳區域下方新增文字輸入框
  - 標籤：「📝 補充描述（可選）：描述氣味、觸感、生長環境等」
4. **更新 Notebook**

---

## Phase D — 端對端測試（5/8 → 5/11）

### 目標

完整測試所有功能，修復所有 Bug。

### 測試清單


| 測試           | 輸入          | 預期            |
| ------------ | ----------- | ------------- |
| 有毒植物辨識       | 姑婆芋照片       | 🔴 + 混淆鑑別引導   |
| 可食植物辨識       | 大花咸豐草照片     | 🟢 + 採集方式     |
| 混淆物種         | 芋頭照片        | 觸發混淆鑑別 → 水珠測試 |
| 危險動物         | 虎頭蜂照片       | 🔴 + 急救 SOP   |
| 毒蛇辨識         | 赤尾青竹絲       | 🔴 + 混淆青蛇     |
| 不確定物種        | 隨便一棵樹       | ⚪ 建議不碰        |
| Layer 1.5 兜底 | 不在知識庫的有毒植物  | 🟡 模型認為可能危險   |
| 多照片          | 同一植物 3 角度   | 信心度提升         |
| 文字描述         | 照片 + 「葉面光滑」 | 影響判斷          |
| OOM 防護       | 連點載入按鈕      | 不重複載入         |
| 歷史紀錄         | 連續辨識 3 次    | 紀錄正確累積        |


### 修復流程

1. 發現 Bug → 紀錄在 TestLog
2. 修復 → 更新 app/ 下的原始碼
3. 重新產生 Notebook
4. 再次測試確認

---

## Phase E — Write-up 撰寫（5/11 → 5/14）

### 目標

撰寫比賽提交所需的 Write-up，展示專案的價值和技術深度。

### Write-up 結構（建議）

```markdown
# JungleSurvivor: Offline AI Wilderness Survival Assistant

## 🎯 Problem
- 每年數百人因野外誤食有毒植物或被毒蛇咬傷
- 野外通常無網路，需要 on-device 解決方案

## 💡 Solution
- Gemma 4 E2B-it 多模態識別
- 四層安全辨識流程（Safety-first）
- 離線知識庫 + 模型原生知識雙重防線
- 互動式測試引導（水珠測試等）

## 🏗️ Architecture
- Layer 0: 環境上下文
- Layer 1: 危險物種知識庫快篩
- Layer 1.5: 模型原生知識交叉驗證
- Layer 2: 混淆物種專項鑑別
- Layer 3: 可利用資源辨識
- Layer 4: 不確定 → 安全預設

## 📊 Knowledge Base
- 20 toxic plants (Taipei focus)
- 20 edible plants
- 13 dangerous animals (snakes, hornets, arthropods)
- 12 confusion pairs with interactive tests
- 5 emergency first-aid SOPs

## 🔒 Safety Design
- Conservative threshold: warns even at 60% match
- When uncertain → always treat as dangerous
- Model cross-validation prevents KB blind spots
- Trust boundary disclosure

## 📱 Future: On-device deployment
- Gemma 4 E2B INT4 quantized → 4GB RAM phones
- MediaPipe / AI Edge SDK integration

## 🎥 Demo
[Kaggle Notebook Link]
```

### 產出物

- Write-up markdown（提交到 Kaggle Discussion 或 Notebook 的第一個 Cell）
- 可選：Demo 影片（30-60 秒）

---

## Phase F — 最終提交（5/14 → 5/18）

### 步驟


| #   | 動作                  | 截止   |
| --- | ------------------- | ---- |
| F-1 | 最終 Notebook 完整測試通過  | 5/15 |
| F-2 | Write-up 定稿         | 5/16 |
| F-3 | Notebook 發布為 Public | 5/17 |
| F-4 | 確認提交（Submit）        | 5/17 |
| F-5 | 最終確認一切正常            | 5/18 |


### 提交檢查清單

- Notebook 能在 Kaggle 環境從頭跑到尾
- 模型載入不 OOM
- Gradio UI 能正常產生 public URL
- 辨識結果正確顯示（顏色、等級、詳細分析）
- 歷史紀錄正常運作
- Write-up 完整且有說服力
- 比賽規則全部符合（使用 Gemma 4、正面用途、Notebook 可執行）

---

## 時間線總覽

```
5/01 ─── Phase A: Kaggle 環境驗證 ────────────── 5/03
       ├─ 上傳 Notebook
       ├─ 完整執行測試
       └─ 確認 Gradio + 模型正常

5/03 ─── Phase B: Layer 1.5 安全兜底 ──────────── 5/06
       ├─ 實作模型原生知識檢查
       ├─ 信賴邊界聲明
       └─ 更新 Notebook

5/06 ─── Phase C: 文字描述輸入 ────────────────── 5/08
       ├─ Prompt 修改
       ├─ UI 新增輸入框
       └─ 更新 Notebook

5/08 ─── Phase D: 端對端測試 ──────────────────── 5/11
       ├─ 完整測試清單
       ├─ Bug 修復
       └─ 重新產生最終 Notebook

5/11 ─── Phase E: Write-up ────────────────────── 5/14
       ├─ 撰寫完整 Write-up
       └─ 可選：錄製 Demo 影片

5/14 ─── Phase F: 最終提交 ────────────────────── 5/18
       ├─ 最終測試
       ├─ 發布 Public Notebook
       └─ Submit
```

---

## 現在的下一步

**立刻做**：上傳重新產生的 `kaggle_gradio_demo.ipynb` 到 Kaggle，從頭跑一次（Phase A）。

回報結果後，我們再繼續 Phase B。