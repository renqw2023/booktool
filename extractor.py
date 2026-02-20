"""Phase 2: 信息提取引擎 (NLU) - LLM 驱动版本

本模块使用大语言模型进行真正的人物、关系和时间线提取。
支持自定义 LLM 客户端，默认提供 OpenAI 兼容接口调用逻辑。
"""
import re
import json
import os
from typing import List, Optional, Dict, Any
from models import Character, Relationship, TimelineEvent


# ==================== LLM 客户端接口 ====================

class LLMClient:
    """LLM 客户端基类 - 可继承实现不同平台的调用"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", "")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """发送对话请求并返回响应文本"""
        raise NotImplementedError("子类必须实现 chat 方法")


class MockLLMClient(LLMClient):
    """Mock LLM 客户端 - 用于测试时无需真实 API 调用"""

    def __init__(self, mock_response: str = ""):
        super().__init__()
        self.mock_response = mock_response

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """返回预设的 mock 响应"""
        return self.mock_response


class OpenAICompatibleClient(LLMClient):
    """OpenAI 兼容 API 客户端 - 支持原生 JSON Structured Output 和自动重试"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: str = "gpt-4o-mini", use_json_mode: bool = True,
                 max_retries: int = 3, retry_delay: float = 1.0):
        """
        初始化 OpenAI 兼容客户端

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            use_json_mode: 是否启用 JSON 结构化输出（response_format=json_object）
            max_retries: 最大重试次数
            retry_delay: 基础重试延迟（秒），实际延迟按指数退避计算
        """
        super().__init__(api_key, base_url)
        self.model = model
        self.use_json_mode = use_json_mode
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7,
             json_mode: bool = False) -> str:
        """
        调用 OpenAI 兼容 API（带自动重试）

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            json_mode: 是否强制使用 JSON 模式（覆盖实例变量）

        Retries:
            使用指数退避策略进行重试：
            - HTTP 429 (Rate Limit): 重试
            - HTTP 5xx (Server Error): 重试
            - Connection Error: 重试
            - HTTP 4xx (Client Error): 不重试
        """
        import time
        import random

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                from openai import OpenAI, APIStatusError, APIConnectionError
                client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url if self.base_url else None
                )

                # 构建请求参数
                request_kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature
                }

                # 启用 JSON 模式（原生结构化输出）
                if self.use_json_mode or json_mode:
                    # 方法 1: 使用 response_format（推荐，适用于支持 JSON Schema 的模型）
                    request_kwargs["response_format"] = {"type": "json_object"}

                    # 方法 2: 同时添加系统提示强化 JSON 要求
                    if messages and messages[0].get("role") != "system":
                        messages = [{
                            "role": "system",
                            "content": "You must respond with valid JSON only. No other text, no markdown code blocks."
                        }] + messages

                response = client.chat.completions.create(**request_kwargs)
                return response.choices[0].message.content

            except ImportError:
                raise ImportError("请安装 openai 包：pip install openai")

            except APIStatusError as e:
                last_exception = e
                status_code = e.status_code

                # 429 Rate Limit - 需要重试
                if status_code == 429:
                    if attempt < self.max_retries:
                        # 指数退避 + 抖动
                        delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"[RETRY] 遇到限流 (429)，{delay:.1f}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"[ERROR] 达到最大重试次数，限流错误仍未解决")
                        raise

                # 5xx Server Error - 需要重试
                elif 500 <= status_code < 600:
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"[RETRY] 服务器错误 ({status_code})，{delay:.1f}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"[ERROR] 达到最大重试次数，服务器错误仍未解决")
                        raise

                # 4xx Client Error - 不重试，直接抛出
                elif 400 <= status_code < 500:
                    print(f"[ERROR] 客户端错误 ({status_code}): {e}")
                    raise

            except APIConnectionError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"[RETRY] 连接错误，{delay:.1f}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    print(f"[ERROR] 达到最大重试次数，连接错误仍未解决")
                    raise

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"[RETRY] 未知错误 ({type(e).__name__})，{delay:.1f}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    print(f"[ERROR] 达到最大重试次数，错误仍未解决")
                    raise

        # 理论上不会到达这里，但为了完整性
        if last_exception:
            raise last_exception
        raise RuntimeError("重试循环异常退出")


# ==================== Prompt 模板 ====================

CHARACTER_EXTRACTION_PROMPT = """你是一个专业的文学小说分析专家。请阅读以下小说文本，提取其中出现的所有主要人物。

请严格按照以下 JSON Schema 格式返回结果：
{{
    "characters": [
        {{
            "id": "char_人物姓名拼音或英文",
            "name": "人物姓名",
            "description": "人物简短描述（50 字以内）",
            "traits": ["性格特点 1", "性格特点 2", ...],
            "goals": ["目标 1", "目标 2", ...],
            "background": "背景故事（可选）",
            "appearance": "外貌描写（可选）"
        }}
    ]
}}

如果某个字段无法确定，可以用空字符串或空数组填充。

小说文本：
{text}

请只返回 JSON，不要包含任何额外说明：
"""

RELATIONSHIP_EXTRACTION_PROMPT = """你是一个专业的文学小说分析专家。请阅读以下小说文本，提取其中人物之间的关系。

请严格按照以下 JSON Schema 格式返回结果：
{{
    "relationships": [
        {{
            "id": "rel_人物 1_人物 2",
            "character_id_1": "char_人物 1 姓名",
            "character_id_2": "char_人物 2 姓名",
            "type": "关系类型（朋友/敌人/伙伴/亲人/师徒/恋人等）",
            "description": "关系描述",
            "conflict_level": 0-5 的整数（0 无冲突，5 极度冲突）,
            "strength": 0-5 的整数（关系强度）
        }}
    ]
}}

如果没有检测到任何人物关系，返回空数组。

小说文本：
{text}

请只返回 JSON，不要包含任何额外说明：
"""

TIMELINE_EXTRACTION_PROMPT = """你是一个专业的文学小说分析专家。请阅读以下小说文本，提取其中的时间线事件。

请严格按照以下 JSON Schema 格式返回结果：
{{
    "events": [
        {{
            "id": "event_ch 章节号",
            "chapter": 章节号（整数）,
            "summary": "事件摘要（20-50 字）",
            "description": "事件详细描述（100 字以内，可选）",
            "character_ids": ["char_人物 1", "char_人物 2", ...],
            "location": "事件发生地点（可选）",
            "timestamp": "时间戳或大致时间（可选）"
        }}
    ]
}}

请按章节顺序提取每个重要事件。

小说文本：
{text}

请只返回 JSON，不要包含任何额外说明：
"""


# ==================== 提取器实现 ====================

class CharacterExtractor:
    """人物提取器 - 使用 LLM 进行智能提取"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化人物提取器

        Args:
            llm_client: LLM 客户端实例，如果为 None 则使用 MockLLMClient
        """
        self.llm_client = llm_client or MockLLMClient()

    def extract(self, text: str) -> List[Character]:
        """从文本中提取人物"""
        prompt = CHARACTER_EXTRACTION_PROMPT.format(text=text)
        messages = [{"role": "user", "content": prompt}]

        response = self.llm_client.chat(messages)
        data = self._parse_json_response(response)

        if not data or "characters" not in data:
            return []

        characters = []
        for char_data in data["characters"]:
            character = Character(
                id=char_data.get("id", f"char_{char_data.get('name', 'unknown')}"),
                name=char_data.get("name", ""),
                description=char_data.get("description", ""),
                traits=char_data.get("traits", []),
                goals=char_data.get("goals", []),
                background=char_data.get("background"),
                appearance=char_data.get("appearance")
            )
            characters.append(character)

        return characters

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 返回的 JSON 响应"""
        # 尝试直接解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # 尝试提取代码块中的 JSON
        match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试查找第一个 { 和最后一个 } 之间的内容
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass

        return None


class RelationshipExtractor:
    """关系提取器 - 使用 LLM 进行智能提取"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or MockLLMClient()

    def extract(self, text: str) -> List[Relationship]:
        """从文本中提取人物关系"""
        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(text=text)
        messages = [{"role": "user", "content": prompt}]

        response = self.llm_client.chat(messages)
        data = self._parse_json_response(response)

        if not data or "relationships" not in data:
            return []

        relationships = []
        for rel_data in data["relationships"]:
            relationship = Relationship(
                id=rel_data.get("id", f"rel_unknown"),
                character_id_1=rel_data.get("character_id_1", ""),
                character_id_2=rel_data.get("character_id_2", ""),
                type=rel_data.get("type", "unknown"),
                description=rel_data.get("description", ""),
                conflict_level=rel_data.get("conflict_level", 0),
                strength=rel_data.get("strength", 3)
            )
            relationships.append(relationship)

        return relationships

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


class TimelineExtractor:
    """时间线提取器 - 使用 LLM 进行智能提取"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or MockLLMClient()

    def extract(self, text: str) -> List[TimelineEvent]:
        """从文本中提取时间线事件"""
        prompt = TIMELINE_EXTRACTION_PROMPT.format(text=text)
        messages = [{"role": "user", "content": prompt}]

        response = self.llm_client.chat(messages)
        data = self._parse_json_response(response)

        if not data or "events" not in data:
            return []

        events = []
        for event_data in data["events"]:
            event = TimelineEvent(
                id=event_data.get("id", f"event_ch{event_data.get('chapter', 'unknown')}"),
                chapter=event_data.get("chapter", 0),
                summary=event_data.get("summary", ""),
                description=event_data.get("description"),
                character_ids=event_data.get("character_ids", []),
                location=event_data.get("location"),
                timestamp=event_data.get("timestamp")
            )
            events.append(event)

        return events

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
    # 演示用法：使用 Mock 客户端
    mock_response = '''
    {
        "characters": [
            {
                "id": "char_harry",
                "name": "哈利·波特",
                "description": "著名的年轻巫师，额头上有一道闪电形伤疤",
                "traits": ["勇敢", "忠诚", "冲动"],
                "goals": ["打败伏地魔", "保护朋友"],
                "background": "孤儿，11 岁时得知自己是巫师",
                "appearance": "黑发绿眼，戴眼镜，额头有闪电伤疤"
            }
        ]
    }
    '''

    client = MockLLMClient(mock_response)
    extractor = CharacterExtractor(client)

    test_text = "哈利·波特是一个年轻的巫师..."
    characters = extractor.extract(test_text)

    for char in characters:
        print(f"人物：{char.name}, 特质：{char.traits}")
