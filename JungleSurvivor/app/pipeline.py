"""
JungleSurvivor v2 — Complete Pipeline

Orchestrates all 4 phases:
  Phase 0: Load KB + preprocess
  Phase 1: LLM feature extraction
  Phase 2: Feature merging
  Phase 3: Matching + scoring
  Phase 4: Post-processing
"""

from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable

from .feature_extractor import (
    load_prompt_template,
    load_enums,
    load_schema,
    parse_llm_response,
    ExtractionResult,
)
from .feature_merger import merge_features, apply_user_input, get_feature_summary
from .matcher import load_kb, match_top_n
from .postprocessor import process_results, format_result_display, ProcessedResult
from .scoring import ScoreResult


@dataclass
class PipelineState:
    """Tracks the state across iterative photo sessions."""
    accumulated_features: dict = field(default_factory=dict)
    photo_count: int = 0
    user_overrides: dict = field(default_factory=dict)
    extraction_history: list[ExtractionResult] = field(default_factory=list)
    latest_result: Optional[ProcessedResult] = None


class JungleSurvivorV2:
    """Main v2 pipeline controller."""

    def __init__(self, kb_root: str | Path | None = None):
        if kb_root is None:
            kb_root = Path(__file__).parent.parent / "knowledge_base"
        self.kb_root = Path(kb_root)
        self.region_dir = self.kb_root / "east_asia_subtropical"

        self.plants, self.schema, self.confusion_db = load_kb(self.region_dir)
        self.enums = load_enums(self.kb_root)
        self.prompt_template = load_prompt_template(self.kb_root)

        self.state = PipelineState()

    def reset(self):
        """Reset pipeline state for a new identification session."""
        self.state = PipelineState()

    def get_prompt(self) -> str:
        """Get the LLM prompt template for feature extraction."""
        return self.prompt_template

    # ── Phase 1: Feature Extraction ──

    def extract_features_from_response(self, llm_response: str) -> ExtractionResult:
        """Parse LLM response into structured features. Plan Phase 1."""
        result = parse_llm_response(llm_response, self.schema, self.enums)
        self.state.extraction_history.append(result)

        if result.success and result.features:
            self.state.accumulated_features = merge_features(
                self.state.accumulated_features,
                result.features,
                self.schema,
            )
            self.state.photo_count += 1

        return result

    # ── Phase 2: Feature Management ──

    def get_current_features(self) -> dict:
        """Get the current accumulated + user-modified features."""
        if self.state.user_overrides:
            return apply_user_input(
                self.state.accumulated_features,
                self.state.user_overrides,
            )
        return self.state.accumulated_features

    def get_feature_summary(self) -> dict:
        """Get summary of filled/missing features for UI."""
        features = self.get_current_features()
        return get_feature_summary(features, self.schema)

    def set_user_feature(self, section: str, attr: str, value):
        """Set a user override for a specific feature. Plan 6.2."""
        if section not in self.state.user_overrides:
            self.state.user_overrides[section] = {}
        self.state.user_overrides[section][attr] = value

    def remove_user_feature(self, section: str, attr: str):
        """Remove a user override, reverting to AI value."""
        if section in self.state.user_overrides:
            self.state.user_overrides[section].pop(attr, None)

    # ── Phase 3 + 4: Identify ──

    def identify(self, top_n: int = 3) -> ProcessedResult:
        """Run matching + post-processing. Plan Phase 3+4."""
        features = self.get_current_features()
        has_photo = self.state.photo_count > 0

        top_results = match_top_n(
            features,
            self.plants,
            self.schema,
            has_photo=has_photo,
            top_n=top_n,
        )

        result = process_results(top_results, self.confusion_db, self.plants)
        self.state.latest_result = result
        return result

    def format_display(self, result: Optional[ProcessedResult] = None) -> str:
        """Format results for display. Plan 8.4."""
        r = result or self.state.latest_result
        if r is None:
            return "尚未進行辨識。請先上傳照片。"
        return format_result_display(r, self.plants)

    # ── Utility ──

    def get_species_info(self, species_id: str) -> Optional[dict]:
        """Get full species data from KB."""
        for sp in self.plants:
            if sp["id"] == species_id:
                return sp
        return None

    def get_schema_enums_for_attr(self, section: str, attr: str) -> list[str]:
        """Get valid enum values for a specific attribute (for UI dropdowns)."""
        return self.enums.get(section, {}).get(attr, [])
