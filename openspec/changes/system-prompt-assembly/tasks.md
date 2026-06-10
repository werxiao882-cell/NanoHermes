## 1. 项目设置

- [x] 1.1 创建 `src/prompt/` 目录结构
- [x] 1.2 定义提示相关类型和接口 (PromptAssembler)
- [x] 1.3 配置 pytest 测试框架 (Python 项目)

## 2. 三层提示组装实现

- [x] 2.1 实现 assemble() 函数（组装完整系统提示）
- [x] 2.2 实现 get_stable_hash() 函数（缓存判断）
- [x] 2.3 实现 loadSoulMd 函数
- [x] 2.4 实现 buildToolGuidance 函数
- [x] 2.5 实现 buildSkillsPrompt 函数
- [x] 2.6 实现 buildModelOperationalGuidance 函数（Gemini、OpenAI）
- [x] 2.7 实现 buildContextFilesPrompt 函数
- [x] 2.8 实现 buildMemoryContext 函数
- [x] 2.9 实现 buildUserProfile 函数
- [x] 2.10 编写提示组装的单元测试 (52 tests, all passing)
  - [x] 2.10.1 测试构建完整提示
  - [x] 2.10.2 测试缓存提示
  - [x] 2.10.3 测试压缩后重建

## 3. 上下文文件扫描实现

- [x] 3.1 实现 CONTEXT_THREAT_PATTERNS 常量
- [x] 3.2 实现 CONTEXT_INVISIBLE_CHARS 常量
- [x] 3.3 实现 scan_context_content 函数
- [x] 3.4 实现 find_git_root 和 find_hermes_md 辅助函数
- [x] 3.5 编写上下文扫描的单元测试
  - [x] 3.5.1 测试检测 "ignore previous instructions"
  - [x] 3.5.2 测试检测不可见 Unicode
  - [x] 3.5.3 测试检测 curl 密钥泄露
  - [x] 3.5.4 测试安全内容通过

## 4. 提示缓存实现

- [x] 4.1 实现 apply_anthropic_cache_control 函数
- [x] 4.2 实现 _apply_cache_marker 辅助函数
- [x] 4.3 实现 _build_marker 辅助函数
- [x] 4.4 编写提示缓存的单元测试
  - [x] 4.4.1 测试系统提示 + 3 条消息
  - [x] 4.4.2 测试少于 4 条消息
  - [x] 4.4.3 测试 TTL 设置