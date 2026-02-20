# -*- coding: utf-8 -*-
"""Phase 5: 系统流水线整合 - 支持长文本处理

本模块整合了长文本分块引擎和原有的处理流水线，支持：
1. 按章节智能切分长篇小说
2. 跨章节记忆合并
3. 检查点保存与恢复
4. 命令行参数配置
5. 真实 LLM API 调用
"""
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from models import Character, Relationship, TimelineEvent, ScriptScene, StoryboardShot
from extractor import (
    CharacterExtractor, RelationshipExtractor, TimelineExtractor,
    LLMClient, OpenAICompatibleClient, MockLLMClient
)
from script_generator import ScriptGenerator
from storyboard_generator import StoryboardGenerator
from chunking_engine import NovelReader, MemoryBank, ChunkingPipeline, TextChunk
from vector_store import VectorMemoryBank


class NovelProcessor:
    """小说处理器 - 完整的自动化处理流水线"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化小说处理器

        Args:
            llm_client: LLM 客户端实例，如果为 None 则使用 OpenAICompatibleClient
        """
        # 使用传入的客户端或创建默认的 OpenAI 客户端
        self.llm_client = llm_client or OpenAICompatibleClient(
            api_key=os.environ.get("LLM_API_KEY"),
            base_url=os.environ.get("LLM_BASE_URL"),
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini")
        )

        # 初始化各个提取器和生成器
        self.character_extractor = CharacterExtractor(self.llm_client)
        self.relationship_extractor = RelationshipExtractor(self.llm_client)
        self.timeline_extractor = TimelineExtractor(self.llm_client)
        self.script_generator = ScriptGenerator(self.llm_client)
        self.storyboard_generator = StoryboardGenerator(self.llm_client)

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


class LongNovelProcessor:
    """长篇小说处理器 - 支持分块处理和记忆合并"""

    def __init__(self, llm_client: Optional[LLMClient] = None,
                 max_chunk_size: int = 8000,
                 enable_memory_merge: bool = True,
                 enable_checkpoint: bool = True,
                 checkpoint_interval: int = 5,
                 use_vector_memory: bool = True):
        """
        初始化长篇小说处理器

        Args:
            llm_client: LLM 客户端实例
            max_chunk_size: 单个块的最大字符数
            enable_memory_merge: 是否启用记忆合并
            enable_checkpoint: 是否启用检查点保存
            checkpoint_interval: 检查点保存间隔（每 N 个章节保存一次）
            use_vector_memory: 是否使用向量化记忆银行（解决记忆膨胀问题）
        """
        self.llm_client = llm_client or OpenAICompatibleClient(
            api_key=os.environ.get("LLM_API_KEY"),
            base_url=os.environ.get("LLM_BASE_URL"),
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini")
        )

        self.enable_memory_merge = enable_memory_merge
        self.enable_checkpoint = enable_checkpoint
        self.checkpoint_interval = checkpoint_interval
        self.use_vector_memory = use_vector_memory

        # 初始化分块流水线
        self.chunking_pipeline = ChunkingPipeline(max_chunk_size=max_chunk_size)

        # 初始化记忆银行（使用向量化版本）
        self.memory_bank = VectorMemoryBank() if use_vector_memory else MemoryBank()

        # 初始化提取器和生成器（传入记忆银行）
        self.character_extractor = CharacterExtractor(self.llm_client)
        self.relationship_extractor = RelationshipExtractor(self.llm_client)
        self.timeline_extractor = TimelineExtractor(self.llm_client)
        self.script_generator = ScriptGenerator(self.llm_client, self.memory_bank)
        self.storyboard_generator = StoryboardGenerator(self.llm_client, self.memory_bank)

        # 结果存储
        self.all_characters: List[Character] = []
        self.all_relationships: List[Relationship] = []
        self.all_timeline_events: List[TimelineEvent] = []
        self.all_script_scenes: List[ScriptScene] = []
        self.all_storyboard_shots: List[StoryboardShot] = []

    def load_novel(self, file_path: str) -> List[TextChunk]:
        """加载小说文件并切分"""
        print(f"[INFO] 正在读取小说文件：{file_path}")
        chunks = self.chunking_pipeline.load_novel(file_path)
        print(f"[OK] 识别到 {len(chunks)} 个章节")
        for chunk in chunks:
            title = chunk.chapter_title or f"第{chunk.chapter_number}章"
            print(f"  - 第{chunk.chapter_number}章：{title} ({chunk.word_count} 字)")
        return chunks

    def _extract_with_memory(self, chunk: TextChunk, context: str) -> Dict[str, Any]:
        """使用上下文记忆进行提取"""
        # 将记忆上下文添加到文本前面
        full_text = context + "\n\n" + chunk.content

        # 提取人物、关系、时间线
        characters = self.character_extractor.extract(full_text)
        relationships = self.relationship_extractor.extract(full_text)
        timeline_events = self.timeline_extractor.extract(chunk.content)

        # 修正事件的章节号
        for event in timeline_events:
            event.chapter = chunk.chapter_number

        return {
            "characters": characters,
            "relationships": relationships,
            "timeline_events": timeline_events
        }

    def _merge_characters(self, new_characters: List[Character], chapter_num: int) -> None:
        """将新提取的人物合并到记忆银行"""
        for char in new_characters:
            if self.use_vector_memory:
                # 使用向量化记忆银行
                self.memory_bank.add_character(
                    character_id=char.id,
                    name=char.name,
                    traits=char.traits,
                    goals=char.goals,
                    descriptions=[char.description] if char.description else [],
                    appearances=[char.appearance] if char.appearance else [],
                    metadata={"chapter": chapter_num}
                )
            else:
                # 使用传统记忆银行
                from chunking_engine import CharacterMemory

                memory = CharacterMemory(
                    character_id=char.id,
                    name=char.name,
                    descriptions=[char.description] if char.description else [],
                    traits=char.traits,
                    goals=char.goals,
                    background_fragments=[char.background] if char.background else [],
                    appearance_fragments=[char.appearance] if char.appearance else [],
                    first_appearance_chapter=chapter_num,
                    last_appearance_chapter=chapter_num,
                    mention_count=1
                )
                self.chunking_pipeline.memory_bank.add_character_memory(memory)

    def _merge_relationships(self, new_relationships: List[Relationship]) -> None:
        """合并关系"""
        for rel in new_relationships:
            rel_desc = f"{rel.character_id_1} 与 {rel.character_id_2}: {rel.type}"
            if self.use_vector_memory:
                self.memory_bank.add_relationship(rel_desc)
            else:
                if rel_desc not in self.chunking_pipeline.memory_bank.global_context["relationships"]:
                    self.chunking_pipeline.memory_bank.global_context["relationships"].append(rel_desc)

    def process_chunk(self, chunk: TextChunk) -> Dict[str, Any]:
        """处理单个章节"""
        title = chunk.chapter_title or f"第{chunk.chapter_number}章"
        print(f"\n[PROCESS] 处理第{chunk.chapter_number}章：{title}")

        # 获取带上下文的文本
        chunk_data, context = self.chunking_pipeline.get_chunk_with_context(
            self.chunking_pipeline.reader.chunks.index(chunk)
        )

        # 提取信息
        print("  → 提取人物、关系、时间线...")
        extracted = self._extract_with_memory(chunk, context)

        # 合并到记忆银行
        if self.enable_memory_merge:
            self._merge_characters(extracted["characters"], chunk.chapter_number)
            self._merge_relationships(extracted["relationships"])

        # 构建记忆上下文（用于生成剧本和分镜）
        memory_context = ""
        if self.use_vector_memory:
            memory_context = self.memory_bank.to_context_prompt(chunk.content)
        else:
            memory_context = self.chunking_pipeline.memory_bank.to_context_prompt()

        # 生成剧本场景（注入记忆上下文）
        print("  → 生成剧本场景...")
        script_scenes = self.script_generator.generate(
            extracted["timeline_events"],
            memory_context=memory_context
        )

        # 生成分镜镜头（注入记忆上下文）
        print("  → 生成分镜镜头...")
        storyboard_shots = []
        for scene in script_scenes:
            shots = self.storyboard_generator.generate(
                scene,
                memory_context=memory_context
            )
            storyboard_shots.extend(shots)

        # 累积结果
        self.all_characters.extend(extracted["characters"])
        self.all_relationships.extend(extracted["relationships"])
        self.all_timeline_events.extend(extracted["timeline_events"])
        self.all_script_scenes.extend(script_scenes)
        self.all_storyboard_shots.extend(storyboard_shots)

        # 标记已处理
        self.chunking_pipeline.mark_processed(self.chunking_pipeline.reader.chunks.index(chunk))

        return {
            "chapter": chunk.chapter_number,
            "characters_count": len(extracted["characters"]),
            "relationships_count": len(extracted["relationships"]),
            "events_count": len(extracted["timeline_events"]),
            "scenes_count": len(script_scenes),
            "shots_count": len(storyboard_shots)
        }

    def process_novel(self, file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        处理整部小说

        Args:
            file_path: 小说文件路径
            output_path: 输出文件路径（可选）

        Returns:
            处理结果字典
        """
        start_time = datetime.now()
        chunks = self.load_novel(file_path)

        print(f"\n[START] 开始处理长篇小说...")
        print(f"   启用记忆合并：{self.enable_memory_merge}")
        print(f"   启用检查点：{self.enable_checkpoint}")

        chapter_results = []
        for i, chunk in enumerate(chunks):
            result = self.process_chunk(chunk)
            chapter_results.append(result)

            # 定期保存检查点
            if self.enable_checkpoint and (i + 1) % self.checkpoint_interval == 0:
                checkpoint_path = f".checkpoint_ch{chunk.chapter_number}.json"
                self.chunking_pipeline.save_checkpoint(checkpoint_path)
                print(f"  [OK] 已保存检查点：{checkpoint_path}")

        # 保存最终记忆状态
        if self.enable_checkpoint:
            self.chunking_pipeline.save_checkpoint("memory_bank_final.json")
            print(f"\n✓ 已保存最终记忆状态：memory_bank_final.json")

        end_time = datetime.now()
        duration = end_time - start_time

        # 生成最终结果
        final_result = {
            "metadata": {
                "source_file": file_path,
                "total_chapters": len(chunks),
                "processing_duration": str(duration),
                "completed_at": end_time.isoformat()
            },
            "statistics": {
                "total_characters": len(set(c.id for c in self.all_characters)),
                "total_relationships": len(self.all_relationships),
                "total_events": len(self.all_timeline_events),
                "total_scenes": len(self.all_script_scenes),
                "total_shots": len(self.all_storyboard_shots)
            },
            "chapter_results": chapter_results,
            "characters": [self._char_to_dict(c) for c in self.all_characters],
            "relationships": [self._rel_to_dict(r) for r in self.all_relationships],
            "timeline_events": [self._event_to_dict(e) for e in self.all_timeline_events],
            "script_scenes": [self._scene_to_dict(s) for s in self.all_script_scenes],
            "storyboard_shots": [self._shot_to_dict(s) for s in self.all_storyboard_shots]
        }

        # 保存结果
        if output_path:
            self._save_result(final_result, output_path)

        # 打印摘要
        self._print_summary(final_result, duration)

        return final_result

    def _char_to_dict(self, c: Character) -> Dict:
        return {
            "id": c.id, "name": c.name, "description": c.description,
            "traits": c.traits, "goals": c.goals,
            "background": c.background, "appearance": c.appearance
        }

    def _rel_to_dict(self, r: Relationship) -> Dict:
        return {
            "id": r.id, "character_id_1": r.character_id_1,
            "character_id_2": r.character_id_2, "type": r.type,
            "description": r.description, "conflict_level": r.conflict_level,
            "strength": r.strength
        }

    def _event_to_dict(self, e: TimelineEvent) -> Dict:
        return {
            "id": e.id, "chapter": e.chapter, "summary": e.summary,
            "description": e.description, "character_ids": e.character_ids,
            "location": e.location, "timestamp": e.timestamp
        }

    def _scene_to_dict(self, s: ScriptScene) -> Dict:
        return {
            "id": s.id, "chapter": s.chapter, "location": s.location,
            "time": s.time, "description": s.description,
            "actions": s.actions, "dialogues": s.dialogues,
            "character_ids": s.character_ids
        }

    def _shot_to_dict(self, s: StoryboardShot) -> Dict:
        return {
            "id": s.id, "scene_id": s.scene_id, "shot_number": s.shot_number,
            "shot_type": s.shot_type, "description": s.description,
            "camera_direction": s.camera_direction,
            "duration_seconds": s.duration_seconds,
            "audio_direction": s.audio_direction,
            "characters_in_shot": s.characters_in_shot
        }

    def _save_result(self, result: Dict, output_path: str) -> None:
        """保存结果到文件"""
        indent = 2 if os.environ.get("OUTPUT_INDENT", "true").lower() == "true" else None
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=indent)
        print(f"\n[SAVE] 结果已保存到：{output_path}")

    def _print_summary(self, result: Dict, duration: datetime) -> None:
        """打印处理摘要"""
        print("\n" + "=" * 60)
        print("处理完成！")
        print("=" * 60)
        print(f"\n[STATS] 统计信息:")
        print(f"   处理时长：{duration}")
        print(f"   总章节数：{result['statistics']['total_chapters']}")
        print(f"   人物数量：{result['statistics']['total_characters']}")
        print(f"   关系数量：{result['statistics']['total_relationships']}")
        print(f"   时间线事件：{result['statistics']['total_events']}")
        print(f"   剧本场景：{result['statistics']['total_scenes']}")
        print(f"   分镜镜头：{result['statistics']['total_shots']}")


def create_llm_client() -> LLMClient:
    """根据环境变量创建 LLM 客户端"""
    api_key = os.environ.get("LLM_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        print("⚠️  未检测到 LLM_API_KEY，将使用 Mock 客户端进行测试")
        return MockLLMClient('{"characters": [], "relationships": [], "events": []}')

    # 启用 JSON 结构化输出模式
    return OpenAICompatibleClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        use_json_mode=True
    )


def main():
    """主函数 - 命令行入口"""
    parser = argparse.ArgumentParser(
        description="小说自动化处理系统 - 从小说文本生成剧本和分镜",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理小说文件并输出结果
  python main.py --file novel.txt --output result.json

  # 使用自定义配置
  python main.py --file novel.txt --output result.json --chunk-size 10000 --no-checkpoint

  # 仅处理单个章节（测试用）
  python main.py --file novel.txt --chapter 1
        """
    )

    parser.add_argument(
        "--file", "-f",
        type=str,
        required=True,
        help="小说文件路径（.txt 格式）"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出文件路径（.json 格式）"
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=8000,
        help="单个处理块的最大字符数（默认 8000）"
    )

    parser.add_argument(
        "--no-memory-merge",
        action="store_true",
        help="禁用记忆合并功能"
    )

    parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="禁用检查点保存"
    )

    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=5,
        help="检查点保存间隔（默认每 5 章保存一次）"
    )

    parser.add_argument(
        "--chapter",
        type=int,
        default=None,
        help="仅处理指定章节（用于测试）"
    )

    args = parser.parse_args()

    # 检查文件是否存在
    if not os.path.exists(args.file):
        print(f"[ERROR] 错误：文件不存在 - {args.file}")
        sys.exit(1)

    # 创建 LLM 客户端
    llm_client = create_llm_client()

    # 创建处理器
    processor = LongNovelProcessor(
        llm_client=llm_client,
        max_chunk_size=args.chunk_size,
        enable_memory_merge=not args.no_memory_merge,
        enable_checkpoint=not args.no_checkpoint,
        checkpoint_interval=args.checkpoint_interval
    )

    # 处理小说
    try:
        result = processor.process_novel(
            file_path=args.file,
            output_path=args.output
        )
        print("\n[OK] 处理完成！")
    except Exception as e:
        print(f"\n[ERROR] 处理失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()