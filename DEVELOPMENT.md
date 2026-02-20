# 小说自动化处理系统 - 开发文档

> 从小说文本到剧本分镜的 AI 转换工作台
> 版本：3.0.0
> 更新日期：2026-02-20

---

## 目录

1. [项目概述](#项目概述)
2. [系统架构](#系统架构)
3. [技术栈](#技术栈)
4. [开发日志](#开发日志)
5. [API 接口文档](#api 接口文档)
6. [前端 UI 说明](#前端 ui 说明)
7. [部署指南](#部署指南)

---

## 项目概述

### 功能简介

本系统是一个基于 AI 大语言模型的小说自动化处理工具，能够：

- 📖 **智能分析**：从小说文本中自动提取人物、关系、时间线事件
- 🎬 **剧本生成**：将小说内容转换为标准影视剧本格式
- 📽️ **分镜生成**：为每个剧本场景生成详细的分镜镜头描述
- 📊 **可视化展示**：通过 Web UI 展示人物关系图谱、剧本和分镜

### 适用场景

- 小说改编影视剧的前期分析
- 编剧辅助工具
- 文学作品结构化分析
- IP 开发评估

---

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  数据看板   │  │  剧本模式   │  │     分镜墙          │ │
│  │  (ECharts)  │  │  (Card View)│  │  (CSS Grid Layout)  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Axios (REST API)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  文件上传   │  │  任务管理   │  │    结果返回         │ │
│  │  /upload    │  │  /tasks/:id │  │  /tasks/:id/result  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Background Task Processor                  ││
│  │           (LongNovelProcessor + Memory)                 ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              │ LLM API Call
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM Service                              │
│         (OpenAI Compatible API / 本地模型)                   │
└─────────────────────────────────────────────────────────────┘
```

### 核心模块

```
booktools/
├── api.py                  # FastAPI Web 服务层
├── main.py                 # 长篇小说处理引擎
├── models.py               # 数据模型定义
├── chunking_engine.py      # 文本分块引擎
├── vector_store.py         # 向量记忆存储
├── extractor.py            # 信息提取器
├── script_generator.py     # 剧本生成器
├── storyboard_generator.py # 分镜生成器
├── index.html              # 前端 UI 界面
└── requirements.txt        # Python 依赖
```

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主要编程语言 |
| FastAPI | 0.104+ | Web 框架 |
| Uvicorn | 0.24+ | ASGI 服务器 |
| Pydantic | 2.0+ | 数据验证 |
| OpenAI SDK | 1.3+ | LLM API 调用 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.x | 前端框架 |
| Element Plus | latest | UI 组件库 |
| Tailwind CSS | latest | 原子化 CSS |
| Axios | latest | HTTP 客户端 |
| ECharts | 5.4+ | 图表库 |

---

## 开发日志

### Phase 1: 核心引擎开发

**目标**: 实现小说处理的基础数据处理能力

**完成内容**:
- `models.py` - 定义 5 个核心数据类：
  - `Character` - 人物实体
  - `Relationship` - 人物关系
  - `TimelineEvent` - 时间线事件
  - `ScriptScene` - 剧本场景
  - `StoryboardShot` - 分镜镜头

- `chunking_engine.py` - 长文本分块引擎：
  - 按章节智能切分
  - 支持上下文记忆合并
  - 检查点保存与恢复

- `vector_store.py` - 向量化记忆银行：
  - 基于 TF-IDF + 余弦相似度
  - 解决记忆膨胀问题
  - 高效的人物记忆检索

- `extractor.py` - 信息提取器：
  - CharacterExtractor - 人物提取
  - RelationshipExtractor - 关系提取
  - TimelineExtractor - 时间线提取

**测试文件**:
- `test_phase1_models.py`
- `test_chunking_engine.py`

---

### Phase 2: API 化改造

**目标**: 将核心引擎封装为 RESTful API 服务

**完成内容**:
- `api.py` - FastAPI Web 服务层：
  - `POST /api/v1/novel/upload` - 文件上传
  - `GET /api/v1/tasks/{task_id}` - 任务状态查询
  - `GET /api/v1/tasks/{task_id}/result` - 结果返回
  - `DELETE /api/v1/tasks/{task_id}` - 任务删除

- `TaskStore` - 内存任务存储：
  - 线程安全的任务管理
  - 支持 PENDING/PROCESSING/COMPLETED/FAILED 状态
  - 后台异步任务执行

- CORS 跨域配置 - 支持前端跨域请求

**依赖追加**:
```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6
```

**测试文件**:
- `test_api.py`
- `test_frontend.py`

---

### Phase 3: 前端 UI 开发

**目标**: 打造美观易用的 Web 控制台

**完成内容**:
- `index.html` - 单文件前端应用 (729 行)：
  - 深色科技风格界面
  - 文件上传 + 拖拽支持
  - 实时进度轮询 (每 2 秒)
  - 三个功能 Tab

**Tab 1 - 数据看板**:
- 5 个统计卡片 (人物/关系/事件/场景/镜头)
- ECharts 力导向图展示人物关系
- 支持缩放和拖拽

**Tab 2 - 剧本模式**:
- 卡片流式布局
- 场景头 (时间/地点)
- 动作描述 (斜体样式)
- 对白气泡 (角色名 + 情绪)

**Tab 3 - 分镜墙**:
- CSS Grid 多列布局
- 镜头卡片 (编号/景别/运镜/时长)
- 悬停动画效果

---

## API 接口文档

### 基础信息

- **Base URL**: `http://127.0.0.1:8000`
- **API 版本**: v1
- **CORS**: 允许所有来源

### 接口列表

#### 1. 上传小说文件

```http
POST /api/v1/novel/upload
Content-Type: multipart/form-data
```

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | .txt 格式的小说文件 |

**响应示例**:
```json
{
  "task_id": "af29a8cff04541d59f1748b809b67f5c",
  "status": "pending",
  "message": "文件上传成功，任务已创建并开始处理"
}
```

---

#### 2. 查询任务状态

```http
GET /api/v1/tasks/{task_id}
```

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务唯一标识符 |

**响应示例**:
```json
{
  "task_id": "af29a8cff04541d59f1748b809b67f5c",
  "status": "processing",
  "progress": 30,
  "message": "正在处理章节，提取人物和关系...",
  "created_at": "2026-02-20T12:00:00",
  "updated_at": "2026-02-20T12:02:00"
}
```

**状态枚举**:
- `pending` - 等待处理
- `processing` - 处理中
- `completed` - 已完成
- `failed` - 失败

---

#### 3. 获取处理结果

```http
GET /api/v1/tasks/{task_id}/result
```

**前置条件**: 任务状态必须为 `COMPLETED`

**响应示例**:
```json
{
  "task_id": "af29a8cff04541d59f1748b809b67f5c",
  "status": "completed",
  "result": {
    "statistics": {
      "total_chapters": 3,
      "total_characters": 2,
      "total_relationships": 3,
      "total_events": 3,
      "total_scenes": 3,
      "total_shots": 17
    },
    "characters": [
      {
        "id": "char_LiMing",
        "name": "李明",
        "description": "一位勇敢的冒险者",
        "traits": ["勇敢", "聪明"],
        "goals": ["冒险", "拯救世界"]
      }
    ],
    "relationships": [
      {
        "id": "rel_李明_王华",
        "character_id_1": "char_LiMing",
        "character_id_2": "char_WangHua",
        "type": "朋友",
        "strength": 4
      }
    ],
    "script_scenes": [...],
    "storyboard_shots": [...]
  },
  "completed_at": "2026-02-20T12:05:00"
}
```

---

#### 4. 健康检查

```http
GET /api/v1/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-20T12:00:00",
  "active_tasks": 2
}
```

---

## 前端 UI 说明

### 界面布局

```
┌──────────────────────────────────────────────────────────┐
│  📖 小说自动化处理系统                    [API 在线]     │
│     从小说文本到剧本分镜的 AI 转换工作台                   │
├──────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐ │
│  │  文件上传                                          │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │   ☁️ 点击或拖拽上传小说文件                  │ │ │
│  │  │   支持 .txt 格式，建议不超过 10MB             │ │ │
│  │  │          [开始处理]                          │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  │                                                   │ │
│  │  进度：████████████░░░░░░░░  60%                  │ │
│  │  正在处理章节，提取人物和关系...                  │ │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  处理结果                     [处理新文件]         │ │
│  │  ┌─────────┬─────────┬─────────┐                  │ │
│  │  │ 数据看板│剧本模式 │ 分镜墙  │                  │ │
│  │  ├─────────┴─────────┴─────────┤                  │ │
│  │  │                             │                  │ │
│  │  │   (Tab 内容区)              │                  │ │
│  │  │                             │                  │ │
│  │  └─────────────────────────────┘                  │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 交互流程

1. **上传阶段**:
   - 用户选择/拖拽 .txt 文件
   - 调用 `POST /api/v1/novel/upload`
   - 获取 `task_id`

2. **轮询阶段**:
   - 显示进度条
   - 每 2 秒调用 `GET /api/v1/tasks/{task_id}`
   - 更新进度和状态文字

3. **展示阶段**:
   - 任务完成后显示三个 Tab
   - 加载统计数据和图表
   - 渲染剧本和分镜卡片

---

## 部署指南

### 环境要求

- Python 3.10+
- Node.js (可选，仅用于开发)
- 现代浏览器 (Chrome/Firefox/Edge)

### 安装步骤

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
# 创建 .env 文件
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

3. **启动 API 服务**
```bash
# 开发模式 (支持热重载)
python api.py

# 生产模式
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

4. **打开前端**
```bash
# 直接在浏览器打开
start index.html

# 或使用任意静态文件服务器
npx serve .
```

### 配置文件说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | LLM API 密钥 | - |
| `LLM_BASE_URL` | API 基础 URL | - |
| `LLM_MODEL` | 模型名称 | gpt-4o-mini |
| `OUTPUT_INDENT` | JSON 缩进 | true |

---

## 测试

### 运行测试

```bash
# 模型测试
python test_phase1_models.py

# 提取器测试
python test_phase2_extractor.py

# 剧本生成测试
python test_phase3_script_generator.py

# 分镜生成测试
python test_phase4_storyboard.py

# 完整流水线测试
python test_phase5_pipeline.py

# API 测试
python test_api.py

# 前端集成测试
python test_frontend.py
```

---

## 常见问题

### Q: 处理速度慢怎么办？
A: 处理速度主要取决于 LLM API 响应时间。可以尝试：
- 使用更快的模型 (如 gpt-4o-mini)
- 减小 chunk_size 参数
- 禁用记忆合并 (--no-memory-merge)

### Q: 内存占用过高？
A: 启用向量化记忆银行可显著降低内存占用：
```python
processor = LongNovelProcessor(use_vector_memory=True)
```

### Q: 前端无法连接 API?
A: 检查：
- API 服务是否运行在 8000 端口
- CORS 是否已配置
- 浏览器控制台是否有跨域错误

---

## 更新日志

### v3.0.0 (2026-02-20)
- ✨ 新增前端 UI 工作台
- ✨ 新增 ECharts 人物关系图
- ✨ 新增剧本模式和分镜墙展示
- 🔧 优化进度轮询机制
- 🐛 修复跨域请求问题

### v2.0.0 (2026-02-19)
- ✨ 新增 FastAPI Web 服务层
- ✨ 新增后台异步任务处理
- ✨ 新增任务状态管理
- 🔧 添加 CORS 跨域支持

### v1.0.0 (2026-02-18)
- ✨ 核心处理引擎完成
- ✨ 长文本分块支持
- ✨ 向量化记忆银行

---

## 许可证

MIT License

---

## 联系方式

项目地址：https://github.com/your-username/novel-processing-system