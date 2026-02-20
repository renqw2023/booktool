# -*- coding: utf-8 -*-
"""Phase 5: 系统流水线整合测试 - LLM 驱动版本

使用《哈利波特》片段测试完整的处理流水线。
"""
import pytest
from main import NovelProcessor
from models import Character, Relationship, TimelineEvent, ScriptScene, StoryboardShot
from extractor import MockLLMClient


# ==================== Mock LLM 响应数据 ====================

def get_full_pipeline_mock_responses():
    """完整流水线的 Mock 响应序列"""
    return {
        'characters': '''
        {
            "characters": [
                {
                    "id": "char_harry",
                    "name": "哈利·波特",
                    "description": "著名的年轻巫师，额头上有闪电形伤疤",
                    "traits": ["勇敢", "忠诚", "冲动"],
                    "goals": ["学习魔法", "对抗伏地魔"],
                    "background": "孤儿，11 岁进入霍格沃茨",
                    "appearance": "黑发绿眼，戴眼镜"
                },
                {
                    "id": "char_ron",
                    "name": "罗恩·韦斯莱",
                    "description": "哈利最好的朋友，来自韦斯莱家族",
                    "traits": ["忠诚", "幽默"],
                    "goals": ["学习魔法"],
                    "background": "纯血统巫师家庭",
                    "appearance": "红头发，满脸雀斑"
                }
            ]
        }
        ''',
        'relationships': '''
        {
            "relationships": [
                {
                    "id": "rel_harry_ron",
                    "character_id_1": "char_harry",
                    "character_id_2": "char_ron",
                    "type": "朋友",
                    "description": "哈利和罗恩在火车上相遇，成为最好的朋友",
                    "conflict_level": 0,
                    "strength": 5
                }
            ]
        }
        ''',
        'timeline': '''
        {
            "events": [
                {
                    "id": "event_ch1",
                    "chapter": 1,
                    "summary": "哈利在对角巷购买开学用品",
                    "description": "哈利独自一人在对角巷闲逛",
                    "character_ids": ["char_harry"],
                    "location": "对角巷",
                    "timestamp": "早晨"
                },
                {
                    "id": "event_ch2",
                    "chapter": 2,
                    "summary": "哈利和罗恩在火车上相遇",
                    "description": "两人在霍格沃茨特快上分享零食",
                    "character_ids": ["char_harry", "char_ron"],
                    "location": "霍格沃茨特快列车",
                    "timestamp": "下午"
                }
            ]
        }
        ''',
        'scene': '''
        {
            "scene": {
                "id": "scene_event_ch1",
                "chapter": 1,
                "location": "对角巷",
                "time": "日",
                "description": "哈利在对角巷闲逛，购买开学用品",
                "actions": ["哈利走进奥利凡德魔杖店", "哈利挑选魔杖"],
                "dialogues": [],
                "character_ids": ["char_harry"]
            }
        }
        ''',
        'storyboard': '''
        {
            "shots": [
                {
                    "id": "scene_event_ch1_shot_1",
                    "scene_id": "scene_event_ch1",
                    "shot_number": 1,
                    "shot_type": "全景",
                    "description": "对角巷的全景，各种商店林立",
                    "camera_direction": "缓慢推进",
                    "duration_seconds": 3.0,
                    "audio_direction": "街道嘈杂声",
                    "characters_in_shot": ["char_harry"]
                },
                {
                    "id": "scene_event_ch1_shot_2",
                    "scene_id": "scene_event_ch1",
                    "shot_number": 2,
                    "shot_type": "近景",
                    "description": "哈利好奇地打量着周围的商店",
                    "camera_direction": "跟随移动",
                    "duration_seconds": 2.5,
                    "audio_direction": "哈利的脚步声",
                    "characters_in_shot": ["char_harry"]
                }
            ]
        }
        '''
    }


class MockLLMClientForPipeline(MockLLMClient):
    """为流水线测试设计的 Mock 客户端，按顺序返回不同响应"""

    def __init__(self, responses: dict):
        super().__init__()
        self.responses = responses
        self.call_count = 0
        self.call_sequence = []

    def chat(self, messages: list, temperature: float = 0.7) -> str:
        self.call_count += 1
        # 根据调用次数返回不同的响应
        if self.call_count == 1:
            self.call_sequence.append('characters')
            return self.responses['characters']
        elif self.call_count == 2:
            self.call_sequence.append('relationships')
            return self.responses['relationships']
        elif self.call_count == 3:
            self.call_sequence.append('timeline')
            return self.responses['timeline']
        elif self.call_count >= 4:
            # 剧本和分镜生成共用同一个响应
            self.call_sequence.append('scene/storyboard')
            return self.responses['scene']


# ==================== 测试用例 ====================

class TestNovelProcessor:
    """测试小说处理流水线"""

    def test_create_processor(self):
        """测试创建处理器"""
        processor = NovelProcessor()
        assert processor is not None

    def test_create_processor_with_mock_llm(self):
        """测试使用 Mock LLM 创建处理器"""
        mock_client = MockLLMClient("")
        processor = NovelProcessor(mock_client)
        assert processor is not None

    def test_process_full_pipeline_with_mock(self):
        """测试使用 Mock 数据执行完整流水线"""
        responses = get_full_pipeline_mock_responses()
        mock_client = MockLLMClientForPipeline(responses)
        processor = NovelProcessor(mock_client)

        novel_text = """
        第一章：对角巷

        哈利·波特是一个著名的年轻巫师，额头上有一道闪电形伤疤。
        他独自一人在对角巷闲逛，准备购买开学用品。

        第二章：霍格沃茨特快

        哈利在火车上遇到了罗恩·韦斯莱，一个红头发的男孩。
        两人很快就成为了好朋友。
        """

        result = processor.process(novel_text)

        # 验证结果
        assert result is not None
        assert "characters" in result
        assert "relationships" in result
        assert "timeline_events" in result
        assert "script_scenes" in result
        assert "storyboard_shots" in result

        # 验证提取到人物
        assert len(result["characters"]) > 0
        char_names = [c.name for c in result["characters"]]
        assert "哈利·波特" in char_names

    def test_process_generates_storyboard_shots_with_mock(self):
        """测试使用 Mock 数据处理生成分镜镜头"""
        responses = get_full_pipeline_mock_responses()
        mock_client = MockLLMClientForPipeline(responses)
        processor = NovelProcessor(mock_client)

        novel_text = """
        第一章：测试

        哈利·波特在对角巷闲逛。
        """

        result = processor.process(novel_text)
        assert len(result["storyboard_shots"]) > 0

    def test_process_returns_character_traits_with_mock(self):
        """测试使用 Mock 数据处理返回人物特质"""
        responses = get_full_pipeline_mock_responses()
        mock_client = MockLLMClientForPipeline(responses)
        processor = NovelProcessor(mock_client)

        novel_text = """
        第一章：介绍

        哈利·波特是一个年轻的巫师，他勇敢、忠诚，但有时有些冲动。
        """

        result = processor.process(novel_text)
        harry = next((c for c in result["characters"] if "哈利" in c.name), None)
        assert harry is not None
        # Mock 数据中应该有特质
        assert len(harry.traits) > 0 or len(harry.description) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
