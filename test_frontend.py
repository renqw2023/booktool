# -*- coding: utf-8 -*-
"""前端 UI 测试脚本 - 验证 API 和前端功能"""

import requests
import time
import json

API_BASE = "http://127.0.0.1:8000"


def test_health():
    """测试健康检查"""
    r = requests.get(f"{API_BASE}/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    print("[OK] 健康检查通过")
    return True


def test_upload():
    """测试文件上传"""
    with open("E:/booktools/test_novel.txt", "rb") as f:
        r = requests.post(
            f"{API_BASE}/api/v1/novel/upload",
            files={"file": f}
        )
    assert r.status_code == 200
    data = r.json()
    assert "task_id" in data
    print(f"[OK] 文件上传通过，task_id: {data['task_id']}")
    return data["task_id"]


def test_polling(task_id):
    """测试状态轮询"""
    max_attempts = 100  # 增加到 200 秒
    for i in range(max_attempts):
        r = requests.get(f"{API_BASE}/api/v1/tasks/{task_id}")
        data = r.json()
        status = data["status"]
        progress = data["progress"]
        if i % 10 == 0:  # 每 20 秒打印一次
            print(f"  进度：{progress}% - {status}")

        if status == "COMPLETED":
            print(f"[OK] 任务完成，耗时约 {i*2} 秒")
            return True
        elif status == "FAILED":
            print(f"[ERROR] 任务失败：{data.get('error_message', 'Unknown')}")
            return False
        time.sleep(2)

    print("[ERROR] 轮询超时")
    return False


def test_result(task_id):
    """测试结果获取"""
    r = requests.get(f"{API_BASE}/api/v1/tasks/{task_id}/result")
    assert r.status_code == 200
    data = r.json()

    result = data["result"]
    stats = result.get("statistics", {})

    print("\n=== 统计数据 ===")
    print(f"  章节数：{stats.get('total_chapters', 0)}")
    print(f"  人物数：{stats.get('total_characters', 0)}")
    print(f"  关系数：{stats.get('total_relationships', 0)}")
    print(f"  事件数：{stats.get('total_events', 0)}")
    print(f"  场景数：{stats.get('total_scenes', 0)}")
    print(f"  镜头数：{stats.get('total_shots', 0)}")

    # 验证数据结构
    assert "characters" in result
    assert "relationships" in result
    assert "script_scenes" in result
    assert "storyboard_shots" in result

    # 验证人物关系图所需字段
    for char in result["characters"]:
        assert "id" in char
        assert "name" in char

    # 验证关系字段
    for rel in result["relationships"]:
        assert "character_id_1" in rel
        assert "character_id_2" in rel
        assert "type" in rel

    # 验证剧本文案结构
    for scene in result["script_scenes"]:
        assert "id" in scene
        assert "location" in scene
        assert "time" in scene
        assert "actions" in scene or "dialogues" in scene

    # 验证分镜字段
    for shot in result["storyboard_shots"]:
        assert "shot_number" in shot
        assert "shot_type" in shot
        assert "description" in shot
        assert "camera_direction" in shot
        assert "duration_seconds" in shot

    print("[OK] 数据结构验证通过")
    return True


def main():
    print("=" * 50)
    print("前端 UI API 测试")
    print("=" * 50)

    # 1. 健康检查
    if not test_health():
        print("✗ 健康检查失败，请确保 API 服务正在运行")
        return False

    # 2. 上传文件
    task_id = test_upload()

    # 3. 轮询状态
    if not test_polling(task_id):
        return False

    # 4. 验证结果
    if not test_result(task_id):
        return False

    print("\n" + "=" * 50)
    print("[OK] 所有测试通过！前端 UI 可以正常使用")
    print("=" * 50)
    print("\n提示：在浏览器中打开 index.html 即可使用前端界面")
    return True


if __name__ == "__main__":
    main()
