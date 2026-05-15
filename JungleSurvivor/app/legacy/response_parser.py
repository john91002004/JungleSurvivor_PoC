"""
回應解析器 — 解析 AI 模型的 JSON 回覆，提取結構化辨識結果。

支援：
- <JSON_START>/<JSON_END> 標記擷取
- ```json codeblock 擷取（含不完整）
- 備用 { } 擷取
- 截斷修復（補齊括號）
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from config import JSON_START_MARKER, JSON_END_MARKER


@dataclass
class CandidateMatch:
    """單一候選物種"""
    rank: int
    common_name_zh: str
    common_name_en: str
    scientific_name: str
    confidence: int
    category: str  # "dangerous", "edible", "medicinal"
    key_matching_features: list[str] = field(default_factory=list)
    danger_info: Optional[dict] = None


@dataclass
class UnifiedResult:
    """單次 AI 呼叫的解析結果"""
    raw_response: str
    json_data: Optional[dict]
    parse_success: bool
    parse_error: Optional[str] = None
    candidates: list[CandidateMatch] = field(default_factory=list)
    observed_features: list[str] = field(default_factory=list)


@dataclass
class ConfusionResult:
    """混淆鑑別結果"""
    raw_response: str
    json_data: Optional[dict]
    parse_success: bool
    parse_error: Optional[str] = None

    @property
    def is_safe(self) -> bool:
        if not self.json_data:
            return False
        return self.json_data.get("judgment") == "safe"

    @property
    def confidence(self) -> int:
        if not self.json_data:
            return 0
        return self.json_data.get("confidence", 0)

    @property
    def final_message(self) -> str:
        if not self.json_data:
            return ""
        return self.json_data.get("final_message_zh", "")


# ═══════════════════════════════════════════════════════════════
# JSON 擷取與修復
# ═══════════════════════════════════════════════════════════════

def _extract_json_from_markers(text: str) -> Optional[str]:
    if JSON_START_MARKER in text and JSON_END_MARKER in text:
        return text.split(JSON_START_MARKER, 1)[1].split(JSON_END_MARKER, 1)[0].strip()
    if JSON_START_MARKER in text:
        return text.split(JSON_START_MARKER, 1)[1].strip()
    return None


def _extract_json_from_codeblock(text: str) -> Optional[str]:
    m = re.search(r'```(?:json)?\s*\n?([\s\S]*?)```', text)
    if m:
        return m.group(1).strip()
    m = re.search(r'```(?:json)?\s*\n?([\s\S]+)', text)
    if m:
        return m.group(1).strip()
    return None


def _extract_json_fallback(text: str) -> Optional[str]:
    start = text.find('{')
    if start < 0:
        return None
    candidate = text[start:]
    end = candidate.rfind('}')
    if end >= 0:
        return candidate[:end + 1].strip()
    return candidate.strip()


def _repair_truncated_json(json_str: str) -> Optional[str]:
    last_complete = -1
    for m in re.finditer(r',\s*"[^"]+"\s*:', json_str):
        last_complete = m.start()

    if last_complete > 0:
        candidate = json_str[:last_complete]
        result = _close_json(candidate)
        if result:
            return result

    for marker in ['},', '}]', '}"', '],']:
        pos = json_str.rfind(marker)
        if pos > 0:
            candidate = json_str[:pos + 1]
            result = _close_json(candidate)
            if result:
                return result

    for ch in ['}', ']']:
        pos = json_str.rfind(ch)
        if pos > 0:
            candidate = json_str[:pos + 1]
            result = _close_json(candidate)
            if result:
                return result

    return _close_json(json_str)


def _close_json(candidate: str) -> Optional[str]:
    candidate = candidate.rstrip()
    while candidate.endswith(',') or candidate.endswith(':'):
        candidate = candidate[:-1].rstrip()

    opens = candidate.count('{') - candidate.count('}')
    brackets = candidate.count('[') - candidate.count(']')

    if opens <= 0 and brackets <= 0:
        return None

    candidate += ']' * max(0, brackets) + '}' * max(0, opens)
    return candidate


def _try_parse_json(json_str: str) -> tuple[Optional[dict], Optional[str]]:
    clean = json_str.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        clean = clean.rsplit("```", 1)[0]
    clean = clean.strip()

    try:
        return json.loads(clean), None
    except json.JSONDecodeError:
        pass

    repaired = _repair_truncated_json(clean)
    if repaired:
        try:
            return json.loads(repaired), None
        except json.JSONDecodeError:
            pass
        clean2 = re.sub(r',\s*([}\]])', r'\1', repaired)
        try:
            return json.loads(clean2), None
        except json.JSONDecodeError:
            pass

    clean3 = re.sub(r',\s*([}\]])', r'\1', clean)
    try:
        return json.loads(clean3), None
    except json.JSONDecodeError:
        pass

    for _ in range(5):
        truncated = _repair_truncated_json(clean)
        if truncated:
            truncated2 = re.sub(r',\s*([}\]])', r'\1', truncated)
            try:
                return json.loads(truncated2), None
            except json.JSONDecodeError:
                last_comma = truncated.rstrip('}]').rstrip().rfind(',')
                if last_comma > 0:
                    clean = truncated[:last_comma]
                else:
                    break
        else:
            break

    return None, "JSON 解析失敗"


# ═══════════════════════════════════════════════════════════════
# 主要解析函式
# ═══════════════════════════════════════════════════════════════

def parse_unified_response(response: str) -> UnifiedResult:
    """解析 AI 回覆，提取 candidates[] 列表。"""
    last_error = None
    for extractor in [_extract_json_from_markers, _extract_json_from_codeblock, _extract_json_fallback]:
        json_str = extractor(response)
        if json_str:
            data, error = _try_parse_json(json_str)
            if data is not None:
                candidates = _extract_candidates(data)
                return UnifiedResult(
                    raw_response=response,
                    json_data=data,
                    parse_success=True,
                    candidates=candidates,
                    observed_features=data.get("observed_features", []),
                )
            last_error = error

    return UnifiedResult(
        raw_response=response,
        json_data=None,
        parse_success=False,
        parse_error=last_error or "找不到可解析的 JSON",
    )


def _extract_candidates(data: dict) -> list[CandidateMatch]:
    raw_candidates = data.get("candidates", [])
    results = []
    for c in raw_candidates:
        if not isinstance(c, dict):
            continue
        results.append(CandidateMatch(
            rank=c.get("rank", len(results) + 1),
            common_name_zh=c.get("common_name_zh", "未知"),
            common_name_en=c.get("common_name_en", "Unknown"),
            scientific_name=c.get("scientific_name", ""),
            confidence=c.get("confidence", 0),
            category=c.get("category", "unknown"),
            key_matching_features=c.get("key_matching_features", []),
            danger_info=c.get("danger_info"),
        ))
    results.sort(key=lambda x: x.confidence, reverse=True)
    return results


def parse_confusion_response(response: str) -> ConfusionResult:
    """解析混淆物種鑑別回覆"""
    for extractor in [_extract_json_from_markers, _extract_json_from_codeblock, _extract_json_fallback]:
        json_str = extractor(response)
        if json_str:
            data, error = _try_parse_json(json_str)
            if data is not None:
                return ConfusionResult(
                    raw_response=response,
                    json_data=data,
                    parse_success=True,
                )

    return ConfusionResult(
        raw_response=response,
        json_data=None,
        parse_success=False,
        parse_error="找不到可解析的 JSON",
    )
