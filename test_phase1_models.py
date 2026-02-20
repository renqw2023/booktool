"""Phase 1: 核心数据结构定义的测试"""
import pytest

from models import Character, Relationship, TimelineEvent, ScriptScene, StoryboardShot


class TestCharacter:
    """测试 Character 实体"""

    def test_create_basic_character(self):
        """测试创建基本人物"""
        char = Character(
            id="char_001",
            name="张三",
            description="一个年轻的剑客"
        )
        assert char.id == "char_001"
        assert char.name == "张三"
        assert char.description == "一个年轻的剑客"
        assert char.traits == []
        assert char.goals == []

    def test_character_with_traits(self):
        """测试带特质的人物"""
        char = Character(
            id="char_002",
            name="李四",
            description="神秘的商人",
            traits=["聪明", "贪婪"],
            goals=["找到宝藏"]
        )
        assert char.traits == ["聪明", "贪婪"]
        assert char.goals == ["找到宝藏"]


class TestRelationship:
    """测试 Relationship 实体"""

    def test_create_relationship(self):
        """测试创建关系"""
        rel = Relationship(
            id="rel_001",
            character_id_1="char_001",
            character_id_2="char_002",
            type="朋友",
            description="志同道合的伙伴"
        )
        assert rel.character_id_1 == "char_001"
        assert rel.character_id_2 == "char_002"
        assert rel.type == "朋友"

    def test_relationship_with_conflict(self):
        """测试冲突关系"""
        rel = Relationship(
            id="rel_002",
            character_id_1="char_001",
            character_id_2="char_003",
            type="敌人",
            description="生死仇敌",
            conflict_level=5
        )
        assert rel.type == "敌人"
        assert rel.conflict_level == 5


class TestTimelineEvent:
    """测试 TimelineEvent 实体"""

    def test_create_event(self):
        """测试创建时间线事件"""
        event = TimelineEvent(
            id="event_001",
            chapter=1,
            summary="张三初次登场",
            description="在一个雨夜，张三走进了小镇的酒馆"
        )
        assert event.chapter == 1
        assert event.summary == "张三初次登场"

    def test_event_with_characters(self):
        """测试带人物的事件"""
        event = TimelineEvent(
            id="event_002",
            chapter=2,
            summary="张三与李四相遇",
            character_ids=["char_001", "char_002"],
            location="小镇酒馆"
        )
        assert event.character_ids == ["char_001", "char_002"]
        assert event.location == "小镇酒馆"


class TestScriptScene:
    """测试 ScriptScene 实体"""

    def test_create_scene(self):
        """测试创建剧本场景"""
        scene = ScriptScene(
            id="scene_001",
            chapter=1,
            location="小镇酒馆 - 内部",
            time="夜",
            description="昏暗的酒馆，几个客人在低声交谈"
        )
        assert scene.location == "小镇酒馆 - 内部"
        assert scene.time == "夜"

    def test_scene_with_dialogue(self):
        """测试带对白的场景"""
        scene = ScriptScene(
            id="scene_002",
            chapter=1,
            location="小镇酒馆 - 内部",
            time="夜",
            description="张三走向柜台",
            dialogues=[
                {"character_id": "char_001", "line": "老板，来杯酒"},
                {"character_id": "char_004", "line": "客官稍等"}
            ]
        )
        assert len(scene.dialogues) == 2
        assert scene.dialogues[0]["line"] == "老板，来杯酒"


class TestStoryboardShot:
    """测试 StoryboardShot 实体"""

    def test_create_shot(self):
        """测试创建分镜镜头"""
        shot = StoryboardShot(
            id="shot_001",
            scene_id="scene_001",
            shot_number=1,
            shot_type="全景",
            description="酒馆的全景，展示环境"
        )
        assert shot.shot_number == 1
        assert shot.shot_type == "全景"

    def test_shot_with_camera_direction(self):
        """测试带镜头指示的分镜"""
        shot = StoryboardShot(
            id="shot_002",
            scene_id="scene_001",
            shot_number=2,
            shot_type="特写",
            description="张三的脸部特写",
            camera_direction="缓慢推进",
            duration_seconds=3.5
        )
        assert shot.shot_type == "特写"
        assert shot.camera_direction == "缓慢推进"
        assert shot.duration_seconds == 3.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
