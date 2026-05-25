## 上下文

业界成熟的自进化 AI Agent 系统的对话循环模块 (~4300 LOC) 和错误分类器模块 (~1170 LOC) 实现了完整的对话循环和错误分类系统。核心设计决策包括：
- 同步对话循环，包含中断检查和迭代预算
- 错误分类学，提供结构化恢复策略
- 后台审查线程，fork Agent 评估对话
- 轨迹保存用于研究

## 技术方案

### 1. 核心对话循环

```typescript
export class ConversationLoop {
  async runConversation(userMessage: string): Promise<ConversationResult> {
    const messages = this.buildInitialMessages(userMessage);
    let apiCallCount = 0;
    
    while (apiCallCount < this.maxIterations && this.iterationBudget.remaining > 0) {
      // 中断检查
      if (this.interruptRequested) break;
      
      try {
        // 模型调用
        const response = await this.callModel(messages);
        
        if (response.toolCalls) {
          // 工具分发
          for (const toolCall of response.toolCalls) {
            const result = await this.dispatchTool(toolCall);
            messages.push(this.buildToolResultMessage(result));
          }
          apiCallCount++;
        } else {
          // 最终响应
          return {
            finalResponse: response.content,
            messages,
            apiCallCount
          };
        }
      } catch (error) {
        // 错误分类和恢复
        const classified = this.classifyError(error);
        const action = this.getRecoveryAction(classified);
        
        switch (action) {
          case 'retry':
            await this.jitteredBackoff();
            continue;
          case 'compress':
            await this.compressContext(messages);
            continue;
          case 'fallback':
            await this.rotateCredential();
            continue;
          case 'abort':
            throw error;
        }
      }
    }
    
    // 达到迭代限制
    return {
      finalResponse: '达到最大迭代次数',
      messages,
      apiCallCount
    };
  }
}
```

### 2. 错误分类器

```typescript
export enum FailoverReason {
  auth = 'auth',
  authPermanent = 'auth_permanent',
  billing = 'billing',
  rateLimit = 'rate_limit',
  overloaded = 'overloaded',
  serverError = 'server_error',
  timeout = 'timeout',
  contextOverflow = 'context_overflow',
  payloadTooLarge = 'payload_too_large',
  imageTooLarge = 'image_too_large',
  modelNotFound = 'model_not_found',
  formatError = 'format_error',
  unknown = 'unknown'
}

export class ErrorClassifier {
  classify(error: ApiError, provider: string, model: string): ClassifiedError {
    const statusCode = error.statusCode;
    const message = error.message.toLowerCase();
    
    // 认证错误
    if (statusCode === 401 || statusCode === 403) {
      return {
        reason: FailoverReason.auth,
        statusCode,
        provider,
        model,
        message: error.message,
        retryable: true,
        shouldRotateCredential: true
      };
    }
    
    // 计费/配额
    if (statusCode === 402 || this.matchesAny(message, BILLING_PATTERNS)) {
      return {
        reason: FailoverReason.billing,
        statusCode,
        retryable: false,
        shouldRotateCredential: true
      };
    }
    
    // 速率限制
    if (statusCode === 429) {
      return {
        reason: FailoverReason.rateLimit,
        statusCode,
        retryable: true,
        shouldRotateCredential: true
      };
    }
    
    // 上下文溢出
    if (this.isContextOverflowError(message, statusCode)) {
      return {
        reason: FailoverReason.contextOverflow,
        retryable: true,
        shouldCompress: true
      };
    }
    
    // 默认：未知
    return {
      reason: FailoverReason.unknown,
      retryable: true
    };
  }
}
```

### 3. 后台审查

```typescript
export function spawnBackgroundReview(parentAgent: AgentState, conversationSnapshot: Message[]): void {
  const thread = new Thread(async () => {
    // Fork Agent，继承运行时配置
    const reviewAgent = forkAgent(parentAgent, {
      toolWhitelist: ['memory', 'skill_manage'],
      skipMemory: true // 不写入共享记忆
    });
    
    // 发送审查提示
    const reviewPrompt = buildReviewPrompt(conversationSnapshot);
    
    // 执行审查
    const result = await reviewAgent.chat(reviewPrompt);
    
    // 审查结果直接写入记忆/技能存储
    logger.info('后台审查完成');
  });
  
  thread.daemon = true;
  thread.start();
}
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| 错误分类不准确导致错误恢复策略 | 详细日志记录分类结果，便于调试 |
| 后台审查线程可能写入不正确的记忆 | 使用工具白名单，跳过共享记忆写入 |
| 对话循环中的重试可能导致无限循环 | 迭代预算和最大迭代次数限制 |
