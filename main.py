# -*- coding: utf-8 -*-
"""Phase 5: 系统流水线整合"""
from typing import Dict, List, Any, Optional
from models import Character, Relationship, TimelineEvent, ScriptScene, StoryboardShot
from extractor import CharacterExtractor, RelationshipExtractor, TimelineExtractor, LLMClient
from script_generator import ScriptGenerator
from storyboard_generator import StoryboardGenerator


class NovelProcessor:
    """小说处理器 - 完整的自动化处理流水线"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化小说处理器

        Args:
            llm_client: LLM 客户端实例，如果为 None 则各组件会使用默认的 MockLLMClient
        """
        # 初始化各个提取器和生成器
        self.character_extractor = CharacterExtractor(llm_client)
        self.relationship_extractor = RelationshipExtractor(llm_client)
        self.timeline_extractor = TimelineExtractor(llm_client)
        self.script_generator = ScriptGenerator(llm_client)
        self.storyboard_generator = StoryboardGenerator(llm_client)

    def process(self, novel_text: str) -> Dict[str, Any]:
        """
        处理小说文本，执行完整的流水线

        流程：
        1. 提取人物
        2. 提取关系
        3. 提取时间线事件
        4. 生成剧本场景
        5. 生成分镜镜头

        返回：包含所有结果的字典
        """
        # Phase 2: 信息提取
        characters = self.character_extractor.extract(novel_text)
        relationships = self.relationship_extractor.extract(novel_text)
        timeline_events = self.timeline_extractor.extract(novel_text)

        # Phase 3: 剧本生成
        script_scenes = self.script_generator.generate(timeline_events)

        # Phase 4: 分镜生成
        storyboard_shots = []
        for scene in script_scenes:
            shots = self.storyboard_generator.generate(scene)
            storyboard_shots.extend(shots)

        return {
            "characters": characters,
            "relationships": relationships,
            "timeline_events": timeline_events,
            "script_scenes": script_scenes,
            "storyboard_shots": storyboard_shots
        }


def main():
    """主函数 - 演示完整流程"""
    # 示例小说文本
    novel_text = """
    第一章：初遇

    张三是一个年轻的剑客，性格坚毅。
    在一个雨夜，张三走进了小镇的酒馆。

    第二章：结伴

    李四是个神秘的商人，为人聪明。
    张三和李四决定一起踏上旅程。
    他们成为了伙伴。

    第三章：敌人

    王五出现了，他是张三的仇敌。
    """

    # 创建处理器并执行
    processor = NovelProcessor()
    result = processor.process(novel_text)

    # 输出结果
    print("=" * 50)
    print("处理结果")
    print("=" * 50)

    print(f"\n【人物】共 {len(result['characters'])} 个:")
    for char in result["characters"]:
        print(f"  - {char.name}: {char.description[:30]}... (特质：{char.traits})")

    print(f"\n【关系】共 {len(result['relationships'])} 个:")
    for rel in result["relationships"]:
        print(f"  - {rel.type}: {rel.description}")

    print(f"\n【时间线事件】共 {len(result['timeline_events'])} 个:")
    for event in result["timeline_events"]:
        print(f"  - 第{event.chapter}章：{event.summary}")

    print(f"\n【剧本场景】共 {len(result['script_scenes'])} 个:")
    for scene in result["script_scenes"]:
        print(f"  - Scene {scene.id}: {scene.location} ({scene.time})")

    print(f"\n【分镜镜头】共 {len(result['storyboard_shots'])} 个:")
    for shot in result["storyboard_shots"][:5]:  # 只显示前 5 个
        print(f"  - {shot.shot_type}: {shot.description[:30]}...")

    if len(result["storyboard_shots"]) > 5:
        print(f"  ... 还有 {len(result['storyboard_shots']) - 5} 个镜头")

    return result


if __name__ == "__main__":
    main()
