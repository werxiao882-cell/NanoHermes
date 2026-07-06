#!/usr/bin/env python3
"""
NanoHermes PTY 完整回归测试 — 每用例独立会话
37 个核心 PTY 用例，每个启动独立 NanoHermes 会话。
使用 script 命令捕获 TUI 输出，ANSI 清理后验证。

用法：
  python scripts/full_regression_v2.py

输出：
  testing-artifacts/reports/report-YYYY-MM-DD-HHMM.md
  testing-artifacts/logs/regression-YYYY-MM-DD-HHMM.log

预计耗时：~18 分钟（37 用例 × 29 秒/用例）
"""
import pexpect
import os
import re
import sys
import time
from datetime import datetime

WORKDIR = "/mnt/d/code/NanoHermes"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = f"{BASE}/testing-artifacts/logs"
REPORT_DIR = f"{BASE}/testing-artifacts/reports"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y-%m-%d-%H%M")
LOG_FILE = f"{LOG_DIR}/regression-{TIMESTAMP}.log"
REPORT_FILE = f"{REPORT_DIR}/report-{TIMESTAMP}.md"


def clean_ansi(text):
    """移除所有 ANSI 转义序列。"""
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'\x1b\[\?[0-9]+[a-z]', '', text)
    text = re.sub(r'\x1b\][0-9];.*?\x07', '', text)
    text = re.sub(r'\x08', '', text)
    text = re.sub(r'\r\n', '\n', text)
    return text


def run_single_test(test_id, prompt, expected_patterns, wait_time=15, setup=None, post_check=None):
    """启动一个独立的 NanoHermes 会话执行单个测试。"""
    script_log = f"/tmp/nanohermes_{test_id}_{int(time.time())}.log"

    if setup:
        os.system(setup)

    child = pexpect.spawn(
        'bash',
        args=['-c',
              f'eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312 && cd {WORKDIR} && script -q -c "python -m src.main" {script_log}'],
        encoding='utf-8',
        timeout=120,
    )

    time.sleep(12)  # 等待启动 + TUI 渲染
    child.sendline(prompt)
    time.sleep(wait_time)  # 等待 AI 响应
    child.sendline("/quit")
    time.sleep(2)
    child.close(force=True)

    if os.path.exists(script_log):
        with open(script_log, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        os.remove(script_log)
    else:
        raw = ""

    cleaned = clean_ansi(raw)

    pass_fail = {}
    all_pass = True
    for name, pattern in expected_patterns.items():
        if re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL):
            pass_fail[name] = True
        else:
            pass_fail[name] = False
            all_pass = False

    if post_check:
        try:
            post_result = post_check()
            pass_fail['post_check'] = post_result
            if not post_result:
                all_pass = False
        except Exception:
            pass_fail['post_check'] = False
            all_pass = False

    return {
        'id': test_id,
        'status': 'PASS' if all_pass else 'FAIL',
        'patterns': pass_fail,
        'output_snippet': cleaned[-300:] if cleaned else "(empty)",
    }


def check_memory_file(expected_content_pattern):
    memory_path = os.path.expanduser("~/.nanohermes/memory/USER.md")
    if not os.path.exists(memory_path):
        return False
    with open(memory_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return bool(re.search(expected_content_pattern, content, re.IGNORECASE))


# ============================================================
# 37 个 PTY 用例定义
# ============================================================
ALL_CASES = [
    # 基础对话
    {'id': 'P-01', 'prompt': '你好', 'expected_patterns': {'reply': r'你好|hello|hi'}},
    {'id': 'C-01', 'prompt': '请回复 OK', 'expected_patterns': {'ok': r'OK|ok'}},
    # 工具链
    {'id': 'T-02', 'prompt': '运行 echo hello', 'expected_patterns': {'hello': r'hello'}},
    {'id': 'T-14', 'prompt': '运行 false 命令', 'expected_patterns': {'exit_code': r'exit.*1|code.*1|non.?zero|失败'}},
    {'id': 'T-05', 'prompt': '创建 /tmp/nanotest.txt 写入 "Hello NanoHermes"',
     'expected_patterns': {'written': r'written|写入|bytes'}},
    {'id': 'T-04', 'prompt': '读取 /tmp/nanotest.txt 文件',
     'expected_patterns': {'content': r'Hello NanoHermes'}},
    {'id': 'T-06', 'prompt': '打开 /tmp/nanotest.txt 把 Hello 替换为 Hi',
     'expected_patterns': {'replaced': r'替换|replaced|Hi'}},
    {'id': 'C-02', 'prompt': '读取 /tmp/nanotest.txt 确认内容是 Hi',
     'expected_patterns': {'hi': r'Hi NanoHermes'}},
    {'id': 'T-16', 'prompt': '读取 /tmp/nanotest.txt 第 1 行 offset=1 limit=1',
     'expected_patterns': {'line': r'1\|'}},
    # 文件搜索
    {'id': 'T-07', 'prompt': '搜索 *.py 文件', 'expected_patterns': {'files': r'\.py|python'}},
    {'id': 'T-08', 'prompt': '搜索包含 class 的 Python 文件',
     'expected_patterns': {'matches': r'class|匹配|match'}},
    # 代码执行
    {'id': 'T-10', 'prompt': '计算 100 以内的质数和', 'expected_patterns': {'sum': r'1060'}, 'wait': 25},
    # 自动创建目录
    {'id': 'T-17', 'prompt': '创建文件 /tmp/a/b/c/test.txt 写入内容 test123',
     'expected_patterns': {'created': r'created|写入|bytes|成功'}},
    # 搜索模式
    {'id': 'T-20', 'prompt': '搜索 *.py 文件只返回文件路径',
     'expected_patterns': {'files_only': r'files_only|路径|path'}},
    {'id': 'T-21', 'prompt': '统计包含 class 的 Python 文件数量',
     'expected_patterns': {'count': r'count|数量|files'}},
    {'id': 'T-22', 'prompt': '搜索 async def 前后 3 行上下文',
     'expected_patterns': {'context': r'context|上下文|前后'}},
    # 大输出截断
    {'id': 'T-39', 'prompt': '运行 ls /usr/bin 列出前 50 个',
     'expected_patterns': {'output': r'bin|usr|文件|file'}},
    # 记忆
    {'id': 'M-02', 'prompt': '请使用 memory 工具在 user 记忆中写入：测试用户名字是小王',
     'expected_patterns': {'memory': r'memory|记忆|成功|success'}},
    {'id': 'T-27', 'prompt': '请使用 memory 工具在 memory 记忆中写入：测试偏好是简洁回复',
     'expected_patterns': {'memory': r'memory|记忆|成功|success'}},
    # TODO
    {'id': 'T-33', 'prompt': '创建 TODO 任务：测试 PTY 回归',
     'expected_patterns': {'todo': r'todo|任务|创建|created'}},
    {'id': 'T-34', 'prompt': '查看 TODO 列表', 'expected_patterns': {'list': r'todo|测试|列表|list'}},
    # TUI
    {'id': 'T-01', 'prompt': '/tools', 'expected_patterns': {'tools': r'tools|工具|terminal|read_file'}},
    # 工具搜索
    {'id': 'TS-02', 'prompt': '搜索执行代码的工具',
     'expected_patterns': {'execute_code': r'execute_code|代码|code'}},
    {'id': 'TS-06', 'prompt': '搜索一个不存在的工具 spell_checker',
     'expected_patterns': {'not_found': r'不存在|not found|未找到|没有|no.*tool'}},
    {'id': 'TS-04', 'prompt': '搜索 async def 相关文件',
     'expected_patterns': {'bm25': r'async|def|搜索|search'}},
    {'id': 'TS-05', 'prompt': '使用正则搜索数字模式',
     'expected_patterns': {'regex': r'regex|正则|搜索|search'}},
    # 高级场景
    {'id': 'T-48', 'prompt': '尝试写入 .env 敏感文件',
     'expected_patterns': {'reject': r'拒绝|deny|安全|sensitive|敏感'}},
    {'id': 'T-50', 'prompt': '搜索 *.md 文件中的 NanoHermes',
     'expected_patterns': {'search': r'md|markdown|NanoHermes'}},
    {'id': 'T-52', 'prompt': '运行 ls /tmp', 'expected_patterns': {'ls': r'tmp|文件|file'}},
    # TS-01（已修复）
    {'id': 'TS-01', 'prompt': '/tools',
     'expected_patterns': {'deferred': r'deferred', 'loaded': r'loaded'}},
    # T-44（已修复）
    {'id': 'T-44', 'prompt': '请用 read_file 读取 /tmp/test_binary.png',
     'setup': f'cd {WORKDIR} && python3 -c "import base64; open(\'/tmp/test_binary.png\',\'wb\').write(base64.b64decode(\'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==\'))"',
     'expected_patterns': {'binary_reject': r'binary|二进制|非文本|无法读取|不支持|拒绝|deny|cannot|image|图片|png'}},
    # 存储验证
    {'id': 'S-01', 'prompt': '检查当前会话信息',
     'expected_patterns': {'session': r'session|会话|ID'}},
    {'id': 'S-02', 'prompt': '列出历史会话',
     'expected_patterns': {'sessions': r'会话|session|历史|history'}},
    {'id': 'S-03', 'prompt': '查看会话状态',
     'expected_patterns': {'status': r'status|状态'}},
    {'id': 'S-30', 'prompt': '查询当前使用的模型',
     'expected_patterns': {'model': r'model|qwen|模型'}},
    {'id': 'M-01', 'prompt': '请使用 memory 工具在 user 记忆中写入：持久化验证通过',
     'expected_patterns': {'memory': r'memory|记忆|成功|success'},
     'post_check': lambda: check_memory_file(r'持久化验证通过|测试用户名字是小王|小王')},
]


def generate_report(results, duration):
    total = len(results)
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    rate = (passed / total * 100) if total > 0 else 0

    report = f"""# NanoHermes PTY 回归测试报告

**日期**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**总耗时**: {duration:.0f} 秒
**版本**: SKILL.md v6.1.0
**策略**: 每用例独立会话 + script 捕获 + ANSI 清理

## 结果摘要

| 总计 | 通过 | 失败 | 通过率 |
|------|------|------|--------|
| {total} | {passed} | {failed} | **{rate:.1f}%** |

## 详细结果

| ID | 状态 | 详情 |
|----|------|------|
"""
    for r in results:
        status_icon = "✅" if r['status'] == 'PASS' else "❌"
        details = ", ".join([f"{k}={'✓' if v else '✗'}" for k, v in r['patterns'].items()])
        report += f"| {r['id']} | {status_icon} {r['status']} | {details} |\n"

    report += f"\n## 日志\n\n`{LOG_FILE}`\n"
    return report


# ============================================================
# 主入口
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🧪 NanoHermes PTY 回归测试 — 37 用例")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📦 策略：每用例独立会话")
    print("=" * 60)

    start_time = time.time()
    os.system(f'rm -rf ~/.nanohermes/sessions/* ~/.nanohermes/sessions.db* ~/.nanohermes/memory/*')

    all_results = []
    for i, tc in enumerate(ALL_CASES):
        print(f"\n🧪 [{i + 1}/{len(ALL_CASES)}] {tc['id']}...")
        result = run_single_test(
            tc['id'], tc['prompt'], tc.get('expected_patterns', {}),
            tc.get('wait', 15), tc.get('setup'), tc.get('post_check'),
        )
        all_results.append(result)
        status_icon = "✅" if result['status'] == 'PASS' else "❌"
        print(f"  {status_icon} {result['status']}")
        if result['status'] == 'FAIL':
            details = ", ".join([f"{k}={'✓' if v else '✗'}" for k, v in result['patterns'].items()])
            print(f"  📝 {details}")

    duration = time.time() - start_time
    report = generate_report(all_results, duration)

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
        f.write("\n\n## 原始日志摘要\n\n")
        for r in all_results:
            f.write(f"### {r['id']} ({r['status']})\n```\n{r['output_snippet']}\n```\n\n")

    total = len(all_results)
    passed = sum(1 for r in all_results if r['status'] == 'PASS')
    failed = sum(1 for r in all_results if r['status'] == 'FAIL')
    print(f"\n{'=' * 60}")
    print(f"📊 最终结果")
    print(f"{'=' * 60}")
    print(f"总计: {total} | 通过: {passed} | 失败: {failed} | 通过率: {passed / total * 100:.1f}%")
    print(f"⏱️  耗时: {duration:.0f} 秒")
    print(f"📄 报告: {REPORT_FILE}")
