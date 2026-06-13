"""技能系统模块。

SKILL.md 标准格式、技能加载、技能管理、Curator 自进化。
Phase 2: 渐进式披露、安全扫描、来源追踪、预处理。
"""

from src.skills.loader import SkillLoader, Skill
from src.skills.manager import SkillManager
from src.skills.curator import Curator
from src.skills.progressive_disclosure import (
    SkillProgressiveDisclosure,
    skill_matches_platform,
    skill_should_show,
    extract_skill_conditions,
)
from src.skills.security import (
    SkillGuard,
    SkillProvenance,
    SkillAstAuditor,
    is_background_review,
    set_write_origin,
    reset_write_origin,
)
from src.skills.preprocessing import (
    preprocess_skill_content,
    substitute_template_vars,
    expand_inline_shell,
)

__all__ = [
    "SkillLoader", "Skill", "SkillManager", "Curator",
    "SkillProgressiveDisclosure", "skill_matches_platform", "skill_should_show",
    "SkillGuard", "SkillProvenance", "SkillAstAuditor",
    "preprocess_skill_content", "substitute_template_vars", "expand_inline_shell",
]
