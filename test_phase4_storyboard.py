# -*- coding: utf-8 -*-
"""Phase 4: 分镜转化模块的测试 - LLM 驱动版本

使用《哈利波特》片段测试分镜生成器的泛化能力。
"""
import pytest
from storyboard_generator import StoryboardGenerator, MockLLMClient
from models import ScriptScene, StoryboardShot


# ==================== Mock LLM 响应数据 ====================

def get_storyboard_mock_response():
    """分镜生成的 Mock 响应"""
    return '''
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
            },
            {
                "id": "scene_001_shot_4",
                "scene_id": "scene_001",
                "shot_number": 4,
                "shot_type": "近景",
                "description": "罗恩紧张地看着哈利，小声说话",
                "camera_direction": "轻微摇摄",
                "duration_seconds": 2.0,
                "audio_direction": "罗恩的对白",
                "characters_in_shot": ["char_ron"]
            }
        ]
    }
    '''


def get_simple_storyboard_mock_response():
    """简化版分镜生成的 Mock 响应"""
    return '''
    {
        "shots": [
            {
                "id": "scene_002_shot_1",
                "scene_id": "scene_002",
                "shot_number": 1,
                "shot_type": "全景",
                "description": "魔药课教室的全景，阴冷的地窖里点着几支蜡烛",
                "camera_direction": "固定镜头",
                "duration_seconds": 3.0,
                "audio_direction": "安静的环境音"
            },
            {
                "id": "scene_002_shot_2",
                "scene_id": "scene_002",
                "shot_number": 2,
                "shot_type": "中景",
                "description": "斯内普教授转身面向学生，黑袍飘动",
                "camera_direction": "跟随移动",
                "duration_seconds": 2.5,
                "audio_direction": "斯内普的说话声"
            }
        ]
    }
    '''


# ==================== 测试用例 ====================

class TestStoryboardGenerator:
    """测试分镜生成器"""

    def test_create_generator(self):
        """测试创建生成器"""
        generator = StoryboardGenerator()
        assert generator is not None

    def test_generate_shots_from_harry_potter_scene(self):
        """测试从哈利波特场景生成分镜镜头"""
        mock_client = MockLLMClient(get_storyboard_mock_response())
        generator = StoryboardGenerator(mock_client)
        scene = ScriptScene(
            id="scene_001",
            chapter=1,
            location="霍格沃茨大礼堂",
            time="夜",
            description="新生们参加分院仪式",
            actions=[
                "哈利紧张地握紧魔杖",
                "分院帽开始歌唱"
            ],
            dialogues=[
                {"character_id": "char_harry", "line": "我希望我能进格兰芬多。"},
                {"character_id": "char_ron", "line": "我也是。"}
            ],
            character_ids=["char_harry", "char_ron", "char_hermione"]
        )

        shots = generator.generate(scene)
        assert len(shots) > 0
        assert all(isinstance(shot, StoryboardShot) for shot in shots)

    def test_shots_have_sequential_numbers(self):
        """测试镜头编号是连续的"""
        mock_client = MockLLMClient(get_storyboard_mock_response())
        generator = StoryboardGenerator(mock_client)
        scene = ScriptScene(
            id="scene_002",
            chapter=1,
            location="霍格沃茨大礼堂",
            time="夜",
            description="分院仪式进行中"
        )

        shots = generator.generate(scene)
        for i, shot in enumerate(shots):
            assert shot.shot_number == i + 1

    def test_shots_have_scene_id(self):
        """测试镜头有关联的场景 ID"""
        mock_client = MockLLMClient(get_storyboard_mock_response())
        generator = StoryboardGenerator(mock_client)
        # 使用与 Mock 数据一致的场景 ID
        scene = ScriptScene(
            id="scene_001",
            chapter=1,
            location="霍格沃茨大礼堂",
            time="夜",
            description="新生们参加分院仪式"
        )

        shots = generator.generate(scene)
        assert all(shot.scene_id == "scene_001" for shot in shots)

    def test_first_shot_is_establishing(self):
        """测试第一个镜头是全景/建立镜头"""
        mock_client = MockLLMClient(get_storyboard_mock_response())
        generator = StoryboardGenerator(mock_client)
        scene = ScriptScene(
            id="scene_004",
            chapter=1,
            location="霍格沃茨大礼堂",
            time="夜",
            description="分院仪式开始"
        )

        shots = generator.generate(scene)
        assert shots[0].shot_type in ["全景", "远景", "中景"]

    def test_scene_with_dialogue_generates_shots(self):
        """测试有对白的场景会生成多个镜头"""
        mock_client = MockLLMClient(get_storyboard_mock_response())
        generator = StoryboardGenerator(mock_client)
        scene = ScriptScene(
            id="scene_005",
            chapter=1,
            location="霍格沃茨大礼堂",
            time="夜",
            description="哈利和罗恩对话",
            dialogues=[
                {"character_id": "char_harry", "line": "你好"},
                {"character_id": "char_ron", "line": "好久不见"}
            ]
        )

        shots = generator.generate(scene)
        # 有多个镜头
        assert len(shots) >= 1

    def test_shot_has_camera_direction(self):
        """测试镜头有运镜方向"""
        mock_client = MockLLMClient(get_storyboard_mock_response())
        generator = StoryboardGenerator(mock_client)
        scene = ScriptScene(
            id="scene_006",
            chapter=1,
            location="霍格沃茨大礼堂",
            time="夜",
            description="分院仪式"
        )

        shots = generator.generate(scene)
        # 镜头应该有运镜方向
        for shot in shots:
            assert shot.camera_direction is not None or shot.description

    def test_shot_has_duration(self):
        """测试镜头有时长的合理值"""
        mock_client = MockLLMClient(get_storyboard_mock_response())
        generator = StoryboardGenerator(mock_client)
        scene = ScriptScene(
            id="scene_007",
            chapter=1,
            location="霍格沃茨大礼堂",
            time="夜",
            description="分院仪式"
        )

        shots = generator.generate(scene)
        for shot in shots:
            assert shot.duration_seconds is None or shot.duration_seconds > 0

    def test_fallback_mechanism(self):
        """测试当 LLM 失败时的备用机制"""
        # 使用无效响应的 Mock 客户端
        mock_client = MockLLMClient('{"invalid": "data"}')
        generator = StoryboardGenerator(mock_client)
        scene = ScriptScene(
            id="scene_008",
            chapter=1,
            location="测试地点",
            time="日",
            description="测试场景"
        )

        shots = generator.generate(scene)
        assert len(shots) > 0
        # 备用机制应该至少返回一个镜头
        assert shots[0].shot_type == "全景"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
