# -*- coding: utf-8 -*-
"""
Phase 2: API 化改造 - FastAPI Web 接口层

本模块提供基于 FastAPI 的 RESTful API 接口，支持：
1. 小说文件上传和后台异步处理
2. 任务状态查询
3. 处理结果获取
4. CORS 跨域支持

核心设计：
- 使用 BackgroundTasks 执行耗时任务，不阻塞 HTTP 响应
- 使用内存 TaskStore 保存任务状态
- 工业级错误处理和参数验证
"""
import json
import os
import uuid
import shutil
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ==================== 数据模型 ====================

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo(BaseModel):
    """任务信息模型"""
    task_id: str = Field(..., description="任务唯一标识符")
    status: TaskStatus = Field(..., description="当前任务状态")
    progress: int = Field(default=0, description="处理进度百分比 (0-100)")
    message: Optional[str] = Field(default=None, description="任务状态消息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    error_message: Optional[str] = Field(default=None, description="错误信息（如果失败）")


class TaskResult(BaseModel):
    """任务结果模型"""
    task_id: str = Field(..., description="任务唯一标识符")
    status: TaskStatus = Field(..., description="任务状态")
    result: Dict[str, Any] = Field(..., description="处理结果数据")
    completed_at: datetime = Field(..., description="完成时间")


class UploadResponse(BaseModel):
    """上传响应模型"""
    task_id: str = Field(..., description="任务唯一标识符")
    status: TaskStatus = Field(..., description="初始任务状态")
    message: str = Field(..., description="响应消息")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    detail: str = Field(..., description="错误详情")


# ==================== 任务存储 ====================

import threading

class TaskStore:
    """
    内存任务存储

    使用线程锁保证线程安全
    生产环境可替换为 Redis 或其他持久化存储。
    """

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()  # 线程锁

    def create_task(self, task_id: str) -> Dict[str, Any]:
        """创建新任务"""
        with self._lock:
            task = {
                "task_id": task_id,
                "status": TaskStatus.PENDING,
                "progress": 0,
                "message": "任务已创建，等待处理",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "completed_at": None,
                "error_message": None,
                "result": None,
                "temp_dir": None  # 临时目录路径
            }
            self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新任务状态（线程安全）"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if status is not None:
                task["status"] = status
            if progress is not None:
                task["progress"] = progress
            if message is not None:
                task["message"] = message
            if error_message is not None:
                task["error_message"] = error_message

            task["updated_at"] = datetime.now()

            if status == TaskStatus.COMPLETED:
                task["completed_at"] = datetime.now()

            return task

    def set_result(self, task_id: str, result: Dict[str, Any]) -> bool:
        """设置任务结果（线程安全）"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task["result"] = result
            task["status"] = TaskStatus.COMPLETED
            task["completed_at"] = datetime.now()
            task["updated_at"] = datetime.now()
            return True

    def cleanup_task(self, task_id: str) -> None:
        """清理任务（删除临时文件）"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.get("temp_dir"):
                temp_dir = task["temp_dir"]
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            if task_id in self._tasks:
                del self._tasks[task_id]


# 全局任务存储实例
task_store = TaskStore()


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="Novel Processing API",
    description="小说自动化处理系统 - 从小说文本生成剧本和分镜",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源跨域
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)


# ==================== 工具函数 ====================

def get_long_novel_processor():
    """获取 LongNovelProcessor 实例"""
    from main import LongNovelProcessor, create_llm_client

    llm_client = create_llm_client()
    processor = LongNovelProcessor(
        llm_client=llm_client,
        max_chunk_size=8000,
        enable_memory_merge=True,
        enable_checkpoint=False,  # API 模式下禁用检查点
        use_vector_memory=True
    )
    return processor


def process_novel_background(task_id: str, novel_path: str, output_path: str):
    """
    后台处理小说任务

    该函数在后台异步执行，不阻塞 HTTP 响应

    Args:
        task_id: 任务 ID
        novel_path: 小说文件路径
        output_path: 输出文件路径
    """
    try:
        # 更新状态为处理中
        task_store.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=10,
            message="正在加载小说文件..."
        )

        # 获取处理器
        processor = get_long_novel_processor()

        # 更新进度
        task_store.update_task(
            task_id,
            progress=30,
            message="正在处理章节，提取人物和关系..."
        )

        # 处理小说
        result = processor.process_novel(
            file_path=novel_path,
            output_path=output_path
        )

        # 更新进度
        task_store.update_task(
            task_id,
            progress=90,
            message="正在整理结果..."
        )

        # 设置结果
        task_store.set_result(task_id, {
            "metadata": result.get("metadata", {}),
            "statistics": result.get("statistics", {}),
            "characters": result.get("characters", []),
            "relationships": result.get("relationships", []),
            "timeline_events": result.get("timeline_events", []),
            "script_scenes": result.get("script_scenes", []),
            "storyboard_shots": result.get("storyboard_shots", [])
        })

        # 更新最终状态
        task_store.update_task(
            task_id,
            progress=100,
            message="处理完成！"
        )

    except Exception as e:
        # 处理失败
        task_store.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error_message=str(e),
            message=f"处理失败：{str(e)}"
        )
        # 记录详细错误日志
        import traceback
        print(f"[ERROR] Task {task_id} failed:")
        traceback.print_exc()


# ==================== API 端点 ====================

@app.get("/", response_model=Dict[str, str])
async def root():
    """API 根路径 - 健康检查"""
    return {
        "service": "Novel Processing API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.post(
    "/api/v1/novel/upload",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "文件格式错误"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"}
    }
)
async def upload_novel(
    file: UploadFile = File(..., description="上传的小说文件（.txt 格式）")
):
    """
    上传小说文件并创建后台处理任务

    接收上传的 .txt 文件，保存到临时目录，创建后台任务并立即返回 task_id

    Args:
        file: 上传的小说文件

    Returns:
        包含 task_id 的响应

    Raises:
        HTTPException: 文件格式不正确或服务器错误
    """
    # 验证文件扩展名
    if not file.filename.lower().endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式：{file.filename}，请上传 .txt 格式的文件"
        )

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix=f"novel_{uuid.uuid4().hex[:8]}_")

    try:
        # 保存上传的文件
        novel_path = os.path.join(temp_dir, file.filename)
        with open(novel_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 创建任务
        task_id = uuid.uuid4().hex
        task = task_store.create_task(task_id)
        task["temp_dir"] = temp_dir

        # 定义输出路径
        output_path = os.path.join(temp_dir, f"result_{task_id}.json")

        # 启动后台任务
        # 注意：使用 BackgroundTasks 确保任务在后台异步执行
        # 不会阻塞当前 HTTP 响应
        import asyncio

        def run_background_task():
            try:
                process_novel_background(task_id, novel_path, output_path)
            except Exception as e:
                print(f"[ERROR] Background task failed: {e}")

        # 在后台线程中执行
        import threading
        thread = threading.Thread(target=run_background_task)
        thread.daemon = True
        thread.start()

        return UploadResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=f"文件上传成功，任务已创建并开始处理"
        )

    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误：{str(e)}"
        )


@app.get(
    "/api/v1/tasks/{task_id}",
    response_model=TaskInfo,
    responses={
        404: {"model": ErrorResponse, "description": "任务不存在"}
    }
)
async def get_task_status(task_id: str):
    """
    查询任务状态

    根据 task_id 查询当前处理状态和进度

    Args:
        task_id: 任务唯一标识符

    Returns:
        任务状态信息

    Raises:
        HTTPException: 任务不存在
    """
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在：{task_id}"
        )

    return TaskInfo(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        created_at=task["created_at"],
        updated_at=task["updated_at"],
        completed_at=task["completed_at"],
        error_message=task.get("error_message")
    )


@app.get(
    "/api/v1/tasks/{task_id}/result",
    response_model=TaskResult,
    responses={
        404: {"model": ErrorResponse, "description": "任务不存在"},
        400: {"model": ErrorResponse, "description": "任务未完成"}
    }
)
async def get_task_result(task_id: str):
    """
    获取任务处理结果

    当任务状态为 COMPLETED 时，返回小说提取的完整 JSON 数据
    包含 characters, relationships, scenes, shots 等

    Args:
        task_id: 任务唯一标识符

    Returns:
        完整的处理结果

    Raises:
        HTTPException: 任务不存在或未完成
    """
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在：{task_id}"
        )

    if task["status"] != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未完成，当前状态：{task['status']}"
        )

    if task["result"] is None:
        raise HTTPException(
            status_code=500,
            detail="任务已完成但未找到结果数据"
        )

    return TaskResult(
        task_id=task["task_id"],
        status=task["status"],
        result=task["result"],
        completed_at=task["completed_at"]
    )


@app.delete(
    "/api/v1/tasks/{task_id}",
    response_model=Dict[str, str],
    responses={
        404: {"model": ErrorResponse, "description": "任务不存在"}
    }
)
async def delete_task(task_id: str):
    """
    删除任务

    清理任务数据和临时文件

    Args:
        task_id: 任务唯一标识符

    Returns:
        删除结果

    Raises:
        HTTPException: 任务不存在
    """
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在：{task_id}"
        )

    task_store.cleanup_task(task_id)

    return {"message": f"任务 {task_id} 已删除"}


@app.get("/api/v1/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len(task_store._tasks)
    }


# ==================== 启动配置 ====================

if __name__ == "__main__":
    import uvicorn

    # 开发模式启动
    # 生产环境建议使用：uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式启用热重载
        log_level="info"
    )
