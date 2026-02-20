# -*- coding: utf-8 -*-
"""Phase 3: 剧本生成模块的测试"""
import pytest
from script_generator import ScriptGenerator
from models import TimelineEvent, ScriptScene


class TestScriptGenerator:
    """测试剧本生成器"""

    def test_create_generator(self):
        """测试创建生成器"""
        generator = ScriptGenerator()
        assert generator is not None

    def test_generate_scene_from_event(self):
        """测试从事件生成剧本场景"""
        generator = ScriptGenerator()
        event = TimelineEvent(
            id="event_001",
            chapter=1,
            summary="张三走进酒馆",
            description="在一个雨夜，张三走进了小镇的酒馆",
            location="酒馆"
        )

        scenes = generator.generate([event])
        assert len(scenes) > 0
        scene = scenes[0]
        assert isinstance(scene, ScriptScene)
        assert scene.chapter == 1
        assert "酒馆" in scene.location

    def test_scene_has_time(self):
        """测试生成的场景有时间设定"""
        generator = ScriptGenerator()
        event = TimelineEvent(
            id="event_002",
            chapter=2,
            summary="张三在雨夜出行",
            description="在一个下着大雨的夜晚",
            location="小镇"
        )

        scenes = generator.generate([event])
        assert len(scenes) > 0
        # 雨夜应该被识别为"夜"
        assert scenes[0].time in ["夜", "夜晚", "晚上"]

    def test_generate_multiple_scenes(self):
        """测试生成多个场景"""
        generator = ScriptGenerator()
        events = [
            TimelineEvent(
                id="event_003",
                chapter=1,
                summary="张三出发",
                location="家里"
            ),
            TimelineEvent(
                id="event_004",
                chapter=2,
                summary="张三到达酒馆",
                location="酒馆"
            )
        ]

        scenes = generator.generate(events)
        assert len(scenes) >= 2

    def test_scene_has_description(self):
        """测试生成的场景有描述"""
        generator = ScriptGenerator()
        event = TimelineEvent(
            id="event_005",
            chapter=1,
            summary="张三遇到李四",
            description="张三在酒馆里遇到了神秘的李四，两人对视一眼"
        )

        scenes = generator.generate([event])
        assert len(scenes) > 0
        assert scenes[0].description != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
