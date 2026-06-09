"""SkillManager - 技能编排器。

管理技能加载、启用/禁用、使用追踪、创建、编辑、删除。
将技能描述注入系统提示的 volatile 层，使模型知道可用技能。

技能目录结构：
    ~/.nanohermes/skills/
    ├── my-skill/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── templates/
    │   ├── scripts/
    │   └── assets/
    └── category-name/
        └── another-skill/
            └── SKILL.md
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.skills.loader import Skill, SkillLoader


# ============================================================================
# 常量
# ============================================================================
# 技能名称长度限制：防止文件系统兼容性问题（某些系统对路径长度有限制）
# 64 字符足够表达语义名称，同时避免路径过长导致的问题
MAX_NAME_LENGTH = 64

# 描述长度限制：控制注入系统提示的 token 消耗
# 1024 字符约 400-500 tokens，避免单个技能描述占用过多上下文窗口
MAX_DESCRIPTION_LENGTH = 1024

# 技能内容字符限制：SKILL.md 的最大大小
# 100,000 字符约 36k tokens（按 2.75 chars/token 估算），
# 确保单个技能不会消耗过多上下文预算，为对话留出足够空间
MAX_SKILL_CONTENT_CHARS = 100_000  # ~36k tokens

# 支持文件字节限制：每个辅助文件（references/templates/scripts/assets）的最大大小
# 1 MiB 是合理的上限，防止恶意或意外的大文件占用磁盘和内存
MAX_SKILL_FILE_BYTES = 1_048_576   # 1 MiB per supporting file

# 技能名称允许的字符模式：文件系统安全且 URL 友好
# - 仅允许小写字母、数字、点、下划线、连字符
# - 必须以字母或数字开头（避免隐藏文件问题，如 .hidden）
# - 避免大写字母和特殊字符，确保跨平台兼容性（Windows/macOS/Linux）
# - 连字符/下划线/点用于分隔单词，符合 URL slug 惯例
VALID_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')

# write_file/remove_file 允许的子目录白名单
# 限制技能只能在这些特定子目录下创建文件，实现以下目标：
# 1. 防止路径遍历攻击（如 ../../etc/passwd）
# 2. 保持技能目录结构的一致性
# 3. 明确技能支持的资源类型：
#    - references: 参考文档、API 说明等
#    - templates: 代码模板、提示模板等
#    - scripts: 辅助脚本（Python/Shell 等）
#    - assets: 静态资源（图片、配置等）
ALLOWED_SUBDIRS = {"references", "templates", "scripts", "assets"}


@dataclass
class SkillEntry:
    """技能条目。

    封装技能元数据和运行时状态，是 SkillManager 内部使用的数据结构。

    设计考量：
    - 使用 dataclass 减少样板代码，提供默认的 __init__、__repr__ 等
    - enabled 默认为 True：新创建或新发现的技能默认启用，符合"开箱即用"原则
    - use_count 和 last_used_at 用于追踪技能使用频率，未来可用于：
      * 技能推荐（常用技能优先展示）
      * 技能清理建议（长期未使用的技能）
      * 性能分析（哪些技能被频繁调用）

    Attributes:
        skill: 技能元数据（从 SKILL.md 解析的 name、description 等）。
        enabled: 是否启用。禁用后技能仍保留在磁盘，但不会注入系统提示。
        use_count: 使用次数。每次工具调用时通过 record_use() 递增。
        last_used_at: 最后使用时间戳（Unix 时间戳）。用于计算使用频率。
    """
    skill: Skill
    enabled: bool = True
    use_count: int = 0
    last_used_at: float = 0.0


class SkillManager:
    """技能编排器。

    管理技能加载、启用/禁用、使用追踪、创建、编辑、删除。
    将已启用技能的描述注入系统提示 volatile 层。

    架构设计：
    - 技能数据存储在内存字典 _skills 中，启动时从磁盘加载
    - 启用/禁用状态仅保存在内存中，不持久化到磁盘
      （重启后所有技能恢复为默认启用状态）
    - SKILL.md 是技能的唯一真实来源，修改后立即重新加载
    - 所有文件操作使用原子写入，防止并发或崩溃导致的数据损坏

    Attributes:
        skills_dir: 技能目录路径。
        _skills: 已加载的技能字典（名称 → SkillEntry）。
        _loader: SKILL.md 加载器，负责解析 YAML frontmatter 和提取元数据。
    """

    def __init__(self, skills_dir: str | Path | None = None):
        """初始化技能管理器。

        设计决策：
        - 默认目录为 ~/.nanohermes/skills/，与项目数据存储约定一致
        - 启动时自动创建目录（parents=True 确保父目录也存在）
        - 立即加载所有技能（_load_all），使管理器处于可用状态
        - 使用依赖注入模式：skills_dir 可通过参数传入，便于测试

        Args:
            skills_dir: 技能目录路径，None 时使用 ~/.nanohermes/skills/。
        """
        # 使用 Path.home() 获取用户主目录，确保跨平台兼容性
        if skills_dir is None:
            skills_dir = Path.home() / ".nanohermes" / "skills"
        self.skills_dir = Path(skills_dir)
        # parents=True: 如果 ~/.nanohermes 不存在，一并创建
        # exist_ok=True: 目录已存在时不报错（支持多次初始化）
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, SkillEntry] = {}
        self._loader = SkillLoader()
        # 启动时加载所有技能，使内存状态与磁盘同步
        self._load_all()

    def _load_all(self) -> None:
        """加载技能目录中的所有 SKILL.md 文件。

        加载策略：
        - 仅遍历 skills_dir 的直接子目录（不递归），每个子目录代表一个技能
        - 技能目录必须包含 SKILL.md 文件才被视为有效技能
        - 使用 skill.name（从 frontmatter 解析）作为字典键，而非目录名
          这允许目录名和技能名不一致的情况（虽然不推荐）

        错误处理：
        - 单个技能加载失败不影响其他技能（容错设计）
        - 失败时打印警告，便于调试，但不中断启动流程
        - 常见失败原因：SKILL.md 格式错误、YAML frontmatter 缺失、编码问题
        """
        if not self.skills_dir.exists():
            return

        # iterdir() 只遍历直接子项，不递归
        # 这确保了技能目录结构是一层扁平的（或带分类的两层）
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue  # 跳过文件，只处理目录
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue  # 没有 SKILL.md 的目录不是有效技能

            try:
                skill = self._loader.load(skill_file)
                # 使用 skill.name 作为键，而非目录名
                # 如果多个技能的 name 相同，后面的会覆盖前面的（最后加载的获胜）
                self._skills[skill.name] = SkillEntry(skill=skill)
            except Exception as e:
                # 容错设计：单个技能失败不影响整体加载
                # 使用 print 而非 logging，因为这是启动时的关键路径，
                # 确保即使日志系统未初始化也能看到错误
                print(f"[警告] 加载技能失败 {skill_file}: {e}")

    def _reload(self) -> None:
        """重新加载所有技能。

        调用时机：
        - create_skill(): 创建新技能后，确保内存状态与磁盘同步
        - edit_skill(): 编辑 SKILL.md 后，重新解析更新后的元数据
        - patch_skill(): 修改 SKILL.md 后，验证并重新加载
        - delete_skill(): 删除技能后，清理内存中的过期条目

        注意：
        - reload 会丢失所有运行时状态（use_count、last_used_at、enabled 状态）
        - 这是设计上的权衡：简化实现，确保内存状态始终与磁盘一致
        - 未来可优化为增量加载（仅重新加载变更的技能）
        """
        self._skills.clear()
        self._load_all()

    # ========================================================================
    # 公共 API - 技能查询
    # ========================================================================

    def get_skill(self, name: str) -> Skill | None:
        """获取技能。

        时间复杂度：O(1)，字典查找。

        Args:
            name: 技能名称（必须是完整的技能名，不支持模糊匹配）。

        Returns:
            技能实例，未找到返回 None。
        """
        entry = self._skills.get(name)
        return entry.skill if entry else None

    def list_skills(self, enabled_only: bool = False) -> list[SkillEntry]:
        """列出所有技能。

        设计考量：
        - 返回 SkillEntry 而非 Skill，因为调用者可能需要知道 enabled 状态
        - enabled_only 参数用于构建系统提示时仅获取已启用技能
        - 返回列表的快照，避免调用者修改内部状态

        Args:
            enabled_only: 是否只返回已启用的技能。

        Returns:
            技能条目列表（按加载顺序，非字母序）。
        """
        # list() 创建副本，防止调用者修改内部字典
        entries = list(self._skills.values())
        if enabled_only:
            # 列表推导式过滤，保留 enabled=True 的条目
            entries = [e for e in entries if e.enabled]
        return entries

    def get_enabled_skills(self) -> list[dict[str, Any]]:
        """获取已启用技能的详细信息（含 trigger/skip 规则）。

        设计理由：
        - PromptAssembler 通过此方法获取技能信息，避免访问私有属性 _skills
        - 返回 dict 列表而非 SkillEntry，解耦数据结构
        - 包含 trigger/skip 字段，支持 TRIGGER/SKIP 内联格式

        Returns:
            已启用技能信息列表，每个包含 name, description, trigger, skip。
        """
        entries = [e for e in self._skills.values() if e.enabled]
        return [
            {
                "name": e.skill.name,
                "description": e.skill.description,
                "trigger": e.skill.trigger or [],
                "skip": e.skill.skip or [],
            }
            for e in entries
        ]

    def list_skills_with_query(self, query: str = "") -> list[dict[str, Any]]:
        """列出可用技能，支持关键词过滤。

        与 list_skills() 的区别：
        - 直接从磁盘加载（不依赖内存 _skills），确保获取最新状态
        - 返回简化的字典格式（name/description/path），适合 UI 展示
        - 支持关键词搜索（在名称和描述中模糊匹配）

        性能注意：
        - 每次调用都会重新加载所有技能，频繁调用可能影响性能
        - 适用于低频操作（如用户搜索技能），不适用于高频查询

        Args:
            query: 搜索关键词（不区分大小写）。

        Returns:
            技能列表，每个技能包含 name, description, path。
        """
        if not self.skills_dir.exists():
            return []

        skills = []
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                skill = self._loader.load(skill_file)

                # 关键词过滤：不区分大小写的子串匹配
                # 同时搜索技能名称和描述，提高匹配率
                if query:
                    query_lower = query.lower()
                    # 使用 and 条件：只要名称或描述包含关键词就匹配
                    if query_lower not in skill.name.lower() and query_lower not in skill.description.lower():
                        continue

                skills.append({
                    "name": skill.name,
                    "description": skill.description,
                    # 使用 relative_to 获取相对路径，便于 UI 展示
                    "path": str(skill_dir.relative_to(self.skills_dir)),
                })
            except Exception:
                # 忽略加载失败的技能，继续处理其他技能
                continue

        return skills

    def get_skills_by_category(self) -> dict[str, list[str]]:
        """按类别分类技能。

        类别推断逻辑：
        - 从技能路径中提取分类目录名
        - 路径格式：~/.nanohermes/skills/{category}/{skill_name}/SKILL.md
        - 如果技能直接在 skills/ 下（无分类），归类为 "other"
        - 使用 "/skills/" 作为锚点分割路径，避免绝对路径前缀干扰

        返回结构：
        {
            "category1": ["skill-a", "skill-b"],
            "category2": ["skill-c"],
            "other": ["skill-d"]
        }

        Returns:
            类别字典，键为类别名，值为该类别下的技能名称列表。
        """
        skill_categories: dict[str, list[str]] = {}
        for entry in self.list_skills():
            path = entry.skill.path
            # 从路径中提取分类：查找 "/skills/" 后的第一个目录
            if "/skills/" in path:
                # split("/skills/")[1] 获取 "skills/" 之后的部分
                # split("/") 按目录分隔符分割
                parts = path.split("/skills/")[1].split("/")
                # parts[0] 是分类目录名，parts[1] 是技能目录名
                if len(parts) >= 2:
                    category = parts[0]
                else:
                    category = "other"  # 技能直接在 skills/ 下，无分类
            else:
                category = "other"  # 路径不包含 "/skills/"，异常情况

            if category not in skill_categories:
                skill_categories[category] = []
            skill_categories[category].append(entry.skill.name)

        return skill_categories

    def get_skill_details(self, name: str) -> dict[str, Any] | None:
        """获取技能详情，包括元数据和支持文件列表。

        与 get_skill() 的区别：
        - 返回更丰富的信息（version、author、license、支持文件列表）
        - 直接从磁盘读取，确保获取最新状态
        - 遍历支持文件目录，列出所有辅助资源

        Args:
            name: 技能名称。

        Returns:
            技能详情字典，未找到返回 None。
        """
        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return None

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None

        try:
            skill = self._loader.load(skill_md)

            # 列出支持文件：遍历允许的子目录，收集所有文件
            files = []
            for subdir in ALLOWED_SUBDIRS:
                d = skill_dir / subdir
                if d.exists():
                    # rglob("*") 递归遍历所有子目录和文件
                    for f in d.rglob("*"):
                        if f.is_file():
                            # 存储相对于技能目录的路径，便于后续访问
                            files.append(str(f.relative_to(skill_dir)))

            return {
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
                "author": skill.author,
                "license": skill.license,
                "path": str(skill_dir.relative_to(self.skills_dir)),
                "files": files,
            }
        except Exception:
            # 加载失败返回 None，调用者应处理这种情况
            return None

    def enable_skill(self, name: str) -> bool:
        """启用技能。

        启用/禁用的影响：
        - 启用：技能会出现在 build_skill_prompt() 的结果中，注入系统提示
        - 禁用：技能仍然保留在磁盘和内存中，但不会出现在系统提示中
        - 模型"不知道"被禁用的技能存在，无法主动使用它们
        - 启用/禁用状态仅保存在内存中，重启后恢复为默认启用

        设计决策：
        - 不删除技能文件：禁用是可逆操作，保留用户数据
        - 不持久化状态：简化实现，避免状态不一致问题
          （如果未来需要持久化，可添加 enabled_skills.json 配置文件）

        Args:
            name: 技能名称。

        Returns:
            True 表示成功，False 表示技能不存在。
        """
        entry = self._skills.get(name)
        if not entry:
            return False
        entry.enabled = True
        return True

    def disable_skill(self, name: str) -> bool:
        """禁用技能。

        使用场景：
        - 用户暂时不需要某个技能，但不想删除
        - 调试时隔离特定技能
        - 减少系统提示长度，节省 token 预算

        Args:
            name: 技能名称。

        Returns:
            True 表示成功，False 表示技能不存在。
        """
        entry = self._skills.get(name)
        if not entry:
            return False
        entry.enabled = False
        return True

    def record_use(self, name: str) -> None:
        """记录技能使用。

        调用时机：
        - 工具分发器调用技能相关工具时，调用此方法记录使用
        - 用于统计技能使用频率，未来可用于智能推荐

        注意：
        - 使用 time.time() 获取 Unix 时间戳（秒级精度）
        - use_count 仅在内存中维护，重启后归零
        - 如果技能不在内存中（未加载），静默忽略（不报错）

        Args:
            name: 技能名称。
        """
        entry = self._skills.get(name)
        if entry:
            entry.use_count += 1
            entry.last_used_at = time.time()

    def build_skill_prompt(self) -> str:
        """构建技能提示文本，注入到系统提示 volatile 层。

        提示格式（Claude Code 风格，含 TRIGGER/SKIP 规则）：
        ```
        ## Available Skills

        - **skill-name**: Skill description TRIGGER — when X; when Y SKIP — when Z
        - **another-skill**: Another description

        To use a skill, mention its name in your response.
        ```

        设计考量：
        - 仅包含已启用技能（enabled_only=True）
        - 使用 Markdown 列表格式，便于模型解析
        - TRIGGER/SKIP 规则内联到技能描述，提高模型理解效率
        - 无规则的技能仅显示名称和描述，保持简洁
        - 末尾添加使用说明，引导模型正确使用技能

        注入位置：
        - 系统提示的 volatile 层（动态变化部分）
        - 每次对话开始时重新构建，反映最新的启用状态

        Returns:
            技能提示文本，无启用技能时返回空字符串。
        """
        enabled = self.list_skills(enabled_only=True)
        if not enabled:
            return ""

        lines = ["## Available Skills", ""]
        for entry in enabled:
            skill = entry.skill
            line = f"- **{skill.name}**: {skill.description}"

            if skill.trigger:
                trigger_text = "; ".join(skill.trigger)
                line += f" TRIGGER — {trigger_text}"

            if skill.skip:
                skip_text = "; ".join(skill.skip)
                line += f" SKIP — {skip_text}"

            lines.append(line)
        lines.append("")
        lines.append("To use a skill, mention its name in your response.")

        return "\n".join(lines)

    # ========================================================================
    # 公共 API - 技能管理
    # ========================================================================

    def create_skill(self, name: str, content: str, category: str | None = None) -> dict[str, Any]:
        """创建新技能。

        创建流程：
        1. 验证名称格式（文件系统安全、URL 友好）
        2. 验证分类格式（防止路径遍历）
        3. 验证 SKILL.md 内容（必须有正确的 YAML frontmatter）
        4. 验证内容大小（防止超出 token 预算）
        5. 检查名称冲突（避免覆盖现有技能）
        6. 创建目录并原子写入文件
        7. 重新加载技能列表，使内存状态与磁盘同步

        安全考量：
        - 所有验证失败时立即返回错误，不执行任何文件系统操作
        - 使用原子写入（_atomic_write_text），防止写入中断导致文件损坏
        - 目录创建使用 exist_ok=True，但名称冲突检查在前，实际不会触发

        Args:
            name: 技能名称（必须符合 VALID_NAME_RE 模式）。
            content: SKILL.md 内容（必须以 YAML frontmatter 开头）。
            category: 可选分类目录名（会成为 skills/ 下的子目录）。

        Returns:
            操作结果字典，包含 success、message/error、path 等字段。
        """
        # 步骤 1：验证名称格式
        # 防止非法字符导致文件系统问题或 URL 编码问题
        err = self._validate_name(name)
        if err:
            return {"success": False, "error": err}

        # 步骤 2：验证分类格式
        # 防止分类名包含路径分隔符，导致目录结构混乱
        err = self._validate_category(category)
        if err:
            return {"success": False, "error": err}

        # 步骤 3：验证 SKILL.md 内容格式
        # 确保有正确的 YAML frontmatter（name、description 字段）
        # 这是技能可被正确加载的前提条件
        err = self._validate_frontmatter(content)
        if err:
            return {"success": False, "error": err}

        # 步骤 4：验证内容大小
        # 防止单个技能占用过多上下文窗口（token 预算）
        err = self._validate_content_size(content)
        if err:
            return {"success": False, "error": err}

        # 步骤 5：检查名称冲突
        # 遍历磁盘查找同名技能，避免覆盖现有技能
        # 注意：_find_skill_dir 按技能名（非目录名）查找
        if self._find_skill_dir(name):
            return {
                "success": False,
                "error": f"A skill named '{name}' already exists."
            }

        # 步骤 6：创建技能目录
        # parents=True 确保分类目录也会一并创建
        skill_dir = self._resolve_skill_dir(name, category)
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 原子写入 SKILL.md
        # 使用临时文件 + rename 确保写入的原子性：
        # - 如果写入中断，临时文件会被清理，原文件不受影响
        # - 如果写入成功，rename 是原子操作（同一文件系统内）
        skill_md = skill_dir / "SKILL.md"
        self._atomic_write_text(skill_md, content)

        # 步骤 7：重新加载技能列表
        # 确保新创建的技能被加载到内存中
        self._reload()

        result = {
            "success": True,
            "message": f"Skill '{name}' created.",
            # 返回相对路径，便于用户定位技能文件
            "path": str(skill_dir.relative_to(self.skills_dir)),
            "skill_md": str(skill_md),
        }
        if category:
            result["category"] = category
        # 提示信息：引导用户如何添加支持文件
        result["hint"] = (
            f"To add reference files, templates, or scripts, use "
            f"skill_manage(action='write_file', name='{name}', file_path='references/example.md', file_content='...')"
        )
        return result

    def edit_skill(self, name: str, content: str) -> dict[str, Any]:
        """替换技能的 SKILL.md 内容。

        与 patch_skill() 的区别：
        - edit_skill: 完全替换整个 SKILL.md 文件
        - patch_skill: 在文件中进行局部查找替换

        使用场景：
        - 用户提供了完整的 SKILL.md 新内容
        - 从模板创建技能后需要自定义内容

        安全考量：
        - 验证 frontmatter 确保新内容格式正确
        - 验证内容大小防止超出 token 预算
        - 使用原子写入防止文件损坏

        Args:
            name: 技能名称。
            content: 新的 SKILL.md 内容（必须包含完整的 YAML frontmatter）。

        Returns:
            操作结果字典。
        """
        # 验证新内容的 frontmatter 格式
        # 确保替换后技能仍可被正确加载
        err = self._validate_frontmatter(content)
        if err:
            return {"success": False, "error": err}

        # 验证新内容大小
        err = self._validate_content_size(content)
        if err:
            return {"success": False, "error": err}

        # 查找技能目录
        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found."}

        skill_md = skill_dir / "SKILL.md"
        # 原子写入：确保写入过程不会因中断导致文件损坏
        self._atomic_write_text(skill_md, content)

        # 重新加载技能：使内存中的技能元数据与磁盘同步
        # 注意：这会丢失运行时状态（use_count、enabled 等）
        self._reload()

        return {
            "success": True,
            "message": f"Skill '{name}' updated.",
            "path": str(skill_dir),
        }

    def patch_skill(
        self,
        name: str,
        old_string: str,
        new_string: str,
        file_path: str | None = None,
        replace_all: bool = False,
    ) -> dict[str, Any]:
        """在技能文件中进行查找替换。

        设计考量：
        - 支持修改 SKILL.md 或支持文件（references/templates/scripts/assets）
        - 修改 SKILL.md 时需要额外验证 frontmatter 完整性
        - 提供 replace_all 选项处理多次匹配的情况
        - 匹配失败时提供文件预览，帮助用户定位问题

        安全考量：
        - 文件路径必须通过 _validate_file_path 验证（防止路径遍历）
        - 目标文件必须在技能目录内（_resolve_skill_target 二次验证）
        - 修改后验证内容大小和 frontmatter 格式

        Args:
            name: 技能名称。
            old_string: 要查找的字符串（必须精确匹配）。
            new_string: 替换后的字符串（空字符串表示删除）。
            file_path: 支持文件路径（None 表示 SKILL.md）。
            replace_all: 是否替换所有匹配项（默认只替换第一个）。

        Returns:
            操作结果字典。
        """
        # 验证必需参数
        # old_string 为空无法执行替换
        if not old_string:
            return {"success": False, "error": "old_string is required for 'patch'."}
        # new_string 为 None 表示参数缺失，空字符串是合法的（用于删除）
        if new_string is None:
            return {"success": False, "error": "new_string is required for 'patch'. Use empty string to delete."}

        # 查找技能目录
        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found."}

        # 确定目标文件
        if file_path:
            # 修改支持文件：验证路径合法性
            err = self._validate_file_path(file_path)
            if err:
                return {"success": False, "error": err}
            # 解析并验证目标文件在技能目录内
            target, err = self._resolve_skill_target(skill_dir, file_path)
            if err:
                return {"success": False, "error": err}
        else:
            # 修改 SKILL.md
            target = skill_dir / "SKILL.md"

        # 检查目标文件是否存在
        if not target.exists():
            return {"success": False, "error": f"File not found: {target.relative_to(skill_dir)}"}

        # 读取文件内容
        content = target.read_text(encoding="utf-8")

        # 查找匹配次数
        count = content.count(old_string)
        if count == 0:
            # 未找到匹配：提供文件预览，帮助用户定位问题
            # 限制预览长度为 500 字符，避免响应过大
            preview = content[:500] + ("..." if len(content) > 500 else "")
            return {
                "success": False,
                "error": f"old_string not found in {'SKILL.md' if not file_path else file_path}.",
                "file_preview": preview,
            }
        # 多次匹配但未指定 replace_all：防止意外替换
        if count > 1 and not replace_all:
            return {
                "success": False,
                "error": f"old_string found {count} times. Use replace_all=True to replace all, or be more specific.",
            }

        # 执行替换
        # count=1: 只替换第一次匹配
        # count=-1: 替换所有匹配（replace_all=True 时）
        new_content = content.replace(old_string, new_string, 1 if not replace_all else -1)

        # 检查替换后的内容大小
        target_label = "SKILL.md" if not file_path else file_path
        err = self._validate_content_size(new_content, label=target_label)
        if err:
            return {"success": False, "error": err}

        # 如果修改 SKILL.md，验证 frontmatter 完整性
        # 这是关键的安全检查：防止 patch 操作破坏技能元数据
        if not file_path:
            err = self._validate_frontmatter(new_content)
            if err:
                return {"success": False, "error": f"Patch would break SKILL.md structure: {err}"}

        # 原子写入新内容
        self._atomic_write_text(target, new_content)

        # 如果修改了 SKILL.md，重新加载技能
        # 支持文件修改不需要重新加载（不影响技能元数据）
        if not file_path:
            self._reload()

        return {
            "success": True,
            "message": f"Patched {'SKILL.md' if not file_path else file_path} in skill '{name}' ({count} replacement{'s' if count > 1 else ''}).",
        }

    def delete_skill(self, name: str) -> dict[str, Any]:
        """删除技能。

        删除流程：
        1. 查找技能目录
        2. 递归删除整个技能目录（包括 SKILL.md 和所有支持文件）
        3. 清理空的分类目录（如果删除后分类目录为空）
        4. 重新加载技能列表

        安全考量：
        - 使用 shutil.rmtree 递归删除，确保所有文件被清除
        - 清理空目录保持目录结构整洁
        - 删除后重新加载，确保内存状态与磁盘同步

        注意：
        - 删除是不可逆操作，文件无法恢复（除非有备份）
        - 与 disable_skill 不同：disable 保留文件，delete 永久删除

        Args:
            name: 技能名称。

        Returns:
            操作结果字典。
        """
        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found."}

        # 递归删除技能目录
        # rmtree 会删除目录及其所有子目录和文件
        shutil.rmtree(skill_dir)

        # 清理空分类目录
        # 如果技能在分类目录下，删除后检查分类目录是否为空
        # 空分类目录没有意义，一并删除保持整洁
        parent = skill_dir.parent
        if parent != self.skills_dir and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

        # 重新加载技能列表
        # 确保被删除的技能从内存中移除
        self._reload()

        return {
            "success": True,
            "message": f"Skill '{name}' deleted.",
        }

    def write_file(self, name: str, file_path: str, file_content: str) -> dict[str, Any]:
        """添加或覆盖技能中的支持文件。

        支持文件类型：
        - references/: 参考文档、API 说明、最佳实践等
        - templates/: 代码模板、提示模板、配置模板等
        - scripts/: 辅助脚本（Python/Shell/Bash 等）
        - assets/: 静态资源（图片、JSON 配置等）

        安全考量：
        - 文件路径必须通过 _validate_file_path 验证
          * 防止路径遍历（.. 被禁止）
          * 必须在允许的子目录下
        - 目标文件必须在技能目录内（_resolve_skill_target 二次验证）
        - 文件大小限制（1 MiB），防止大文件占用磁盘和内存

        Args:
            name: 技能名称。
            file_path: 支持文件路径（如 references/example.md）。
            file_content: 文件内容。

        Returns:
            操作结果字典。
        """
        # 验证文件路径合法性
        err = self._validate_file_path(file_path)
        if err:
            return {"success": False, "error": err}

        # 验证文件内容不为空
        if file_content is None:
            return {"success": False, "error": "file_content is required."}

        # 检查文件大小限制（按字节计算）
        # 使用 encode("utf-8") 获取实际字节数，而非字符数
        content_bytes = len(file_content.encode("utf-8"))
        if content_bytes > MAX_SKILL_FILE_BYTES:
            return {
                "success": False,
                "error": f"File content is {content_bytes:,} bytes (limit: {MAX_SKILL_FILE_BYTES:,} bytes / 1 MiB)."
            }

        # 查找技能目录
        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found. Create it first with action='create'."}

        # 解析并验证目标文件路径
        target, err = self._resolve_skill_target(skill_dir, file_path)
        if err:
            return {"success": False, "error": err}

        # 创建父目录（如果不存在）
        # parents=True 确保多级目录也会一并创建
        target.parent.mkdir(parents=True, exist_ok=True)
        # 原子写入文件内容
        self._atomic_write_text(target, file_content)

        return {
            "success": True,
            "message": f"File '{file_path}' written to skill '{name}'.",
            "path": str(target),
        }

    def remove_file(self, name: str, file_path: str) -> dict[str, Any]:
        """删除技能中的支持文件。

        删除流程：
        1. 验证文件路径合法性
        2. 查找技能目录
        3. 解析并验证目标文件路径
        4. 检查文件是否存在（不存在时列出可用文件）
        5. 删除文件
        6. 清理空子目录

        安全考量：
        - 文件路径验证防止删除技能目录外的文件
        - 只能删除支持文件，不能删除 SKILL.md（保护技能元数据）
        - 清理空目录保持目录结构整洁

        Args:
            name: 技能名称。
            file_path: 支持文件路径（必须在 ALLOWED_SUBDIRS 下）。

        Returns:
            操作结果字典。
        """
        # 验证文件路径合法性
        err = self._validate_file_path(file_path)
        if err:
            return {"success": False, "error": err}

        # 查找技能目录
        skill_dir = self._find_skill_dir(name)
        if not skill_dir:
            return {"success": False, "error": f"Skill '{name}' not found."}

        # 解析并验证目标文件路径
        target, err = self._resolve_skill_target(skill_dir, file_path)
        if err:
            return {"success": False, "error": err}

        # 检查文件是否存在
        if not target.exists():
            # 文件不存在时，列出技能目录下的所有可用文件
            # 帮助用户确认正确的文件路径
            available = []
            for subdir in ALLOWED_SUBDIRS:
                d = skill_dir / subdir
                if d.exists():
                    for f in d.rglob("*"):
                        if f.is_file():
                            available.append(str(f.relative_to(skill_dir)))
            return {
                "success": False,
                "error": f"File '{file_path}' not found in skill '{name}'.",
                "available_files": available if available else None,
            }

        # 删除文件
        target.unlink()

        # 清理空子目录
        # 如果删除文件后父目录为空，删除该目录
        # 保持目录结构整洁，避免空目录累积
        parent = target.parent
        if parent != skill_dir and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

        return {
            "success": True,
            "message": f"File '{file_path}' removed from skill '{name}'.",
        }

    # ========================================================================
    # 内部辅助函数
    # ========================================================================

    def _validate_name(self, name: str) -> str | None:
        """验证技能名称。返回错误消息或 None。

        验证规则：
        1. 名称不能为空
        2. 长度不超过 MAX_NAME_LENGTH（64 字符）
        3. 必须符合 VALID_NAME_RE 模式：
           - 仅允许小写字母、数字、点、下划线、连字符
           - 必须以字母或数字开头

        设计考量：
        - 限制字符集确保文件系统兼容性（Windows/macOS/Linux）
        - 避免特殊字符导致的路径解析问题
        - 禁止大写字母避免跨平台大小写敏感性问题
        - 以字母/数字开头避免隐藏文件问题（.hidden）

        Args:
            name: 待验证的技能名称。

        Returns:
            错误消息字符串，验证通过返回 None。
        """
        if not name:
            return "Skill name is required."
        if len(name) > MAX_NAME_LENGTH:
            return f"Skill name exceeds {MAX_NAME_LENGTH} characters."
        if not VALID_NAME_RE.match(name):
            return (
                f"Invalid skill name '{name}'. Use lowercase letters, numbers, "
                f"hyphens, dots, and underscores. Must start with a letter or digit."
            )
        return None

    def _validate_category(self, category: str | None) -> str | None:
        """验证可选的分类名称。

        验证规则：
        1. None 或空字符串表示无分类，直接通过
        2. 必须是字符串类型
        3. 不能包含路径分隔符（/ 或 \\）
        4. 长度不超过 MAX_NAME_LENGTH
        5. 必须符合 VALID_NAME_RE 模式

        安全考量：
        - 禁止路径分隔符防止目录遍历攻击
        - 分类名最终会成为文件系统目录名，必须安全
        - 与技能名称使用相同的字符限制，保持一致性

        Args:
            category: 待验证的分类名称。

        Returns:
            错误消息字符串，验证通过返回 None。
        """
        if category is None:
            return None
        if not isinstance(category, str):
            return "Category must be a string."

        category = category.strip()
        if not category:
            return None
        # 禁止路径分隔符：防止创建嵌套目录结构或目录遍历
        if "/" in category or "\\" in category:
            return (
                f"Invalid category '{category}'. Categories must be a single directory name."
            )
        if len(category) > MAX_NAME_LENGTH:
            return f"Category exceeds {MAX_NAME_LENGTH} characters."
        if not VALID_NAME_RE.match(category):
            return (
                f"Invalid category '{category}'. Use lowercase letters, numbers, "
                "hyphens, dots, and underscores."
            )
        return None

    def _validate_frontmatter(self, content: str) -> str | None:
        """验证 SKILL.md 内容是否有正确的前置元数据。

        SKILL.md 格式要求：
        ```
        ---
        name: skill-name
        description: A brief description
        version: 1.0.0
        author: author-name
        ---
        Skill body content goes here...
        ```

        验证步骤：
        1. 内容不能为空
        2. 必须以 "---" 开头（YAML frontmatter 标记）
        3. 必须有闭合的 "---"（frontmatter 结束标记）
        4. 解析 YAML 内容，提取键值对
        5. 必须包含 'name' 和 'description' 字段
        6. description 长度不超过 MAX_DESCRIPTION_LENGTH
        7. frontmatter 后必须有正文内容

        设计考量：
        - 使用简单的键值对解析（非完整 YAML 解析器），减少依赖
        - 仅支持单行键值对（不支持嵌套结构或列表）
        - 去除引号包裹的值（支持 "value" 和 'value' 格式）
        - 验证 body 内容确保技能有实际说明，非空壳

        Args:
            content: SKILL.md 的完整内容。

        Returns:
            错误消息字符串，验证通过返回 None。
        """
        if not content.strip():
            return "Content cannot be empty."

        # 检查是否以 YAML frontmatter 标记开头
        if not content.startswith("---"):
            return "SKILL.md must start with YAML frontmatter (---)."

        # 查找闭合的 frontmatter 标记
        # 从第 4 个字符开始搜索（跳过开头的 "---"）
        # 模式：\n---\s*\n 确保 "---" 是独立的一行
        end_match = re.search(r'\n---\s*\n', content[3:])
        if not end_match:
            return "SKILL.md frontmatter is not closed. Ensure you have a closing '---' line."

        # 提取 YAML 内容（两个 "---" 之间的部分）
        # content[3:] 跳过开头的 "---"
        # end_match.start() + 3 计算闭合 "---" 的绝对位置
        yaml_content = content[3:end_match.start() + 3]

        # 简单的 YAML 键值对解析
        # 不使用完整 YAML 解析器的原因：
        # 1. 减少外部依赖
        # 2. 技能 frontmatter 格式简单，只需键值对
        # 3. 避免 YAML 解析错误或安全漏洞（如 YAML 反序列化攻击）
        frontmatter = {}
        for line in yaml_content.split("\n"):
            if ":" in line:
                # partition(":") 按第一个冒号分割
                # 支持值中包含冒号的情况（如 URL）
                key, _, value = line.partition(":")
                key = key.strip()
                # 去除值两端的引号（支持双引号和单引号）
                value = value.strip().strip('"').strip("'")
                frontmatter[key] = value

        # 验证必需字段
        if "name" not in frontmatter:
            return "Frontmatter must include 'name' field."
        if "description" not in frontmatter:
            return "Frontmatter must include 'description' field."
        # 验证 description 长度
        if len(str(frontmatter.get("description", ""))) > MAX_DESCRIPTION_LENGTH:
            return f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters."

        # 验证 frontmatter 后有正文内容
        # end_match.end() 是闭合 "---" 后的位置
        # +3 跳过 "---" 后的换行符
        body = content[end_match.end() + 3:].strip()
        if not body:
            return "SKILL.md must have content after the frontmatter."

        return None

    def _validate_content_size(self, content: str, label: str = "SKILL.md") -> str | None:
        """检查内容是否超出字符限制。

        限制原因：
        - 技能内容会注入系统提示，占用上下文窗口
        - 过大的技能会减少可用对话空间
        - MAX_SKILL_CONTENT_CHARS = 100,000 约 36k tokens

        Args:
            content: 待检查的内容。
            label: 内容标签（用于错误消息，如 "SKILL.md"）。

        Returns:
            错误消息字符串，验证通过返回 None。
        """
        if len(content) > MAX_SKILL_CONTENT_CHARS:
            return (
                f"{label} content is {len(content):,} characters "
                f"(limit: {MAX_SKILL_CONTENT_CHARS:,})."
            )
        return None

    def _validate_file_path(self, file_path: str) -> str | None:
        """验证 write_file/remove_file 的文件路径。

        安全考量（路径遍历防护）：
        - 禁止 ".." 防止向上遍历访问技能目录外的文件
        - 必须在 ALLOWED_SUBDIRS 白名单下（references/templates/scripts/assets）
        - 必须有文件名，不能只是目录路径

        这是关键的输入验证层，防止恶意输入：
        - "../../etc/passwd" → 被 ".." 检查拦截
        - "SKILL.md" → 被白名单检查拦截（不在 ALLOWED_SUBDIRS 下）
        - "references/" → 被文件名检查拦截（只有目录路径）

        Args:
            file_path: 待验证的文件路径（相对路径，如 "references/example.md"）。

        Returns:
            错误消息字符串，验证通过返回 None。
        """
        if not file_path:
            return "file_path is required."

        normalized = Path(file_path)

        # 路径遍历防护：禁止 ".." 组件
        # normalized.parts 将路径分解为组件，如 ("..", "..", "etc", "passwd")
        # 检查任何组件是否为 ".."，防止向上遍历
        if ".." in normalized.parts:
            return "Path traversal ('..') is not allowed."

        # 白名单检查：文件必须在允许的子目录下
        # normalized.parts[0] 是路径的第一个组件（子目录名）
        # 这确保只能操作 references/、templates/、scripts/、assets/ 下的文件
        if not normalized.parts or normalized.parts[0] not in ALLOWED_SUBDIRS:
            allowed = ", ".join(sorted(ALLOWED_SUBDIRS))
            return f"File must be under one of: {allowed}. Got: '{file_path}'"

        # 必须有文件名：防止只指定目录路径
        # len(normalized.parts) < 2 表示只有子目录名，没有文件名
        # 例如 "references" 只有一个组件，"references/example.md" 有两个
        if len(normalized.parts) < 2:
            return f"Provide a file path, not just a directory."

        return None

    def _resolve_skill_dir(self, name: str, category: str | None = None) -> Path:
        """构建新技能的目录路径。

        路径结构：
        - 无分类：~/.nanohermes/skills/{name}/
        - 有分类：~/.nanohermes/skills/{category}/{name}/

        Args:
            name: 技能名称。
            category: 可选分类目录名。

        Returns:
            技能目录的完整路径。
        """
        if category:
            return self.skills_dir / category / name
        return self.skills_dir / name

    def _find_skill_dir(self, name: str) -> Path | None:
        """按名称查找技能目录。

        查找策略：
        - 使用 rglob("SKILL.md") 递归遍历所有子目录
        - 检查 SKILL.md 的父目录名是否匹配技能名
        - 这允许技能在分类目录下（skills/category/name/SKILL.md）

        注意：
        - 按技能名（非目录名）查找，技能名来自 SKILL.md 的 frontmatter
        - 如果多个技能同名，返回第一个找到的（遍历顺序不确定）

        Args:
            name: 技能名称。

        Returns:
            技能目录路径，未找到返回 None。
        """
        if not self.skills_dir.exists():
            return None

        # rglob 递归查找所有 SKILL.md 文件
        for skill_md in self.skills_dir.rglob("SKILL.md"):
            # 检查父目录名是否匹配技能名
            if skill_md.parent.name == name:
                return skill_md.parent
        return None

    def _resolve_skill_target(self, skill_dir: Path, file_path: str) -> tuple[Path | None, str | None]:
        """解析支持文件路径并确保在技能目录内。

        这是第二层路径安全验证（第一层是 _validate_file_path）：
        - 即使路径通过了白名单检查，仍需验证解析后的绝对路径
          仍在技能目录内
        - 使用 resolve() 解析符号链接和相对路径
        - 使用 relative_to() 验证目标路径是否在 skill_dir 下

        防御场景：
        - 符号链接攻击：如果 skill_dir 包含指向外部的符号链接，
          resolve() 会解析真实路径，relative_to() 会失败
        - 复杂路径操作：如 "references/../../etc/passwd" 虽然被
          _validate_file_path 拦截，但这里提供二次保护

        Args:
            skill_dir: 技能目录路径。
            file_path: 支持文件相对路径。

        Returns:
            (目标文件路径, None) 表示成功，(None, 错误消息) 表示失败。
        """
        # 拼接目标路径
        target = skill_dir / file_path
        try:
            # resolve() 解析绝对路径和符号链接
            # relative_to() 验证 target 是否在 skill_dir 下
            # 如果不在，会抛出 ValueError
            target.resolve().relative_to(skill_dir.resolve())
        except ValueError:
            return None, "File path escapes skill directory."
        return target, None

    def _atomic_write_text(self, file_path: Path, content: str, encoding: str = "utf-8") -> None:
        """原子写入文本内容到文件。

        原子写入的安全考量：
        - 使用临时文件 + os.replace() 确保写入的原子性
        - os.replace() 在同一文件系统内是原子操作
        - 如果写入过程中断（崩溃、断电等），临时文件会被清理，
          原文件保持完整（不会损坏）

        写入流程：
        1. 创建临时文件（在目标文件的同一目录下）
        2. 写入内容到临时文件
        3. 使用 os.replace() 原子替换目标文件
        4. 如果任何步骤失败，清理临时文件

        为什么在同一目录创建临时文件？
        - os.replace() 要求源和目标在同一文件系统
        - 使用 tempfile.mkstemp(dir=...) 确保在同一目录

        为什么使用 os.replace() 而非 shutil.move()？
        - os.replace() 是底层系统调用，保证原子性
        - shutil.move() 可能退化为复制+删除，非原子操作

        Args:
            file_path: 目标文件路径。
            content: 要写入的内容。
            encoding: 文件编码（默认 UTF-8）。
        """
        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建临时文件
        # mkstemp 返回 (fd, path)，fd 是文件描述符，path 是临时文件路径
        # prefix 和 suffix 确保临时文件名易于识别
        fd, temp_path = tempfile.mkstemp(
            dir=str(file_path.parent),
            prefix=f".{file_path.name}.tmp.",
            suffix="",
        )
        try:
            # 写入内容到临时文件
            with os.fdopen(fd, "w", encoding=encoding) as f:
                f.write(content)
            # 原子替换目标文件
            # os.replace() 在同一文件系统内是原子操作
            os.replace(temp_path, file_path)
        except Exception:
            # 写入失败时清理临时文件
            # 使用 try/except 确保即使 unlink 失败也不影响原异常
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # 临时文件可能已被清理，忽略
            raise  # 重新抛出原异常
