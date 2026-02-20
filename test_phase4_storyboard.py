# -*- coding: utf-8 -*-
"""Phase 4: 分镜转化模块的测试"""
import pytest
from storyboard_generator import StoryboardGenerator
from models import ScriptScene, StoryboardShot


class TestStoryboardGenerator:
    """测试分镜生成器"""

    def test_create_generator(self):
        """测试创建生成器"""
        generator = StoryboardGenerator()
        assert generator is not None

    def test_generate_shots_from_scene(self):
        """测试从场景生成分镜镜头"""
        generator = StoryboardGenerator()
        scene = ScriptScene(
            id="scene_001",
            chapter=1,
            location="酒馆 - 内部",
            time="夜",
            description="昏暗的酒馆，几个客人在低声交谈"
        )

        shots = generator.generate(scene)
        assert len(shots) > 0
        assert all(isinstance(shot, StoryboardShot) for shot in shots)

    def test_shots_have_sequential_numbers(self):
        """测试镜头编号是连续的"""
        generator = StoryboardGenerator()
        scene = ScriptScene(
            id="scene_002",
            chapter=1,
            location="酒馆",
            time="夜",
            description="张三走进酒馆"
        )

        shots = generator.generate(scene)
        for i, shot in enumerate(shots):
            assert shot.shot_number == i + 1

    def test_shots_have_scene_id(self):
        """测试镜头有关联的场景 ID"""
        generator = StoryboardGenerator()
        scene = ScriptScene(
            id="scene_003",
            chapter=2,
            location="小镇街道",
            time="日",
            description="热闹的街道"
        )

        shots = generator.generate(scene)
        assert all(shot.scene_id == "scene_003" for shot in shots)

    def test_first_shot_is_establishing(self):
        """测试第一个镜头是全景/建立镜头"""
        generator = StoryboardGenerator()
        scene = ScriptScene(
            id="scene_004",
            chapter=1,
            location="酒馆",
            time="夜",
            description="昏暗的酒馆里，张三走向柜台"
        )

        shots = generator.generate(scene)
        assert shots[0].shot_type in ["全景", "远景", "中景"]

    def test_scene_with_dialogue_generates_reaction_shots(self):
        """测试有对白的场景会生成反应镜头"""
        generator = StoryboardGenerator()
        scene = ScriptScene(
            id="scene_005",
            chapter=1,
            location="酒馆",
            time="夜",
            description="张三和李四对话",
            dialogues=[
                {"character_id": "char_张三", "line": "你好"},
                {"character_id": "char_李四", "line": "好久不见"}
            ]
        )

        shots = generator.generate(scene)
        # 有对话时应该有多个镜头
        assert len(shots) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
