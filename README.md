# 自动化小说理解与剧本分镜生成系统

> 🎬 基于 LLM 的 AI 驱动小说分析引擎 - 将文学作品自动转化为专业剧本和分镜

## 项目简介

本系统是一个工业级的 AI 驱动流水线，能够：

1. **智能人物提取** - 从小说文本中自动识别和提取人物信息、性格特质、背景故事
2. **关系网络分析** - 分析人物之间的关系类型、冲突程度和情感强度
3. **时间线构建** - 按章节提取关键事件、地点和参与人物
4. **剧本生成** - 将叙事性小说转化为标准格式的影视剧本
5. **分镜拆解** - 从剧本场景生成专业的分镜镜头设计（包含运镜、时长、音频指导）

## 核心特性

### ✅ LLM 驱动的智能提取

系统使用大语言模型进行真正的语义理解，而非硬编码的字符串匹配。支持：

- **泛化能力强** - 可处理任意小说文本（《哈利波特》《三体》《流浪地球》等）
- **结构化输出** - 严格按照预定义的数据模型返回结果
- **Prompt 工程** - 精心设计的提示词确保高质量的提取效果

### ✅ 工业级架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      NovelProcessor                         │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: 信息提取                                           │
│  ├── CharacterExtractor (人物提取器)                         │
│  ├── RelationshipExtractor (关系提取器)                      │
│  └── TimelineExtractor (时间线提取器)                        │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: 剧本生成                                           │
│  └── ScriptGenerator (剧本生成器)                            │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: 分镜生成                                           │
│  └── StoryboardGenerator (分镜生成器)                        │
└─────────────────────────────────────────────────────────────┘
```

### ✅ 完整的测试覆盖

- **41 个单元测试** 100% 通过
- 使用 `MockLLMClient` 进行本地快速测试
- 支持注入真实 LLM 客户端（OpenAI 兼容接口）

## 快速开始

### 环境要求

- Python 3.10+
- 可选：OpenAI API 密钥或其他 LLM 服务

### 安装依赖

```bash
pip install openai pytest
```

### 基本使用

```python
from main import NovelProcessor
from extractor import OpenAICompatibleClient

# 配置 LLM 客户端
llm_client = OpenAICompatibleClient(
    api_key="your-api-key",
    base_url="https://api.openai.com/v1",
    model="gpt-4o-mini"
)

# 创建处理器
processor = NovelProcessor(llm_client)

# 读取小说文本
novel_text = """
第一章：初遇

哈利·波特是一个年轻的巫师，额头上有一道闪电形的伤疤。
他独自一人在对角巷闲逛，准备购买开学用品。
"""

# 执行完整流水线
result = processor.process(novel_text)

# 访问结果
print(f"人物：{len(result['characters'])} 个")
print(f"关系：{len(result['relationships'])} 个")
print(f"事件：{len(result['timeline_events'])} 个")
print(f"剧本场景：{len(result['script_scenes'])} 个")
print(f"分镜镜头：{len(result['storyboard_shots'])} 个")
```

### 运行测试

```bash
# 运行所有测试
pytest -v

# 运行特定模块测试
pytest test_phase2_extractor.py -v
pytest test_phase3_script_generator.py -v
pytest test_phase4_storyboard.py -v
pytest test_phase5_pipeline.py -v
```

## 核心模块说明

### extractor.py

LLM 驱动的信息提取引擎，包含三个核心提取器：

| 提取器 | 功能 | 输出 |
|--------|------|------|
| `CharacterExtractor` | 人物提取 | `Character` 实体列表 |
| `RelationshipExtractor` | 关系提取 | `Relationship` 实体列表 |
| `TimelineExtractor` | 时间线提取 | `TimelineEvent` 实体列表 |

**支持的 LLM 客户端：**
- `MockLLMClient` - 用于测试的 Mock 客户端
- `OpenAICompatibleClient` - OpenAI 及兼容 API 客户端

### script_generator.py

将时间线事件转化为标准剧本格式：

- 自动识别场景时间（日/夜/黄昏/黎明）
- 将叙事语言转化为可视化的 `actions`（动作描写）
- 生成符合人物性格的 `dialogues`（对白）
- 包含 fallback 机制保证系统健壮性

### storyboard_generator.py

从剧本场景生成专业分镜镜头：

- 自动设计镜头类型（全景/中景/近景/特写）
- 智能分配运镜方向（推/拉/摇/移/跟/固定）
- 预估镜头时长和音频方向
- 第一个镜头自动设为建立场景的全景

### models.py

5 个核心数据实体定义：

```python
@dataclass
class Character:          # 人物实体
@dataclass
class Relationship:       # 关系实体
@dataclass
class TimelineEvent:      # 时间线事件
@dataclass
class ScriptScene:        # 剧本场景
@dataclass
class StoryboardShot:     # 分镜镜头
```

## 输出示例

### 人物提取示例
```
人物：哈利·波特
描述：著名的年轻巫师，额头上有闪电形伤疤
特质：['勇敢', '忠诚', '冲动']
目标：['学习魔法', '对抗伏地魔']
背景：孤儿，11 岁进入霍格沃茨
外貌：黑发绿眼，戴眼镜
```

### 剧本场景示例
```
场景 ID: scene_event_ch1
地点：对角巷
时间：日
动作：['哈利走进奥利凡德魔杖店', '哈利挑选魔杖']
对白：[]
```

### 分镜镜头示例
```
镜头 1: 全景 - 对角巷的全景，各种商店林立
运镜：缓慢推进
时长：3.0s
音频：街道嘈杂声
```

## 测试覆盖

| 测试模块 | 测试数 | 状态 |
|----------|--------|------|
| test_phase1_models.py | 10 | ✅ 通过 |
| test_phase2_extractor.py | 10 | ✅ 通过 |
| test_phase3_script_generator.py | 7 | ✅ 通过 |
| test_phase4_storyboard.py | 9 | ✅ 通过 |
| test_phase5_pipeline.py | 5 | ✅ 通过 |
| **总计** | **41** | ✅ **100%** |

## 扩展与定制

### 使用其他 LLM 服务

继承 `LLMClient` 基类实现自定义客户端：

```python
from extractor import LLMClient

class MyLLMClient(LLMClient):
    def chat(self, messages, temperature=0.7) -> str:
        # 实现你的 LLM 调用逻辑
        return "response"
```

### 自定义 Prompt 模板

修改各模块中的 Prompt 模板变量以适配不同场景：

- `CHARACTER_EXTRACTION_PROMPT`
- `RELATIONSHIP_EXTRACTION_PROMPT`
- `TIMELINE_EXTRACTION_PROMPT`
- `SCENE_GENERATION_PROMPT`
- `STORYBOARD_GENERATION_PROMPT`

## 项目结构

```
booktools/
├── models.py                    # 核心数据实体定义
├── extractor.py                 # 人物/关系/时间线提取器
├── script_generator.py          # 剧本生成器
├── storyboard_generator.py      # 分镜生成器
├── main.py                      # 系统主流水线
├── test_phase1_models.py        # 数据模型测试
├── test_phase2_extractor.py     # 提取器测试
├── test_phase3_script_generator.py  # 剧本生成器测试
├── test_phase4_storyboard.py    # 分镜生成器测试
├── test_phase5_pipeline.py      # 流水线集成测试
└── README.md                    # 项目文档
```

## 开发日志

### v2.0 - LLM 驱动重构版

- ✅ 删除所有硬编码（NAMES、keywords 等）
- ✅ 引入 LLM 调用框架和 Prompt 工程
- ✅ 重写 extractor.py、script_generator.py、storyboard_generator.py
- ✅ 测试使用《哈利波特》文段，验证泛化能力
- ✅ 41 个测试 100% 通过

### v1.0 - 基础架构版

- 核心数据模型定义
- 基于规则的提取逻辑
- 基础流水线架构

## License

MIT License
