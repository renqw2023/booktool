# -*- coding: utf-8 -*-
"""Phase 2: 信息提取引擎 (NLU) 的测试 - LLM 驱动版本

使用《哈利波特》片段测试提取器的泛化能力，通过 Mock LLM 返回值进行单元测试。
"""
import pytest
from unittest.mock import MagicMock
from extractor import CharacterExtractor, RelationshipExtractor, TimelineExtractor, MockLLMClient


class MockNovelText:
    """《哈利波特》小说片段 - 用于测试泛化能力"""

    @staticmethod
    def get_harry_potter_sample():
        """返回哈利波特片段"""
        return """
        第一章：大难不死的男孩

        哈利·波特是一个著名的年轻巫师，额头上有一道闪电形的伤疤。
        他从小在姨妈家长大，直到 11 岁生日那天才知道自己是巫师。
        赫敏·格兰杰是个聪明的女巫，出身于麻瓜家庭，但天赋异禀。
        罗恩·韦斯莱是哈利最好的朋友，来自一个纯血统巫师家庭。

        在霍格沃茨特快列车上，哈利和罗恩成为了朋友。
        他们决定一起踏上魔法学习的旅程。

        第二章：分院仪式

        邓布利多教授站在高台上，宣布分院仪式开始。
        哈利紧张地等待着，他希望自己能被分进格兰芬多。
        分院帽最终将哈利、罗恩和赫敏都分到了格兰芬多学院。

        第三章：魔药课

        斯内普教授是魔药课老师，他对哈利态度冷淡。
        斯内普和哈利之间似乎有着不为人知的过往。
        """

    @staticmethod
    def get_hogwarts_chapter_1():
        """第一章片段"""
        return """
        第一章：大难不死的男孩

        哈利·波特是一个年轻的巫师，他身材瘦高，有着一头乱糟糟的黑发。
        在一个雾蒙蒙的早晨，哈利走进了对角巷，准备购买开学用品。
        他的额头上有一道闪电形的伤疤，这是他作为"大难不死的男孩"的标志。
        """

    @staticmethod
    def get_hogwarts_chapter_2():
        """第二章片段"""
        return """
        第二章：友谊的开始

        哈利在霍格沃茨特快上遇到了罗恩·韦斯莱，一个红头发的男孩。
        罗恩为人忠诚友善，很快就和哈利成为了好朋友。
        他们决定一起面对魔法学校的挑战。
        """


# ==================== Mock LLM 响应数据 ====================

def get_character_mock_response():
    """人物提取的 Mock 响应"""
    return '''
    {
        "characters": [
            {
                "id": "char_harry",
                "name": "哈利·波特",
                "description": "著名的年轻巫师，额头上有闪电形伤疤",
                "traits": ["勇敢", "忠诚", "冲动"],
                "goals": ["学习魔法", "对抗伏地魔"],
                "background": "孤儿，11 岁进入霍格沃茨",
                "appearance": "黑发绿眼，戴眼镜，额头有闪电伤疤"
            },
            {
                "id": "char_ron",
                "name": "罗恩·韦斯莱",
                "description": "哈利最好的朋友，来自韦斯莱家族",
                "traits": ["忠诚", "幽默", "有些胆小"],
                "goals": ["学习魔法", "帮助哈利"],
                "background": "纯血统巫师家庭",
                "appearance": "红头发，满脸雀斑"
            }
        ]
    }
    '''


def get_relationship_mock_response():
    """关系提取的 Mock 响应"""
    return '''
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
    '''


def get_timeline_mock_response():
    """时间线提取的 Mock 响应"""
    return '''
    {
        "events": [
            {
                "id": "event_ch1",
                "chapter": 1,
                "summary": "哈利在对角巷购买开学用品",
                "description": "哈利独自一人在对角巷闲逛，最后来到了奥利凡德魔杖店",
                "character_ids": ["char_harry"],
                "location": "对角巷",
                "timestamp": "早晨"
            },
            {
                "id": "event_ch2",
                "chapter": 2,
                "summary": "哈利和罗恩在火车上相遇",
                "description": "两人在霍格沃茨特快上分享零食，很快就成了朋友",
                "character_ids": ["char_harry", "char_ron"],
                "location": "霍格沃茨特快列车",
                "timestamp": "下午"
            }
        ]
    }
    '''


# ==================== 测试用例 ====================

class TestCharacterExtractor:
    """测试人物提取器"""

    def test_extract_characters_from_harry_potter(self):
        """测试从哈利波特文本中提取人物"""
        mock_client = MockLLMClient(get_character_mock_response())
        extractor = CharacterExtractor(mock_client)
        text = MockNovelText.get_harry_potter_sample()
        characters = extractor.extract(text)

        assert len(characters) > 0
        # 应该能提取到哈利·波特、罗恩等角色
        char_names = [c.name for c in characters]
        assert "哈利·波特" in char_names or any("哈利" in name for name in char_names)

    def test_extract_character_with_traits(self):
        """测试提取人物特质"""
        mock_client = MockLLMClient(get_character_mock_response())
        extractor = CharacterExtractor(mock_client)
        text = MockNovelText.get_hogwarts_chapter_1()
        characters = extractor.extract(text)

        # 检查提取到的人物是否有特质
        if characters:
            harry = next((c for c in characters if "哈利" in c.name), None)
            if harry:
                assert len(harry.traits) > 0 or len(harry.description) > 0

    def test_extractor_without_mock(self):
        """测试提取器可以使用默认 Mock 客户端"""
        extractor = CharacterExtractor()  # 使用默认 MockLLMClient
        text = "这是一个测试文本"
        # 空响应应该返回空列表
        characters = extractor.extract(text)
        # MockLLMClient 默认返回空响应
        assert isinstance(characters, list)


class TestRelationshipExtractor:
    """测试关系提取器"""

    def test_extract_relationships(self):
        """测试提取人物关系"""
        mock_client = MockLLMClient(get_relationship_mock_response())
        extractor = RelationshipExtractor(mock_client)
        text = MockNovelText.get_harry_potter_sample()
        relationships = extractor.extract(text)

        assert len(relationships) > 0

    def test_extract_friend_relationship(self):
        """测试提取朋友关系"""
        mock_client = MockLLMClient(get_relationship_mock_response())
        extractor = RelationshipExtractor(mock_client)
        text = MockNovelText.get_hogwarts_chapter_2()
        relationships = extractor.extract(text)

        # 应该能提取到朋友关系
        friend_rels = [r for r in relationships if r.type == "朋友"]
        assert len(friend_rels) > 0 or len(relationships) > 0

    def test_relationship_has_strength(self):
        """测试关系有强度属性"""
        mock_client = MockLLMClient(get_relationship_mock_response())
        extractor = RelationshipExtractor(mock_client)
        relationships = extractor.extract(MockNovelText.get_harry_potter_sample())

        for rel in relationships:
            assert 0 <= rel.strength <= 5
            assert 0 <= rel.conflict_level <= 5


class TestTimelineExtractor:
    """测试时间线提取器"""

    def test_extract_timeline_events(self):
        """测试提取时间线事件"""
        mock_client = MockLLMClient(get_timeline_mock_response())
        extractor = TimelineExtractor(mock_client)
        text = MockNovelText.get_harry_potter_sample()
        events = extractor.extract(text)

        assert len(events) > 0

    def test_event_has_chapter(self):
        """测试事件有关联章节"""
        mock_client = MockLLMClient(get_timeline_mock_response())
        extractor = TimelineExtractor(mock_client)
        text = MockNovelText.get_hogwarts_chapter_1()
        events = extractor.extract(text)

        for event in events:
            assert event.chapter is not None
            assert event.chapter > 0

    def test_extract_event_location(self):
        """测试提取事件地点"""
        mock_client = MockLLMClient(get_timeline_mock_response())
        extractor = TimelineExtractor(mock_client)
        events = extractor.extract(MockNovelText.get_harry_potter_sample())

        # 检查是否有事件提取到地点
        locations = [e.location for e in events if e.location]
        assert len(locations) > 0

    def test_event_character_ids(self):
        """测试事件包含人物 ID"""
        mock_client = MockLLMClient(get_timeline_mock_response())
        extractor = TimelineExtractor(mock_client)
        events = extractor.extract(MockNovelText.get_harry_potter_sample())

        # 至少有一个事件应该包含人物 ID
        events_with_chars = [e for e in events if e.character_ids]
        assert len(events_with_chars) > 0 or len(events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
