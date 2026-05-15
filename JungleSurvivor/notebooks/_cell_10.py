"""
合併式辨識 Pipeline — 單次 AI 推論 + 程式後處理。

流程：
  1. 環境上下文 → 載入區域知識庫
  2. 單次 AI 呼叫 → 比對全部物種 → 輸出前 3 名候選
  3. 程式後處理：
     - 檢查候選是否包含混淆物種對
     - 根據類別決定警告等級
     - 生成互動測試指引（如需要）
"""

from dataclasses import dataclass, field
from typing import Optional
from PIL import Image


@dataclass
class PipelineResult:
    """Pipeline 最終輸出"""
    warning_level: str
    summary_zh: str
    candidates: list[CandidateMatch] = field(default_factory=list)
    observed_features: list[str] = field(default_factory=list)
    reasoning: str = ""
    confusion_warning: Optional[str] = None
    interactive_guidance: Optional[str] = None
    raw_response: str = ""
    parse_success: bool = True
    parse_error: Optional[str] = None


class JungleSurvivorPipeline:
    """單次推論合併式 Pipeline"""

    def __init__(self, model):
        self.model = model

    def identify(
        self,
        images: list[Image.Image],
        context: Optional[EnvironmentContext] = None,
        mode: str = "auto",
        description: str | None = None,
    ) -> PipelineResult:
        """
        執行合併式辨識。

        Args:
            images: PIL Image 列表
            context: 環境上下文
            mode: "auto" | "danger_only" | "animal" | "medicinal"
            description: 使用者文字描述

        Returns:
            PipelineResult
        """
        if context is None:
            context = create_context()

        kb = load_knowledge_base(context.region_id)
        target_type = "animal" if mode == "animal" else "plant"

        # === 單次 AI 呼叫 ===
        prompt = build_unified_prompt(context, kb, target_type, user_description=description)

        if len(images) > 1:
            prompt = build_multi_photo_wrapper(prompt, len(images))

        response = self.model.generate(prompt, images)
        result = parse_unified_response(response)

        if not result.parse_success:
            snippet = result.raw_response[:500] if result.raw_response else "(empty)"
            print(f"[Pipeline] Parse failed. Error: {result.parse_error}\nSnippet: {snippet}")
            return PipelineResult(
                warning_level="GRAY",
                summary_zh=(
                    f"⚠️ 辨識結果解析失敗，請重新拍照嘗試。\n\n"
                    f"Debug: {result.parse_error}\n"
                    f"回覆前 300 字: {(result.raw_response or '')[:300]}"
                ),
                raw_response=result.raw_response,
                parse_success=False,
                parse_error=result.parse_error,
            )

        # === 程式後處理 ===
        return self._post_process(result, kb, mode)

    def _post_process(
        self,
        result: UnifiedResult,
        kb: KnowledgeBase,
        mode: str,
    ) -> PipelineResult:
        """根據候選結果進行後處理：判定警告等級、檢查混淆物種"""
        candidates = result.candidates
        top = result.top_candidate

        if not top or top.confidence < 30:
            return PipelineResult(
                warning_level="GRAY",
                summary_zh=(
                    "⚪ 無法確定此物種的身份。\n"
                    "建議不要接觸或食用。\n"
                    "如有可能，請拍攝更多角度的照片重試。"
                ),
                candidates=candidates,
                observed_features=result.observed_features,
                reasoning=result.reasoning_summary,
                raw_response=result.raw_response,
            )

        # 判定警告等級
        warning_level = result.warning_level

        # 建構摘要
        summary_parts = []

        if warning_level == "RED":
            summary_parts.append(f"🔴 警告：偵測到危險物種！")
            di = top.danger_info or {}
            if di.get("warning"):
                summary_parts.append(f"⚠️ {di['warning']}")
        elif warning_level == "YELLOW":
            summary_parts.append(f"🟡 注意：可能為危險物種")
        elif warning_level == "GREEN":
            if top.category == "medicinal":
                summary_parts.append(f"🟢 辨識為藥用植物")
            else:
                summary_parts.append(f"🟢 辨識為可利用資源")
        else:
            summary_parts.append(f"⚪ 不確定")

        summary_parts.append(f"\n🏆 第一候選：{top.common_name_zh} ({top.scientific_name})")
        summary_parts.append(f"   信心度：{top.confidence}%")
        summary_parts.append(f"   類別：{self._category_label(top.category)}")

        if len(candidates) > 1:
            summary_parts.append(f"\n📋 其他候選：")
            for c in candidates[1:]:
                summary_parts.append(f"   #{c.rank} {c.common_name_zh} — {c.confidence}% ({self._category_label(c.category)})")

        if result.observed_features:
            summary_parts.append(f"\n🔍 觀察到的特徵：{'、'.join(result.observed_features[:5])}")

        # 檢查混淆物種
        confusion_warning = None
        interactive_guidance = None

        if result.has_confusion_risk:
            pair = self._find_confusion_pair(candidates, kb)
            if pair:
                safe_name = pair["safe_species"]["common_name_zh"]
                danger_name = pair["dangerous_species"]["common_name_zh"]
                confusion_warning = (
                    f"\n\n⚠️ 混淆警告：前兩名候選包含已知的混淆物種對！\n"
                    f"🔴 {danger_name}（有毒） vs 🟢 {safe_name}（可食）\n"
                    f"這兩種植物外觀極度相似，請務必進行以下測試確認。"
                )
                interactive_guidance = build_interactive_test_guidance(pair)
                warning_level = "YELLOW"
                summary_parts.append(confusion_warning)

        summary = "\n".join(summary_parts)

        return PipelineResult(
            warning_level=warning_level,
            summary_zh=summary,
            candidates=candidates,
            observed_features=result.observed_features,
            reasoning=result.reasoning_summary,
            confusion_warning=confusion_warning,
            interactive_guidance=interactive_guidance,
            raw_response=result.raw_response,
        )

    def _find_confusion_pair(
        self, candidates: list[CandidateMatch], kb: KnowledgeBase
    ) -> Optional[dict]:
        """檢查前兩名候選是否存在於已知的混淆物種對中"""
        if len(candidates) < 2:
            return None

        top_names = set()
        for c in candidates[:3]:
            top_names.add(c.scientific_name.lower().replace(" ", "_"))
            top_names.add(c.common_name_zh)

        for pair in kb.confusion_pairs:
            safe = pair["safe_species"]
            danger = pair["dangerous_species"]

            safe_ids = {
                safe.get("id", ""),
                safe.get("scientific_name", "").lower().replace(" ", "_"),
                safe.get("common_name_zh", ""),
            }
            danger_ids = {
                danger.get("id", ""),
                danger.get("scientific_name", "").lower().replace(" ", "_"),
                danger.get("common_name_zh", ""),
            }

            if top_names & safe_ids and top_names & danger_ids:
                return pair

        return None

    @staticmethod
    def _category_label(category: str) -> str:
        labels = {
            "dangerous": "⚠️ 危險",
            "edible": "🍃 可食",
            "medicinal": "💊 藥用",
        }
        return labels.get(category, category)
