"""Phase 2: 信息提取引擎 (NLU)"""
import re
from typing import List, Optional
from models import Character, Relationship, TimelineEvent


# 人名列表
NAMES = ["张三", "李四", "王五", "赵六"]


class CharacterExtractor:
    """人物提取器"""

    def __init__(self):
        pass

    def extract(self, text: str) -> List[Character]:
        """从文本中提取人物"""
        characters = []
        seen_names = set()

        # 查找所有人名
        for name in NAMES:
            if name in text and name not in seen_names:
                seen_names.add(name)

                # 获取上下文
                idx = text.find(name)
                start = max(0, idx - 50)
                end = min(len(text), idx + 100)
                context = text[start:end]

                # 提取特质
                traits = self._extract_traits(context)

                # 提取描述
                description = self._extract_description(context, name)

                char = Character(
                    id=f"char_{name}",
                    name=name,
                    description=description,
                    traits=traits
                )
                characters.append(char)

        return characters

    def _extract_traits(self, context: str) -> List[str]:
        """从上下文中提取特质"""
        traits = []

        # 简单方法：直接查找关键词后的内容
        # 匹配 "性格 XX" 模式
        for keyword in ["性格", "为人"]:
            idx = context.find(keyword)
            if idx != -1:
                # 获取关键词后的 2-4 个字符
                start = idx + len(keyword)
                end = min(start + 4, len(context))
                trait = context[start:end].strip()
                # 去除标点
                for char in ".,.!?.,":
                    trait = trait.replace(char, "")
                if trait and len(trait) >= 1 and trait not in traits:
                    traits.append(trait)

        # 匹配 "是个 XX 的" 模式
        for pattern in ["是个", "是一个"]:
            idx = context.find(pattern)
            if idx != -1:
                start = idx + len(pattern)
                end = context.find("的", start)
                if end != -1 and end - start <= 6:
                    trait = context[start:end].strip()
                    if trait and trait not in traits:
                        traits.append(trait)

        return traits

    def _extract_description(self, context: str, name: str) -> str:
        """提取人物描述"""
        # 简单返回包含名字的句子
        sentences = re.split(r"[。.!?]", context)
        for sentence in sentences:
            if name in sentence:
                return sentence.strip()
        return ""


class RelationshipExtractor:
    """关系提取器"""

    def __init__(self):
        self.relationship_keywords = {
            "朋友": ["朋友", "伙伴", "同伴", "一起", "结伴"],
            "敌人": ["敌人", "仇敌", "仇人", "报复", "凶恶"],
            "伙伴": ["伙伴", "同行", "一起", "结伴"],
        }

    def extract(self, text: str) -> List[Relationship]:
        """从文本中提取关系"""
        relationships = []

        # 检测出现的人物
        names = self._find_names(text)

        if len(names) < 2:
            return relationships

        # 分析关系类型
        rel_type = self._determine_relationship_type(text)

        if rel_type:
            # 简单处理：将前两个人名关联
            rel = Relationship(
                id=f"rel_{names[0]}_{names[1]}",
                character_id_1=f"char_{names[0]}",
                character_id_2=f"char_{names[1]}",
                type=rel_type,
                description=f"{names[0]} 和 {names[1]} 是{rel_type}关系"
            )
            relationships.append(rel)

        return relationships

    def _find_names(self, text: str) -> List[str]:
        """找出文本中的人名"""
        result = []
        for name in NAMES:
            if name in text and name not in result:
                result.append(name)
        return result

    def _determine_relationship_type(self, text: str) -> Optional[str]:
        """确定关系类型"""
        for rel_type, keywords in self.relationship_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return rel_type
        return None


class TimelineExtractor:
    """时间线提取器"""

    def __init__(self):
        self.chapter_pattern = r"第 ([一二三四五六七八九十\d]+) 章"
        self.location_keywords = ["酒馆", "小镇", "宝藏", "旅程"]

    def extract(self, text: str) -> List[TimelineEvent]:
        """从文本中提取时间线事件"""
        events = []

        # 按章节分割文本
        chapters = re.split(r"(第 [一二三四五六七八九十\d]+ 章)", text)

        current_chapter = 1
        current_title = ""

        for i, chunk in enumerate(chapters):
            if re.match(self.chapter_pattern, chunk):
                # 这是章节标题
                current_chapter = self._parse_chapter_number(chunk) or current_chapter
                current_title = chunk.strip()
            elif chunk.strip() and current_chapter:
                # 这是章节内容 - 为每个章节创建一个事件
                event = self._create_event_from_chunk(current_chapter, chunk, current_title)
                if event:
                    events.append(event)
                # 重置 current_chapter 以防止重复添加
                # 只在找到下一个章节标题时才更新

        return events

    def _parse_chapter_number(self, title: str) -> Optional[int]:
        """解析章号"""
        # 简单处理中文数字
        chinese_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        for char in title:
            if char in chinese_nums:
                return chinese_nums[char]
            elif char.isdigit():
                return int(char)
        return None

    def _create_event_from_chunk(self, chapter: int, chunk: str, title: str = "") -> Optional[TimelineEvent]:
        """从文本块创建事件"""
        # 提取摘要（第一句）
        sentences = re.split(r"[。.!?]", chunk)
        summary = sentences[0].strip()[:50] if sentences else ""

        if not summary:
            return None

        # 提取地点
        location = None
        for loc in self.location_keywords:
            if loc in chunk:
                location = loc
                break

        # 提取人物
        characters = []
        for name in NAMES:
            if name in chunk and name not in characters:
                characters.append(name)

        return TimelineEvent(
            id=f"event_ch{chapter}",
            chapter=chapter,
            summary=summary,
            description=chunk.strip()[:100],
            character_ids=[f"char_{c}" for c in characters],
            location=location
        )


if __name__ == "__main__":
    # 简单测试
    extractor = CharacterExtractor()
    text = "张三是一个年轻的剑客，性格坚毅。"
    chars = extractor.extract(text)
    for char in chars:
        print(f"人物：{char.name}, 特质：{char.traits}")
