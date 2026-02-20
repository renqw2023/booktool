# -*- coding: utf-8 -*-
"""Phase 3: 剧本生成模块 - LLM 驱动版本

本模块使用大语言模型将时间线事件转化为规范的剧本场景。
LLM 负责理解叙事语言，将其转化为动作描写和对白。
"""
import re
import json
import os
from typing import List, Optional, Dict, Any
from models import TimelineEvent, ScriptScene


# ==================== LLM 客户端接口（复用 extractor 中的定义） ====================

class LLMClient:
    """LLM 客户端基类"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", "")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        raise NotImplementedError("子类必须实现 chat 方法")


class MockLLMClient(LLMClient):
    """Mock LLM 客户端 - 用于测试"""

    def __init__(self, mock_response: str = ""):
        super().__init__()
        self.mock_response = mock_response

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        return self.mock_response


class OpenAICompatibleClient(LLMClient):
    """OpenAI 兼容 API 客户端"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-4o-mini"):
        super().__init__(api_key, base_url)
        self.model = model

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None
            )
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except ImportError:
            raise ImportError("请安装 openai 包：pip install openai")


# ==================== Prompt 模板 ====================

SCENE_GENERATION_PROMPT = """你是一个专业的影视剧本改编专家。请将以下小说时间线事件转化为规范的剧本场景。

输入事件信息：
- 章节：第{chapter}章
- 摘要：{summary}
- 描述：{description}
- 地点：{location}
- 涉及人物：{characters}

请按照标准剧本格式，将上述事件转化为一个完整的剧本场景。需要：
1. 确定场景时间（日/夜/黄昏/黎明等）
2. 确定场景地点
3. 将叙事性描述转化为可视化的动作描写（actions）
4. 如果有对话，提取或创作符合人物的对白（dialogues）

请严格按照以下 JSON Schema 格式返回结果：
{{
    "scene": {{
        "id": "scene_{event_id}",
        "chapter": {chapter},
        "location": "场景地点",
        "time": "日/夜/黄昏/黎明等",
        "description": "场景总体描述（50-100 字）",
        "actions": ["动作描写 1", "动作描写 2", ...],
        "dialogues": [
            {{"character_id": "char_人物 ID", "line": "对白内容"}},
            ...
        ],
        "character_ids": ["char_人物 1", "char_人物 2", ...]
    }}
}}

注意：
- actions 数组中的每个元素应该是一个具体的、可视化的动作描述
- dialogues 应该符合人物性格和情境
- 如果没有明确的对白，dialogues 可以是空数组

请只返回 JSON，不要包含任何额外说明：
"""


# ==================== 剧本生成器实现 ====================

class ScriptGenerator:
    """剧本生成器 - 使用 LLM 进行智能转化"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化剧本生成器

        Args:
            llm_client: LLM 客户端实例，如果为 None 则使用 MockLLMClient
        """
        self.llm_client = llm_client or MockLLMClient()

    def generate(self, events: List[TimelineEvent]) -> List[ScriptScene]:
        """从时间线事件生成剧本场景"""
        scenes = []

        for event in events:
            scene = self._create_scene_from_event(event)
            if scene:
                scenes.append(scene)

        return scenes

    def _create_scene_from_event(self, event: TimelineEvent) -> ScriptScene:
        """从单个事件创建场景"""
        # 构建人物列表字符串
        characters_str = ", ".join(event.character_ids) if event.character_ids else "未明确"

        prompt = SCENE_GENERATION_PROMPT.format(
            chapter=event.chapter,
            summary=event.summary,
            description=event.description or event.summary,
            location=event.location or "未明确",
            characters=characters_str,
            event_id=event.id
        )
        messages = [{"role": "user", "content": prompt}]

        response = self.llm_client.chat(messages, temperature=0.8)
        data = self._parse_json_response(response)

        if not data or "scene" not in data:
            # 如果 LLM 解析失败，返回一个基础版本
            return self._create_fallback_scene(event)

        scene_data = data["scene"]
        return ScriptScene(
            id=scene_data.get("id", f"scene_{event.id}"),
            chapter=scene_data.get("chapter", event.chapter),
            location=scene_data.get("location", event.location or "未知地点"),
            time=scene_data.get("time", "日"),
            description=scene_data.get("description", event.summary),
            actions=scene_data.get("actions", []),
            dialogues=scene_data.get("dialogues", []),
            character_ids=scene_data.get("character_ids", event.character_ids)
        )

    def _create_fallback_scene(self, event: TimelineEvent) -> ScriptScene:
        """当 LLM 解析失败时，创建一个基础场景"""
        time = self._determine_time_fallback(event)

        return ScriptScene(
            id=f"scene_{event.id}",
            chapter=event.chapter,
            location=event.location or "未知地点",
            time=time,
            description=event.description or event.summary,
            actions=[event.summary],
            dialogues=[],
            character_ids=event.character_ids
        )

    def _determine_time_fallback(self, event: TimelineEvent) -> str:
        """备用时间判断逻辑（当 LLM 不可用时）"""
        time_keywords = {
            "夜": ["夜", "夜晚", "晚上", "深夜", "傍晚", "黄昏", "雨夜"],
            "日": ["日", "白天", "早晨", "早上", "中午", "下午", "清晨"],
            "晨": ["晨", "黎明", "破晓", "晨曦"],
        }

        text = f"{event.summary} {event.description}"

        for time_value, keywords in time_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return time_value

        return "日"

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 返回的 JSON 响应"""
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass

        return None


if __name__ == "__main__":
    # 演示用法
    mock_response = '''
    {
        "scene": {
            "id": "scene_event_001",
            "chapter": 1,
            "location": "霍格沃茨大礼堂",
            "time": "夜",
            "description": "大礼堂内烛光摇曳，新生们紧张地等待着分院仪式",
            "actions": [
                "哈利紧张地握紧了拳头",
                "赫敏轻声安慰罗恩",
                "邓布利多站起身走向讲台"
            ],
            "dialogues": [
                {"character_id": "char_harry", "line": "我希望我能进格兰芬多。"},
                {"character_id": "char_ron", "line": "我也是，我妈妈说格兰芬多是最好的。"}
            ],
            "character_ids": ["char_harry", "char_ron", "char_hermione"]
        }
    }
    '''

    client = MockLLMClient(mock_response)
    generator = ScriptGenerator(client)

    from models import TimelineEvent
    event = TimelineEvent(
        id="event_001",
        chapter=1,
        summary="新生们参加分院仪式",
        description="哈利和罗恩在大礼堂里等待分院",
        location="霍格沃茨大礼堂",
        character_ids=["char_harry", "char_ron"]
    )

    scenes = generator.generate([event])
    for scene in scenes:
        print(f"场景：{scene.location} ({scene.time})")
        print(f"动作：{scene.actions}")
        print(f"对白：{scene.dialogues}")
