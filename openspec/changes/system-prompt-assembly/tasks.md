## 1. 项目设置

- [ ] 1.1 创建 `src/prompt/` 目录结构
- [ ] 1.2 定义提示相关类型和接口
- [ ] 1.3 配置 vitest 测试框架

## 2. 三层提示组装实现

- [ ] 2.1 实现 buildSystemPromptParts 函数
- [ ] 2.2 实现 buildSystemPrompt 函数
- [ ] 2.3 实现 loadSoulMd 函数
- [ ] 2.4 实现 buildToolGuidance 函数
- [ ] 2.5 实现 buildSkillsPrompt 函数
- [ ] 2.6 实现 buildModelOperationalGuidance 函数（Gemini、OpenAI）
- [ ] 2.7 实现 buildContextFilesPrompt 函数
- [ ] 2.8 实现 buildMemoryContext 函数
- [ ] 2.9 实现 buildUserProfile 函数
- [ ] 2.10 编写提示组装的单元测试
  - [ ] 2.10.1 测试构建完整提示
  - [ ] 2.10.2 测试缓存提示
  - [ ] 2.10.3 测试压缩后重建

## 3. 上下文文件扫描实现

- [ ] 3.1 实现 CONTEXT_THREAT_PATTERNS 常量
- [ ] 3.2 实现 CONTEXT_INVISIBLE_CHARS 常量
- [ ] 3.3 实现 scanContextContent 函数
- [ ] 3.4 实现 _findGitRoot 和 _findHermesMd 辅助函数
- [ ] 3.5 编写上下文扫描的单元测试
  - [ ] 3.5.1 测试检测 "ignore previous instructions"
  - [ ] 3.5.2 测试检测不可见 Unicode
  - [ ] 3.5.3 测试检测 curl 密钥泄露
  - [ ] 3.5.4 测试安全内容通过

## 4. 提示缓存实现

- [ ] 4.1 实现 applyAnthropicCacheControl 函数
- [ ] 4.2 实现 _applyCacheMarker 辅助函数
- [ ] 4.3 实现 _buildMarker 辅助函数
- [ ] 4.4 编写提示缓存的单元测试
  - [ ] 4.4.1 测试系统提示 + 3 条消息
  - [ ] 4.4.2 测试少于 4 条消息
  - [ ] 4.4.3 测试 TTL 设置
