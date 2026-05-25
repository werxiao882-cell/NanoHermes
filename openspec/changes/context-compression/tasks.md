## 1. 项目设置

- [ ] 1.1 创建 `src/compression/` 目录结构
- [ ] 1.2 定义压缩相关类型和接口
- [ ] 1.3 配置 vitest 测试框架

## 2. ContextCompressor 核心实现

- [ ] 2.1 实现 ContextCompressor 类
- [ ] 2.2 实现 compress 方法，包含头部/尾部保护和摘要生成
- [ ] 2.3 实现 calculateSummaryBudget 方法（20% 比例，最小/最大限制）
- [ ] 2.4 实现 protectHead 方法（保护前 N 条消息）
- [ ] 2.5 实现 protectTail 方法（使用 token 预算保护尾部）
- [ ] 2.6 实现 getMiddle 方法（获取中间消息）
- [ ] 2.7 实现 estimateContentLength 和 estimateMessageLength 方法
- [ ] 2.8 实现 generateSummary 方法，调用辅助 LLM
- [ ] 2.9 编写 ContextCompressor 的单元测试
  - [ ] 2.9.1 测试压缩长对话
  - [ ] 2.9.2 测试摘要包含正确前缀
  - [ ] 2.9.3 测试小内容预算
  - [ ] 2.9.4 测试中等内容预算
  - [ ] 2.9.5 测试大内容预算上限
  - [ ] 2.9.6 测试保护前 3 条消息
  - [ ] 2.9.7 测试消息少于保护数量
  - [ ] 2.9.8 测试保护尾部消息

## 3. 辅助客户端实现

- [ ] 3.1 实现 AuxiliaryClient 类
- [ ] 3.2 实现提供商解析逻辑
- [ ] 3.3 实现连接错误处理
- [ ] 3.4 编写辅助客户端的单元测试
  - [ ] 3.4.1 测试解析 auto 提供商
  - [ ] 3.4.2 测试解析明确提供商
  - [ ] 3.4.3 测试连接错误重试

## 4. 工具输出剪枝实现

- [ ] 4.1 实现 pruneToolOutputs 方法
- [ ] 4.2 实现 truncateToolCallArgs 方法，保持 JSON 有效性
- [ ] 4.3 实现 truncateObjectStrings 辅助方法
- [ ] 4.4 实现图像部分剥离方法
- [ ] 4.5 编写工具输出剪枝的单元测试
  - [ ] 4.5.1 测试替换长工具输出
  - [ ] 4.5.2 测试保留短工具输出
  - [ ] 4.5.3 测试非工具消息不变
  - [ ] 4.5.4 测试截断 JSON 字符串值
  - [ ] 4.5.5 测试非 JSON 参数不变
  - [ ] 4.5.6 测试嵌套对象字符串截断
  - [ ] 4.5.7 测试数组字符串截断

## 5. 可行性检查实现

- [ ] 5.1 实现 checkCompressionModelFeasibility 方法
- [ ] 5.2 实现辅助模型上下文窗口验证
- [ ] 5.3 编写可行性检查的单元测试
