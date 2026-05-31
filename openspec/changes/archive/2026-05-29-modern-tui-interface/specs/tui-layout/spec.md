## ADDED Requirements

### Requirement: 响应式终端布局
系统 SHALL 根据终端尺寸自动调整布局，确保在不同窗口大小下正常显示。

#### Scenario: 终端宽度变化
- **WHEN** 用户调整终端窗口宽度
- **THEN** 系统重新计算布局，调整面板宽度

#### Scenario: 终端高度变化
- **WHEN** 用户调整终端窗口高度
- **THEN** 系统调整可见区域，保持关键内容可见

#### Scenario: 最小宽度限制
- **WHEN** 终端宽度小于 80 字符
- **THEN** 系统显示警告，但继续工作

### Requirement: 动态面板管理
系统 SHALL 支持动态面板的创建、销毁和重排，适应不同工作模式。

#### Scenario: 显示工具面板
- **WHEN** Agent 调用工具
- **THEN** 系统动态显示工具面板

#### Scenario: 隐藏工具面板
- **WHEN** 工具调用完成且用户折叠面板
- **THEN** 系统隐藏工具面板，释放空间

#### Scenario: 面板重排
- **WHEN** 终端尺寸变化
- **THEN** 系统重新排列面板位置

### Requirement: 窗口调整事件处理
系统 SHALL 监听并处理终端窗口调整事件，实时更新布局。

#### Scenario: 监听 SIGWINCH 信号
- **WHEN** 终端窗口大小改变
- **THEN** 系统捕获 SIGWINCH 信号（Unix）或使用 Windows API

#### Scenario: 更新布局
- **WHEN** 收到窗口调整事件
- **THEN** 系统在 100ms 内完成布局更新

### Requirement: 布局配置
系统 SHALL 提供布局配置选项，允许用户自定义界面元素的位置和可见性。

#### Scenario: 配置工具面板位置
- **WHEN** 用户配置工具面板位置
- **THEN** 系统在指定位置（左侧/右侧/底部）显示面板

#### Scenario: 配置面板可见性
- **WHEN** 用户隐藏工具面板
- **THEN** 系统不再显示工具面板，直到用户重新启用
