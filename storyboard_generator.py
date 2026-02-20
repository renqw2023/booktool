# -*- coding: utf-8 -*-
"""Phase 4: 分镜转化模块"""
from typing import List
from models import ScriptScene, StoryboardShot


class StoryboardGenerator:
    """分镜生成器 - 将剧本场景拆解为分镜镜头"""

    def __init__(self):
        # 镜头类型
        self.shot_types = ["全景", "中景", "近景", "特写"]

    def generate(self, scene: ScriptScene) -> List[StoryboardShot]:
        """从剧本场景生成分镜镜头"""
        shots = []

        # 第一个镜头：建立场景的全景
        establishing_shot = self._create_establishing_shot(scene, len(shots) + 1)
        shots.append(establishing_shot)

        # 如果有对白，为每个对白生成镜头
        if scene.dialogues:
            for dialogue in scene.dialogues:
                dialogue_shot = self._create_dialogue_shot(scene, dialogue, len(shots) + 1)
                shots.append(dialogue_shot)
        else:
            # 没有对白时，生成一个描述性镜头
            action_shot = self._create_action_shot(scene, len(shots) + 1)
            shots.append(action_shot)

        return shots

    def _create_establishing_shot(self, scene: ScriptScene, shot_number: int) -> StoryboardShot:
        """创建建立场景的全景镜头"""
        return StoryboardShot(
            id=f"{scene.id}_shot_{shot_number}",
            scene_id=scene.id,
            shot_number=shot_number,
            shot_type="全景",
            description=f"{scene.location} 的全景，{scene.time}",
            camera_direction="固定镜头",
            duration_seconds=3.0
        )

    def _create_dialogue_shot(self, scene: ScriptScene, dialogue: dict, shot_number: int) -> StoryboardShot:
        """创建对白镜头"""
        char_id = dialogue.get("character_id", "unknown")
        line = dialogue.get("line", "")

        return StoryboardShot(
            id=f"{scene.id}_shot_{shot_number}",
            scene_id=scene.id,
            shot_number=shot_number,
            shot_type="近景",
            description=f"{char_id} 说：{line}",
            camera_direction="轻微推进",
            duration_seconds=2.5,
            characters_in_shot=[char_id]
        )

    def _create_action_shot(self, scene: ScriptScene, shot_number: int) -> StoryboardShot:
        """创建动作镜头"""
        return StoryboardShot(
            id=f"{scene.id}_shot_{shot_number}",
            scene_id=scene.id,
            shot_number=shot_number,
            shot_type="中景",
            description=scene.description,
            camera_direction="跟随移动",
            duration_seconds=3.0
        )
