## 上下文

业界成熟的自进化 AI Agent 系统的系统提示组装模块 (~380 LOC) 和提示构建模块 (~1465 LOC) 实现了完整的系统提示组装系统。核心设计决策包括：
- 三层架构：stable（不变）、context（上下文相关）、volatile（每轮变化）
- 系统提示在会话期间缓存，仅压缩时重建
- 上下文文件注入前进行安全检查（提示注入检测）
- 模型家族操作指导（Gemini、OpenAI/GPT）

## 技术方案

### 1. 三层提示组装

```typescript
export function buildSystemPromptParts(agent: AgentState): PromptParts {
  const stable: string[] = [];
  const context: string[] = [];
  const volatile: string[] = [];
  
  // Stable 层：身份
  const soulContent = loadSoulMd();
  if (soulContent) {
    stable.push(soulContent);
  } else {
    stable.push(DEFAULT_AGENT_IDENTITY);
  }
  
  // Stable 层：工具指导
  const toolGuidance = buildToolGuidance(agent.validToolNames);
  if (toolGuidance) stable.push(toolGuidance);
  
  // Stable 层：技能提示
  const skillsPrompt = buildSkillsPrompt(agent);
  if (skillsPrompt) stable.push(skillsPrompt);
  
  // Stable 层：模型家族操作指导
  const modelGuidance = buildModelOperationalGuidance(agent.model);
  if (modelGuidance) stable.push(modelGuidance);
  
  // Context 层：上下文文件
  const contextFiles = buildContextFilesPrompt(agent.cwd);
  if (contextFiles) context.push(contextFiles);
  
  // Context 层：调用者提供的 system_message
  if (agent.systemMessage) context.push(agent.systemMessage);
  
  // Volatile 层：记忆快照
  const memoryContext = buildMemoryContext(agent);
  if (memoryContext) volatile.push(memoryContext);
  
  // Volatile 层：用户画像
  const userProfile = buildUserProfile(agent);
  if (userProfile) volatile.push(userProfile);
  
  // Volatile 层：时间戳/会话/模型/提供商
  volatile.push(buildMetadataLine(agent));
  
  return {
    stable: stable.join('\n\n'),
    context: context.join('\n\n'),
    volatile: volatile.join('\n\n')
  };
}

export function buildSystemPrompt(parts: PromptParts): string {
  return [parts.stable, parts.context, parts.volatile].filter(Boolean).join('\n\n');
}
```

### 2. 上下文文件安全检查

```typescript
const CONTEXT_THREAT_PATTERNS = [
  [/ignore\s+(previous|all|above|prior)\s+instructions/i, 'prompt_injection'],
  [/do\s+not\s+tell\s+the\s+user/i, 'deception_hide'],
  [/system\s+prompt\s+override/i, 'sys_prompt_override'],
  [/disregard\s+(your|all|any)\s+(instructions|rules|guidelines)/i, 'disregard_rules'],
  [/act\s+as\s+(if|though)\s+you\s+(have\s+no|don't\s+have)\s+(restrictions|limits|rules)/i, 'bypass_restrictions'],
  [/curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)/i, 'exfil_curl'],
  [/cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass)/i, 'read_secrets'],
];

const CONTEXT_INVISIBLE_CHARS = new Set([
  '\u200b', '\u200c', '\u200d', '\u2060', '\ufeff',
  '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
]);

export function scanContextContent(content: string, filename: string): string {
  const findings: string[] = [];
  
  // 检查不可见 Unicode
  for (const char of CONTEXT_INVISIBLE_CHARS) {
    if (content.includes(char)) {
      findings.push(`invisible unicode U+${char.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')}`);
    }
  }
  
  // 检查威胁模式
  for (const [pattern, pid] of CONTEXT_THREAT_PATTERNS) {
    if (pattern.test(content)) {
      findings.push(pid as string);
    }
  }
  
  if (findings.length > 0) {
    logger.warn(`上下文文件 ${filename} 被阻止: ${findings.join(', ')}`);
    return `[BLOCKED: ${filename} contained potential prompt injection (${findings.join(', ')}). Content not loaded.]`;
  }
  
  return content;
}
```

### 3. 提示缓存

```typescript
export function applyAnthropicCacheControl(
  messages: Message[],
  cacheTtl: '5m' | '1h' = '5m'
): Message[] {
  const cloned = JSON.parse(JSON.stringify(messages));
  if (cloned.length === 0) return cloned;
  
  const marker = { type: 'ephemeral', ...(cacheTtl === '1h' ? { ttl: '1h' } : {}) };
  let breakpointsUsed = 0;
  
  // 系统提示缓存断点
  if (cloned[0].role === 'system') {
    applyCacheMarker(cloned[0], marker);
    breakpointsUsed++;
  }
  
  // 最后 3 条非系统消息缓存断点
  const remaining = 4 - breakpointsUsed;
  const nonSysIndices = cloned.map((m, i) => m.role !== 'system' ? i : -1).filter(i => i !== -1);
  
  for (const idx of nonSysIndices.slice(-remaining)) {
    applyCacheMarker(cloned[idx], marker);
  }
  
  return cloned;
}
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| 提示注入可能绕过安全限制 | 上下文文件扫描检测常见注入模式 |
| 提示缓存失效导致成本增加 | 三层架构确保 stable 层不变，缓存有效 |
| 不可见 Unicode 字符可能隐藏恶意内容 | 扫描并阻止包含不可见字符的上下文文件 |
