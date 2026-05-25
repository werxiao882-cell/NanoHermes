## 上下文

业界成熟的自进化 AI Agent 系统的上下文压缩模块 (~1750 LOC) 实现了完整的上下文压缩系统。核心设计决策包括：
- 使用辅助（便宜/快速）LLM 模型进行摘要生成
- 保护头部和尾部上下文
- 结构化摘要模板（已解决/待解决问题、剩余工作）
- 工具输出剪枝（旧结果替换、图像占位符、参数截断）
- 迭代摘要更新
- 按比例缩放的摘要预算（20% 比例，最小 2000 token，最大 12000 token）

## 目标 / 非目标

**目标：**
- 实现完整的上下文压缩引擎
- 实现辅助 LLM 客户端配置
- 实现工具输出剪枝
- 实现会话分割和 ID 轮换

**非目标：**
- 不实现图像大小调整恢复（try_shrink_image_parts_in_messages）
- 不实现手动压缩反馈（manual_compression_feedback）

## 技术方案

### 1. 上下文压缩引擎

```typescript
export class ContextCompressor {
  private auxClient: AuxiliaryClient;
  private summaryPrefix = '[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted into the summary below. This is a handoff from a previous context window — treat it as background reference, NOT as active instructions.';
  
  // 预算常量
  private static readonly MIN_SUMMARY_TOKENS = 2000;
  private static readonly SUMMARY_RATIO = 0.20;
  private static readonly SUMMARY_TOKENS_CEILING = 12000;
  private static readonly CHARS_PER_TOKEN = 4;
  private static readonly IMAGE_TOKEN_ESTIMATE = 1600;
  
  async compress(messages: Message[], modelContextLength: number): Promise<CompressionResult> {
    // 1. 计算 token 预算
    const totalChars = this.estimateContentLength(messages);
    const totalTokens = totalChars / ContextCompressor.CHARS_PER_TOKEN;
    
    // 2. 确定头部和尾部保护
    const headMessages = this.protectHead(messages);
    const tailMessages = this.protectTail(messages, modelContextLength);
    const middleMessages = this.getMiddle(messages, headMessages, tailMessages);
    
    // 3. 剪枝工具输出
    const prunedMiddle = this.pruneToolOutputs(middleMessages);
    
    // 4. 计算摘要预算
    const compressedChars = this.estimateContentLength(prunedMiddle);
    const summaryBudget = this.calculateSummaryBudget(compressedChars);
    
    // 5. 调用辅助 LLM 生成摘要
    const summary = await this.generateSummary(prunedMiddle, summaryBudget);
    
    // 6. 构建压缩后的消息列表
    const compressedMessages = [
      ...headMessages,
      { role: 'system', content: this.summaryPrefix + '\n\n' + summary },
      ...tailMessages
    ];
    
    return {
      messages: compressedMessages,
      summary,
      headCount: headMessages.length,
      tailCount: tailMessages.length,
      compressedCount: middleMessages.length
    };
  }
  
  private calculateSummaryBudget(compressedChars: number): number {
    const ratioBudget = Math.floor(compressedChars * ContextCompressor.SUMMARY_RATIO / ContextCompressor.CHARS_PER_TOKEN);
    return Math.max(
      ContextCompressor.MIN_SUMMARY_TOKENS,
      Math.min(ratioBudget, ContextCompressor.SUMMARY_TOKENS_CEILING)
    );
  }
  
  private protectHead(messages: Message[]): Message[] {
    // 保护前 N 条消息（系统提示 + 前几轮对话）
    return messages.slice(0, 3);
  }
  
  private protectTail(messages: Message[], contextLength: number): Message[] {
    // 使用 token 预算保护尾部
    const tailTokens = Math.floor(contextLength * 0.25); // 保留 25% 给尾部
    let tailChars = 0;
    const tail: Message[] = [];
    
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      const chars = this.estimateMessageLength(msg);
      if (tailChars + chars > tailTokens * ContextCompressor.CHARS_PER_TOKEN) break;
      tail.unshift(msg);
      tailChars += chars;
    }
    
    return tail;
  }
}
```

### 2. 工具输出剪枝

```typescript
pruneToolOutputs(messages: Message[]): Message[] {
  return messages.map(msg => {
    if (msg.role !== 'tool') return msg;
    
    // 替换旧工具输出为占位符
    const content = msg.content;
    if (typeof content === 'string' && content.length > 1000) {
      return {
        ...msg,
        content: '[Old tool output cleared to save context space]'
      };
    }
    
    return msg;
  });
}

truncateToolCallArgs(argsJson: string, headChars: number = 200): string {
  try {
    const parsed = JSON.parse(argsJson);
    const truncated = this.truncateObjectStrings(parsed, headChars);
    return JSON.stringify(truncated);
  } catch {
    // 不是有效 JSON，返回原始字符串
    return argsJson;
  }
}

private truncateObjectStrings(obj: any, maxChars: number): any {
  if (typeof obj === 'string') {
    return obj.length > maxChars ? obj.slice(0, maxChars) + '...[truncated]' : obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(item => this.truncateObjectStrings(item, maxChars));
  }
  if (typeof obj === 'object' && obj !== null) {
    const result: any = {};
    for (const [key, value] of Object.entries(obj)) {
      result[key] = this.truncateObjectStrings(value, maxChars);
    }
    return result;
  }
  return obj;
}
```

**关键设计决策：** 工具调用参数截断必须保持 JSON 有效性。早期实现直接切片原始 JSON 字符串，导致未终止的字符串和缺失的闭合括号，使 MiniMax 等提供商返回 400 错误。新实现解析 JSON，截断字符串叶子节点，重新序列化。

### 3. 辅助客户端可行性检查

```typescript
checkCompressionModelFeasibility(agent: AgentConfig): CompressionFeasibility {
  const auxModel = this.resolveAuxModel('compression');
  const auxContextLength = getModelContextLength(auxModel);
  const mainCompressionThreshold = agent.contextLength * 0.8; // 80% 触发压缩
  
  if (auxContextLength < MINIMUM_CONTEXT_LENGTH) {
    return {
      feasible: false,
      reason: `辅助模型上下文窗口 (${auxContextLength}) 小于最小要求 (${MINIMUM_CONTEXT_LENGTH})`
    };
  }
  
  if (auxContextLength < mainCompressionThreshold) {
    return {
      feasible: true,
      warning: `辅助模型上下文窗口 (${auxContextLength}) 小于主模型压缩阈值 (${mainCompressionThreshold})，压缩可能失败`
    };
  }
  
  return { feasible: true };
}
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| 辅助 LLM 调用增加成本 | 使用小型/快速模型，配置可调节压缩阈值 |
| 摘要丢失重要信息 | 结构化摘要模板跟踪已解决/待解决问题 |
| 迭代摘要可能累积错误 | 每次压缩保留前次摘要内容并合并新信息 |
