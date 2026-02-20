"""Phase 2: 信息提取引擎 (NLU) 的测试"""
import pytest
from extractor import CharacterExtractor, RelationshipExtractor, TimelineExtractor


class MockNovelText:
    """硬编码的小说 mock 数据"""

    @staticmethod
    def get_sample_text():
        """返回示例小说文本"""
        return """
        第一章：初遇

        张三是一个年轻的剑客，他身材高大，性格坚毅。
        李四是个神秘的商人，为人聪明但贪婪。

        在一个雨夜，张三走进了小镇的酒馆。他看到了李四坐在角落里。
        两人对视一眼，仿佛命中注定要相遇。

        第二章：结伴同行

        张三和李四决定一起踏上寻找宝藏的旅程。
        他们成为了志同道合的伙伴。

        第三章：遭遇敌人

        王五出现了，他是张三的生死仇敌，冲突达到了顶点。
        王五是个凶恶的强盗，一直想要报复张三。
        """

    @staticmethod
    def get_chapter_1():
        return """
        第一章：初遇

        张三是一个年轻的剑客，他身材高大，性格坚毅。
        在一个雨夜，张三走进了小镇的酒馆。
        天色已晚，酒馆里人声鼎沸。
        """

    @staticmethod
    def get_chapter_2():
        return """
        第二章：结伴同行

        张三看到了李四，一个神秘的商人。
        李四为人聪明但贪婪。
        两人决定一起踏上旅程。
        他们成为了朋友。
        """


class TestCharacterExtractor:
    """测试人物提取器"""

    def test_extract_characters_from_text(self):
        """测试从文本中提取人物"""
        extractor = CharacterExtractor()
        text = MockNovelText.get_sample_text()
        characters = extractor.extract(text)

        assert len(characters) > 0
        # 应该能提取到张三、李四、王五
        char_names = [c.name for c in characters]
        assert "张三" in char_names
        assert "李四" in char_names

    def test_extract_character_with_traits(self):
        """测试提取人物特质"""
        extractor = CharacterExtractor()
        text = MockNovelText.get_chapter_1()
        characters = extractor.extract(text)

        # 张三应该有"坚毅"的特质
        zhangsan = next((c for c in characters if c.name == "张三"), None)
        assert zhangsan is not None
        assert "坚毅" in zhangsan.traits or "年轻" in zhangsan.traits


class TestRelationshipExtractor:
    """测试关系提取器"""

    def test_extract_relationships(self):
        """测试提取人物关系"""
        extractor = RelationshipExtractor()
        text = MockNovelText.get_sample_text()
        relationships = extractor.extract(text)

        assert len(relationships) > 0

    def test_extract_friend_relationship(self):
        """测试提取朋友关系"""
        extractor = RelationshipExtractor()
        text = MockNovelText.get_chapter_2()
        relationships = extractor.extract(text)

        # 应该能提取到张三和李四的朋友关系
        friend_rels = [r for r in relationships if r.type == "朋友" or r.type == "伙伴"]
        assert len(friend_rels) > 0


class TestTimelineExtractor:
    """测试时间线提取器"""

    def test_extract_timeline_events(self):
        """测试提取时间线事件"""
        extractor = TimelineExtractor()
        text = MockNovelText.get_sample_text()
        events = extractor.extract(text)

        assert len(events) > 0

    def test_event_has_chapter(self):
        """测试事件有关联章节"""
        extractor = TimelineExtractor()
        text = MockNovelText.get_chapter_1()
        events = extractor.extract(text)

        for event in events:
            assert event.chapter is not None

    def test_extract_event_location(self):
        """测试提取事件地点"""
        extractor = TimelineExtractor()
        text = MockNovelText.get_chapter_1()
        events = extractor.extract(text)

        # 应该能提取到"酒馆"这个地点
        locations = [e.location for e in events if e.location]
        assert any("酒馆" in loc for loc in locations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
