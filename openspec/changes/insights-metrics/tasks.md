## 1. 项目设置

- [ ] 1.1 创建 `src/insights/` 目录结构
- [ ] 1.2 定义洞察相关类型和接口
- [ ] 1.3 配置 vitest 测试框架

## 2. InsightsEngine 实现

- [ ] 2.1 实现 InsightsEngine 类
- [ ] 2.2 实现 generate 方法
- [ ] 2.3 实现 getSessions、getToolUsage、getSkillUsage、getMessageStats 方法
- [ ] 2.4 实现 computeOverview 方法
- [ ] 2.5 实现 computeModelBreakdown 方法
- [ ] 2.6 实现 computePlatformBreakdown 方法
- [ ] 2.7 实现 computeToolRanking 方法
- [ ] 2.8 实现 computeSkillUsage 方法
- [ ] 2.9 实现 computeActivityTrend 方法
- [ ] 2.10 实现 computeTopSessions 方法
- [ ] 2.11 实现 formatTerminal 方法
- [ ] 2.12 实现 formatBarChart 辅助方法
- [ ] 2.13 编写 InsightsEngine 的单元测试
  - [ ] 2.13.1 测试生成完整报告
  - [ ] 2.13.2 测试空数据报告
  - [ ] 2.13.3 测试按源过滤
  - [ ] 2.13.4 测试格式化概览
  - [ ] 2.13.5 测试格式化条形图

## 3. 成本估算实现

- [ ] 3.1 实现 PRICING_DATABASE 常量
- [ ] 3.2 实现 estimateCost 函数
- [ ] 3.3 实现 TokenUsage 接口
- [ ] 3.4 编写成本估算的单元测试
  - [ ] 3.4.1 测试估算已知模型成本
  - [ ] 3.4.2 测试估算缓存 token 成本
  - [ ] 3.4.3 测试未知模型成本

## 4. 活动趋势实现

- [ ] 4.1 实现活动趋势计算
- [ ] 4.2 编写活动趋势的单元测试
  - [ ] 4.2.1 测试计算每日会话数
  - [ ] 4.2.2 测试条形图峰值归一化
  - [ ] 4.2.3 测试全零数据条形图
