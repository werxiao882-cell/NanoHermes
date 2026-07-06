# VeRL Agentic RL Source Code Analysis

Key findings from reading `volcengine/verl` source code for Agentic RL implementation.

## Architecture Overview

VeRL uses a three-tier async architecture:
```
AgentLoopManager (Ray distributed scheduler)
  └─ AgentLoopWorker (per-batch executor)
     └─ ToolAgentLoop (state machine for single trajectory)
```

## Core State Machine (`tool_agent_loop.py`)

Four states control the agent lifecycle:
- `PENDING`: Prepare prompt with chat template
- `GENERATING`: LLM generates text, stops at tool call tokens
- `PROCESSING_TOOLS`: Execute tools concurrently via `asyncio.gather`
- `TERMINATED`: Max turns, answer generated, or length exceeded

## Critical Implementation Details

### Response Masking
Tool responses are marked with `response_mask = 0` so they don't contribute to loss:
```python
agent_data.response_mask += [1] * len(agent_data.response_ids)  # LLM generated
agent_data.response_mask += [0] * len(response_ids)  # Tool response
```

### Advantage Estimation (`core_algos.py`)
VeRL supports multiple advantage estimators:
- `GRPO`: Group-relative policy optimization (DeepSeek-R1 style)
- `GAE`: Generalized advantage estimation (classic PPO)
- `GDPO`: Group reward-Decoupled Normalization (multi-dimensional rewards)
- `GRPO_PASSK`: Only best response per group gets advantage

### Policy Loss (`compute_policy_loss_vanilla`)
Standard PPO clipping with dual-clip support:
- `clip_ratio`: Standard PPO epsilon
- `clip_ratio_c`: Lower bound for dual-clip PPO (default 3.0)
- Uses `response_mask` to only compute loss on LLM-generated tokens

### Reward System (`reward_manager/naive.py`)
- Async reward computation via separate Ray workers
- Supports sandbox execution for code/math evaluation
- Custom reward functions can be loaded from external files

## File Locations
- `verl/experimental/agent_loop/agent_loop.py`: Base classes and worker/manager
- `verl/experimental/agent_loop/tool_agent_loop.py`: Tool calling state machine
- `verl/trainer/ppo/core_algos.py`: Advantage estimators and policy loss
- `verl/experimental/reward_loop/reward_manager/`: Reward computation
- `verl/protocol.py`: DataProto schema for batch data
