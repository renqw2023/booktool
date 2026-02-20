# -*- coding: utf-8 -*-
"""向量存储与检索模块

本模块实现基于语义的人物记忆检索，解决长篇小说处理中的记忆膨胀问题。
使用轻量级的 TF-IDF + 余弦相似度实现，无需额外依赖。

核心功能：
1. 人物记忆向量化存储
2. 基于查询的语义检索
3. Top-K 相关记忆提取
"""
import re
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class VectorizedMemory:
    """向量化的记忆片段"""
    memory_id: str
    character_id: str
    character_name: str
    content: str  # 原始文本内容
    vector: Dict[str, float]  # TF-IDF 向量表示
    metadata: Dict[str, Any]  # 额外元数据


class SimpleTfidfVectorizer:
    """简单的 TF-IDF 向量化器

    无需外部依赖的轻量级实现
    """

    def __init__(self):
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.documents: List[List[str]] = []

    def _tokenize(self, text: str) -> List[str]:
        """中文分词 - 简单按字符和词分割"""
        # 提取中文词语（简单的 2-gram）
        tokens = []
        # 添加单字
        for char in text:
            if '\u4e00' <= char <= '\u9fff' or char.isalnum():
                tokens.append(char.lower())
        # 添加 2-gram
        for i in range(len(text) - 1):
            bigram = text[i:i+2]
            if len(bigram) == 2 and all('\u4e00' <= c <= '\u9fff' for c in bigram):
                tokens.append(bigram)
        return tokens

    def fit(self, documents: List[str]) -> 'SimpleTfidfVectorizer':
        """拟合向量化器"""
        self.documents = [self._tokenize(doc) for doc in documents]

        # 构建词汇表
        all_terms = set()
        for doc_tokens in self.documents:
            all_terms.update(doc_tokens)

        self.vocabulary = {term: idx for idx, term in enumerate(sorted(all_terms))}

        # 计算 IDF
        n_docs = len(self.documents)
        doc_freq = defaultdict(int)

        for doc_tokens in self.documents:
            unique_terms = set(doc_tokens)
            for term in unique_terms:
                doc_freq[term] += 1

        for term, freq in doc_freq.items():
            self.idf[term] = math.log((n_docs + 1) / (freq + 1)) + 1

        return self

    def transform(self, documents: List[str]) -> List[Dict[str, float]]:
        """将文档转换为 TF-IDF 向量"""
        vectors = []

        for doc in documents:
            tokens = self._tokenize(doc)

            # 计算 TF
            tf = defaultdict(float)
            for token in tokens:
                tf[token] += 1

            # 归一化 TF
            n_tokens = len(tokens) if tokens else 1
            for token in tf:
                tf[token] /= n_tokens

            # 计算 TF-IDF
            tfidf = {}
            for token, tf_val in tf.items():
                if token in self.idf:
                    tfidf[token] = tf_val * self.idf[token]

            vectors.append(tfidf)

        return vectors

    def fit_transform(self, documents: List[str]) -> List[Dict[str, float]]:
        """拟合并转换"""
        self.fit(documents)
        return self.transform(documents)


def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """计算两个稀疏向量的余弦相似度"""
    # 找到共同的维度
    common_dims = set(vec1.keys()) & set(vec2.keys())

    if not common_dims:
        return 0.0

    # 计算点积
    dot_product = sum(vec1[dim] * vec2[dim] for dim in common_dims)

    # 计算模长
    norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


class CharacterMemoryStore:
    """人物记忆向量存储

    支持高效的语义检索
    """

    def __init__(self):
        self.memories: Dict[str, VectorizedMemory] = {}
        self.vectors_by_character: Dict[str, List[str]] = defaultdict(list)  # character_id -> memory_ids
        self.vectorizer = SimpleTfidfVectorizer()
        self._needs_refit = False
        self._document_texts: List[str] = []

    def add_memory(self, memory: VectorizedMemory) -> None:
        """添加记忆到存储"""
        self.memories[memory.memory_id] = memory
        self.vectors_by_character[memory.character_id].append(memory.memory_id)
        self._needs_refit = True

    def add_character_memories(self, character_id: str, character_name: str,
                               traits: List[str], goals: List[str],
                               descriptions: List[str], appearances: List[str],
                               metadata: Optional[Dict[str, Any]] = None) -> None:
        """添加人物的多个记忆片段"""
        # 为每个类型的信息创建独立的记忆片段
        memory_fragments = []

        for i, trait in enumerate(traits):
            memory_fragments.append((f"{character_id}_trait_{i}", f"{character_name}的特质：{trait}"))

        for i, goal in enumerate(goals):
            memory_fragments.append((f"{character_id}_goal_{i}", f"{character_name}的目标：{goal}"))

        for i, desc in enumerate(descriptions):
            memory_fragments.append((f"{character_id}_desc_{i}", f"{character_name}的描述：{desc}"))

        for i, app in enumerate(appearances):
            memory_fragments.append((f"{character_id}_app_{i}", f"{character_name}的外貌：{app}"))

        # 批量添加
        for memory_id, content in memory_fragments:
            memory = VectorizedMemory(
                memory_id=memory_id,
                character_id=character_id,
                character_name=character_name,
                content=content,
                vector={},  # 稍后计算
                metadata=metadata or {}
            )
            self.add_memory(memory)
            self._document_texts.append(content)

        self._needs_refit = True

    def _ensure_vectorizer_fitted(self) -> None:
        """确保向量化器已拟合"""
        if self._needs_refit and self._document_texts:
            self.vectorizer.fit(self._document_texts)
            self._needs_refit = False

            # 重新计算所有向量
            for memory_id, memory in self.memories.items():
                vectors = self.vectorizer.transform([memory.content])
                memory.vector = vectors[0] if vectors else {}

    def search_by_query(self, query: str, top_k: int = 5,
                        character_filter: Optional[List[str]] = None) -> List[Tuple[VectorizedMemory, float]]:
        """根据查询检索最相关的记忆

        Args:
            query: 查询文本
            top_k: 返回结果数量
            character_filter: 可选的人物 ID 过滤列表

        Returns:
            (记忆，相似度) 列表，按相似度降序排列
        """
        self._ensure_vectorizer_fitted()

        if not self.memories or not self.vectorizer.vocabulary:
            return []

        # 将查询转换为向量
        query_vectors = self.vectorizer.transform([query])
        query_vector = query_vectors[0] if query_vectors else {}

        if not query_vector:
            return []

        # 计算与所有记忆的相似度
        scores = []

        for memory_id, memory in self.memories.items():
            # 应用过滤器
            if character_filter and memory.character_id not in character_filter:
                continue

            if not memory.vector:
                continue

            similarity = cosine_similarity(query_vector, memory.vector)
            scores.append((memory, similarity))

        # 按相似度排序
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def get_character_memories(self, character_id: str,
                               limit: int = 10) -> List[VectorizedMemory]:
        """获取指定人物的记忆"""
        memory_ids = self.vectors_by_character.get(character_id, [])
        memories = [self.memories[mid] for mid in memory_ids if mid in self.memories]
        return memories[:limit]

    def search_characters_in_text(self, text: str, top_k: int = 3) -> List[str]:
        """从文本中识别最相关的人物

        通过计算文本与人物记忆的相似度来识别人物
        """
        self._ensure_vectorizer_fitted()

        if not self.memories:
            return []

        # 按人物聚合记忆
        character_scores: Dict[str, float] = defaultdict(float)
        character_counts: Dict[str, int] = defaultdict(int)

        # 将查询转换为向量
        query_vectors = self.vectorizer.transform([text])
        query_vector = query_vectors[0] if query_vectors else {}

        for memory_id, memory in self.memories.items():
            if not memory.vector:
                continue

            similarity = cosine_similarity(query_vector, memory.vector)
            if similarity > 0.1:  # 阈值过滤
                character_scores[memory.character_id] += similarity
                character_counts[memory.character_id] += 1

        # 考虑记忆数量的影响
        final_scores = {}
        for char_id, score in character_scores.items():
            count = character_counts[char_id]
            # 归一化：记忆越多，需要的总分数越高
            final_scores[char_id] = score / math.log(count + 2)

        # 排序并返回 top-k
        sorted_chars = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return [char_id for char_id, _ in sorted_chars[:top_k]]

    def get_summary_for_context(self, relevant_character_ids: List[str],
                                query: Optional[str] = None) -> str:
        """为人物生成上下文摘要

        Args:
            relevant_character_ids: 相关人物 ID 列表
            query: 可选的查询，用于优先展示相关记忆

        Returns:
            格式化的上下文字符串
        """
        if not relevant_character_ids:
            return ""

        parts = ["【相关人物记忆】"]

        for char_id in relevant_character_ids:
            memories = self.get_character_memories(char_id, limit=5)
            if not memories:
                continue

            char_name = memories[0].character_name if memories else char_id

            # 收集该人物的所有信息
            traits = []
            goals = []
            descriptions = []
            appearances = []

            for mem in memories:
                content = mem.content
                if "特质" in content:
                    traits.append(content.replace(f"{char_name}的特质：", ""))
                elif "目标" in content:
                    goals.append(content.replace(f"{char_name}的目标：", ""))
                elif "外貌" in content:
                    appearances.append(content.replace(f"{char_name}的外貌：", ""))
                else:
                    descriptions.append(content.replace(f"{char_name}的描述：", ""))

            # 构建人物摘要
            char_info = [f"  {char_name}"]
            if traits:
                char_info.append(f"    特质：{', '.join(traits[:3])}")
            if goals:
                char_info.append(f"    目标：{', '.join(goals[:2])}")
            if appearances:
                char_info.append(f"    外貌：{', '.join(appearances[:2])}")
            if descriptions:
                char_info.append(f"    描述：{descriptions[0][:50]}...")

            parts.append("\n".join(char_info))

        return "\n".join(parts)


class VectorMemoryBank:
    """向量化记忆银行 - 整合向量检索和传统记忆管理"""

    def __init__(self):
        self.vector_store = CharacterMemoryStore()
        self.global_context: Dict[str, Any] = {
            "locations": [],
            "relationships": [],
            "plot_points": []
        }
        self.character_ids_by_name: Dict[str, str] = {}  # 名字 -> ID 映射

    def add_character(self, character_id: str, name: str,
                      traits: List[str], goals: List[str],
                      descriptions: List[str], appearances: List[str],
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """添加人物到记忆银行"""
        self.character_ids_by_name[name] = character_id
        self.vector_store.add_character_memories(
            character_id=character_id,
            character_name=name,
            traits=traits,
            goals=goals,
            descriptions=descriptions,
            appearances=appearances,
            metadata=metadata
        )

    def retrieve_relevant_characters(self, text: str,
                                     top_k: int = 5) -> List[str]:
        """从文本中检索相关人物"""
        return self.vector_store.search_characters_in_text(text, top_k)

    def build_context(self, text: str,
                      max_characters: int = 5) -> str:
        """为给定文本构建相关的上下文记忆

        Args:
            text: 当前处理的文本
            max_characters: 最多包含的人物数量

        Returns:
            格式化的上下文字符串
        """
        # 检索与文本相关的人物
        relevant_chars = self.retrieve_relevant_characters(text, top_k=max_characters)

        if not relevant_chars:
            return ""

        # 生成上下文
        return self.vector_store.get_summary_for_context(relevant_chars)

    def add_relationship(self, relationship_desc: str) -> None:
        """添加关系描述"""
        if relationship_desc not in self.global_context["relationships"]:
            self.global_context["relationships"].append(relationship_desc)

    def add_location(self, location: str) -> None:
        """添加地点"""
        if location not in self.global_context["locations"]:
            self.global_context["locations"].append(location)

    def add_plot_point(self, plot_point: str) -> None:
        """添加剧情要点"""
        self.global_context["plot_points"].append(plot_point)

    def to_context_prompt(self, current_text: Optional[str] = None) -> str:
        """生成上下文提示

        Args:
            current_text: 当前处理的文本，如果提供则使用向量检索
        """
        parts = []

        # 如果有当前文本，使用向量检索
        if current_text:
            char_context = self.build_context(current_text)
            if char_context:
                parts.append(char_context)
        else:
            # 否则返回所有人物摘要
            parts.append(self._get_all_characters_summary())

        # 添加关系和剧情
        if self.global_context["relationships"]:
            parts.append("\n【人物关系】")
            for rel in self.global_context["relationships"][-5:]:
                parts.append(f"  {rel}")

        if self.global_context["plot_points"]:
            parts.append("\n【最近剧情】")
            for point in self.global_context["plot_points"][-3:]:
                parts.append(f"  {point}")

        return "\n".join(parts) if parts else ""

    def _get_all_characters_summary(self) -> str:
        """获取所有人物摘要"""
        all_chars = set()
        for memories in self.vector_store.vectors_by_character.values():
            for mem_id in memories:
                if mem_id in self.vector_store.memories:
                    all_chars.add(self.vector_store.memories[mem_id].character_name)

        if not all_chars:
            return ""

        parts = ["【已识别人物】"]
        for name in list(all_chars)[:10]:
            parts.append(f"  {name}")

        return "\n".join(parts)


if __name__ == "__main__":
    # 演示用法
    print("=" * 60)
    print("向量记忆存储演示")
    print("=" * 60)

    # 创建记忆银行
    memory_bank = VectorMemoryBank()

    # 添加人物
    memory_bank.add_character(
        character_id="char_harry",
        name="哈利·波特",
        traits=["勇敢", "冲动", "忠诚"],
        goals=["打败伏地魔", "保护朋友"],
        descriptions=["年轻的巫师", "霍格沃茨学生"],
        appearances=["黑色头发", "绿色眼睛", "额头有闪电伤疤"]
    )

    memory_bank.add_character(
        character_id="char_hermione",
        name="赫敏·格兰杰",
        traits=["聪明", "勤奋", "逻辑性强"],
        goals=["成为优秀的巫师", "帮助哈利"],
        descriptions=["麻瓜出身", "学霸"],
        appearances=["棕色卷发", "大门牙"]
    )

    # 添加关系
    memory_bank.add_relationship("哈利与赫敏：朋友")
    memory_bank.add_plot_point("哈利进入霍格沃茨学习")

    # 测试检索
    test_text = "哈利拔出格兰芬多宝剑，与怪物战斗"

    print(f"\n查询文本：{test_text}")
    print("\n检索相关人物:")
    relevant = memory_bank.retrieve_relevant_characters(test_text)
    for char_id in relevant:
        print(f"  - {char_id}")

    print("\n构建的上下文:")
    context = memory_bank.to_context_prompt(test_text)
    print(context)
