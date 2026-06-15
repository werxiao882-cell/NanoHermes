#!/usr/bin/env python3
"""
NanoHermes PTY 回归测试 — 直接从 reference 文件解析用例执行。

解析 references/*.md 中的 markdown 表格，提取所有 [PTY] 标记的用例，
每个用例独立启动 NanoHermes 会话，使用 script 命令捕获输出。

用法:
    eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312
    python reference_runner.py [--refs core-tools,session-storage] [--stage 3] [--dry-run]

输出: testing-artifacts/reports/report-YYYY-MM-DD-HHMM.md
"""
import argparse
import os
import re
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

# === 配置 ===
SKILL_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
REF_DIR = SKILL_DIR / "references"
WORKDIR = "/mnt/d/code/NanoHermes"
OUTPUT_BASE = SKILL_DIR / "testing-artifacts"
LOG_DIR = OUTPUT_BASE / "logs"
REPORT_DIR = OUTPUT_BASE / "reports"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y-%m-%d-%H%M")
LOG_FILE = LOG_DIR / f"reference-{TIMESTAMP}.log"
REPORT_FILE = REPORT_DIR / f"report-{TIMESTAMP}.md"

# 等待时间映射（根据用例类型自动选择）
WAIT_MAP = {
    'default': 15,
    'search': 40,       # 文件/内容搜索较慢
    'compute': 25,      # 代码执行计算
    'context': 45,      # 带上下文的搜索
    'memory': 10,       # 记忆操作
    'startup': 12,      # 启动验证
    'storage': 10,      # 存储验证
}


def parse_markdown_tables(filepath):
    """从 markdown 文件中提取所有表格行，返回测试用例列表。"""
    cases = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 markdown 表格：找到所有表格块
    # 表格格式: | ID | 测试内容 | 操作步骤 | 预期 | 标记 |
    lines = content.split('\n')
    in_table = False
    headers = []
    header_idx = 0

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('|'):
            if in_table:
                in_table = False
                headers = []
            continue

        # 跳过分隔行 (|----|...)
        if re.match(r'^\|[\s\-\|:]+\|', stripped):
            continue

        cells = [c.strip() for c in stripped.strip('|').split('|')]

        if not headers:
            # 这是表头行
            headers = cells
            in_table = True
            continue

        if len(cells) != len(headers):
            continue

        row = dict(zip(headers, cells))
        if '标记' in row and 'ID' in row:
            cases.append(row)

    return cases


def extract_keywords(expected_text):
    """从预期描述中提取匹配关键词。
    
    策略：
    1. 如果包含引号，提取引号内的内容（精确匹配）
    2. 如果包含具体数字，提取数字
    3. 否则提取关键中文字词
    """
    # 引号内的内容
    quotes = re.findall(r'"([^"]+)"|\'([^\']+)\'', expected_text)
    quoted = [q[0] or q[1] for q in quotes if q[0] or q[1]]
    if quoted:
        return quoted

    # 具体数字
    numbers = re.findall(r'\d+(?:\.\d+)?', expected_text)
    # 中文字词（2-4 字）
    chinese = re.findall(r'[\u4e00-\u9fff]{2,6}', expected_text)

    return numbers + chinese


def build_regex_patterns(case):
    """从用例构建正则匹配模式。"""
    expected = case.get('预期', '')
    test_id = case.get('ID', '')
    test_content = case.get('测试内容', '')
    operation = case.get('操作步骤', '')

    patterns = {}

    # 1. 从预期描述提取关键词
    keywords = extract_keywords(expected)
    if keywords:
        # 构建 OR 模式：任一关键词匹配即可
        patterns['expected'] = '|'.join(re.escape(k) for k in keywords)

    # 2. 从测试内容提取补充模式
    content_keywords = extract_keywords(test_content)
    if content_keywords:
        patterns['content'] = '|'.join(re.escape(k) for k in content_keywords)

    # 3. 特定用例的特殊处理
    id_prefix = test_id.split('-')[0] if '-' in test_id else ''

    # T-02: echo hello
    if test_id == 'T-02':
        patterns['hello'] = r'\bhello\b'

    # T-14: false exit code
    if test_id == 'T-14':
        patterns['exit_code'] = r'exit.*1|code.*1|non.?zero|失败|error'

    # T-10: prime sum
    if test_id == 'T-10':
        patterns['sum'] = r'\b1060\b'

    # memory 相关
    if id_prefix in ('M',) or 'memory' in test_content.lower():
        patterns['memory'] = r'memory|记忆|成功|success|saved'

    # tool search 相关
    if id_prefix == 'TS':
        patterns['search'] = r'search|搜索|工具|tool'

    # TUI 命令
    if test_id.startswith('TUI') or operation.startswith('/'):
        cmd = operation.split()[0] if operation.startswith('/') else ''
        if cmd:
            patterns['command'] = re.escape(cmd[1:])  # 去掉 /

    # 存储验证
    if id_prefix == 'S':
        patterns['storage'] = r'session|会话|ID|store|存储|jsonl|sqlite'

    # provider 相关
    if id_prefix == 'P':
        patterns['provider'] = r'response|响应|token|model|stream|流'

    # config 相关
    if id_prefix == 'CF':
        patterns['config'] = r'config|配置|load|加载|env'

    # prompt 相关
    if id_prefix == 'PA':
        patterns['prompt'] = r'prompt|提示|stable|context|cache'

    # conversation 相关
    if id_prefix == 'C':
        patterns['conversation'] = r'response|响应|reply|回答|工具|tool'

    # advanced/skills 相关
    if id_prefix in ('SK', 'CC', 'I', 'AUX'):
        patterns['advanced'] = r'skill|技能|压缩|token|insights|后台|async'

    return patterns


def get_wait_time(case):
    """根据用例类型确定等待时间。"""
    test_id = case.get('ID', '')
    operation = case.get('操作步骤', '')
    test_content = case.get('测试内容', '')

    # 搜索类
    if any(kw in operation.lower() for kw in ['搜索', 'search', 'class', 'async']):
        return WAIT_MAP['search']
    if '上下文' in operation or 'context' in operation.lower():
        return WAIT_MAP['context']

    # 计算类
    if any(kw in operation.lower() for kw in ['计算', 'compute', '质数', 'sum']):
        return WAIT_MAP['compute']

    # 记忆类
    if 'memory' in operation.lower() or '记住' in operation:
        return WAIT_MAP['memory']

    # 默认
    return WAIT_MAP['default']


def clean_ansi(text):
    """移除所有 ANSI 转义序列。"""
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'\x1b\[\?[0-9]+[a-z]', '', text)
    text = re.sub(r'\x1b\][0-9];.*?\x07', '', text)
    text = re.sub(r'\x08', '', text)
    text = re.sub(r'\r\n', '\n', text)
    return text


def setup_nanohermes():
    """创建最小 nanohermes.json 配置。"""
    config_path = Path(WORKDIR) / "nanohermes.json"
    if not config_path.exists():
        config = {
            "model": {
                "provider": "openai",
                "name": "qwen3.6-plus"
            },
            "providers": {
                "openai": {
                    "base_url_env": "OPENAI_BASE_URL",
                    "api_key_env": "OPENAI_API_KEY"
                }
            },
            "tui": {
                "typing_speed": 10,
                "show_tool_panel": True,
                "tool_panel_position": "right"
            }
        }
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"  ✓ 创建 nanohermes.json")


def run_single_test(test_id, prompt, patterns, wait_time=15, setup_cmd=None):
    """启动独立的 NanoHermes 会话执行单个测试。"""
    script_log = f"/tmp/nanohermes_{test_id}_{int(time.time())}.log"

    # 执行 setup 命令（如果有）
    if setup_cmd:
        subprocess.run(setup_cmd, shell=True, capture_output=True, timeout=30)

    # 启动 NanoHermes（使用 script 捕获 TUI 输出）
    cmd = (
        f'eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && '
        f'conda activate py312 && '
        f'cd {WORKDIR} && '
        f'script -q -c "python -m src.main" {script_log}'
    )

    import pexpect
    child = pexpect.spawn(
        'bash',
        args=['-c', cmd],
        encoding='utf-8',
        timeout=120,
        maxread=80000,
    )

    # 等待启动
    time.sleep(WAIT_MAP['startup'])

    # 发送测试输入
    child.sendline(prompt)
    time.sleep(wait_time)

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

    # 匹配预期模式
    results = {}
    all_pass = True

    for name, pattern in patterns.items():
        try:
            if re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL):
                results[name] = True
            else:
                results[name] = False
                all_pass = False
        except re.error:
            # 正则错误，回退到字符串匹配
            if pattern.lower() in cleaned.lower():
                results[name] = True
            else:
                results[name] = False
                all_pass = False

    return {
        'id': test_id,
        'status': 'PASS' if all_pass else 'FAIL',
        'patterns': results,
        'output_snippet': cleaned[-500:] if cleaned else "(empty)",
        'output_len': len(cleaned),
    }


def get_setup_command(case):
    """从用例中提取 setup 命令（如果有特殊要求）。"""
    operation = case.get('操作步骤', '')
    test_id = case.get('ID', '')

    # T-44: 二进制文件测试需要创建测试文件
    if test_id == 'T-44':
        return f'cd {WORKDIR} && python3 -c "import base64; open(\'/tmp/test_binary.png\',\'wb\').write(base64.b64decode(\'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==\'))"'

    # T-22: 需要创建测试文件用于上下文搜索
    if test_id == 'T-22':
        return f'printf "import asyncio\\n\\nasync def fetch_data(url):\\n    await asyncio.sleep(1)\\n    return ok" > /tmp/test_async.py'

    return None


def main():
    parser = argparse.ArgumentParser(description='NanoHermes PTY 回归测试（从 reference 文件执行）')
    parser.add_argument('--refs', help='逗号分隔的 reference 文件名（不含 .md），如 core-tools,session-storage')
    parser.add_argument('--stage', type=int, help='执行指定阶段（1-7）')
    parser.add_argument('--dry-run', action='store_true', help='只列出不执行')
    parser.add_argument('--include-tags', help='只执行包含指定标记的用例，如 PTY,FIXME')
    args = parser.parse_args()

    print("=" * 70)
    print("🧪 NanoHermes PTY 回归测试 — Reference Runner")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📂 Reference 目录: {REF_DIR}")
    print("=" * 70)

    # 确定要加载的 reference 文件
    ref_files = {
        'core-tools': REF_DIR / 'core-tools.md',
        'conversation': REF_DIR / 'conversation.md',
        'session-storage': REF_DIR / 'session-storage.md',
        'memory-system': REF_DIR / 'memory-system.md',
        'provider-config': REF_DIR / 'provider-config.md',
        'cli-tui': REF_DIR / 'cli-tui.md',
        'advanced': REF_DIR / 'advanced.md',
    }

    if args.refs:
        selected = {k: v for k, v in ref_files.items() if k in args.refs.split(',')}
        if not selected:
            print(f"❌ 未找到 reference: {args.refs}")
            sys.exit(1)
        ref_files = selected

    # 解析所有用例
    all_cases = []
    for name, path in ref_files.items():
        if not path.exists():
            print(f"  ⚠️  跳过不存在的文件: {path}")
            continue
        cases = parse_markdown_tables(path)
        for c in cases:
            c['_source'] = name
        all_cases.extend(cases)
        print(f"  📄 {name}: {len(cases)} 个用例")

    # 过滤 [PTY] 用例
    pty_cases = []
    for c in all_cases:
        tag = c.get('标记', '')
        if '[PTY]' in tag:
            pty_cases.append(c)

    print(f"\n📊 总计: {len(all_cases)} 个用例, {len(pty_cases)} 个 [PTY]")

    if args.dry_run:
        print("\n📋 用例列表:")
        for c in pty_cases:
            print(f"  {c['ID']}: {c['测试内容']}")
            print(f"    操作: {c['操作步骤']}")
            print(f"    预期: {c['预期']}")
        return

    # 环境准备
    print("\n🔧 环境准备...")
    os.system('rm -rf ~/.nanohermes/sessions/* ~/.nanohermes/sessions.db* ~/.nanohermes/memory/* 2>/dev/null')
    setup_nanohermes()

    start_time = time.time()
    all_results = []

    for i, tc in enumerate(pty_cases):
        test_id = tc['ID']
        prompt = tc['操作步骤']
        patterns = build_regex_patterns(tc)
        wait = get_wait_time(tc)
        setup_cmd = get_setup_command(tc)

        print(f"\n🧪 [{i+1}/{len(pty_cases)}] {test_id}: {tc['测试内容']}")
        print(f"   操作: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

        result = run_single_test(test_id, prompt, patterns, wait, setup_cmd)
        all_results.append(result)

        status_icon = "✅" if result['status'] == 'PASS' else "❌"
        print(f"   {status_icon} {result['status']} (输出 {result['output_len']} 字符)")
        if result['status'] == 'FAIL':
            details = ", ".join([f"{k}={'✓' if v else '✗'}" for k, v in result['patterns'].items()])
            print(f"   📝 {details}")
            # 保存失败日志
            fail_log = LOG_DIR / f"{test_id}-fail-{TIMESTAMP}.log"
            with open(fail_log, 'w') as f:
                f.write(result['output_snippet'])
            print(f"   📄 日志: {fail_log}")

    duration = time.time() - start_time

    # 文件系统验证
    print("\n🔍 文件系统验证...")
    db_path = os.path.expanduser("~/.nanohermes/sessions.db")
    sessions_dir = os.path.expanduser("~/.nanohermes/sessions")
    db_ok = os.path.exists(db_path)
    jsonl_ok = os.path.exists(sessions_dir) and any(f.endswith('.jsonl') for f in os.listdir(sessions_dir))
    print(f"  {'✅' if db_ok else '❌'} sessions.db: {'存在' if db_ok else '不存在'}")
    print(f"  {'✅' if jsonl_ok else '❌'} JSONL 文件: {'有' if jsonl_ok else '无'}")

    # 生成报告
    total = len(all_results)
    passed = sum(1 for r in all_results if r['status'] == 'PASS')
    failed = sum(1 for r in all_results if r['status'] == 'FAIL')
    rate = (passed / total * 100) if total > 0 else 0

    report_lines = [
        f"# NanoHermes PTY 回归测试报告",
        f"",
        f"**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**总耗时**: {duration:.0f} 秒",
        f"**来源**: reference 文件 ({', '.join(ref_files.keys())})",
        f"**策略**: 每用例独立会话 + script 捕获 + ANSI 清理",
        f"",
        f"## 结果摘要",
        f"",
        f"| 总计 | 通过 | 失败 | 通过率 |",
        f"|------|------|------|--------|",
        f"| {total} | {passed} | {failed} | **{rate:.1f}%** |",
        f"",
        f"## 详细结果",
        f"",
        f"| ID | 来源 | 状态 | 详情 |",
        f"|----|------|------|------|",
    ]

    for r in all_results:
        # 找到对应的 source
        source = next((tc['_source'] for tc in pty_cases if tc['ID'] == r['id']), '?')
        status_icon = "✅" if r['status'] == 'PASS' else "❌"
        details = ", ".join([f"{k}={'✓' if v else '✗'}" for k, v in r['patterns'].items()])
        report_lines.append(f"| {r['id']} | {source} | {status_icon} {r['status']} | {details} |")

    report_lines.extend([
        f"",
        f"## 日志",
        f"",
        f"`{LOG_FILE}`",
        f"",
        f"失败用例详细输出保存在 `testing-artifacts/logs/` 目录下。",
    ])

    report = "\n".join(report_lines)

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
        for r in all_results:
            f.write(f"\n### {r['id']} ({r['status']})\n```\n{r['output_snippet'][:1000]}\n```\n")

    print(f"\n{'='*70}")
    print(f"📊 总计: {total} | 通过: {passed} | 失败: {failed} | 通过率: {rate:.1f}%")
    print(f"⏱️  耗时: {duration:.0f} 秒")
    print(f"📄 报告: {REPORT_FILE}")
    print(f"📄 日志: {LOG_FILE}")


if __name__ == '__main__':
    main()
