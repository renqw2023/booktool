# -*- coding: utf-8 -*-
"""Phase 3: 剧本生成模块的测试 - LLM 驱动版本

使用《哈利波特》片段测试剧本生成器的泛化能力。
"""
import pytest
from script_generator import ScriptGenerator, MockLLMClient
from models import TimelineEvent, ScriptScene


# ==================== Mock LLM 响应数据 ====================

def get_scene_generation_mock_response():
    """剧本场景生成的 Mock 响应"""
    return '''
    {
        "scene": {
            "id": "scene_event_001",
            "chapter": 1,
            "location": "霍格沃茨大礼堂",
            "time": "夜",
            "description": "大礼堂内烛光摇曳，新生们紧张地等待着分院仪式。哈利和罗恩站在人群中，赫敏在一旁轻声安慰他们。",
            "actions": [
                "哈利紧张地握紧了魔杖",
                "罗恩咽了口唾沫，显得有些不安",
                "赫敏走近两人，轻声说着鼓励的话",
                "邓布利多站起身，走向讲台"
            ],
            "dialogues": [
                {"character_id": "char_harry", "line": "我希望我能进格兰芬多。"},
                {"character_id": "char_ron", "line": "我也是，我妈妈说格兰芬多是最好的。"},
                {"character_id": "char_hermione", "line": "别担心，你们肯定没问题的。"}
            ],
            "character_ids": ["char_harry", "char_ron", "char_hermione"]
        }
    }
    '''


def get_fallback_scene_mock_response():
    """备用场景生成的 Mock 响应（简化版）"""
    return '''
    {
        "scene": {
            "id": "scene_event_002",
            "chapter": 2,
            "location": "魔药课教室",
            "time": "日",
            "description": "阴冷的地窖里，斯内普教授正在讲课",
            "actions": [
                "斯内普转身面向学生",
                "哈利低头避开他的目光"
            ],
            "dialogues": [],
            "character_ids": ["char_harry", "char_snape"]
        }
    }
    '''


# ==================== 测试用例 ====================

class TestScriptGenerator:
    """测试剧本生成器"""

    def test_create_generator(self):
        """测试创建生成器"""
        generator = ScriptGenerator()
        assert generator is not None

    def test_generate_scene_from_harry_potter_event(self):
        """测试从哈利波特事件生成剧本场景"""
        mock_client = MockLLMClient(get_scene_generation_mock_response())
        generator = ScriptGenerator(mock_client)
        event = TimelineEvent(
            id="event_001",
            chapter=1,
            summary="新生们参加分院仪式",
            description="哈利和罗恩在大礼堂里等待分院，两人都很紧张",
            location="霍格沃茨大礼堂",
            character_ids=["char_harry", "char_ron", "char_hermione"]
        )

        scenes = generator.generate([event])
        assert len(scenes) > 0
        scene = scenes[0]
        assert isinstance(scene, ScriptScene)
        assert scene.chapter == 1

    def test_scene_has_time(self):
        """测试生成的场景有时间设定"""
        mock_client = MockLLMClient(get_scene_generation_mock_response())
        generator = ScriptGenerator(mock_client)
        event = TimelineEvent(
            id="event_002",
            chapter=2,
            summary="哈利在雨夜出行",
            description="在一个下着大雨的夜晚，哈利独自前往禁林",
            location="禁林入口"
        )

        scenes = generator.generate([event])
        assert len(scenes) > 0
        # LLM 应该能正确识别时间
        assert scenes[0].time in ["夜", "夜晚", "晚上", "日", "黄昏", "黎明"]

    def test_generate_multiple_scenes(self):
        """测试生成多个场景"""
        mock_client = MockLLMClient(get_scene_generation_mock_response())
        generator = ScriptGenerator(mock_client)
        events = [
            TimelineEvent(
                id="event_003",
                chapter=1,
                summary="哈利到达霍格沃茨",
                location="霍格沃茨城堡"
            ),
            TimelineEvent(
                id="event_004",
                chapter=2,
                summary="哈利参加魔药课",
                location="魔药课教室"
            )
        ]

        scenes = generator.generate(events)
        assert len(scenes) >= 2

    def test_scene_has_actions(self):
        """测试生成的场景有动作描写"""
        mock_client = MockLLMClient(get_scene_generation_mock_response())
        generator = ScriptGenerator(mock_client)
        event = TimelineEvent(
            id="event_005",
            chapter=1,
            summary="哈利遇到罗恩",
            description="在霍格沃茨特快上，哈利和罗恩分享了零食"
        )

        scenes = generator.generate([event])
        assert len(scenes) > 0
        # LLM 生成的场景应该有动作描写
        scene = scenes[0]
        assert isinstance(scene.actions, list)

    def test_scene_has_dialogues(self):
        """测试生成的场景可以有对白"""
        mock_client = MockLLMClient(get_scene_generation_mock_response())
        generator = ScriptGenerator(mock_client)
        event = TimelineEvent(
            id="event_006",
            chapter=1,
            summary="哈利和罗恩初次见面",
            description="两人在火车上交谈，很快就成了朋友"
        )

        scenes = generator.generate([event])
        assert len(scenes) > 0
        # dialogues 应该是列表
        assert isinstance(scenes[0].dialogues, list)

    def test_fallback_mechanism(self):
        """测试当 LLM 失败时的备用机制"""
        # 使用空响应的 Mock 客户端
        mock_client = MockLLMClient('{"invalid": "data"}')
        generator = ScriptGenerator(mock_client)
        event = TimelineEvent(
            id="event_007",
            chapter=1,
            summary="测试事件",
            location="测试地点"
        )

        scenes = generator.generate([event])
        assert len(scenes) > 0
        # 备用机制应该返回一个基础场景
        assert scenes[0].location == "测试地点"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
