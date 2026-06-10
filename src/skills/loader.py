"""SkillLoader - SKILL.md 解析器。

参考 Hermes Agent 实现，支持：
- BOM 字符处理
- YAML 库解析（优先）+ 简单解析回退
- 列表类型的 platforms 字段
- 嵌套元数据（metadata.hermes.config 等）

SKILL.md 标准格式：
---
name: skill-name
description: 简短描述（≤60 字符）
version: 1.0.0
author: Author Name
license: MIT
platforms: [linux, macos]
---

# Skill Name

技能正文...
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 尝试导入 yaml 库（可选依赖）
try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


@dataclass
class Skill:
    """技能元数据。

    Attributes:
        name: 技能名称。
        description: 简短描述（≤60 字符）。
        version: 版本号。
        author: 作者。
        license: 许可证。
        platforms: 支持的平台列表。
        trigger: 触发规则列表，定义何时应该使用此技能。
        skip: 跳过规则列表，定义何时不应使用此技能。
        body: 技能正文内容。
        path: SKILL.md 文件路径。
    """
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    license: str = ""
    platforms: list[str] | None = None
    trigger: list[str] | None = None
    skip: list[str] | None = None
    body: str = ""
    path: str = ""


class SkillLoader:
    """SKILL.md 解析器。

    参考 Hermes Agent 的 parse_frontmatter 实现：
    - 优先使用 yaml.safe_load 解析（支持嵌套结构、列表）
    - 回退到简单 key:value 解析（无 yaml 库时）
    - 处理 BOM 字符
    """

    def load(self, path: str | Path) -> Skill:
        """加载并解析 SKILL.md 文件。

        Args:
            path: 文件路径。

        Returns:
            解析后的 Skill 实例。

        Raises:
            ValueError: 如果缺少 frontmatter 或格式无效。
        """
        text = Path(path).read_text(encoding="utf-8")
        frontmatter, body = self._parse_frontmatter(text)

        name = frontmatter.get("name", "")
        description = frontmatter.get("description", "")

        if not name:
            raise ValueError(f"SKILL.md 缺少 name 字段: {path}")
        if len(description) > 60:
            raise ValueError(
                f"SKILL.md description 超过 60 字符 ({len(description)}): {path}"
            )

        # 处理 platforms 字段（可能是字符串或列表）
        platforms = frontmatter.get("platforms")
        if isinstance(platforms, str):
            platforms = [p.strip() for p in platforms.split(",") if p.strip()]
        elif platforms is not None and not isinstance(platforms, list):
            platforms = [str(platforms)]

        # 处理 trigger/skip 字段（触发/跳过规则）
        trigger = frontmatter.get("trigger")
        if isinstance(trigger, str):
            trigger = [t.strip() for t in trigger.split(";") if t.strip()]
        elif trigger is not None and not isinstance(trigger, list):
            trigger = [str(trigger)]

        skip = frontmatter.get("skip")
        if isinstance(skip, str):
            skip = [s.strip() for s in skip.split(";") if s.strip()]
        elif skip is not None and not isinstance(skip, list):
            skip = [str(skip)]

        return Skill(
            name=name,
            description=description,
            version=frontmatter.get("version", "1.0.0"),
            author=frontmatter.get("author", ""),
            license=frontmatter.get("license", ""),
            platforms=platforms,
            trigger=trigger,
            skip=skip,
            body=body,
            path=str(path),
        )

    def _parse_frontmatter(self, text: str) -> tuple[dict[str, Any], str]:
        """解析 YAML frontmatter。

        参考 Hermes Agent 实现：
        1. 移除 BOM 字符
        2. 查找 --- 分隔符
        3. 优先使用 yaml.safe_load 解析
        4. 回退到简单 key:value 解析

        Args:
            text: SKILL.md 全文。

        Returns:
            (frontmatter_dict, body) 元组。
        """
        # 移除 BOM 字符
        text = text.lstrip("\ufeff")

        # 查找 frontmatter 分隔符
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
        if not match:
            raise ValueError("SKILL.md 缺少 YAML frontmatter")

        yaml_text = match.group(1)
        body = match.group(2).strip()

        # 优先使用 yaml 库解析
        if _HAS_YAML:
            try:
                frontmatter = yaml.safe_load(yaml_text)
                if isinstance(frontmatter, dict):
                    return frontmatter, body
            except Exception:
                pass  # 回退到简单解析

        # 简单 YAML 解析（不使用外部库）
        frontmatter = {}
        for line in yaml_text.split("\n"):
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            frontmatter[key] = value

        return frontmatter, body


def slugify(text: str) -> str:
    """将文本转换为 slug 格式。

    Args:
        text: 原始文本。

    Returns:
        slug 格式字符串。
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text
