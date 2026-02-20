"""Phase 1: 核心数据结构定义"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Character:
    """小说人物实体"""
    id: str
    name: str
    description: str
    traits: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    background: Optional[str] = None
    appearance: Optional[str] = None


@dataclass
class Relationship:
    """人物关系实体"""
    id: str
    character_id_1: str
    character_id_2: str
    type: str
    description: str
    conflict_level: int = 0  # 0-5，0 表示无冲突，5 表示极度冲突
    strength: int = 5  # 0-5，关系强度


@dataclass
class TimelineEvent:
    """时间线事件实体"""
    id: str
    chapter: int
    summary: str
    description: Optional[str] = None
    character_ids: List[str] = field(default_factory=list)
    location: Optional[str] = None
    timestamp: Optional[str] = None  # 事件在章节中的大致时间点


@dataclass
class ScriptScene:
    """剧本场景实体"""
    id: str
    chapter: int
    location: str
    time: str  # 日/夜/黄昏等
    description: str
    dialogues: List[Dict[str, str]] = field(default_factory=list)
    character_ids: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)


@dataclass
class StoryboardShot:
    """分镜镜头实体"""
    id: str
    scene_id: str
    shot_number: int
    shot_type: str  # 全景/中景/近景/特写等
    description: str
    camera_direction: Optional[str] = None
    duration_seconds: Optional[float] = None
    audio_direction: Optional[str] = None
    characters_in_shot: List[str] = field(default_factory=list)
