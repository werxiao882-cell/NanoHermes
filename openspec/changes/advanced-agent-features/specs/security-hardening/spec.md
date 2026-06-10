## ADDED Requirements

### Requirement: Unicode steganography defense
系统 SHALL 实现 Unicode 隐写防御，对所有外部输入（MCP 工具返回值、文件内容、用户输入）执行 NFKC 规范化 + 危险 Unicode 范围移除。清洗过程迭代执行直到文本不再变化（最多 10 轮）。

#### Scenario: 零宽字符被移除
- **WHEN** 输入文本包含零宽空格（U+200B）或零宽连接符（U+200D）
- **THEN** 系统 SHALL 移除这些不可见字符

#### Scenario: 私有使用区字符被移除
- **WHEN** 输入文本包含 U+E000-U+F8FF 范围的私有使用区字符
- **THEN** 系统 SHALL 移除这些字符

#### Scenario: 迭代清洗防嵌套混淆
- **WHEN** 输入文本包含嵌套的危险 Unicode 序列
- **THEN** 系统 SHALL 迭代执行清洗直到文本稳定（最多 10 轮），超过 10 轮 SHALL 抛出错误

### Requirement: Recursive Unicode sanitization for JSON
系统 SHALL 实现递归 Unicode脱敏函数，处理 JSON 对象、数组中所有字符串字段（包括 key），确保 MCP 工具的任何返回值都经过清洗。

#### Scenario: 递归清洗嵌套 JSON
- **WHEN** MCP 工具返回包含嵌套对象和数组的 JSON 结果
- **THEN** 系统 SHALL 递归清洗所有层级的字符串字段和 key 名

### Requirement: Client-side secret scanning
系统 SHALL 实现客户端密钥扫描，在内容离开本地前（Team Memory 上传、transcript 分享等），使用 30+ 种凭据模式正则进行扫描。

#### Scenario: AWS Access Key 被检测
- **WHEN** 内容包含以 AKIA 开头的 20 字符字符串
- **THEN** 系统 SHALL 检测到 AWS Access Key 模式，返回规则 ID（不返回密钥原文）

#### Scenario: GitHub PAT 被检测
- **WHEN** 内容包含 `ghp_` 前缀的 36 字符字符串
- **THEN** 系统 SHALL 检测到 GitHub Personal Access Token 模式

#### Scenario: 密钥 redact 而非拒绝
- **WHEN** 调用 redactSecrets 函数
- **THEN** 系统 SHALL 将匹配的密钥替换为 `[REDACTED]`，保持上下文可读性

### Requirement: MCP tool return value sanitization
系统 SHALL 对所有 MCP 工具的返回值自动执行 Unicode 脱敏，防止恶意 MCP 服务器通过隐写攻击注入恶意指令。

#### Scenario: MCP 返回值自动清洗
- **WHEN** MCP 工具返回包含 Unicode 隐写字符的文本
- **THEN** 系统 SHALL 在将返回值注入上下文前自动执行 recursivelySanitizeUnicode
