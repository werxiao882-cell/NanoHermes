#!/usr/bin/env python3
"""
NanoHermes PTY 测试 Runner v2 — 使用 script 命令捕获 TUI 输出

解决 v1 的问题：pexpect buffer 被 Textual 清屏序列清空。
本版本通过 script 命令在 TTY 外层录制完整终端会话。

用法：
    python pty_runner_v2.py
"""
import pexpect
import os
import re
import sys
import time

def clean_ansi(text):
    """移除 ANSI 转义序列"""
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'\x1b\[\?[0-9]+[a-z]', '', text)
    text = re.sub(r'\x1b\][0-9];.*?\x07', '', text)
    text = re.sub(r'\x08', '', text)
    text = re.sub(r'\r\n', '\n', text)
    return text

def run_test(test_id, prompt, workdir, expected_patterns,
             startup_wait=12, response_wait=15, log_dir='/tmp'):
    """运行单个 PTY 测试用例
    
    Args:
        test_id: 用例 ID（如 TS-01）
        prompt: 发送给 NanoHermes 的输入
        workdir: NanoHermes 项目目录
        expected_patterns: {名称: 正则表达式}
        startup_wait: 启动后等待秒数
        response_wait: 发送提示后等待秒数
        log_dir: 日志输出目录
    
    Returns:
        (results_dict, cleaned_output)
    """
    os.makedirs(log_dir, exist_ok=True)
    script_output = os.path.join(log_dir, f"{test_id}_script.log")
    
    cmd = (f'eval "$($HOME/miniconda3/bin/conda shell.bash hook)" '
           f'&& conda activate py312 && cd {workdir} '
           f'&& script -q -c "python -m src.main" {script_output}')
    
    child = pexpect.spawn(
        'bash',
        args=['-c', cmd],
        encoding='utf-8',
        timeout=60,
    )
    
    try:
        # 等待 TUI 启动渲染
        time.sleep(startup_wait)
        
        # 发送测试输入
        child.sendline(prompt)
        
        # 等待 AI 响应
        time.sleep(response_wait)
        
        child.close(force=True)
        
    except Exception as e:
        try:
            child.close(force=True)
        except:
            pass
    
    # 读取 script 输出
    if os.path.exists(script_output):
        with open(script_output, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        
        cleaned = clean_ansi(raw)
        
        # 验证预期模式
        results = {}
        for name, pattern in expected_patterns.items():
            results[name] = bool(re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL))
        
        return results, cleaned
    else:
        return {"script_output_missing": False}, ""

if __name__ == '__main__':
    workdir = "/mnt/d/code/NanoHermes"
    
    # 示例：TS-01 /tools 延迟加载标记验证
    results, output = run_test(
        "TS-01",
        "/tools",
        workdir,
        {
            "has_deferred": r'deferred',
            "has_loaded": r'loaded',
            "memory_deferred": r'memory.*deferred|deferred.*memory',
        }
    )
    
    for name, passed in results.items():
        print(f"  {name}: {'✅' if passed else '❌'}")
