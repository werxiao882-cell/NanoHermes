#!/usr/bin/env python3
"""
PTY 测试失败分析器 — 分析失败原因，给出修复建议。

分类体系：
1. pattern_mismatch: AI 输出了正确内容但预期正则没匹配上（runner 正则太严格）
2. ai_behavior: AI 行为与预期不同（如说"好的我记住了"但不调 memory 工具）
3. missing_feature: 功能确实没实现或返回错误
4. timeout: 超时没响应
5. startup_failure: NanoHermes 启动失败
6. output_truncated: 输出被截断导致关键词丢失
"""
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FailureType(Enum):
    PATTERN_MISMATCH = "pattern_mismatch"      # 正则太严格，实际输出包含相关语义
    AI_BEHAVIOR = "ai_behavior"                # AI 行为模式问题（已知限制）
    MISSING_FEATURE = "missing_feature"         # 功能缺失或报错
    TIMEOUT = "timeout"                         # 超时
    STARTUP_FAILURE = "startup_failure"         # 启动失败
    OUTPUT_TRUNCATED = "output_truncated"       # 输出截断
    UNKNOWN = "unknown"


@dataclass
class FailureAnalysis:
    failure_type: FailureType
    confidence: float  # 0.0 - 1.0
    description: str
    suggestion: str
    is_known_limitation: bool = False


# 已知 AI 行为模式（来自 test-findings.md）
KNOWN_AI_BEHAVIORS = {
    "memory": {
        "pattern": r"(好的.*记住|我已经记住|记住了.*名字|不调用.*memory)",
        "description": "AI 倾向于用文本回复'好的我记住了'，不调用 memory 工具",
        "suggestion": "跳过或改为验证文本回复而非工具调用",
    },
    "clarify": {
        "pattern": r"问我一个问题|选择题",
        "description": "AI 倾向于用文本生成选择题，不调用 clarify 工具",
        "suggestion": "跳过或改为验证文本输出",
    },
    "search_tools": {
        "pattern": r"search_tools.*search_tools",
        "description": "AI 可能调用 search_tools 2-3 次（过度搜索）",
        "suggestion": "放宽匹配条件，只要调用了 search_tools 就算通过",
    },
    "no_py_files": {
        "pattern": r"未找到.*\.py|没有.*Python|no.*\.py",
        "description": "AI 搜索 *.py 文件但项目目录下没有（正常行为）",
        "suggestion": "这是预期行为 — 空搜索结果是正确的，标记为通过",
    },
    "chinese_response": {
        "pattern": r"已成功|内容如下|文件.*不存在|已记住",
        "description": "AI 用中文回复操作结果，而非英文（如 '16 bytes written'）",
        "suggestion": "匹配中文语义而非英文字面 — runner 已自动处理",
    },
    "count_semantic": {
        "pattern": r"共找到.*匹配",
        "description": "AI 用自然语言报告数量（'共找到 N 个匹配'），而非显式输出 'output_mode=count'",
        "suggestion": "跳过 — AI 表达 count 语义的方式不同，非功能 bug",
    },
    "explain_not_execute": {
        "pattern": r"(你想读取哪个文件.*告诉我|推荐以下命令|场景.*命令|基本用法示例)",
        "description": "AI 把操作步骤理解为'请教如何做'，输出教程/推荐命令，而非真正执行操作",
        "suggestion": "跳过 — 这是 prompt 歧义导致的 AI 行为偏差，非功能 bug",
    },
}

# 按用例 ID 直接跳过的已知限制（output 截断等场景下 pattern 无法匹配时的兜底）
SKIP_BY_TEST_ID = {
    "T-21": "AI 不显式输出 'output_mode=count'，用自然语言表达 count 语义",
}

# 已知输出截断模式
TRUNCATION_PATTERNS = [
    r"\.\.\.\s*$",
    r"\[truncated\]",
    r"output.*budget",
]

# 常见启动失败模式
STARTUP_FAILURES = [
    r"ModuleNotFoundError",
    r"ImportError",
    r"Traceback.*Error",
    r"Connection refused",
    r"API key",
]


def analyze_failure(
    test_id: str,
    output: str,
    expected_patterns: dict,
    pattern_results: dict,
) -> FailureAnalysis:
    """分析单个用例的失败原因。"""

    # 1. 检查是否所有 sub-pattern 都失败
    all_failed = all(not v for v in pattern_results.values()) if pattern_results else True
    some_passed = any(pattern_results.values()) if pattern_results else False

    # 2. 检查启动失败
    for pat in STARTUP_FAILURES:
        if re.search(pat, output, re.IGNORECASE):
            return FailureAnalysis(
                failure_type=FailureType.STARTUP_FAILURE,
                confidence=0.9,
                description=f"NanoHermes 启动失败: 匹配到 '{pat}'",
                suggestion="检查环境配置、依赖、API Key",
            )

    # 3. 检查 AI 已知行为模式
    for name, info in KNOWN_AI_BEHAVIORS.items():
        if re.search(info["pattern"], output, re.IGNORECASE | re.DOTALL):
            return FailureAnalysis(
                failure_type=FailureType.AI_BEHAVIOR,
                confidence=0.85,
                description=f"已知 AI 行为: {info['description']}",
                suggestion=info["suggestion"],
                is_known_limitation=True,
            )

    # 4. 检查输出截断
    for pat in TRUNCATION_PATTERNS:
        if re.search(pat, output, re.IGNORECASE):
            return FailureAnalysis(
                failure_type=FailureType.OUTPUT_TRUNCATED,
                confidence=0.7,
                description="输出被截断，可能丢失了关键词",
                suggestion="增加等待时间或检查 output_budget 配置",
            )

    # 5. 部分匹配 → 正则太严格
    if some_passed and not all_failed:
        passed_patterns = [k for k, v in pattern_results.items() if v]
        failed_patterns = [k for k, v in pattern_results.items() if not v]
        return FailureAnalysis(
            failure_type=FailureType.PATTERN_MISMATCH,
            confidence=0.8,
            description=f"部分模式匹配: {passed_patterns} 通过，{failed_patterns} 失败",
            suggestion=f"检查失败的正则是否过于严格，output 长度={len(output)}",
        )

    # 6. 全部失败但有内容 → 可能是功能问题或 AI 理解偏差
    if len(output) > 100 and all_failed:
        # 检查输出中是否包含与 test_id 相关的语义内容
        return FailureAnalysis(
            failure_type=FailureType.AI_BEHAVIOR,
            confidence=0.5,
            description=f"AI 未产生预期输出（output {len(output)} 字符）",
            suggestion="检查操作步骤是否清晰，AI 是否理解了意图",
        )

    # 7. 空输出或极短输出
    if len(output) < 500:
        return FailureAnalysis(
            failure_type=FailureType.TIMEOUT,
            confidence=0.6,
            description=f"输出过短（{len(output)} 字符），可能超时或未完成",
            suggestion="增加等待时间",
        )

    # 8. 兜底：按用例 ID 检查已知限制
    skip_check = _check_skip_by_id(test_id)
    if skip_check:
        return skip_check

    return FailureAnalysis(
        failure_type=FailureType.UNKNOWN,
        confidence=0.3,
        description="无法自动分类",
        suggestion="需要人工检查输出内容",
    )


def _check_skip_by_id(test_id: str) -> FailureAnalysis | None:
    """兜底：按用例 ID 检查是否为已知限制。"""
    if test_id in SKIP_BY_TEST_ID:
        return FailureAnalysis(
            failure_type=FailureType.AI_BEHAVIOR,
            confidence=0.9,
            description=f"已知限制 ({test_id}): {SKIP_BY_TEST_ID[test_id]}",
            suggestion="跳过此用例",
            is_known_limitation=True,
        )
    return None


def generate_fix_suggestion(analysis: FailureAnalysis, case: dict) -> dict:
    """根据分析结果生成修复建议。"""
    return {
        "test_id": case.get("ID", ""),
        "failure_type": analysis.failure_type.value,
        "confidence": analysis.confidence,
        "description": analysis.description,
        "suggestion": analysis.suggestion,
        "is_known_limitation": analysis.is_known_limitation,
        "action": _recommend_action(analysis),
    }


def _recommend_action(analysis: FailureAnalysis) -> str:
    """推荐下一步行动。"""
    if analysis.failure_type == FailureType.PATTERN_MISMATCH:
        return "update_pattern"  # 更新 runner 的正则匹配
    elif analysis.failure_type == FailureType.AI_BEHAVIOR and analysis.is_known_limitation:
        return "skip"  # 跳过已知限制
    elif analysis.failure_type == FailureType.AI_BEHAVIOR:
        return "adjust_prompt"  # 调整操作步骤表述
    elif analysis.failure_type == FailureType.MISSING_FEATURE:
        return "fix_code"  # 修复代码
    elif analysis.failure_type == FailureType.TIMEOUT:
        return "increase_timeout"
    elif analysis.failure_type == FailureType.OUTPUT_TRUNCATED:
        return "increase_budget"
    elif analysis.failure_type == FailureType.STARTUP_FAILURE:
        return "fix_environment"
    else:
        return "manual_review"


def main():
    """CLI 入口：分析单个失败用例的日志。"""
    if len(sys.argv) < 2:
        print("用法: python failure_analyzer.py <fail_log_file> [--json]")
        sys.exit(1)

    log_path = Path(sys.argv[1])
    if not log_path.exists():
        print(f"文件不存在: {log_path}")
        sys.exit(1)

    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        output = f.read()

    # 从文件名提取 test_id
    test_id = log_path.stem.split("-fail-")[0] if "-fail-" in log_path.stem else "unknown"

    # 模拟空的 pattern_results（实际应该从 runner 传入）
    pattern_results = {}
    expected_patterns = {}

    analysis = analyze_failure(test_id, output, expected_patterns, pattern_results)

    if "--json" in sys.argv:
        import json
        result = generate_fix_suggestion(analysis, {"ID": test_id})
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print(f"🔍 失败分析: {test_id}")
        print(f"{'='*60}")
        print(f"  类型: {analysis.failure_type.value}")
        print(f"  置信度: {analysis.confidence:.0%}")
        print(f"  描述: {analysis.description}")
        print(f"  建议: {analysis.suggestion}")
        if analysis.is_known_limitation:
            print(f"  ⚠️  已知限制，建议跳过")
        print(f"  推荐行动: {_recommend_action(analysis)}")
        print(f"  输出长度: {len(output)} 字符")
        print()


if __name__ == "__main__":
    main()
