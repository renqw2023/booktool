# -*- coding: utf-8 -*-
"""Phase 4: 分镜转化模块 - LLM 驱动版本

本模块使用大语言模型将剧本场景拆解为专业的分镜镜头。
LLM 负责根据画面张力和戏剧节奏自动分配镜头类型和运镜方向。
"""
import re
import json
import os
from typing import List, Optional, Dict, Any
from models import ScriptScene, StoryboardShot


# ==================== LLM 客户端接口 ====================

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
    """OpenAI 兼容 API 客户端（带重试机制）"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: str = "gpt-4o-mini", max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__(api_key, base_url)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """调用 OpenAI 兼容 API（带自动重试）"""
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
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature
                )
                return response.choices[0].message.content

            except ImportError:
                raise ImportError("请安装 openai 包：pip install openai")

            except APIStatusError as e:
                last_exception = e
                status_code = e.status_code
                if status_code in (429, 500, 502, 503, 504):
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"[RETRY] API 错误 ({status_code})，{delay:.1f}秒后重试...")
                        time.sleep(delay)
                        continue
                raise

            except APIConnectionError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"[RETRY] 连接错误，{delay:.1f}秒后重试...")
                    time.sleep(delay)
                    continue
                raise

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"[RETRY] 未知错误，{delay:.1f}秒后重试...")
                    time.sleep(delay)
                    continue
                raise

        if last_exception:
            raise last_exception
        raise RuntimeError("重试循环异常退出")


# ==================== Prompt 模板 ====================

STORYBOARD_GENERATION_PROMPT = """你是一个经验丰富的电影分镜师，擅长将剧本场景拆解为具有视觉冲击力的分镜镜头。

请分析以下剧本场景，并将其拆解为 3-6 个专业的分镜镜头：

场景信息：
- 场景 ID: {scene_id}
- 章节：第{chapter}章
- 地点：{location}
- 时间：{time}
- 场景描述：{description}
- 动作列表：{actions}
- 对白列表：{dialogues}
- 涉及人物：{characters}

作为分镜师，你需要考虑：
1. 第一个镜头应该是建立镜头（Establishing Shot），用于展示场景环境
2. 根据动作和对白的戏剧张力，选择合适的镜头类型（全景/中景/近景/特写）
3. 设计合理的运镜方向（推/拉/摇/移/跟/固定等）
4. 为每个镜头预估合理的时长
5. 考虑音频方向（背景音乐/音效/对白等）

请严格按照以下 JSON Schema 格式返回结果：
{{
    "shots": [
        {{
            "id": "{scene_id}_shot_1",
            "scene_id": "{scene_id}",
            "shot_number": 1,
            "shot_type": "全景/中景/近景/特写/大特写",
            "description": "镜头内容描述（50-100 字）",
            "camera_direction": "固定镜头/推镜头/拉镜头/摇镜头/移镜头/跟镜头",
            "duration_seconds": 3.0,
            "audio_direction": "音频说明",
            "characters_in_shot": ["char_人物 1", ...]
        }},
        ...
    ]
}}

注意：
- shot_number 从 1 开始连续编号
- 第一个镜头应该是建立场景的全景镜头
- 根据对白数量安排适当的反应镜头
- 动作场面应该使用更有动感的运镜方式

请只返回 JSON，不要包含任何额外说明：
"""


# ==================== 分镜生成器实现 ====================

class StoryboardGenerator:
    """分镜生成器 - 使用 LLM 进行智能拆解"""

    def __init__(self, llm_client: Optional[LLMClient] = None,
                 memory_bank: Optional[Any] = None):
        """
        初始化分镜生成器

        Args:
            llm_client: LLM 客户端实例，如果为 None 则使用 MockLLMClient
            memory_bank: 可选的记忆银行，用于注入人物上下文
        """
        self.llm_client = llm_client or MockLLMClient()
        self.memory_bank = memory_bank  # 支持向量化记忆银行或传统 MemoryBank

    def generate(self, scene: ScriptScene,
                 memory_context: Optional[str] = None) -> List[StoryboardShot]:
        """从剧本场景生成分镜镜头

        Args:
            scene: 剧本场景
            memory_context: 可选的记忆上下文，用于保持人物连贯性
        """
        prompt_parts = []

        # 如果有记忆上下文，添加到 prompt 前面
        if memory_context:
            prompt_parts.append(f"以下是相关人物的记忆信息，请在生成分镜时参考这些信息来保持人物的一致性：\n{memory_context}\n\n")

        prompt_parts.append(STORYBOARD_GENERATION_PROMPT.format(
            scene_id=scene.id,
            chapter=scene.chapter,
            location=scene.location,
            time=scene.time,
            description=scene.description,
            actions=", ".join(scene.actions) if scene.actions else "无明显动作",
            dialogues=str(scene.dialogues) if scene.dialogues else "无对白",
            characters=", ".join(scene.character_ids) if scene.character_ids else "未明确"
        ))

        prompt = "".join(prompt_parts)
        messages = [{"role": "user", "content": prompt}]

        response = self.llm_client.chat(messages, temperature=0.8)
        data = self._parse_json_response(response)

        if not data or "shots" not in data:
            # 如果 LLM 解析失败，返回一个基础版本
            return self._create_fallback_shots(scene)

        shots_data = data["shots"]
        shots = []

        for shot_data in shots_data:
            shot = StoryboardShot(
                id=shot_data.get("id", f"{scene.id}_shot_{shot_data.get('shot_number', len(shots)+1)}"),
                scene_id=shot_data.get("scene_id", scene.id),
                shot_number=shot_data.get("shot_number", len(shots) + 1),
                shot_type=shot_data.get("shot_type", "中景"),
                description=shot_data.get("description", scene.description),
                camera_direction=shot_data.get("camera_direction"),
                duration_seconds=shot_data.get("duration_seconds", 3.0),
                audio_direction=shot_data.get("audio_direction"),
                characters_in_shot=shot_data.get("characters_in_shot", [])
            )
            shots.append(shot)

        # 确保至少有一个镜头
        if not shots:
            shots = self._create_fallback_shots(scene)

        return shots

    def _create_fallback_shots(self, scene: ScriptScene) -> List[StoryboardShot]:
        """当 LLM 解析失败时，创建基础分镜"""
        shots = []

        # 第一个镜头：建立场景的全景
        establishing_shot = StoryboardShot(
            id=f"{scene.id}_shot_1",
            scene_id=scene.id,
            shot_number=1,
            shot_type="全景",
            description=f"{scene.location} 的全景，{scene.time}",
            camera_direction="固定镜头",
            duration_seconds=3.0,
            audio_direction="环境音"
        )
        shots.append(establishing_shot)

        # 如果有对白，为每个对白生成镜头
        if scene.dialogues:
            for i, dialogue in enumerate(scene.dialogues):
                char_id = dialogue.get("character_id", "unknown")
                line = dialogue.get("line", "")

                dialogue_shot = StoryboardShot(
                    id=f"{scene.id}_shot_{len(shots) + 1}",
                    scene_id=scene.id,
                    shot_number=len(shots) + 1,
                    shot_type="近景",
                    description=f"{char_id} 说：{line}",
                    camera_direction="轻微推进",
                    duration_seconds=2.5,
                    audio_direction=f"{char_id} 对白",
                    characters_in_shot=[char_id]
                )
                shots.append(dialogue_shot)
        else:
            # 没有对白时，生成一个动作镜头
            action_shot = StoryboardShot(
                id=f"{scene.id}_shot_{len(shots) + 1}",
                scene_id=scene.id,
                shot_number=len(shots) + 1,
                shot_type="中景",
                description=scene.description,
                camera_direction="跟随移动",
                duration_seconds=3.0,
                audio_direction="动作音效"
            )
            shots.append(action_shot)

        return shots

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
        "shots": [
            {
                "id": "scene_001_shot_1",
                "scene_id": "scene_001",
                "shot_number": 1,
                "shot_type": "全景",
                "description": "霍格沃茨大礼堂的全景，数百支蜡烛悬浮在空中，新生们紧张地站在中央",
                "camera_direction": "缓慢推进",
                "duration_seconds": 4.0,
                "audio_direction": "低沉的交谈声，神秘的背景音乐",
                "characters_in_shot": ["char_harry", "char_ron", "char_hermione"]
            },
            {
                "id": "scene_001_shot_2",
                "scene_id": "scene_001",
                "shot_number": 2,
                "shot_type": "近景",
                "description": "哈利紧张地吞咽口水，手不自觉地摸向额头的伤疤",
                "camera_direction": "固定镜头",
                "duration_seconds": 2.5,
                "audio_direction": "哈利的呼吸声",
                "characters_in_shot": ["char_harry"]
            },
            {
                "id": "scene_001_shot_3",
                "scene_id": "scene_001",
                "shot_number": 3,
                "shot_type": "特写",
                "description": "分院帽突然张开大嘴，开始歌唱",
                "camera_direction": "快速拉远",
                "duration_seconds": 3.0,
                "audio_direction": "分院帽的歌声",
                "characters_in_shot": []
            }
        ]
    }
    '''

    client = MockLLMClient(mock_response)
    generator = StoryboardGenerator(client)

    from models import ScriptScene
    scene = ScriptScene(
        id="scene_001",
        chapter=1,
        location="霍格沃茨大礼堂",
        time="夜",
        description="新生们参加分院仪式",
        actions=["哈利紧张地握紧拳头", "赫敏轻声安慰罗恩"],
        dialogues=[
            {"character_id": "char_harry", "line": "我希望我能进格兰芬多。"},
            {"character_id": "char_ron", "line": "我也是。"}
        ],
        character_ids=["char_harry", "char_ron", "char_hermione"]
    )

    shots = generator.generate(scene)
    for shot in shots:
        print(f"镜头{shot.shot_number}: {shot.shot_type} - {shot.description[:30]}...")
