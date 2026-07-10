## 压缩模式（Compression Modes）

### 需求

- **MUST** 支持 Reactive 模式（基于 token 阈值触发）
- **MUST** 支持 Micro 模式（基于对话轮次触发）
- **MUST** 支持 Snip 模式（基于消息内容特征触发）
- **MUST** 提供工厂函数创建指定模式
