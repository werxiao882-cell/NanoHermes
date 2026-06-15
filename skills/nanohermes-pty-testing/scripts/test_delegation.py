#!/usr/bin/env python3
"""
PTY 测试 NanoHermes 的 delegate_task 工具。

使用 pexpect 启动 NanoHermes --debug，发送委托任务指令，
观察 delegate_task 工具调用和子 Agent 执行结果。
"""
import os
import sys
import re
import time
import json
import pexpect

WORKDIR = "/mnt/d/code/NanoHermes"
CONDA_ACTIVATE = 'eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312'


def clean_ansi(text):
    """清理 ANSI 转义码。"""
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'\x1b\[\?[0-9]+[a-z]', '', text)
    text = re.sub(r'\x1b\][0-9];.*?\x07', '', text)
    text = re.sub(r'\x08', '', text)
    text = re.sub(r'\r\n', '\n', text)
    return text


def setup_nanohermes():
    """确保 nanohermes.json 存在。"""
    config_path = os.path.join(WORKDIR, "nanohermes.json")
    if not os.path.exists(config_path):
        config = {
            "model": {"provider": "openai", "name": "qwen3.6-plus"},
            "providers": {
                "openai": {
                    "base_url_env": "OPENAI_BASE_URL",
                    "api_key_env": "OPENAI_API_KEY"
                }
            },
            "tui": {"typing_speed": 10, "show_tool_panel": True, "tool_panel_position": "right"}
        }
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print("  ✓ 创建 nanohermes.json")


def test_delegation_single():
    """测试单任务委托。"""
    print("\n" + "="*60)
    print("🧪 测试: delegate_task 单任务委托")
    print("="*60)

    script_log = "/tmp/nanohermes_delegation_test.log"

    cmd = (
        f'{CONDA_ACTIVATE} && '
        f'cd {WORKDIR} && '
        f'script -q -c "python -m src.main --debug" {script_log}'
    )

    print("\n🚀 启动 NanoHermes --debug ...")
    child = pexpect.spawn(
        'bash',
        args=['-c', cmd],
        encoding='utf-8',
        timeout=120,
        maxread=200000,
    )

    # 等待启动（debug 模式下输出更多）
    print("  等待启动 (15s)...")
    time.sleep(15)

    # 发送委托任务指令
    prompt = "使用 delegate_task 工具委托一个子 Agent 计算 1 到 100 的质数数量，goal 是计算质数数量，使用 terminal 工具集"
    print(f"\n📤 发送指令: {prompt[:60]}...")
    child.sendline(prompt)

    # delegate_task 需要子 Agent 执行，给足够时间
    print("  等待子 Agent 执行 (60s)...")
    time.sleep(60)

    # 退出
    child.sendline("/quit")
    time.sleep(2)
    child.close(force=True)

    # 读取输出
    raw = ""
    if os.path.exists(script_log):
        with open(script_log, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        os.remove(script_log)

    cleaned = clean_ansi(raw)

    print(f"\n📊 输出总长度: {len(cleaned)} 字符")

    # 分析结果
    results = {}

    # 1. 检查是否调用了 delegate_task
    has_delegate = bool(re.search(r'delegate_task', cleaned, re.IGNORECASE))
    results['delegate_task_called'] = has_delegate

    # 2. 检查是否有子 Agent 启动迹象
    has_subagent = bool(re.search(r'subagent|child.*agent|子.*Agent|DELEGATION', cleaned, re.IGNORECASE))
    results['subagent_detected'] = has_subagent

    # 3. 检查是否看到 debug 输出（--debug 模式）
    has_debug = bool(re.search(r'DEBUG|debug|DEBUG.*conversation', cleaned, re.IGNORECASE))
    results['debug_output'] = has_debug

    # 4. 检查是否有工具调用的 trace
    has_tool_call = bool(re.search(r'tool_call|tool.*call|工具调用', cleaned, re.IGNORECASE))
    results['tool_call_trace'] = has_tool_call

    # 5. 检查是否看到质数相关内容（子 Agent 的回复）
    has_prime = bool(re.search(r'质数|prime|25', cleaned, re.IGNORECASE))
    results['prime_result'] = has_prime

    # 6. 检查是否有 task_id
    has_task_id = bool(re.search(r'task[_-]?id|task_id', cleaned, re.IGNORECASE))
    results['task_id_present'] = has_task_id

    # 7. 检查 delegation 相关关键词
    has_delegation = bool(re.search(r'delegat|委托|spawn|child', cleaned, re.IGNORECASE))
    results['delegation_keywords'] = has_delegation

    # 8. 检查是否有错误
    has_error = bool(re.search(r'error|失败|Error|Exception', cleaned, re.IGNORECASE))
    results['has_error'] = has_error

    print("\n📋 检查结果:")
    for key, val in results.items():
        icon = "✅" if val else "❌"
        print(f"  {icon} {key}: {val}")

    # 输出关键片段
    print(f"\n📝 输出片段（前 2000 字符）:")
    print("-"*60)
    print(cleaned[:2000])
    print("-"*60)

    # 保存完整日志
    log_path = f"/mnt/d/code/NanoHermes/skills/nanohermes-pty-testing/testing-artifacts/logs/delegation-test-{time.strftime('%Y%m%d-%H%M')}.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"Test: delegation_single\n")
        f.write(f"Results: {json.dumps(results, indent=2)}\n")
        f.write(f"\n--- FULL OUTPUT ---\n{cleaned}\n")
    print(f"\n💾 完整日志: {log_path}")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"\n📊 通过: {passed_count}/{total_count}")

    return results


def test_delegation_goal_only():
    """测试简单的 goal 模式委托。"""
    print("\n" + "="*60)
    print("🧪 测试: delegate_task 简单 goal 模式")
    print("="*60)

    script_log = "/tmp/nanohermes_delegation_goal.log"

    cmd = (
        f'{CONDA_ACTIVATE} && '
        f'cd {WORKDIR} && '
        f'script -q -c "python -m src.main --debug" {script_log}'
    )

    print("\n🚀 启动 NanoHermes --debug ...")
    child = pexpect.spawn(
        'bash',
        args=['-c', cmd],
        encoding='utf-8',
        timeout=120,
        maxread=200000,
    )

    print("  等待启动 (15s)...")
    time.sleep(15)

    # 更简单的指令
    prompt = "用 delegate_task 委托一个子 Agent，goal 是计算 50 以内的质数列表"
    print(f"\n📤 发送指令: {prompt}")
    child.sendline(prompt)

    print("  等待子 Agent 执行 (45s)...")
    time.sleep(45)

    child.sendline("/quit")
    time.sleep(2)
    child.close(force=True)

    raw = ""
    if os.path.exists(script_log):
        with open(script_log, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        os.remove(script_log)

    cleaned = clean_ansi(raw)
    print(f"\n📊 输出总长度: {len(cleaned)} 字符")

    results = {}
    results['delegate_task'] = bool(re.search(r'delegate_task', cleaned, re.IGNORECASE))
    results['subagent'] = bool(re.search(r'subagent|child|子.*Agent|DELEGATION', cleaned, re.IGNORECASE))
    results['debug'] = bool(re.search(r'DEBUG|debug', cleaned, re.IGNORECASE))
    results['prime_result'] = bool(re.search(r'质数|prime|2, 3, 5|3, 5, 7', cleaned, re.IGNORECASE))
    results['task_id'] = bool(re.search(r'task_id', cleaned, re.IGNORECASE))
    results['has_error'] = bool(re.search(r'error|Error|Exception', cleaned, re.IGNORECASE))

    print("\n📋 检查结果:")
    for key, val in results.items():
        icon = "✅" if val else "❌"
        print(f"  {icon} {key}: {val}")

    print(f"\n📝 输出片段（前 1500 字符）:")
    print("-"*60)
    print(cleaned[:1500])
    print("-"*60)

    log_path = f"/mnt/d/code/NanoHermes/skills/nanohermes-pty-testing/testing-artifacts/logs/delegation-goal-test-{time.strftime('%Y%m%d-%H%M')}.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"Test: delegation_goal_only\n")
        f.write(f"Results: {json.dumps(results, indent=2)}\n")
        f.write(f"\n--- FULL OUTPUT ---\n{cleaned}\n")
    print(f"\n💾 完整日志: {log_path}")

    return results


if __name__ == "__main__":
    print("🔬 NanoHermes Delegation Tool PTY 测试")
    print(f"📅 {time.strftime('%Y-%m-%d %H:%M')}")

    setup_nanohermes()

    # 测试 1: 单任务委托
    r1 = test_delegation_single()

    # 清理会话，避免干扰
    os.system('rm -rf ~/.nanohermes/sessions/* ~/.nanohermes/sessions.db* ~/.nanohermes/memory/* 2>/dev/null')

    # 测试 2: 简单 goal 模式
    r2 = test_delegation_goal_only()

    print("\n" + "="*60)
    print("📊 汇总结果")
    print("="*60)
    print("\n测试 1 (单任务委托):")
    for k, v in r1.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print("\n测试 2 (简单 goal):")
    for k, v in r2.items():
        print(f"  {'✅' if v else '❌'} {k}")

    passed1 = sum(1 for v in r1.values() if v)
    passed2 = sum(1 for v in r2.values() if v)
    total1 = len(r1)
    total2 = len(r2)

    print(f"\n测试 1: {passed1}/{total1} 通过")
    print(f"测试 2: {passed2}/{total2} 通过")
    print(f"总计: {passed1+passed2}/{total1+total2} 通过")
