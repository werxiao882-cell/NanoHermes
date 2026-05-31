# tui-tool-display Specification

## Purpose
TBD - created by archiving change modern-tui-interface. Update Purpose after archive.
## Requirements
### Requirement: 工具调用状态显示
系统 SHALL 实时显示工具调用的状态，包括开始、执行中、完成和失败。

#### Scenario: 工具开始执行
- **WHEN** Agent 调用工具
- **THEN** 系统显示工具名称和"开始执行"状态，带加载动画

#### Scenario: 工具执行中
- **WHEN** 工具正在执行
- **THEN** 系统显示进度指示器（如旋转动画或进度条）

#### Scenario: 工具执行完成
- **WHEN** 工具执行完成
- **THEN** 系统显示结果摘要和成功状态

#### Scenario: 工具执行失败
- **WHEN** 工具执行失败
- **THEN** 系统显示错误信息和失败状态

### Requirement: 工具调用历史面板
系统 SHALL 提供工具调用历史面板，显示当前会话中的所有工具调用。

#### Scenario: 显示工具调用历史
- **WHEN** 用户查看工具面板
- **THEN** 系统按时间顺序显示所有工具调用

#### Scenario: 折叠/展开工具详情
- **WHEN** 用户点击工具调用项
- **THEN** 系统展开/折叠该工具调用的详细信息

### Requirement: 工具调用可视化样式
系统 SHALL 使用一致的样式显示工具调用，包括图标、颜色和格式。

#### Scenario: 成功工具调用样式
- **WHEN** 工具调用成功
- **THEN** 系统使用绿色图标和文本显示

#### Scenario: 失败工具调用样式
- **WHEN** 工具调用失败
- **THEN** 系统使用红色图标和文本显示

#### Scenario: 进行中工具调用样式
- **WHEN** 工具调用正在进行
- **THEN** 系统使用黄色图标和旋转动画显示

### Requirement: 工具调用结果摘要
系统 SHALL 为每个工具调用提供简洁的结果摘要，便于快速理解。

#### Scenario: 文件读取结果摘要
- **WHEN** `read_file` 工具完成
- **THEN** 系统显示"读取 10 行，256 字符"

#### Scenario: 终端命令结果摘要
- **WHEN** `terminal` 工具完成
- **THEN** 系统显示命令输出前几行和退出码

#### Scenario: 搜索结果摘要
- **WHEN** `search_files` 工具完成
- **THEN** 系统显示"找到 5 个匹配文件"

