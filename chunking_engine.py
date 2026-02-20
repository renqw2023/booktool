# -*- coding: utf-8 -*-
"""长文本分块与上下文记忆引擎 (Chunking & Memory Pipeline)

本模块解决长小说处理的两个核心问题：
1. 按章节/场景智能切分文本，避免 Token 超出上下文限制
2. 跨章节记忆合并，确保人物特征在不同章节间平滑累积
"""
import re
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from models import Character


@dataclass
class TextChunk:
    """文本块 - 代表小说的一个章节或场景"""
    chapter_number: int
    chapter_title: Optional[str]
    content: str
    start_position: int
    end_position: int
    word_count: int

    def __post_init__(self):
        if self.word_count == 0:
            self.word_count = len(self.content)


@dataclass
class CharacterMemory:
    """人物记忆 - 用于跨章节累积人物信息"""
    character_id: str
    name: str
    descriptions: List[str] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    background_fragments: List[str] = field(default_factory=list)
    appearance_fragments: List[str] = field(default_factory=list)
    first_appearance_chapter: int = 0
    last_appearance_chapter: int = 0
    mention_count: int = 0

    def merge(self, other: 'CharacterMemory') -> 'CharacterMemory':
        """合并另一个人物记忆到当前记忆"""
        merged = CharacterMemory(
            character_id=self.character_id,
            name=self.name,
            descriptions=self.descriptions.copy(),
            traits=self.traits.copy(),
            goals=self.goals.copy(),
            background_fragments=self.background_fragments.copy(),
            appearance_fragments=self.appearance_fragments.copy(),
            first_appearance_chapter=min(self.first_appearance_chapter, other.first_appearance_chapter),
            last_appearance_chapter=max(self.last_appearance_chapter, other.last_appearance_chapter),
            mention_count=self.mention_count + other.mention_count
        )

        # 合并描述（去重）
        for desc in other.descriptions:
            if desc not in merged.descriptions:
                merged.descriptions.append(desc)

        # 合并特质（去重）
        for trait in other.traits:
            if trait not in merged.traits:
                merged.traits.append(trait)

        # 合并目标（去重）
        for goal in other.goals:
            if goal not in merged.goals:
                merged.goals.append(goal)

        # 合并背景片段
        merged.background_fragments.extend(other.background_fragments)
        merged.appearance_fragments.extend(other.appearance_fragments)

        return merged

    def to_character(self) -> Character:
        """转换为 Character 实体"""
        return Character(
            id=self.character_id,
            name=self.name,
            description="; ".join(self.descriptions) if self.descriptions else "",
            traits=list(set(self.traits)),
            goals=list(set(self.goals)),
            background="; ".join(self.background_fragments) if self.background_fragments else None,
            appearance="; ".join(self.appearance_fragments) if self.appearance_fragments else None
        )


class NovelReader:
    """小说阅读器 - 负责读取和切分小说文本"""

    # 章节匹配模式（支持多种格式）
    CHAPTER_PATTERNS = [
        r'(?:第\s*([零一二三四五六七八九十百千万\d]+)\s*章 |Chapter\s+(\d+)|CHAPTER\s+(\d+))',
        r'(?:第\s*([零一二三四五六七八九十百千万\d]+)\s* 回 |Episode\s+(\d+))',
        r'(?:卷\s*([零一二三四五六七八九十百千万\d]+)\s*|Book\s+(\d+))',
    ]

    # 中文数字转换
    CHINESE_NUMS = {
        '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '百': 100, '千': 1000, '万': 10000
    }

    def __init__(self, max_chunk_size: int = 8000, overlap_size: int = 500):
        """
        初始化小说阅读器

        Args:
            max_chunk_size: 每个块的最大字符数（考虑 Token 限制）
            overlap_size: 块之间重叠的字符数（用于保持上下文连续性）
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.chunks: List[TextChunk] = []

    def read_file(self, file_path: str) -> str:
        """读取小说文件，自动检测编码"""
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb18030', 'big5']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # 如果所有编码都失败，使用 utf-8 并忽略错误
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _chinese_to_int(self, s: str) -> int:
        """将中文数字转换为整数"""
        if not s:
            return 0

        # 处理纯数字
        if s.isdigit():
            return int(s)

        # 处理中文数字
        result = 0
        temp = 0
        section = 0

        for char in reversed(s):
            if char in self.CHINESE_NUMS:
                num = self.CHINESE_NUMS[char]
                if num >= 100:
                    if num > section:
                        section = num
                    else:
                        section *= num
                else:
                    temp += num
            else:
                break

        result = section + temp
        return result if result > 0 else 1

    def _find_chapter_title(self, content: str, start_pos: int) -> Optional[str]:
        """提取章节标题"""
        # 获取章节行
        lines = content[start_pos:start_pos + 200].split('\n')
        for line in lines:
            line = line.strip()
            if line and not any(pattern.match(line) for pattern in [
                re.compile(p, re.IGNORECASE) for p in self.CHAPTER_PATTERNS
            ]):
                # 找到非章节标记的文本作为标题
                if len(line) > 2 and len(line) < 100:
                    return line
        return None

    def split_by_chapters(self, text: str) -> List[TextChunk]:
        """
        按章节切分小说文本

        Args:
            text: 完整的小说文本

        Returns:
            按章节切分的文本块列表
        """
        self.chunks = []

        # 查找所有章节位置
        chapter_positions = []
        for pattern in self.CHAPTER_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE)
            for match in regex.finditer(text):
                # 提取章节号（从各捕获组中找非空值）
                groups = match.groups()
                chapter_num = None
                for g in groups:
                    if g:
                        try:
                            chapter_num = self._chinese_to_int(g)
                        except:
                            chapter_num = len(chapter_positions) + 1
                        break

                if chapter_num is None:
                    chapter_num = len(chapter_positions) + 1

                chapter_positions.append((match.start(), chapter_num, match.group()))

        # 按位置排序
        chapter_positions.sort(key=lambda x: x[0])

        # 去重（同一章节可能被多个模式匹配）
        unique_positions = []
        last_pos = -100
        for pos, num, title in chapter_positions:
            if pos - last_pos > 50:  # 距离上一个位置足够远
                unique_positions.append((pos, num, title))
                last_pos = pos

        if not unique_positions:
            # 没有找到章节，按固定大小切分
            self.chunks = self._split_by_size(text)
            return self.chunks

        # 创建文本块
        for i, (pos, chapter_num, chapter_title) in enumerate(unique_positions):
            # 确定块的结束位置
            if i + 1 < len(unique_positions):
                end_pos = unique_positions[i + 1][0]
            else:
                end_pos = len(text)

            # 提取章节内容
            content = text[pos:end_pos].strip()

            # 尝试提取更精确的章节标题
            title_match = re.search(r':\s*(.+?)\n', chapter_title)
            if title_match:
                chapter_title = title_match.group(1).strip()
            else:
                chapter_title = chapter_title.strip()

            chunk = TextChunk(
                chapter_number=chapter_num,
                chapter_title=chapter_title,
                content=content,
                start_position=pos,
                end_position=end_pos,
                word_count=len(content)
            )
            self.chunks.append(chunk)

        return self.chunks

    def _split_by_size(self, text: str) -> List[TextChunk]:
        """当无法识别章节时，按固定大小切分"""
        chunks = []
        start = 0
        chunk_num = 1

        while start < len(text):
            end = min(start + self.max_chunk_size, len(text))

            # 尝试在句子边界切断
            if end < len(text):
                for sep in ['。\n', '！\n', '？\n', '。\n\n', '!\n', '?\n']:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > self.max_chunk_size // 2:
                        end = start + last_sep + len(sep)
                        break

            content = text[start:end].strip()
            if content:
                chunk = TextChunk(
                    chapter_number=chunk_num,
                    chapter_title=f"第{chunk_num}部分",
                    content=content,
                    start_position=start,
                    end_position=end,
                    word_count=len(content)
                )
                chunks.append(chunk)
                chunk_num += 1

            start = end - self.overlap_size if end < len(text) else end

        return chunks

    def get_context_window(self, chunk_index: int, include_previous: int = 1) -> str:
        """
        获取包含上下文的文本窗口

        Args:
            chunk_index: 当前块索引
            include_previous: 包含前多少个块的内容

        Returns:
            包含上下文的文本
        """
        if not self.chunks:
            return ""

        start_idx = max(0, chunk_index - include_previous)
        end_idx = chunk_index + 1

        context_parts = []
        for i in range(start_idx, end_idx):
            if i < len(self.chunks):
                context_parts.append(self.chunks[i].content)

        return "\n\n".join(context_parts)


class MemoryBank:
    """记忆银行 - 存储和管理跨章节的人物记忆"""

    def __init__(self):
        self.character_memories: Dict[str, CharacterMemory] = {}
        self.global_context: Dict[str, Any] = {
            "locations": [],
            "relationships": [],
            "plot_points": []
        }

    def add_character_memory(self, memory: CharacterMemory) -> None:
        """添加或合并人物记忆"""
        if memory.character_id in self.character_memories:
            # 合并到现有记忆
            existing = self.character_memories[memory.character_id]
            self.character_memories[memory.character_id] = existing.merge(memory)
        else:
            # 新增记忆
            self.character_memories[memory.character_id] = memory

    def get_character_memory(self, character_id: str) -> Optional[CharacterMemory]:
        """获取指定人物的记忆"""
        return self.character_memories.get(character_id)

    def get_all_characters(self) -> List[Character]:
        """获取所有人物实体"""
        return [mem.to_character() for mem in self.character_memories.values()]

    def get_summary(self) -> str:
        """生成记忆摘要，用于传递给 LLM"""
        parts = []

        # 人物摘要
        if self.character_memories:
            parts.append("【已识别人物】")
            for char_id, mem in self.character_memories.items():
                parts.append(f"- {mem.name}: {', '.join(mem.traits[:3]) if mem.traits else '未知特质'}")
                if mem.goals:
                    parts.append(f"  目标：{', '.join(mem.goals[:2])}")

        # 关系摘要
        if self.global_context.get("relationships"):
            parts.append("\n【已识别关系】")
            for rel in self.global_context["relationships"][:10]:
                parts.append(f"- {rel}")

        # 剧情要点
        if self.global_context.get("plot_points"):
            parts.append("\n【剧情要点】")
            for point in self.global_context["plot_points"][-5:]:
                parts.append(f"- {point}")

        return "\n".join(parts)

    def to_context_prompt(self) -> str:
        """生成用于 LLM 提示的上下文"""
        summary = self.get_summary()
        if not summary.strip():
            return ""

        return f"""以下是之前章节已提取的信息，请在处理新内容时参考：

{summary}

注意：如果发现新内容更新了某个人物的信息，请在返回的 JSON 中包含更新后的完整信息。
"""

    def save(self, file_path: str) -> None:
        """保存记忆到文件"""
        data = {
            "characters": {
                cid: {
                    "character_id": mem.character_id,
                    "name": mem.name,
                    "descriptions": mem.descriptions,
                    "traits": mem.traits,
                    "goals": mem.goals,
                    "background_fragments": mem.background_fragments,
                    "appearance_fragments": mem.appearance_fragments,
                    "first_appearance_chapter": mem.first_appearance_chapter,
                    "last_appearance_chapter": mem.last_appearance_chapter,
                    "mention_count": mem.mention_count
                }
                for cid, mem in self.character_memories.items()
            },
            "global_context": self.global_context
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, file_path: str) -> None:
        """从文件加载记忆"""
        if not os.path.exists(file_path):
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for cid, mem_data in data.get("characters", {}).items():
            self.character_memories[cid] = CharacterMemory(
                character_id=mem_data["character_id"],
                name=mem_data["name"],
                descriptions=mem_data.get("descriptions", []),
                traits=mem_data.get("traits", []),
                goals=mem_data.get("goals", []),
                background_fragments=mem_data.get("background_fragments", []),
                appearance_fragments=mem_data.get("appearance_fragments", []),
                first_appearance_chapter=mem_data.get("first_appearance_chapter", 0),
                last_appearance_chapter=mem_data.get("last_appearance_chapter", 0),
                mention_count=mem_data.get("mention_count", 0)
            )

        self.global_context = data.get("global_context", {})


class ChunkingPipeline:
    """分块处理流水线 - 整合阅读器和记忆银行"""

    def __init__(self, max_chunk_size: int = 8000):
        self.reader = NovelReader(max_chunk_size=max_chunk_size)
        self.memory_bank = MemoryBank()
        self.processed_chunks: List[int] = []

    def load_novel(self, file_path: str) -> List[TextChunk]:
        """加载小说并切分"""
        text = self.reader.read_file(file_path)
        # NovelReader.split_by_chapters 会更新 self.reader.chunks
        return self.reader.split_by_chapters(text)

    def get_chunk_with_context(self, chunk_index: int) -> Tuple[TextChunk, str]:
        """获取指定块及其上下文"""
        chunk = self.reader.chunks[chunk_index]
        context = self.reader.get_context_window(chunk_index, include_previous=1)
        memory_context = self.memory_bank.to_context_prompt()

        full_context = ""
        if memory_context:
            full_context += memory_context + "\n\n"
        full_context += context

        return chunk, full_context

    def mark_processed(self, chunk_index: int) -> None:
        """标记块已处理"""
        self.processed_chunks.append(chunk_index)

    def save_checkpoint(self, checkpoint_path: str) -> None:
        """保存检查点"""
        self.memory_bank.save(checkpoint_path)

    def load_checkpoint(self, checkpoint_path: str) -> None:
        """加载检查点"""
        self.memory_bank.load(checkpoint_path)


if __name__ == "__main__":
    # 演示用法
    print("=" * 60)
    print("长文本分块与记忆引擎演示")
    print("=" * 60)

    # 创建示例文本
    sample_novel = """
第一章：开始

哈利·波特是一个年轻的巫师，他有着黑色的头发和绿色的眼睛。
他额头上有一道闪电形的伤疤。
哈利从小在姨妈家长大，不知道自己是巫师。

第二章：魔法学校

哈利收到了霍格沃茨的录取通知书。
在前往学校的火车上，他遇到了罗恩·韦斯莱。
罗恩有一头红发，来自一个巫师家庭。
两人很快成为了朋友。

第三章：新的冒险

哈利和罗恩一起探索城堡。
他们遇到了赫敏·格兰杰，一个聪明的女巫。
赫敏出身于麻瓜家庭，但天赋异禀。
三人组开始了他们的冒险。
"""

    # 创建阅读器并切分
    reader = NovelReader()
    chunks = reader.split_by_chapters(sample_novel)

    print(f"\n识别到 {len(chunks)} 个章节:")
    for chunk in chunks:
        print(f"  - 第{chunk.chapter_number}章：{chunk.chapter_title} ({chunk.word_count} 字)")

    # 创建记忆银行并演示合并
    memory_bank = MemoryBank()

    # 模拟从第一章提取的记忆
    harry_ch1 = CharacterMemory(
        character_id="char_harry",
        name="哈利·波特",
        descriptions=["年轻的巫师"],
        traits=["黑色头发", "绿色眼睛"],
        goals=[],
        background_fragments=["从小在姨妈家长大"],
        appearance_fragments=["额头有闪电形伤疤"],
        first_appearance_chapter=1,
        last_appearance_chapter=1,
        mention_count=1
    )
    memory_bank.add_character_memory(harry_ch1)

    # 模拟从第二章提取的记忆（部分信息重复，部分新增）
    harry_ch2 = CharacterMemory(
        character_id="char_harry",
        name="哈利·波特",
        descriptions=["霍格沃茨学生"],
        traits=["勇敢"],
        goals=["学习魔法"],
        background_fragments=[],
        appearance_fragments=[],
        first_appearance_chapter=2,
        last_appearance_chapter=2,
        mention_count=1
    )
    memory_bank.add_character_memory(harry_ch2)

    # 添加新人物
    ron_ch2 = CharacterMemory(
        character_id="char_ron",
        name="罗恩·韦斯莱",
        descriptions=["哈利的朋友"],
        traits=["红头发", "忠诚"],
        goals=[],
        background_fragments=["来自巫师家庭"],
        appearance_fragments=[],
        first_appearance_chapter=2,
        last_appearance_chapter=2,
        mention_count=1
    )
    memory_bank.add_character_memory(ron_ch2)

    print("\n" + "=" * 60)
    print("记忆合并结果:")
    print("=" * 60)
    print(memory_bank.get_summary())

    print("\n" + "=" * 60)
    print("转换为人物实体:")
    print("=" * 60)
    for char in memory_bank.get_all_characters():
        print(f"\n{char.name} ({char.id})")
        print(f"  描述：{char.description}")
        print(f"  特质：{char.traits}")
        print(f"  目标：{char.goals}")
        if char.background:
            print(f"  背景：{char.background}")
