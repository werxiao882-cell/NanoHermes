## 1. 项目设置

- [ ] 1.1 创建 `src/memory/` 目录结构
- [ ] 1.2 定义 TypeScript 接口和类型
- [ ] 1.3 配置 vitest 测试框架

## 2. MemoryProvider 抽象基类

- [ ] 2.1 实现 MemoryProvider 抽象类
- [ ] 2.2 定义 InitializeOptions 接口
- [ ] 2.3 定义 ToolSchema 接口
- [ ] 2.4 定义 ConfigField 接口
- [ ] 2.5 实现所有核心抽象方法
- [ ] 2.6 实现所有可选钩子的默认空实现
- [ ] 2.7 编写 MemoryProvider 的单元测试
  - [ ] 2.7.1 测试实现核心方法
  - [ ] 2.7.2 测试可选钩子有默认实现
  - [ ] 2.7.3 测试覆盖可选钩子
  - [ ] 2.7.4 测试接收完整选项
  - [ ] 2.7.5 测试跳过非 primary 上下文

## 3. MemoryManager 编排器

- [ ] 3.1 实现 MemoryManager 类
- [ ] 3.2 实现 addProvider 方法，包含单外部提供者检查
- [ ] 3.3 实现 buildSystemPrompt 方法
- [ ] 3.4 实现 prefetchAll 方法，包含上下文包裹
- [ ] 3.5 实现 syncAll 方法
- [ ] 3.6 实现 queuePrefetchAll 方法
- [ ] 3.7 实现 wrapContext 辅助函数
- [ ] 3.8 编写 MemoryManager 的单元测试
  - [ ] 3.8.1 测试注册内置提供者
  - [ ] 3.8.2 测试注册第一个外部提供者
  - [ ] 3.8.3 测试拒绝第二个外部提供者
  - [ ] 3.8.4 测试单个提供者提示
  - [ ] 3.8.5 测试多个提供者提示
  - [ ] 3.8.6 测试空提示被跳过
  - [ ] 3.8.7 测试包裹记忆上下文

## 4. FileMemoryProvider 实现

- [ ] 4.1 实现 FileMemoryProvider 类
- [ ] 4.2 实现 initialize 方法，确保文件存在
- [ ] 4.3 实现 prefetch 方法，读取文件内容
- [ ] 4.4 实现 syncTurn 方法（异步写入）
- [ ] 4.5 实现 handleMemoryAction 方法，支持 add/replace/remove
- [ ] 4.6 实现 replaceEntry 和 removeEntry 辅助方法
- [ ] 4.7 实现 getToolSchemas 方法，返回 memory 工具 schema
- [ ] 4.8 编写 FileMemoryProvider 的单元测试
  - [ ] 4.8.1 测试创建 MEMORY.md 和 USER.md
  - [ ] 4.8.2 测试不覆盖已存在的文件
  - [ ] 4.8.3 测试返回完整记忆内容
  - [ ] 4.8.4 测试空文件返回空字符串
  - [ ] 4.8.5 测试添加记忆条目
  - [ ] 4.8.6 测试替换记忆条目
  - [ ] 4.8.7 测试删除记忆条目

## 5. 上下文隔离实现

- [ ] 5.1 实现 sanitize_context 函数
- [ ] 5.2 定义正则表达式常量
- [ ] 5.3 实现 StreamingContextScrubber 类
- [ ] 5.4 实现 feed 方法的状态机逻辑
- [ ] 5.5 实现 flush 方法
- [ ] 5.6 实现 maxPartialSuffix 辅助方法
- [ ] 5.7 实现 findBoundaryOpenTag 辅助方法
- [ ] 5.8 实现 isBlockBoundary 和 hasBlockOpenerSuffix 辅助方法
- [ ] 5.9 编写上下文隔离的单元测试
  - [ ] 5.9.1 测试移除完整上下文块
  - [ ] 5.9.2 测试移除系统注释
  - [ ] 5.9.3 测试保留可见内容
  - [ ] 5.9.4 测试完整标签在单个 chunk
  - [ ] 5.9.5 测试打开标签在第一个 chunk，关闭在第二个
  - [ ] 5.9.6 测试部分打开标签
  - [ ] 5.9.7 测试 flush 时仍在 span 内
  - [ ] 5.9.8 测试 flush 时不在 span 内
  - [ ] 5.9.9 测试行首标签
  - [ ] 5.9.10 测试行中标签不被识别
