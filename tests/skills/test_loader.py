"""Tests for skills loader module."""

import pytest
import tempfile
from pathlib import Path

from src.skills.loader import SkillLoader, Skill, slugify


class TestSkill:
    """Tests for Skill dataclass."""

    def test_default_values(self):
        """Test default values."""
        skill = Skill(name="test", description="Test skill")
        assert skill.name == "test"
        assert skill.description == "Test skill"
        assert skill.version == "1.0.0"
        assert skill.author == ""
        assert skill.license == ""
        assert skill.platforms is None
        assert skill.body == ""
        assert skill.path == ""

    def test_custom_values(self):
        """Test custom values."""
        skill = Skill(
            name="test",
            description="Test skill",
            version="2.0.0",
            author="Author",
            license="MIT",
            platforms=["linux", "macos"],
            body="Body content",
            path="/path/to/skill",
        )
        assert skill.version == "2.0.0"
        assert skill.author == "Author"
        assert skill.license == "MIT"
        assert skill.platforms == ["linux", "macos"]
        assert skill.body == "Body content"
        assert skill.path == "/path/to/skill"


class TestSkillLoader:
    """Tests for SkillLoader class."""

    def test_load_valid_skill(self):
        """Test loading a valid SKILL.md file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: test-skill\n"
                "description: A test skill\n"
                "version: 1.0.0\n"
                "author: Test Author\n"
                "license: MIT\n"
                "---\n"
                "# Test Skill\n"
                "This is the skill body.",
                encoding="utf-8",
            )

            loader = SkillLoader()
            skill = loader.load(skill_file)

            assert skill.name == "test-skill"
            assert skill.description == "A test skill"
            assert skill.version == "1.0.0"
            assert skill.author == "Test Author"
            assert skill.license == "MIT"
            assert "This is the skill body" in skill.body
            assert skill.path == str(skill_file)

    def test_load_missing_frontmatter(self):
        """Test loading file without frontmatter raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text("# No frontmatter", encoding="utf-8")

            loader = SkillLoader()
            with pytest.raises(ValueError, match="缺少 YAML frontmatter"):
                loader.load(skill_file)

    def test_load_missing_name(self):
        """Test loading skill without name raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "description: No name\n"
                "---\n"
                "Body",
                encoding="utf-8",
            )

            loader = SkillLoader()
            with pytest.raises(ValueError, match="缺少 name 字段"):
                loader.load(skill_file)

    def test_load_description_too_long(self):
        """Test loading skill with description > 60 chars raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: test\n"
                "description: " + "x" * 61 + "\n"
                "---\n"
                "Body",
                encoding="utf-8",
            )

            loader = SkillLoader()
            with pytest.raises(ValueError, match="超过 60 字符"):
                loader.load(skill_file)

    def test_load_with_platforms(self):
        """Test loading skill with platforms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: test\n"
                "description: Test\n"
                "platforms: [linux, macos]\n"
                "---\n"
                "Body",
                encoding="utf-8",
            )

            loader = SkillLoader()
            skill = loader.load(skill_file)
            # platforms 应该被正确解析为列表
            assert skill.platforms == ["linux", "macos"]

    def test_parse_frontmatter_simple(self):
        """Test parsing simple frontmatter."""
        loader = SkillLoader()
        text = (
            "---\n"
            "name: test\n"
            "description: Test\n"
            "---\n"
            "Body"
        )
        frontmatter, body = loader._parse_frontmatter(text)
        assert frontmatter["name"] == "test"
        assert frontmatter["description"] == "Test"
        assert body == "Body"

    def test_parse_frontmatter_quoted_values(self):
        """Test parsing frontmatter with quoted values."""
        loader = SkillLoader()
        text = (
            "---\n"
            "name: 'test'\n"
            'description: "Test"\n'
            "---\n"
            "Body"
        )
        frontmatter, body = loader._parse_frontmatter(text)
        assert frontmatter["name"] == "test"
        assert frontmatter["description"] == "Test"


class TestSlugify:
    """Tests for slugify function."""

    def test_simple_text(self):
        """Test slugifying simple text."""
        assert slugify("Hello World") == "hello-world"

    def test_special_characters(self):
        """Test slugifying text with special characters."""
        assert slugify("Hello, World!") == "hello-world"

    def test_multiple_spaces(self):
        """Test slugifying text with multiple spaces."""
        assert slugify("Hello   World") == "hello-world"

    def test_underscores(self):
        """Test slugifying text with underscores."""
        assert slugify("Hello_World") == "hello-world"

    def test_mixed_case(self):
        """Test slugifying mixed case text."""
        assert slugify("HelloWorld") == "helloworld"

    def test_empty_string(self):
        """Test slugifying empty string."""
        assert slugify("") == ""

    def test_leading_trailing_whitespace(self):
        """Test slugifying text with leading/trailing whitespace."""
        assert slugify("  Hello World  ") == "hello-world"
