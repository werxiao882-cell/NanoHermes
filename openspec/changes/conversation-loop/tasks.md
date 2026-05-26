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
- [x] 2.7 实现 debug 模式（请求/响应输出）
- [x] 2.8 编写对话循环的单元测试
  - [x] 2.8.1 测试单轮工具调用
  - [x] 2.8.2 测试多轮工具调用
  - [x] 2.8.3 测试达到迭代限制
  - [x] 2.8.4 测试中断停止循环
  - [x] 2.8.5 测试 debug 模式输出请求
  - [x] 2.8.6 测试 debug 模式输出响应

## 3. 错误分类器实现

- [ ] 3.1 实现 FailoverReason 枚举
- [ ] 3.2 实现 ClassifiedError 类
- [ ] 3.3 实现 ErrorClassifier 类
- [ ] 3.4 实现所有错误模式匹配（auth、billing、rate_limit、context_overflow 等）
- [ ] 3.5 实现恢复策略决策逻辑
- [ ] 3.6 编写错误分类的单元测试
  - [ ] 3.6.1 测试分类 401 认证错误
  - [ ] 3.6.2 测试分类 402 计费错误
  - [ ] 3.6.3 测试分类 429 速率限制
  - [ ] 3.6.4 测试分类上下文溢出
  - [ ] 3.6.5 测试分类服务器错误
  - [ ] 3.6.6 测试分类未知错误

## 4. 后台审查实现

- [ ] 4.1 实现 spawnBackgroundReview 函数
- [ ] 4.2 实现 forkAgent 函数
- [ ] 4.3 实现 buildReviewPrompt 函数
- [ ] 4.4 实现 _MEMORY_REVIEW_PROMPT 和 _SKILL_REVIEW_PROMPT 常量
- [ ] 4.5 编写后台审查的单元测试
  - [ ] 4.5.1 测试 fork Agent 继承配置
  - [ ] 4.5.2 测试审查记忆
  - [ ] 4.5.3 测试审查技能
  - [ ] 4.5.4 测试无内容可保存
