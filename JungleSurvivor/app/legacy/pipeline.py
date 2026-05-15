"""
兩階段辨識 Pipeline — JungleSurvivor 核心邏輯。

流程：
  Stage 1: 危險物種比對 → 取信心度最高的 3 個
  Stage 2: 可食用/藥用物種比對 → 取信心度最高的 3 個
  Merge:   合併 6 個候選 → 依信心度排序 → 取前 3 名
  Confusion: 為前 3 名附上混淆物種對資訊 + 進一步觀察指引

信心度 = 絕對特徵吻合度（越多特徵符合，信心度越高）。
"""

from dataclasses import dataclass, field
from typing import Optional
from PIL import Image

from config import THRESHOLDS
from context_engine import EnvironmentContext, KnowledgeBase, load_knowledge_base, create_context
from prompt_builder import (
    build_danger_prompt,
    build_edible_prompt,
    build_confusion_pairs_prompt,
    build_interactive_test_guidance,
    build_multi_photo_wrapper,
)
from response_parser import (
    CandidateMatch,
    UnifiedResult,
    ConfusionResult,
    parse_unified_response,
    parse_confusion_response,
)


@dataclass
class ConfusionInfo:
    """某候選物種的混淆警告"""
    candidate_name: str
    confused_with: str
    pair_id: str
    distinguishing_features: list[str] = field(default_factory=list)
    interactive_tests: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Pipeline 最終輸出"""
    warning_level: str            # RED / YELLOW / GREEN / GRAY
    summary_zh: str               # 給使用者看的摘要
    candidates: list[CandidateMatch] = field(default_factory=list)
    observed_features: list[str] = field(default_factory=list)
    reasoning: str = ""
    confusion_warnings: list[ConfusionInfo] = field(default_factory=list)
    interactive_guidance: Optional[str] = None
    raw_responses: list[str] = field(default_factory=list)


class JungleSurvivorPipeline:
    """兩階段辨識 Pipeline"""

    def __init__(self, model):
        self.model = model

    def identify(
        self,
        images: list[Image.Image],
        context: Optional[EnvironmentContext] = None,
        mode: str = "auto",
        description: Optional[str] = None,
    ) -> PipelineResult:
        if context is None:
            context = create_context()

        kb = load_knowledge_base(context.region_id)

        target_type = "animal" if mode == "animal" else "plant"

        # ═══ Stage 1：危險物種比對 ═══
        danger_candidates, danger_obs, danger_reasoning, danger_raw = \
            self._run_stage(images, context, kb, "danger", target_type, description)

        # ═══ Stage 2：可食用/藥用物種比對 ═══
        if mode == "animal":
            edible_candidates, edible_obs, edible_reasoning, edible_raw = [], [], "", ""
        else:
            edible_candidates, edible_obs, edible_reasoning, edible_raw = \
                self._run_stage(images, context, kb, "edible", target_type, description)

        raw_responses = [r for r in [danger_raw, edible_raw] if r]

        # ═══ Merge：合併 6 → 取前 3 ═══
        all_six = danger_candidates + edible_candidates
        all_six.sort(key=lambda c: c.confidence, reverse=True)
        top3 = all_six[:3]

        for i, c in enumerate(top3, 1):
            c.rank = i

        all_obs = list(dict.fromkeys(danger_obs + edible_obs))

        reasoning_parts = []
        if danger_reasoning:
            reasoning_parts.append(f"【危險物種分析】\n{danger_reasoning}")
        if edible_reasoning:
            reasoning_parts.append(f"【可食用物種分析】\n{edible_reasoning}")
        combined_reasoning = "\n\n".join(reasoning_parts)

        # ═══ Confusion：為前 3 名檢查混淆物種 ═══
        confusion_warnings, guidance_text = self._check_confusion_pairs(
            images, context, kb, top3
        )

        # ═══ 決定警告等級與摘要 ═══
        warning_level, summary = self._build_summary(top3, confusion_warnings, guidance_text)

        return PipelineResult(
            warning_level=warning_level,
            summary_zh=summary,
            candidates=top3,
            observed_features=all_obs,
            reasoning=combined_reasoning,
            confusion_warnings=confusion_warnings,
            interactive_guidance=guidance_text,
            raw_responses=raw_responses,
        )

    # ───────────────────────────────────────────────────────────
    # 單階段執行
    # ───────────────────────────────────────────────────────────

    def _run_stage(
        self,
        images: list[Image.Image],
        context: EnvironmentContext,
        kb: KnowledgeBase,
        stage: str,
        target_type: str,
        description: Optional[str],
    ) -> tuple[list[CandidateMatch], list[str], str, str]:
        """
        執行單一階段的 AI 辨識。
        回傳 (candidates, observed_features, reasoning, raw_response)。
        """
        if stage == "danger":
            prompt = build_danger_prompt(context, kb, target_type)
        else:
            prompt = build_edible_prompt(context, kb)

        if len(images) > 1:
            prompt = build_multi_photo_wrapper(prompt, len(images))

        if description:
            prompt += f"\n\n使用者補充描述：{description}"

        response = self.model.generate(prompt, images)
        result = parse_unified_response(response)

        if not result.parse_success:
            return [], [], "", response

        reasoning = ""
        if result.json_data:
            reasoning = result.json_data.get("reasoning_summary", "")

        candidates = result.candidates[:3]
        return candidates, result.observed_features, reasoning, response

    # ───────────────────────────────────────────────────────────
    # 混淆物種偵測
    # ───────────────────────────────────────────────────────────

    def _check_confusion_pairs(
        self,
        images: list[Image.Image],
        context: EnvironmentContext,
        kb: KnowledgeBase,
        top3: list[CandidateMatch],
    ) -> tuple[list[ConfusionInfo], Optional[str]]:
        """
        對前 3 名候選檢查是否有已知的混淆物種對。
        如果有，附上區分特徵與互動測試指引。
        """
        confusion_infos: list[ConfusionInfo] = []
        guidance_parts: list[str] = []

        for candidate in top3:
            matched_pair = self._find_confusion_pair(kb, candidate)
            if not matched_pair:
                continue

            safe = matched_pair["safe_species"]
            danger = matched_pair["dangerous_species"]

            distinguishing = []
            for row in matched_pair.get("comparison_table", []):
                distinguishing.append(
                    f"{row['feature']}：安全→{row['safe']}，危險→{row['danger']}"
                )

            test_names = [
                t["test_name"]
                for t in matched_pair.get("interactive_tests", [])
            ]

            other = danger["common_name_zh"] \
                if candidate.common_name_zh == safe["common_name_zh"] \
                else safe["common_name_zh"]

            info = ConfusionInfo(
                candidate_name=candidate.common_name_zh,
                confused_with=other,
                pair_id=matched_pair["id"],
                distinguishing_features=distinguishing,
                interactive_tests=test_names,
            )
            confusion_infos.append(info)

            guidance = build_interactive_test_guidance(matched_pair)
            guidance_parts.append(
                f"⚠️ 「{candidate.common_name_zh}」與「{other}」容易混淆：\n{guidance}"
            )

        guidance_text = "\n\n".join(guidance_parts) if guidance_parts else None
        return confusion_infos, guidance_text

    def _find_confusion_pair(
        self, kb: KnowledgeBase, candidate: CandidateMatch
    ) -> Optional[dict]:
        """在知識庫的混淆物種對中尋找與此候選相關的配對。"""
        candidate_sci = candidate.scientific_name.lower().replace(" ", "_")
        candidate_zh = candidate.common_name_zh

        for pair in kb.confusion_pairs:
            safe = pair["safe_species"]
            danger = pair["dangerous_species"]

            safe_names = {
                safe.get("id", ""),
                safe.get("scientific_name", "").lower().replace(" ", "_"),
                safe.get("common_name_zh", ""),
            }
            danger_names = {
                danger.get("id", ""),
                danger.get("scientific_name", "").lower().replace(" ", "_"),
                danger.get("common_name_zh", ""),
            }

            if candidate_sci in safe_names or candidate_sci in danger_names:
                return pair
            if candidate_zh in safe_names or candidate_zh in danger_names:
                return pair

        return None

    # ───────────────────────────────────────────────────────────
    # 決定警告等級與摘要
    # ───────────────────────────────────────────────────────────

    def _build_summary(
        self,
        top3: list[CandidateMatch],
        confusion_warnings: list[ConfusionInfo],
        guidance_text: Optional[str],
    ) -> tuple[str, str]:
        """根據前 3 候選的類別與信心度決定警告等級和摘要文字。"""
        if not top3:
            return "GRAY", "⚪ 無法辨識此物種，建議不要接觸或食用。\n請嘗試拍攝更清楚的照片。"

        first = top3[0]
        has_danger_in_top = any(c.category == "dangerous" for c in top3)
        top_is_danger = first.category == "dangerous"
        has_confusion = len(confusion_warnings) > 0
        danger_threshold = THRESHOLDS.get("danger_screening", 60)

        # --- 1) 最高信心的是危險物種 ---
        if top_is_danger and first.confidence >= danger_threshold:
            lines = [
                f"🔴 **警告：最可能為危險物種！**",
                f"",
                f"最高匹配：**{first.common_name_zh}** (*{first.scientific_name}*)",
                f"信心度：{first.confidence}%（{len(first.key_matching_features)} 項特徵吻合）",
            ]
            if first.danger_info:
                tox = first.danger_info.get("toxicity", "")
                if tox:
                    lines.append(f"⚠️ 毒性：{tox}")
                fa = first.danger_info.get("first_aid", "")
                if fa:
                    lines.append(f"🩹 急救：{fa}")
            lines.append("")
            lines.append("📋 完整候選排名：")
            for c in top3:
                cat_label = "⚠️危險" if c.category == "dangerous" else "🍃可食" if c.category == "edible" else "💊藥用"
                lines.append(f"  #{c.rank} {c.common_name_zh}（{cat_label}）— {c.confidence}%")

            if has_confusion:
                lines.append("")
                lines.append("🔀 混淆物種警告：")
                for cw in confusion_warnings:
                    lines.append(f"  「{cw.candidate_name}」⟷「{cw.confused_with}」")
                lines.append("")
                lines.append("👉 請參考下方「互動測試指引」做進一步區分！")

            return "RED", "\n".join(lines)

        # --- 2) 前 3 中有危險物種但非最高 ---
        if has_danger_in_top:
            lines = [
                f"🟡 **注意：候選中包含危險物種，需進一步確認！**",
                f"",
                f"最高匹配：**{first.common_name_zh}** (*{first.scientific_name}*)",
                f"信心度：{first.confidence}%",
                "",
                "📋 完整候選排名：",
            ]
            for c in top3:
                cat_label = "⚠️危險" if c.category == "dangerous" else "🍃可食" if c.category == "edible" else "💊藥用"
                lines.append(f"  #{c.rank} {c.common_name_zh}（{cat_label}）— {c.confidence}%")

            lines.extend(self._build_verification_guidance(top3, confusion_warnings))
            return "YELLOW", "\n".join(lines)

        # --- 3) 前 3 都是可食/藥用但有混淆 ---
        if has_confusion:
            lines = [
                f"🟡 **辨識為可食用物種，但存在混淆風險！**",
                f"",
                f"最高匹配：**{first.common_name_zh}** (*{first.scientific_name}*)",
                f"信心度：{first.confidence}%",
                "",
                "📋 完整候選排名：",
            ]
            for c in top3:
                cat_label = "🍃可食" if c.category == "edible" else "💊藥用"
                lines.append(f"  #{c.rank} {c.common_name_zh}（{cat_label}）— {c.confidence}%")

            lines.append("")
            lines.append("🔀 混淆物種警告：")
            for cw in confusion_warnings:
                lines.append(f"  「{cw.candidate_name}」與「{cw.confused_with}」外觀極相似")

            lines.extend(self._build_verification_guidance(top3, confusion_warnings))
            return "YELLOW", "\n".join(lines)

        # --- 4) 前 3 都是安全物種，無混淆 ---
        if first.confidence >= THRESHOLDS.get("useful_resources", 70):
            lines = [
                f"🟢 **辨識為可利用資源**",
                f"",
                f"最高匹配：**{first.common_name_zh}** (*{first.scientific_name}*)",
                f"信心度：{first.confidence}%（{len(first.key_matching_features)} 項特徵吻合）",
                "",
                "📋 完整候選排名：",
            ]
            for c in top3:
                cat_label = "🍃可食" if c.category == "edible" else "💊藥用"
                lines.append(f"  #{c.rank} {c.common_name_zh}（{cat_label}）— {c.confidence}%")

            lines.extend(self._build_verification_guidance(top3, confusion_warnings))
            return "GREEN", "\n".join(lines)

        # --- 5) 信心度都偏低 ---
        lines = [
            f"⚪ **信心度不足，無法確定物種。**",
            f"",
            f"最高匹配：{first.common_name_zh}（{first.confidence}%）",
            "",
            "📋 候選排名（信心度均偏低）：",
        ]
        for c in top3:
            cat_label = {"dangerous": "⚠️危險", "edible": "🍃可食", "medicinal": "💊藥用"}.get(c.category, "❓")
            lines.append(f"  #{c.rank} {c.common_name_zh}（{cat_label}）— {c.confidence}%")

        lines.append("")
        lines.append("💡 建議：")
        lines.append("  - 拍攝更多角度的照片（葉面、葉背、花、莖、根部）")
        lines.append("  - 在信心度不足的情況下，切勿食用或觸碰")
        return "GRAY", "\n".join(lines)

    def _build_verification_guidance(
        self,
        top3: list[CandidateMatch],
        confusion_warnings: list[ConfusionInfo],
    ) -> list[str]:
        """產出「如何進一步確認」的指引。"""
        lines = [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🔍 **如何進一步確認？**",
            "",
        ]

        lines.append("📸 **多角度觀察（提升信心度）**：")
        lines.append("  1. 拍攝葉子的正面與背面（觀察葉脈、絨毛、質地）")
        lines.append("  2. 拍攝莖部橫切面（觀察是否中空、有乳汁）")
        lines.append("  3. 拍攝花和果實的近照")
        lines.append("  4. 拍攝整株植物的生長環境")

        if confusion_warnings:
            lines.append("")
            lines.append("🔬 **區分混淆物種的關鍵特徵**：")
            for cw in confusion_warnings:
                lines.append(f"")
                lines.append(f"  「{cw.candidate_name}」vs「{cw.confused_with}」：")
                for feat in cw.distinguishing_features[:5]:
                    lines.append(f"    • {feat}")
                if cw.interactive_tests:
                    lines.append(f"    🧪 實地測試：{'、'.join(cw.interactive_tests)}")

        lines.append("")
        lines.append("🧪 **通用可食性野外測試（不確定時務必執行）**：")
        lines.append("  1. 皮膚測試：取少量汁液塗在手腕內側，等待 15 分鐘觀察是否紅腫")
        lines.append("  2. 唇部測試：將少量放在嘴唇上，等待 5 分鐘觀察是否刺痛")
        lines.append("  3. 舌尖測試：少量放在舌尖上 15 分鐘，注意異常味道或麻痺感")
        lines.append("  4. 微量試食：咀嚼一小口後吐出，等待 8 小時觀察是否有不適")
        lines.append("  ⚠️ 每個步驟之間如有任何不適反應，立即停止並大量喝水！")

        return lines
