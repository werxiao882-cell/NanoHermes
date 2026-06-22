"""task-notification 格式化单元测试。"""

from src.delegation.notification import format_task_notification


class TestFormatTaskNotification:
    def test_completed(self):
        result = format_task_notification(
            task_id="a1b2",
            status="completed",
            summary="Refactored auth to JWT",
            tool_calls=5,
            duration_s=150.0,
        )
        assert "<task-notification>" in result
        assert "<task-id>a1b2</task-id>" in result
        assert "<status>completed</status>" in result
        assert "<summary>Refactored auth to JWT</summary>" in result
        assert "<tool-calls>5</tool-calls>" in result
        assert "<duration>150.0s</duration>" in result
        assert "</task-notification>" in result

    def test_failed(self):
        result = format_task_notification(
            task_id="c3d4",
            status="failed",
            summary="Error: API key missing",
        )
        assert "<status>failed</status>" in result
        assert "<tool-calls>0</tool-calls>" in result
        assert "<duration>0.0s</duration>" in result

    def test_timeout(self):
        result = format_task_notification(
            task_id="e5f6",
            status="timeout",
            summary="Timed out after 300s",
            duration_s=300.0,
        )
        assert "<status>timeout</status>" in result
        assert "<duration>300.0s</duration>" in result

    def test_xml_well_formed(self):
        """验证 XML 标签正确闭合。"""
        result = format_task_notification("t1", "completed", "done")
        # 每个开标签都有对应的闭标签
        for tag in ["task-notification", "task-id", "status", "summary", "tool-calls", "duration"]:
            assert f"<{tag}>" in result
            assert f"</{tag}>" in result
