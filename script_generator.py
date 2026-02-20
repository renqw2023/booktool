# -*- coding: utf-8 -*-
"""Phase 3: 剧本生成模块"""
from typing import List
from models import TimelineEvent, ScriptScene


class ScriptGenerator:
    """剧本生成器 - 将时间线事件转化为剧本场景"""

    def __init__(self):
        # 时间关键词映射
        self.time_keywords = {
            "夜": ["夜", "夜晚", "晚上", "深夜", "傍晚", "黄昏", "雨夜"],
            "日": ["日", "白天", "早晨", "早上", "中午", "下午", "清晨"],
            "晨": ["晨", "黎明", "破晓", "晨曦"],
        }

    def generate(self, events: List[TimelineEvent]) -> List[ScriptScene]:
        """从时间线事件生成剧本场景"""
        scenes = []

        for event in events:
            scene = self._create_scene_from_event(event)
            if scene:
                scenes.append(scene)

        return scenes

    def _create_scene_from_event(self, event: TimelineEvent) -> ScriptScene:
        """从单个事件创建场景"""
        # 确定时间
        time = self._determine_time(event)

        # 确定地点
        location = self._determine_location(event)

        # 生成描述
        description = self._generate_description(event)

        # 提取人物
        character_ids = event.character_ids if event.character_ids else []

        scene = ScriptScene(
            id=f"scene_{event.id}",
            chapter=event.chapter,
            location=location,
            time=time,
            description=description,
            character_ids=character_ids
        )

        return scene

    def _determine_time(self, event: TimelineEvent) -> str:
        """从事件中确定时间"""
        # 默认时间
        time = "日"

        # 检查摘要和描述中的时间关键词
        text = f"{event.summary} {event.description}"

        for time_value, keywords in self.time_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return time_value

        return time

    def _determine_location(self, event: TimelineEvent) -> str:
        """从事件中确定地点"""
        if event.location:
            return event.location

        # 尝试从描述中提取地点
        # 这里简单返回一个默认值
        return "未知地点"

    def _generate_description(self, event: TimelineEvent) -> str:
        """生成场景描述"""
        if event.description:
            return event.description
        return event.summary
