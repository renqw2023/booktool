# -*- coding: utf-8 -*-
"""
Phase 2: API 化改造 - API 接口测试

本测试文件验证 FastAPI API 接口的功能：
1. 任务创建和状态查询
2. 文件上传处理
3. 任务结果获取
4. 错误处理
"""
import pytest
import json
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import os

# 导入 API 模块
from api import app, task_store, TaskStore, TaskStatus, get_long_novel_processor


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def temp_novel_file():
    """创建临时小说文件用于测试"""
    # 创建一个简单的测试小说文件
    novel_content = """第一章 初遇

李明走进了咖啡馆，看到了坐在窗边的张华。
"好久不见，"李明说道。
张华抬起头，微笑着说："是啊，已经三年了。"

第二章 冒险的开始

"我们需要找到那个古老的地图，"张华神秘地说。
李明点了点头："我父亲说过，它藏在图书馆的地下室里。"
两人决定第二天一早就出发。

第三章 挑战

地下室的门被锁住了。"我来试试这个，"李明从口袋里掏出一把钥匙。
门开了，里面一片黑暗。
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(novel_content)
        temp_path = f.name

    yield temp_path

    # 清理
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestTaskStore:
    """测试任务存储"""

    def setup_method(self):
        """每个测试前重置任务存储"""
        task_store._tasks = {}

    def test_create_task(self):
        """测试创建任务"""
        task_id = "test_task_001"
        task = task_store.create_task(task_id)

        assert task["task_id"] == task_id
        assert task["status"] == TaskStatus.PENDING
        assert task["progress"] == 0
        assert task["result"] is None

    def test_get_task(self):
        """测试获取任务"""
        task_id = "test_task_002"
        task_store.create_task(task_id)

        task = task_store.get_task(task_id)
        assert task is not None
        assert task["task_id"] == task_id

        # 测试不存在的任务
        nonexistent_task = task_store.get_task("nonexistent")
        assert nonexistent_task is None

    def test_update_task(self):
        """测试更新任务"""
        task_id = "test_task_003"
        task_store.create_task(task_id)

        # 更新状态
        updated = task_store.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=50,
            message="处理中"
        )

        assert updated["status"] == TaskStatus.PROCESSING
        assert updated["progress"] == 50
        assert updated["message"] == "处理中"

    def test_set_result(self):
        """测试设置任务结果"""
        task_id = "test_task_004"
        task_store.create_task(task_id)

        result_data = {"characters": [], "relationships": []}
        success = task_store.set_result(task_id, result_data)

        assert success is True
        task = task_store.get_task(task_id)
        assert task["status"] == TaskStatus.COMPLETED
        assert task["result"] == result_data

    def test_cleanup_task(self):
        """测试清理任务"""
        task_id = "test_task_005"
        task_store.create_task(task_id)

        task_store.cleanup_task(task_id)

        # 验证任务已被删除
        task = task_store.get_task(task_id)
        assert task is None


class TestAPIEndpoints:
    """测试 API 端点"""

    def setup_method(self):
        """每个测试前重置任务存储"""
        task_store._tasks = {}

    def test_root(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "Novel Processing API"
        assert data["status"] == "running"

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_get_task_not_found(self, client):
        """测试获取不存在的任务"""
        response = client.get("/api/v1/tasks/nonexistent")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data

    def test_get_task_status(self, client):
        """测试获取任务状态"""
        # 先创建一个任务
        task_id = "test_task_status_001"
        task_store.create_task(task_id)

        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "pending"

    def test_delete_task(self, client):
        """测试删除任务"""
        task_id = "test_task_delete_001"
        task_store.create_task(task_id)

        response = client.delete(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200

        # 验证任务已被删除
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 404

    def test_get_result_task_not_completed(self, client):
        """测试获取未完成的任务结果"""
        task_id = "test_result_001"
        task = task_store.create_task(task_id)
        task["status"] = TaskStatus.PENDING

        response = client.get(f"/api/v1/tasks/{task_id}/result")
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "尚未完成" in data["detail"]

    def test_get_result_success(self, client):
        """测试成功获取任务结果"""
        task_id = "test_result_002"
        task = task_store.create_task(task_id)
        task["status"] = TaskStatus.COMPLETED
        task["result"] = {
            "characters": [{"id": "char_1", "name": "测试人物"}],
            "relationships": []
        }
        task["completed_at"] = "2024-01-01T00:00:00"

        response = client.get(f"/api/v1/tasks/{task_id}/result")
        assert response.status_code == 200

        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "completed"
        assert "result" in data
        assert len(data["result"]["characters"]) == 1

    def test_upload_novel_wrong_format(self, client):
        """测试上传错误格式的文件"""
        # 创建一个测试的 PDF 文件（模拟）
        response = client.post(
            "/api/v1/novel/upload",
            files={"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        )
        assert response.status_code == 400

        data = response.json()
        assert "不支持的文件格式" in data["detail"]


class TestUploadAndProcess:
    """测试完整的上传和处理流程"""

    def setup_method(self):
        """每个测试前重置任务存储"""
        task_store._tasks = {}

    def test_upload_novel_success(self, client, temp_novel_file):
        """测试成功上传小说文件"""
        with open(temp_novel_file, 'r', encoding='utf-8') as f:
            content = f.read()

        response = client.post(
            "/api/v1/novel/upload",
            files={"file": (os.path.basename(temp_novel_file), content.encode('utf-8'), "text/plain")}
        )

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert data["status"] == "pending"
        assert "任务已创建" in data["message"]

    def test_full_workflow(self, client, temp_novel_file):
        """测试完整的工作流程：上传 -> 查询状态 -> 获取结果"""
        # 由于实际处理需要调用 LLM API，这里使用 Mock 方式测试

        # 1. 创建任务
        task_id = "mock_task_001"
        task = task_store.create_task(task_id)

        # 2. 模拟任务完成
        mock_result = {
            "metadata": {
                "source_file": "test.txt",
                "total_chapters": 3,
                "processing_duration": "0:01:00",
                "completed_at": "2024-01-01T00:00:00"
            },
            "statistics": {
                "total_characters": 2,
                "total_relationships": 1,
                "total_events": 3,
                "total_scenes": 5,
                "total_shots": 10
            },
            "characters": [
                {"id": "char_liming", "name": "李明", "description": "主角"},
                {"id": "char_zhanghua", "name": "张华", "description": "配角"}
            ],
            "relationships": [
                {"id": "rel_001", "character_id_1": "char_liming", "character_id_2": "char_zhanghua", "type": "朋友"}
            ],
            "timeline_events": [
                {"id": "event_ch1", "chapter": 1, "summary": "初遇"}
            ],
            "script_scenes": [
                {"id": "scene_001", "chapter": 1, "location": "咖啡馆"}
            ],
            "storyboard_shots": [
                {"id": "shot_001", "scene_id": "scene_001", "shot_number": 1, "shot_type": "全景"}
            ]
        }

        task_store.set_result(task_id, mock_result)

        # 3. 查询状态
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        # 4. 获取结果
        response = client.get(f"/api/v1/tasks/{task_id}/result")
        assert response.status_code == 200
        assert response.json()["result"]["statistics"]["total_characters"] == 2


class TestLongNovelProcessorIntegration:
    """测试 LongNovelProcessor 集成"""

    def test_processor_initialization(self):
        """测试处理器初始化"""
        # 注意：这需要 LLM_API_KEY 环境变量
        # 如果没有设置，将使用 Mock 客户端
        try:
            processor = get_long_novel_processor()
            assert processor is not None
            assert processor.enable_memory_merge is True
            assert processor.use_vector_memory is True
        except ImportError as e:
            # 如果 main.py 导入失败，跳过此测试
            pytest.skip(f"无法导入 LongNovelProcessor: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
