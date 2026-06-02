## 1. 项目设置

- [x] 1.1 创建 `src/compression/` 目录结构
- [x] 1.2 定义压缩相关类型和接口
- [x] 1.3 配置 pytest 测试框架

## 2. ContextEngine 抽象基类

- [x] 2.1 实现 ContextEngine 抽象基类（ABC）
- [x] 2.2 定义 3 个核心抽象方法：`update_from_response`, `should_compress`, `compress`
- [x] 2.3 实现可选工具接口：`get_tool_schemas`, `handle_tool_call`
- [x] 2.4 编写 ContextEngine 的单元测试

## 3. ContextCompressor 核心实现

- [x] 3.1 实现 ContextCompressor 类（继承 ContextEngine）
- [x] 3.2 实现 compress 方法，包含分层压缩策略
- [x] 3.3 实现 calculate_summary_budget 方法（20% 比例，最小 2000 token，最大 12000 token）
- [x] 3.4 实现 protect_head 方法（保护前 3 条消息）
- [x] 3.5 实现 protect_tail 方法（使用 token 预算保护尾部）
- [x] 3.6 实现 get_middle 方法（获取中间消息）
- [x] 3.7 实现 estimate_content_length 和 estimate_message_length 方法
- [x] 3.8 实现 generate_summary 方法，调用辅助 LLM 生成结构化摘要
- [x] 3.9 实现迭代摘要更新（_previous_summary 存储和合并）
- [x] 3.10 实现预飞行压缩检查（进入主循环前估算 token 数）
- [x] 3.11 实现响应后压缩触发（context_length_exceeded 或超阈值）
- [x] 3.12 编写 ContextCompressor 的单元测试

## 4. 辅助客户端实现

- [x] 4.1 实现 AuxiliaryClient 类
- [x] 4.2 实现提供商解析逻辑
- [x] 4.3 实现连接错误处理
- [x] 4.4 编写辅助客户端的单元测试

## 5. 工具输出剪枝实现

- [x] 5.1 实现 prune_tool_outputs 方法（>200 字符替换为占位符）
- [x] 5.2 实现 truncate_tool_call_args 方法，保持 JSON 有效性
- [x] 5.3 实现 _truncate_object_strings 辅助方法（递归截断字符串叶子节点）
- [x] 5.4 编写工具输出剪枝的单元测试

## 6. Session Splitting 实现

- [x] 6.1 实现 session_splitting 方法
- [x] 6.2 创建新 session，parent_session_id 指向旧 session
- [x] 6.3 摘要作为新 session 第一条消息
- [x] 6.4 尾部保护消息搬到新 session
- [x] 6.5 编写 Session Splitting 的单元测试

## 7. on_pre_compress 钩子实现

- [x] 7.1 实现 on_pre_compress 钩子调用逻辑
- [x] 7.2 集成 MemoryManager.on_pre_compress_all()
- [x] 7.3 编写 on_pre_compress 钩子的单元测试

## 8. 可行性检查实现

- [x] 8.1 实现 check_compression_model_feasibility 方法
- [x] 8.2 实现辅助模型上下文窗口验证
- [x] 8.3 编写可行性检查的单元测试
  - [x] 8.3.1 测试辅助模型窗口小于最小要求
  - [x] 8.3.2 测试辅助模型窗口小于主模型阈值（警告）
  - [x] 8.3.3 测试可行配置
