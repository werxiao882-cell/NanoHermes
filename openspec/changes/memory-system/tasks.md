## 1. 项目设置

- [x] 1.1 创建 `src/memory/` 目录结构
- [x] 1.2 定义 Python 接口和类型
- [x] 1.3 配置 pytest 测试框架

## 2. MemoryProvider 抽象基类

- [x] 2.1 实现 MemoryProvider 抽象基类（ABC）
- [x] 2.2 定义 4 个核心抽象方法：`name`, `is_available`, `initialize`, `system_prompt_block`
- [x] 2.3 实现 13 个可选方法的默认空实现
- [x] 2.4 编写 MemoryProvider 的单元测试
  - [x] 2.4.1 测试实现核心方法
  - [x] 2.4.2 测试可选钩子有默认实现
  - [x] 2.4.3 测试覆盖可选钩子
  - [x] 2.4.4 测试接收完整选项
  - [x] 2.4.5 测试跳过非 primary 上下文

## 3. MemoryManager 编排器

- [x] 3.1 实现 MemoryManager 类
- [x] 3.2 实现 `add_provider` 方法，包含单外部提供者检查
- [x] 3.3 实现 `build_system_prompt` 方法
- [x] 3.4 实现 `prefetch_all` 方法，包含上下文包裹
- [x] 3.5 实现 `sync_all` 方法，包含 Fan-out 容错
- [x] 3.6 实现 `queue_prefetch_all` 方法
- [x] 3.7 实现 `_wrap_context` 辅助函数
- [x] 3.8 编写 MemoryManager 的单元测试
  - [x] 3.8.1 测试注册内置提供者
  - [x] 3.8.2 测试注册第一个外部提供者
  - [x] 3.8.3 测试拒绝第二个外部提供者
  - [x] 3.8.4 测试单个提供者提示
  - [x] 3.8.5 测试多个提供者提示
  - [x] 3.8.6 测试空提示被跳过
  - [x] 3.8.7 测试包裹记忆上下文
  - [x] 3.8.8 测试 Fan-out 容错（一个 provider 失败不影响其他）

## 4. FileMemoryProvider 实现

- [x] 4.1 实现 FileMemoryProvider 类
- [x] 4.2 实现 `initialize` 方法，确保文件存在
- [x] 4.3 实现 `prefetch` 方法，读取文件内容
- [x] 4.4 实现 `sync_turn` 方法（异步写入）
- [x] 4.5 实现 `_handle_memory_action` 方法，支持 add/replace/remove
- [x] 4.6 实现 `_replace_entry` 和 `_remove_entry` 辅助方法
- [x] 4.7 实现 `get_tool_schemas` 方法，返回 memory 工具 schema
- [x] 4.8 实现原子写入（临时文件 + rename）
- [x] 4.9 编写 FileMemoryProvider 的单元测试
  - [x] 4.9.1 测试创建 MEMORY.md 和 USER.md
  - [x] 4.9.2 测试不覆盖已存在的文件
  - [x] 4.9.3 测试返回完整记忆内容
  - [x] 4.9.4 测试空文件返回空字符串
  - [x] 4.9.5 测试添加记忆条目
  - [x] 4.9.6 测试替换记忆条目
  - [x] 4.9.7 测试删除记忆条目
  - [x] 4.9.8 测试原子写入

## 5. 上下文隔离实现

- [x] 5.1 实现 `sanitize_context` 函数
- [x] 5.2 定义正则表达式常量
- [x] 5.3 实现 `StreamingContextScrubber` 类
- [x] 5.4 实现 `feed` 方法的状态机逻辑
- [x] 5.5 实现 `flush` 方法
- [x] 5.6 实现 `_max_partial_suffix` 辅助方法
- [x] 5.7 实现 `_find_boundary_open_tag` 辅助方法
- [x] 5.8 实现 `_is_block_boundary` 和 `_has_block_opener_suffix` 辅助方法
- [x] 5.9 编写上下文隔离的单元测试
  - [x] 5.9.1 测试移除完整上下文块
  - [x] 5.9.2 测试移除系统注释
  - [x] 5.9.3 测试保留可见内容
  - [x] 5.9.4 测试完整标签在单个 chunk
  - [x] 5.9.5 测试打开标签在第一个 chunk，关闭在第二个
  - [x] 5.9.6 测试部分打开标签
  - [x] 5.9.7 测试 flush 时仍在 span 内
  - [x] 5.9.8 测试 flush 时不在 span 内
  - [x] 5.9.9 测试行首标签
  - [x] 5.9.10 测试行中标签不被识别
