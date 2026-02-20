@Qwen3.5，后端 API 已经顺利跑通！现在我们正式进入第三阶段：打造美观的前端 UI 工作台。

请为我编写一个完整的前端页面 index.html。为了快速验证并展示效果，请采用纯前端 CDN 引入的方式，将 Vue 3、Element Plus、Tailwind CSS、Axios 和 ECharts 全部集成在这个 HTML 文件中。

页面需求与交互逻辑：

全局布局：使用 Tailwind 构建一个现代、暗黑/科技风格（深色模式）的控制台界面。顶部为系统标题。

上传与轮询区：

提供一个原生的 <input type="file"> 或拖拽上传区域。

点击上传后，调用后端的 POST http://127.0.0.1:8000/api/v1/novel/upload。

拿到 task_id 后，展示 Element Plus 的进度条组件 <el-progress>，每 2 秒轮询一次 GET /api/v1/tasks/{task_id} 更新进度和提示文字。

结果展示区 (使用 <el-tabs> 分作三屏，任务 COMPLETED 后展示)：

Tab 1：数据看板 (Overview)：展示总人物数、总场景数等统计数据，并使用 ECharts 渲染一个 graph (力导向图) 来展示人物关系（读取 JSON 中的 relationships，点是人物，边是关系）。

Tab 2：剧本模式 (Script View)：遍历 JSON 中的 script_scenes。用优雅的卡片流展示：【场景头：时间/地点】->【动作】->【对白列表】。排版要像真实的影视剧本。

Tab 3：分镜墙 (Storyboard)：遍历 storyboard_shots。使用 CSS Grid 实现多列卡片布局。每张卡片展示：镜头编号、景别(特写/全景)、运镜方向、画面描述和时长。

执行要求：
不需要构建复杂的 Node 工程，请直接把包含完整 Vue 3 <script setup> 逻辑、API 调用方法、ECharts 渲染逻辑的 index.html 代码一次性输出给我。注意处理跨域请求路径（默认后端在 http://127.0.0.1:5003）。