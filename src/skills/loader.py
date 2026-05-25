"""SkillLoader - SKILL.md 解析器。

SKILL.md 标准格式：
---
name: skill-name
description: 简短描述（≤60 字符）
version: 1.0.0
author: Author Name
license: MIT
---

# Skill Name

技能正文...
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
        body: 技能正文内容。
        path: SKILL.md 文件路径。
    """
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    license: str = ""
    platforms: list[str] | None = None
    body: str = ""
    path: str = ""


class SkillLoader:
    """SKILL.md 解析器。

    解析 YAML frontmatter 和 Markdown 正文。
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

        return Skill(
            name=name,
            description=description,
            version=frontmatter.get("version", "1.0.0"),
            author=frontmatter.get("author", ""),
            license=frontmatter.get("license", ""),
            platforms=frontmatter.get("platforms"),
            body=body,
            path=str(path),
        )

    def _parse_frontmatter(self, text: str) -> tuple[dict[str, Any], str]:
        """解析 YAML frontmatter。

        Args:
            text: SKILL.md 全文。

        Returns:
            (frontmatter_dict, body) 元组。
        """
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
        if not match:
            raise ValueError("SKILL.md 缺少 YAML frontmatter")

        yaml_text = match.group(1)
        body = match.group(2).strip()

        # 简单 YAML 解析（不使用外部库）
        frontmatter = {}
        for line in yaml_text.split("\n"):
            if ":" in line:
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
