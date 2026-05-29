## 1. 项目设置

- [x] 1.1 创建 `src/conversation/` 目录结构
- [x] 1.2 定义对话循环相关类型和接口
- [x] 1.3 配置 pytest 测试框架

## 2. 核心对话循环实现

- [x] 2.1 实现 ConversationLoop 类
- [x] 2.2 实现 runConversation 方法
- [x] 2.3 实现 callModel 方法
- [x] 2.4 实现 dispatchTool 方法
- [x] 2.5 实现中断检查逻辑
- [x] 2.6 实现迭代预算管理
- [x] 2.7 实现 debug 模式（请求体/响应体 JSON 输出）
- [x] 2.8 实现 reasoning 思考内容输出
- [x] 2.9 实现 on_message_append 回调（实时保存 tool 消息）
- [x] 2.10 编写对话循环的单元测试
  - [x] 2.10.1 测试单轮工具调用
  - [x] 2.10.2 测试多轮工具调用
  - [x] 2.10.3 测试达到迭代限制
  - [x] 2.10.4 测试中断停止循环
  - [x] 2.10.5 测试 debug 模式输出请求体 JSON
  - [x] 2.10.6 测试 debug 模式输出响应体 JSON
  - [x] 2.10.7 测试 debug 模式输出 reasoning 内容

## 3. 错误分类器实现

- [x] 3.1 实现 FailoverReason 枚举
- [x] 3.2 实现 ClassifiedError 类
- [x] 3.3 实现 ErrorClassifier 类
- [x] 3.4 实现所有错误模式匹配（auth、billing、rate_limit、context_overflow 等）
- [x] 3.5 实现恢复策略决策逻辑
- [x] 3.6 编写错误分类的单元测试
  - [x] 3.6.1 测试分类 401 认证错误
  - [x] 3.6.2 测试分类 402 计费错误
  - [x] 3.6.3 测试分类 429 速率限制
  - [x] 3.6.4 测试分类上下文溢出
  - [x] 3.6.5 测试分类服务器错误
  - [x] 3.6.6 测试分类未知错误

## 4. CLI 斜杠命令系统

- [x] 4.1 实现 /clear 清空对话
- [x] 4.2 实现 /status 查看会话状态
- [x] 4.3 实现 /sessions 查看历史会话列表
- [x] 4.4 实现 /title 设置会话标题
- [x] 4.5 实现 /skills 查看可用技能
- [x] 4.6 实现 /tools 查看已加载工具列表
- [x] 4.7 所有命令使用 /xxx 格式，模型不拦截

## 5. 现代化 TUI 聊天界面

- [x] 5.1 添加 rich 和 prompt_toolkit 依赖到 pyproject.toml
- [x] 5.2 实现 TUI 布局类（顶部横幅、对话区域、输入区）
- [x] 5.3 实现顶部横幅组件（模型、工具、技能、会话信息）
- [x] 5.4 实现对话输出区域（流式显示工具调用和响应）
- [x] 5.5 实现底部固定输入区
- [x] 5.6 实现斜杠命令自动补全
- [x] 5.7 实现 --tui 命令行参数启动 TUI 模式
- [x] 5.8 实现工具调用进度显示（preparing xxx... 格式）
- [x] 5.9 实现工具执行时间显示
- [x] 5.10 实现代理响应分隔符
- [x] 5.11 编写 TUI 组件单元测试

## 6. 传统 CLI 工具调用显示

- [x] 6.1 实现 ConversationLoop 工具回调机制（on_tool_start, on_tool_end）
- [x] 6.2 实现传统 CLI 工具调用显示（工具名称、参数摘要、执行耗时）
- [x] 6.3 移除死循环防护（不限制模型能力）
- [x] 6.4 更新 main.py 使用工具回调

## 7. 后台审查实现

- [x] 7.1 实现 spawnBackgroundReview 函数
- [x] 7.2 实现 forkAgent 函数
- [x] 7.3 实现 buildReviewPrompt 函数
- [x] 7.4 实现 _MEMORY_REVIEW_PROMPT 和 _SKILL_REVIEW_PROMPT 常量
- [x] 7.5 编写后台审查的单元测试
  - [x] 7.5.1 测试 fork Agent 继承配置
  - [x] 7.5.2 测试审查记忆
  - [x] 7.5.3 测试审查技能
  - [x] 7.5.4 测试无内容可保存

## 8. TUI 实际逻辑集成

- [x] 8.1 实现 TUI 对话循环集成（替换 Mock 逻辑）
- [x] 8.2 实现 TUI 工具调用显示
- [x] 8.3 实现 TUI 流式响应显示
- [x] 8.4 实现 TUI 思考过程显示
- [x] 8.5 实现 TUI 工具调用简要结果显示
- [x] 8.6 编写 TUI 集成测试
- [x] 8.7 将 TUI 设为默认聊天界面，移除传统 CLI 交互模式
- [x] 8.8 实现模型思考内容折叠显示（+ Thought: xxxms，点击展开）

## 9. 工具调用简要结果显示

- [x] 9.1 实现 Read 操作简要结果显示
- [x] 9.2 实现 Write 操作简要结果显示
- [x] 9.3 实现 Glob 操作简要结果显示
- [x] 9.4 集成到传统 CLI 聊天界面
- [x] 9.5 集成到 TUI 聊天界面
