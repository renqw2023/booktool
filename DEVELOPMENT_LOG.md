# 开发日志

## 项目概述

**小说自动化处理与剧本分镜生成系统**

将长篇小说自动分析并转化为专业影视剧本和分镜镜头的 AI 驱动系统。

---

## 开发历程

### 2026-02-20 - 长文本处理引擎升级

#### 背景
原有系统只能处理短文本，面对几十万字的长篇小说会因 Token 超出上下文限制而崩溃。

#### 新增功能

1. **智能章节切分 (`chunking_engine.py`)**
   - 支持中文格式（第 1 章、第一章）和英文格式（Chapter 1）
   - 自动识别 1500+ 章节
   - 章节无法识别时按固定大小智能切分

2. **跨章节记忆合并 (`CharacterMemory`, `MemoryBank`)**
   - 人物特征在不同章节间平滑累积
   - 自动去重合并
   - 支持记忆持久化存储

3. **检查点机制**
   - 每处理 N 章自动保存进度
   - 支持中断后恢复处理

4. **命令行入口升级 (`main.py`)**
   ```bash
   python main.py --file novel.txt --output result.json
   ```

5. **配置管理**
   - 新增 `.env.example` 配置模板
   - 支持环境变量配置 LLM API

#### 代码质量改进

- 移除 `script_generator.py` 中的硬编码 time_keywords
- `extractor.py` 启用原生 JSON Structured Output
- 新增 18 个单元测试，覆盖率提升

#### 真实测试验证

- 测试文件：《放开那个女巫》（7MB，1506 章）
- 章节识别：成功识别全部 1506 章
- API 调用：阿里云 qwen-plus 成功提取人物

#### 提交记录

```
commit 6893106
feat: 添加长文本处理引擎

- 新增 chunking_engine.py
- 新增 .env.example
- 新增 test_chunking_engine.py (18 个测试)
- 更新 main.py (命令行参数)
- 更新 extractor.py (JSON Structured Output)
- 更新 script_generator.py (移除硬编码)
- 更新 .gitignore (忽略.env)
```

---

### 2026-02-20 - AI 核心升级 (no01.md)

#### 问题
初始版本存在"测试驱动作弊"行为：
- 硬编码人物名称（张三、李四）
- 硬编码时间关键词字典
- 字符串匹配代替真正的 NLU

#### 解决方案

1. **真正的 LLM 驱动提取 (`extractor.py`)**
   - 删除所有硬编码字典
   - 实现 `LLMClient` 基类
   - 实现 `MockLLMClient`（测试用）
   - 实现 `OpenAICompatibleClient`（生产用）

2. **高质量 Prompt 工程**
   - 人物提取 Prompt
   - 关系提取 Prompt
   - 时间线提取 Prompt
   - 支持 JSON Schema 结构化输出

3. **测试升级**
   - 使用《哈利波特》作为测试数据
   - 测试泛化能力
   - 28 个测试全部通过

---

### 2026-02-20 - 初始架构 (no02.md)

#### 核心数据结构 (`models.py`)

| 类名 | 说明 |
|------|------|
| `Character` | 人物实体 |
| `Relationship` | 人物关系 |
| `TimelineEvent` | 时间线事件 |
| `ScriptScene` | 剧本场景 |
| `StoryboardShot` | 分镜镜头 |

#### 处理流水线

```
小说文本
  → 人物/关系/时间线提取 (Extractor)
  → 剧本场景生成 (ScriptGenerator)
  → 分镜镜头拆解 (StoryboardGenerator)
  → JSON 输出
```

---

## 技术栈

- **语言**: Python 3.12
- **AI 模型**: 阿里云 qwen-plus / OpenAI GPT-4o-mini
- **测试框架**: pytest
- **数据处理**: 正则表达式 + JSON 解析

---

## 当前状态

- ✅ 核心处理引擎完成
- ✅ 长文本支持（1500+ 章节）
- ✅ 记忆合并机制
- ✅ 单元测试覆盖
- ✅ 真实数据验证

---

## 待办事项

- [ ] 支持更多输出格式（YAML、Markdown）
- [ ] 添加 Web 界面
- [ ] 支持向量数据库记忆存储
- [ ] 优化批量处理性能
