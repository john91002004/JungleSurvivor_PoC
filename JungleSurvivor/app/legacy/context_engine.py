"""
環境上下文引擎 — 根據使用者的位置/環境資訊載入對應的知識庫。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from config import REGIONS_PATH, EMERGENCY_PATH, AVAILABLE_REGIONS, DEFAULT_REGION


@dataclass
class EnvironmentContext:
    """使用者當前的環境上下文"""
    region_id: str = DEFAULT_REGION
    country: str = "台灣"
    climate_zone: str = "亞熱帶"
    altitude: int = 500
    vegetation_zone: str = "低海拔闊葉林"
    season: str = ""
    month: int = 0

    def __post_init__(self):
        if not self.month:
            self.month = datetime.now().month
        if not self.season:
            self.season = self._month_to_season(self.month)

    @staticmethod
    def _month_to_season(month: int) -> str:
        if month in (3, 4, 5):
            return "春季"
        elif month in (6, 7, 8):
            return "夏季"
        elif month in (9, 10, 11):
            return "秋季"
        else:
            return "冬季"

    def to_prompt_header(self) -> str:
        return (
            f"【環境上下文】\n"
            f"地點：{self.country}\n"
            f"氣候帶：{self.climate_zone}\n"
            f"海拔：約 {self.altitude}m\n"
            f"植被帶：{self.vegetation_zone}\n"
            f"季節：{self.season}"
        )


@dataclass
class KnowledgeBase:
    """載入的區域知識庫"""
    toxic_plants: list = field(default_factory=list)
    confusion_pairs: list = field(default_factory=list)
    edible_plants: list = field(default_factory=list)
    dangerous_animals: list = field(default_factory=list)
    snakebite_first_aid: dict = field(default_factory=dict)
    plant_poisoning_first_aid: dict = field(default_factory=dict)
    wound_care: dict = field(default_factory=dict)


def _load_json(path: Path) -> list | dict:
    """安全地載入 JSON 檔案"""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_knowledge_base(region_id: str = DEFAULT_REGION) -> KnowledgeBase:
    """根據 region_id 載入對應的知識庫"""
    region_path = REGIONS_PATH / region_id

    if not region_path.exists():
        raise FileNotFoundError(
            f"找不到區域知識庫：{region_id}。"
            f"可用區域：{list(AVAILABLE_REGIONS.keys())}"
        )

    kb = KnowledgeBase(
        toxic_plants=_load_json(region_path / "toxic_plants.json"),
        confusion_pairs=_load_json(region_path / "confusion_pairs.json"),
        edible_plants=_load_json(region_path / "edible_plants.json"),
        dangerous_animals=_load_json(region_path / "dangerous_animals.json"),
        snakebite_first_aid=_load_json(EMERGENCY_PATH / "snakebite_first_aid.json"),
        plant_poisoning_first_aid=_load_json(EMERGENCY_PATH / "plant_poisoning_first_aid.json"),
        wound_care=_load_json(EMERGENCY_PATH / "wound_care.json"),
    )

    return kb


def create_context(
    country: str = "台灣",
    altitude: int = 500,
    climate_zone: str = "亞熱帶",
    vegetation_zone: str = "低海拔闊葉林",
    region_id: str = DEFAULT_REGION,
) -> EnvironmentContext:
    """建立環境上下文"""
    return EnvironmentContext(
        region_id=region_id,
        country=country,
        climate_zone=climate_zone,
        altitude=altitude,
        vegetation_zone=vegetation_zone,
    )


def get_vegetation_zone(altitude: int) -> str:
    """根據海拔推算植被帶（台灣）"""
    if altitude < 500:
        return "低海拔闊葉林"
    elif altitude < 1500:
        return "中海拔闊葉林"
    elif altitude < 2500:
        return "中高海拔針闊混合林"
    elif altitude < 3500:
        return "高海拔針葉林"
    else:
        return "高山草原"
