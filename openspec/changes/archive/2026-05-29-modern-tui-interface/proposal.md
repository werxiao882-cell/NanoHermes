## Why

NanoHermes 当前的 TUI 界面功能有限，缺乏现代化的终端用户体验。用户期望更丰富的交互功能，包括：流式输出、动态加载动画、进度指示器、智能补全、语法高亮和响应式布局。通过整合 prompt_toolkit（核心交互）+ Ink UI（高级渲染）+ ANSI 转义码（底层控制），可以构建一个既强大又美观的终端界面。

## What Changes

- **新增**: 基于 prompt_toolkit 的现代化 TUI 核心架构
- **新增**: Ink UI 组件库用于高级渲染（加载动画、进度条、面板）
- **新增**: ANSI 转义码直接控制（颜色、光标、清屏、窗口调整）
- **增强**: 流式消息输出，支持打字机效果和实时 Markdown 渲染
- **增强**: 智能输入补全，支持命令、文件路径和上下文感知
- **增强**: 动态工具调用可视化，实时显示工具执行状态
- **增强**: 响应式布局，自适应终端窗口大小
- **移除**: 旧的简单 CLI 对话模式（保留为 fallback）

## Capabilities

### New Capabilities

- `tui-core`: TUI 核心架构，包括主循环、事件处理和状态管理
- `tui-input`: 高级输入组件，支持 prompt_toolkit 集成、补全和历史记录
- `tui-rendering`: 渲染引擎，整合 Ink UI 组件和 ANSI 转义码
- `tui-streaming`: 流式输出系统，支持打字机效果和增量渲染
- `tui-tool-display`: 工具调用可视化，实时显示工具执行状态和结果
- `tui-layout`: 响应式布局系统，自适应终端尺寸和窗口调整

### Modified Capabilities

<!-- 无现有能力需要修改 -->

## Impact

- **受影响代码**: `src/cli/tui_chat.py`（重写），`src/cli/` 目录结构重组
- **新增依赖**: `prompt_toolkit`（已存在），`rich`（已存在），可能需要 `alive_progress` 或自定义动画
- **API 变更**: TUI 初始化参数变更，新增配置选项
- **测试影响**: 需要新增 TUI 组件测试、集成测试和端到端测试
- **向后兼容**: 保留 `--cli` 标志作为 fallback，默认启用新 TUI
