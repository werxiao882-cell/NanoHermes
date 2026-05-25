## 为什么

业界成熟的自进化 AI Agent 系统使用三层系统提示组装架构（stable/context/volatile），确保提示缓存有效。包含身份、工具指导、技能索引、上下文文件、记忆快照、用户画像等。NanoHermes 需要实现相同的提示组装系统。

## 变更内容

- 实现三层系统提示组装（stable、context、volatile）
- 实现上下文文件扫描和注入安全检查
- 实现提示缓存和恢复
- 实现模型家族操作指导注入

## 能力

### 新增能力

- `prompt-assembly`: 三层系统提示组装。stable（身份、工具指导、技能提示、环境提示）、context（上下文文件、system_message）、volatile（记忆快照、用户画像、时间戳）。
- `context-file-scanner`: 上下文文件扫描，检测 AGENTS.md、.cursorrules、SOUL.md 中的提示注入。检查不可见 Unicode 和威胁模式。
- `prompt-caching`: 提示缓存，Anthropic cache_control 策略（system_and_3），4 个缓存断点。

### 修改能力

<!-- 无现有能力需要修改 -->

## 影响

- 新增 `src/prompt/` 目录
- 依赖记忆系统和技能系统
- 无破坏性变更，从零开始构建
