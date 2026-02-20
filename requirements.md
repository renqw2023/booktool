# 目标：使用 Python 从零构建完整的『自动化小说理解与剧本分镜生成系统』

请严格遵循 TDD（测试驱动开发）原则，按顺序完成以下 5 个阶段。每个阶段必须编写对应的 pytest 单元测试，且测试必须 100% 通过（All Green）才能进入下一阶段！如果测试失败，请读取报错、修复代码并重试。

## Phase 1: 核心数据结构定义
- 使用 Pydantic 或 Dataclass 定义核心实体：Character, Relationship, TimelineEvent, ScriptScene, StoryboardShot。
- 编写测试并跑通。

## Phase 2: 信息提取引擎 (NLU)
- 创建 `extractor.py`，包含提取人物关系和时间线的框架。
- 编写测试，用硬编码的小说 mock 数据验证提取结果。

## Phase 3: 剧本生成模块
- 创建 `script_generator.py`，实现小说转化为 `ScriptScene` 的逻辑。
- 编写并跑通测试。

## Phase 4: 分镜转化模块
- 创建 `storyboard_generator.py`，实现 `ScriptScene` 拆解为 `StoryboardShot` 的逻辑。
- 编写并跑通测试。

## Phase 5: 系统流水线整合 (Pipeline)
- 创建 `main.py` 和 `NovelProcessor` 类，将 Phase 2 到 Phase 4 串联成完整流水线。
- 编写端到端 (End-to-End) 综合测试并跑通。

## 规则
你必须一步一步来。在解决当前 Phase 的测试报错之前，绝对不允许编写下一个 Phase 的代码！当所有代码编写完毕，且 `pytest` 运行结果为 100% 通过时，输出暗号：<promise>SYSTEM_ALL_COMPLETE</promise>