# -*- coding: utf-8 -*-
"""Phase 5: 系统流水线整合测试"""
import pytest
from main import NovelProcessor
from models import Character, Relationship, TimelineEvent, ScriptScene, StoryboardShot


class TestNovelProcessor:
    """测试小说处理流水线"""

    def test_create_processor(self):
        """测试创建处理器"""
        processor = NovelProcessor()
        assert processor is not None

    def test_process_full_pipeline(self):
        """测试完整的处理流水线"""
        processor = NovelProcessor()
        novel_text = """
        第一章：初遇

        张三是一个年轻的剑客，性格坚毅。
        在一个雨夜，张三走进了小镇的酒馆。

        第二章：结伴

        李四是个神秘的商人，为人聪明。
        张三和李四决定一起踏上旅程。
        他们成为了伙伴。
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
        assert "张三" in char_names
        assert "李四" in char_names

    def test_process_generates_storyboard_shots(self):
        """测试处理生成分镜镜头"""
        processor = NovelProcessor()
        novel_text = """
        第一章：测试

        张三在酒馆里喝酒。
        """

        result = processor.process(novel_text)
        assert len(result["storyboard_shots"]) > 0

    def test_process_multiple_chapters(self):
        """测试处理多章节小说"""
        processor = NovelProcessor()
        # 使用简单文本，不依赖章节标题分割
        novel_text = """
        第一章：出发
        张三从家里出发。他走啊走，到了酒馆。
        第二章：到达
        张三到达了酒馆。他见到了李四。
        第三章：相遇
        张三遇到了李四。他们开始谈话。
        """

        result = processor.process(novel_text)
        # 应该提取到多个人物
        assert len(result["characters"]) >= 2

    def test_process_returns_character_traits(self):
        """测试处理返回人物特质"""
        processor = NovelProcessor()
        novel_text = """
        第一章：介绍

        张三是一个年轻的剑客，性格坚毅，为人正直。
        """

        result = processor.process(novel_text)
        zhangsan = next((c for c in result["characters"] if c.name == "张三"), None)
        assert zhangsan is not None
        assert len(zhangsan.traits) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
