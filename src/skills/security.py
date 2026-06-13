"""安全扫描器 + 来源追踪 + AST 深度审计。

安全体系三合一模块：
1. SkillGuard: 正则静态分析，检测外部来源技能的安全风险
2. SkillProvenance: ContextVar 追踪技能写入来源
3. SkillAstAuditor: AST 深度审计，检测动态 import/属性访问

参考 hermes-agent-ref: tools/skills_guard.py, tools/skill_provenance.py, tools/skills_ast_audit.py
"""

from __future__ import annotations

import ast
import contextvars
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCANNABLE_EXTENSIONS = {
    ".md", ".txt", ".py", ".sh", ".bash", ".js", ".ts", ".rb",
    ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".conf",
    ".html", ".css", ".xml",
}

MAX_FILE_COUNT = 50
MAX_TOTAL_SIZE_KB = 1024


@dataclass
class Finding:
    """安全扫描发现。"""
    pattern_id: str
    severity: str
    category: str
    file: str
    line: int
    match: str
    description: str


@dataclass
class ScanResult:
    """扫描结果。"""
    skill_name: str
    trust_level: str
    verdict: str
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""


THREAT_PATTERNS: list[tuple[str, str, str, str]] = [
    (r"curl\s+.*\$\{.*(?:API_KEY|SECRET|TOKEN|PASSWORD).*\}", "env_exfil_curl", "critical", "exfiltration"),
    (r"wget\s+.*--post-file", "exfil_wget_post", "critical", "exfiltration"),
    (r"curl\s+.*-d\s+.*(?:api_key|secret|token|password)", "exfil_curl_data", "critical", "exfiltration"),
    (r"(?:cat|head|tail)\s+~\/\.ssh\/", "ssh_key_read", "critical", "exfiltration"),
    (r"(?:cat|head|tail)\s+~\/\.aws\/", "aws_cred_read", "critical", "exfiltration"),
    (r"os\.environ(?:\[|\.get)", "env_dump", "high", "exfiltration"),
    (r"eval\s*\(", "eval_injection", "high", "injection"),
    (r"exec\s*\(", "exec_injection", "high", "injection"),
    (r"ignore\s+(?:previous|all|above|prior)\s+instructions", "prompt_injection", "critical", "injection"),
    (r"system\s+prompt\s+override", "sys_prompt_override", "critical", "injection"),
    (r"developer\s+mode\s*(?:enabled|activated|on)", "developer_mode", "high", "injection"),
    (r"rm\s+-rf\s+/", "rm_rf_root", "critical", "destructive"),
    (r"rm\s+-rf\s+~", "rm_rf_home", "critical", "destructive"),
    (r"mkfs\.", "mkfs", "critical", "destructive"),
    (r"dd\s+if=/dev/zero", "dd_zero", "critical", "destructive"),
    (r"shutil\.rmtree\s*\(\s*['\"]/", "rmtree_root", "critical", "destructive"),
    (r"crontab\s+-", "crontab_mod", "high", "persistence"),
    (r"systemctl\s+enable", "systemd_enable", "medium", "persistence"),
    (r"echo\s+.*>>\s*~\/\.bashrc", "bashrc_mod", "high", "persistence"),
    (r"echo\s+.*>>\s*~\/\.zshrc", "zshrc_mod", "high", "persistence"),
    (r"ssh.*authorized_keys", "ssh_authorized_keys", "high", "persistence"),
    (r"nc\s+-[el]|ncat\s+-[el]|netcat\s+-[el]", "reverse_shell", "critical", "network"),
    (r"bash\s+-i\s+>&", "bash_reverse_shell", "critical", "network"),
    (r"/dev/tcp/", "dev_tcp", "critical", "network"),
    (r"ngrok|cloudflared", "tunnel", "high", "network"),
    (r"base64\s+(?:-d|--decode)\s*\|", "base64_pipe", "high", "obfuscation"),
    (r"echo\s+.*\|\s*(?:ba)?sh", "echo_pipe_shell", "critical", "obfuscation"),
    (r"chr\s*\(\s*\d+\s*\)\s*\+", "chr_build", "medium", "obfuscation"),
    (r"curl\s+.*\|\s*(?:ba)?sh", "curl_pipe_shell", "critical", "supply_chain"),
    (r"wget\s+.*\|\s*(?:ba)?sh", "wget_pipe_shell", "critical", "supply_chain"),
    (r"pip\s+install\s+.*--index-url", "pip_custom_index", "medium", "supply_chain"),
    (r"sudo\s+", "sudo_usage", "medium", "privilege_escalation"),
    (r"NOPASSWD", "sudo_nopasswd", "high", "privilege_escalation"),
]

INSTALL_POLICY = {
    "builtin":       {"safe": "allow", "caution": "allow", "dangerous": "allow"},
    "trusted":       {"safe": "allow", "caution": "allow", "dangerous": "block"},
    "community":     {"safe": "allow", "caution": "block", "dangerous": "block"},
    "agent-created": {"safe": "allow", "caution": "allow", "dangerous": "ask"},
}


class SkillGuard:
    """安全扫描器，正则静态分析检测外部来源技能的安全风险。"""

    def scan(self, skill_dir: Path, source: str = "community") -> ScanResult:
        """扫描技能目录中的所有文件。

        Args:
            skill_dir: 技能目录路径。
            source: 来源标识（builtin/trusted/community/agent-created）。

        Returns:
            扫描结果。
        """
        trust_level = self._resolve_trust_level(source)
        skill_name = skill_dir.name if skill_dir.is_dir() else skill_dir.stem

        if trust_level == "builtin":
            return ScanResult(
                skill_name=skill_name,
                trust_level=trust_level,
                verdict="safe",
                summary="Builtin skill, skipped.",
            )

        findings = self._scan_directory(skill_dir)
        verdict = self._determine_verdict(findings)

        return ScanResult(
            skill_name=skill_name,
            trust_level=trust_level,
            verdict=verdict,
            findings=findings,
            summary=f"{len(findings)} findings, verdict: {verdict}",
        )

    def should_allow_install(self, result: ScanResult, force: bool = False) -> tuple[bool | None, str]:
        """根据信任级别和扫描结果决定是否允许安装。

        Args:
            result: 扫描结果。
            force: 是否强制安装。

        Returns:
            (True, reason) 允许, (False, reason) 拒绝, (None, reason) 需确认。
        """
        policy = INSTALL_POLICY.get(result.trust_level, INSTALL_POLICY["community"])
        action = policy.get(result.verdict, "block")

        if action == "allow":
            return True, f"{result.trust_level}/{result.verdict}: allowed"
        if action == "ask":
            return None, f"{result.trust_level}/{result.verdict}: requires confirmation"
        if force and result.trust_level not in ("community", "trusted"):
            return True, f"Force override: {result.trust_level}/{result.verdict}"
        if force and result.verdict != "dangerous":
            return True, f"Force override: {result.trust_level}/{result.verdict}"
        return False, f"{result.trust_level}/{result.verdict}: blocked"

    def _scan_directory(self, skill_dir: Path) -> list[Finding]:
        """递归扫描目录。"""
        findings: list[Finding] = []
        seen: set[tuple[str, int]] = set()
        file_count = 0

        if skill_dir.is_file():
            return self._scan_file(skill_dir, str(skill_dir.name), seen)

        for path in sorted(skill_dir.rglob("*")):
            if not path.is_file():
                continue
            if any(p.startswith(".") for p in path.parts):
                continue
            file_count += 1
            if file_count > MAX_FILE_COUNT:
                break
            rel = str(path.relative_to(skill_dir))
            file_findings = self._scan_file(path, rel, seen)
            findings.extend(file_findings)

        return findings

    def _scan_file(self, path: Path, rel_path: str, seen: set[tuple[str, int]]) -> list[Finding]:
        """扫描单个文件。"""
        if path.suffix not in SCANNABLE_EXTENSIONS and path.name != "SKILL.md":
            return []

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            return []

        findings: list[Finding] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, pattern_id, severity, category in THREAT_PATTERNS:
                key = (pattern_id, line_num)
                if key in seen:
                    continue
                if re.search(pattern, line, re.IGNORECASE):
                    seen.add(key)
                    match_text = line.strip()[:120]
                    findings.append(Finding(
                        pattern_id=pattern_id,
                        severity=severity,
                        category=category,
                        file=rel_path,
                        line=line_num,
                        match=match_text,
                        description=f"[{severity}] {category}: {pattern_id}",
                    ))

        return findings

    @staticmethod
    def _resolve_trust_level(source: str) -> str:
        if source in ("builtin", "official"):
            return "builtin"
        if source == "agent-created":
            return "agent-created"
        return "community"

    @staticmethod
    def _determine_verdict(findings: list[Finding]) -> str:
        for f in findings:
            if f.severity == "critical":
                return "dangerous"
        for f in findings:
            if f.severity == "high":
                return "caution"
        return "safe"


# ============================================================================
# 来源追踪 (SkillProvenance)
# ============================================================================

BACKGROUND_REVIEW = "background_review"

_write_origin: contextvars.ContextVar[str] = contextvars.ContextVar(
    "skill_write_origin", default="foreground",
)


def set_write_origin(origin: str) -> contextvars.Token[str]:
    """设置当前写入来源上下文。"""
    return _write_origin.set(origin or "foreground")


def reset_write_origin(token: contextvars.Token[str]) -> None:
    """恢复之前的写入来源上下文。"""
    _write_origin.reset(token)


def get_write_origin() -> str:
    """获取当前写入来源。"""
    return _write_origin.get()


def is_background_review() -> bool:
    """当前是否为后台审查写入。"""
    return _write_origin.get() == BACKGROUND_REVIEW


class SkillProvenance:
    """技能来源追踪。

    区分 bundled/hub-installed/agent-created/manual 来源，
    Curator 只管理 agent-created 技能。
    """

    def __init__(self, skills_dir: Path | None = None):
        if skills_dir is None:
            skills_dir = Path.home() / ".nanohermes" / "skills"
        self._skills_dir = Path(skills_dir)
        self._usage_file = self._skills_dir / ".usage.json"

    def mark_agent_created(self, skill_name: str) -> None:
        """标记技能为 agent 创建。"""
        usage = self._load_usage()
        if skill_name not in usage:
            usage[skill_name] = {}
        usage[skill_name]["created_by"] = "agent"
        self._save_usage(usage)

    def is_curator_eligible(self, skill_name: str) -> bool:
        """检查技能是否可被 Curator 管理。"""
        usage = self._load_usage()
        entry = usage.get(skill_name, {})
        return entry.get("created_by") == "agent"

    def get_provenance(self, skill_name: str) -> str:
        """获取技能来源。"""
        usage = self._load_usage()
        entry = usage.get(skill_name, {})
        return entry.get("created_by", "manual")

    def _load_usage(self) -> dict[str, Any]:
        if self._usage_file.exists():
            try:
                import json
                return json.loads(self._usage_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_usage(self, usage: dict[str, Any]) -> None:
        import json
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        self._usage_file.write_text(
            json.dumps(usage, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ============================================================================
# AST 深度审计 (SkillAstAuditor)
# ============================================================================

AstFinding = tuple[str, int, str, str]


class SkillAstAuditor:
    """AST 深度审计，检测动态 import/属性访问。

    可选诊断功能，手动触发，不影响安装流程。
    """

    def audit(self, skill_dir: Path) -> list[AstFinding]:
        """审计技能目录中的所有 Python 文件。

        Args:
            skill_dir: 技能目录路径。

        Returns:
            发现列表: (file, line, pattern_id, description)。
        """
        findings: list[AstFinding] = []

        if skill_dir.is_file() and skill_dir.suffix == ".py":
            findings.extend(self._scan_file(skill_dir, skill_dir.name))
            return findings

        if not skill_dir.is_dir():
            return findings

        for path in sorted(skill_dir.rglob("*.py")):
            if any(p in ("__pycache__", ".venv", "venv", "node_modules") for p in path.parts):
                continue
            rel = str(path.relative_to(skill_dir))
            findings.extend(self._scan_file(path, rel))

        return findings

    def _scan_file(self, path: Path, rel_path: str) -> list[AstFinding]:
        """扫描单个 Python 文件。"""
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        try:
            tree = ast.parse(content, filename=rel_path)
        except (SyntaxError, ValueError):
            return []

        findings: list[AstFinding] = []

        class Visitor(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call) -> None:
                if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                    findings.append((rel_path, node.lineno, "dynamic_import", "importlib.import_module()"))
                elif isinstance(node.func, ast.Name):
                    if node.func.id == "__import__" and node.args:
                        if not isinstance(node.args[0], ast.Constant):
                            findings.append((rel_path, node.lineno, "dynamic_import_computed", "__import__(non-literal)"))
                    elif node.func.id == "getattr" and len(node.args) >= 2:
                        if not isinstance(node.args[1], ast.Constant):
                            findings.append((rel_path, node.lineno, "dynamic_getattr", "getattr(obj, non-literal)"))
                self.generic_visit(node)

            def visit_Subscript(self, node: ast.Subscript) -> None:
                if isinstance(node.value, ast.Attribute) and node.value.attr == "__dict__":
                    if not isinstance(node.slice, ast.Constant):
                        findings.append((rel_path, node.lineno, "dict_access", "obj.__dict__[non-literal]"))
                self.generic_visit(node)

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    if alias.name == "importlib" or alias.name.startswith("importlib."):
                        findings.append((rel_path, node.lineno, "importlib_import", f"import {alias.name}"))
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                if node.module and (node.module == "importlib" or node.module.startswith("importlib.")):
                    findings.append((rel_path, node.lineno, "importlib_import", f"from {node.module} import ..."))
                self.generic_visit(node)

        Visitor().visit(tree)
        return findings


def format_ast_report(findings: list[AstFinding], skill_name: str = "") -> str:
    """格式化 AST 审计报告。"""
    if not findings:
        header = f"AST Audit: {skill_name}" if skill_name else "AST Audit"
        return f"{header}\nNo issues found."

    header = f"AST Audit: {skill_name}" if skill_name else "AST Audit"
    lines = [header, "(diagnostic hints for human review, not security verdicts)", ""]

    by_file: dict[str, list[AstFinding]] = {}
    for f in findings:
        by_file.setdefault(f[0], []).append(f)

    for file, file_findings in sorted(by_file.items()):
        lines.append(f"  {file}:")
        for _, line, pattern_id, desc in file_findings:
            lines.append(f"    [{pattern_id}] line {line} - {desc}")
        lines.append("")

    return "\n".join(lines)
