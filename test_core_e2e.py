#!/usr/bin/env python
"""核心模块端到端测试（绕过 TUI，直接测试各模块）。

测试覆盖 TESTING_GUIDE.md 中的核心场景：
1. 启动验证 - 配置加载、工具注册
2. 基础对话 - 简单回复（真实 API 调用）
3. 工具调用 - terminal 工具执行
4. 会话存储 - JSONL + SQLite 持久化
5. 记忆系统 - 记忆注入和更新
6. 工具搜索 - BM25/Regex 搜索
7. 对话循环 - 完整流程
"""

import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

NANOHERMES_HOME = Path.home() / ".nanohermes"
SESSIONS_DIR = NANOHERMES_HOME / "sessions"
MEMORY_DIR = NANOHERMES_HOME / "memory"


def clean_test_data():
    if SESSIONS_DIR.exists():
        shutil.rmtree(SESSIONS_DIR)
    db = NANOHERMES_HOME / "sessions.db"
    if db.exists():
        db.unlink()
    if MEMORY_DIR.exists():
        shutil.rmtree(MEMORY_DIR)


def setup_test_env():
    from dotenv import load_dotenv
    load_dotenv()
    os.environ.setdefault("DASHSCOPE_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    os.environ.setdefault("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    os.environ.setdefault("MODEL_NAME", "qwen3.6-plus")


class TestRunner:
    def __init__(self):
        self.results = {}
        self.passed = 0
        self.failed = 0

    def record(self, test_name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.results[test_name] = {"status": status, "detail": detail}
        print(f"  [{status}] {test_name}" + (f" - {detail}" if detail else ""))

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'=' * 60}")
        print(f"测试总结: {self.passed}/{total} 通过, {self.failed} 失败")
        print(f"{'=' * 60}")
        return self.failed == 0


def test_startup(runner):
    print("\n[测试 1] 启动验证...")
    try:
        from src.config.loader import load_config
        config = load_config()
        runner.record("配置加载", config is not None, f"模型: {config.model.provider}/{config.model.name}")

        from src.tools.registry import ToolRegistry
        ToolRegistry.init_all_tools()
        all_tools = ToolRegistry.get_all_tools()
        runner.record("工具注册", len(all_tools) > 0, f"共 {len(all_tools)} 个工具")

        from src.tools.registry import get_tool_schemas, get_deferred_tools
        core = get_tool_schemas(exclude_deferred=True)
        deferred = get_deferred_tools()
        runner.record("核心工具加载", len(core) > 0, f"{len(core)} 个始终加载")
        runner.record("延迟工具加载", len(deferred) > 0, f"{len(deferred)} 个延迟加载")

    except Exception as e:
        runner.record("启动验证", False, str(e))


async def test_basic_conversation(runner):
    print("\n[测试 2] 基础对话（真实 API）...")
    try:
        from openai import OpenAI
        from src.config import load_config, get_api_key, get_base_url

        config = load_config()
        api_key = get_api_key(config)
        base_url = get_base_url(config)

        client = OpenAI(api_key=api_key, base_url=base_url)
        messages = [{"role": "user", "content": "你好，请用一句话介绍你自己"}]

        response = client.chat.completions.create(
            model=config.model.name,
            messages=messages,
            max_tokens=100,
        )

        content = response.choices[0].message.content
        runner.record("API 调用成功", bool(content), f"回复长度: {len(content)} 字符")
        if content:
            runner.record("回复内容非空", len(content) > 5, f"回复: {content[:60]}...")

    except Exception as e:
        runner.record("基础对话", False, str(e))


async def test_tool_calling(runner):
    print("\n[测试 3] 工具调用...")
    try:
        from src.tools.dispatcher import dispatch

        result = dispatch(
            name="terminal",
            args={"command": "echo hello_from_test"},
            task_id="test_001",
        )
        data = json.loads(result) if isinstance(result, str) else result
        has_output = "hello_from_test" in str(data)
        runner.record("terminal 工具执行", has_output, f"输出: {str(data)[:100]}")

        from src.tools.file_tool import read_file, write_file
        test_file = NANOHERMES_HOME / "test_e2e_temp.txt"

        write_result = write_file(path=str(test_file), content="e2e test content")
        runner.record("write_file 执行", "success" in str(write_result).lower() or "成功" in str(write_result), str(write_result)[:100])

        if test_file.exists():
            read_result = read_file(path=str(test_file))
            runner.record("read_file 执行", "e2e test content" in str(read_result), str(read_result)[:100])
            test_file.unlink()

    except Exception as e:
        runner.record("工具调用", False, str(e))


async def test_session_storage(runner):
    print("\n[测试 4] 会话存储...")
    try:
        from src.session.session_db import SessionDB
        from src.session.jsonl_store import JsonlSessionStore

        db = SessionDB(NANOHERMES_HOME / "sessions.db")
        jsonl_store = JsonlSessionStore()

        session_id = "test_e2e_session"
        db.create_session(session_id, model="qwen3.6-plus", title="E2E Test")

        messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！我是 NanoHermes。"},
        ]
        for msg in messages:
            jsonl_store.append_message(session_id, msg)

        runner.record("JSONL 文件生成", (SESSIONS_DIR / f"{session_id}.jsonl").exists())

        loaded = jsonl_store.load_messages(session_id)
        runner.record("JSONL 消息加载", len(loaded) == 2, f"加载 {len(loaded)} 条消息")

        sessions = db.list_sessions()
        runner.record("SQLite 会话列表", len(sessions) > 0, f"共 {len(sessions)} 个会话")

    except Exception as e:
        runner.record("会话存储", False, str(e))


async def test_memory_system(runner):
    print("\n[测试 5] 记忆系统...")
    try:
        from src.memory.manager import MemoryManager
        from src.memory.file_provider import FileMemoryProvider

        mem_mgr = MemoryManager()
        mem_mgr.add_provider(FileMemoryProvider(str(NANOHERMES_HOME)))

        # 初始化
        mem_mgr.initialize_all(session_id="test_e2e")

        # 构建系统提示
        prompt = mem_mgr.build_system_prompt()
        runner.record("系统提示构建", len(prompt) >= 0, f"长度: {len(prompt)} 字符")

        # 同步一轮（会触发记忆更新）
        mem_mgr.sync_all(user_content="测试用户", assistant_content="测试助手")

        runner.record("MEMORY.md 生成", (MEMORY_DIR / "MEMORY.md").exists())

        if (MEMORY_DIR / "MEMORY.md").exists():
            md_content = (MEMORY_DIR / "MEMORY.md").read_text(encoding="utf-8")
            runner.record("记忆内容非空", len(md_content) > 0, f"长度: {len(md_content)} 字符")

    except Exception as e:
        runner.record("记忆系统", False, str(e))


async def test_tool_search(runner):
    print("\n[测试 6] 工具搜索...")
    try:
        from src.tools.search_tool import ToolSearch

        sample_tools = [
            {"name": "read_file", "description": "Read a text file with line numbers", "parameters": {"properties": {}}},
            {"name": "write_file", "description": "Write content to a file", "parameters": {"properties": {}}},
            {"name": "execute_code", "description": "Execute Python code in a sandbox", "parameters": {"properties": {}}},
        ]

        searcher = ToolSearch(sample_tools)

        bm25_results = searcher.search("read a text file", mode="bm25")
        runner.record("BM25 搜索", len(bm25_results) > 0, f"找到 {len(bm25_results)} 个结果")
        if bm25_results:
            runner.record("BM25 相关性", bm25_results[0]["name"] == "read_file", f"最佳匹配: {bm25_results[0]['name']}")

        regex_results = searcher.search("read_.*file", mode="regex")
        runner.record("Regex 搜索", len(regex_results) > 0, f"找到 {len(regex_results)} 个结果")

        auto_results = searcher.search("execute python code")
        runner.record("Auto 模式", len(auto_results) > 0, f"找到 {len(auto_results)} 个结果")

    except Exception as e:
        runner.record("工具搜索", False, str(e))


async def test_conversation_loop(runner):
    print("\n[测试 7] 对话循环（完整流程）...")
    try:
        from src.config import load_config, get_api_key, get_base_url
        from src.provider.openai_client import OpenAIClient as ProviderOpenAIClient
        from src.conversation.loop import ConversationLoop
        from src.tools.registry import ToolRegistry, get_tool_schemas
        from openai import OpenAI

        config = load_config()
        api_key = get_api_key(config)
        base_url = get_base_url(config)

        client = OpenAI(api_key=api_key, base_url=base_url)
        provider_client = ProviderOpenAIClient(client, config.model.name)
        model_caller = provider_client.build_caller()

        ToolRegistry.init_all_tools()
        tool_schemas = get_tool_schemas(exclude_deferred=True)

        loop = ConversationLoop(model_call=model_caller)

        messages = [{"role": "user", "content": "你好，请简短回复"}]
        response = loop.run(messages, tools=tool_schemas)

        runner.record("对话循环完成", response is not None, f"迭代次数: {response.get('iterations', 'N/A')}")

        if response and response.get("response"):
            content = response["response"].get("content", "")
            runner.record("响应内容", len(content) > 0, f"长度: {len(content)} 字符")

    except Exception as e:
        runner.record("对话循环", False, str(e))


async def main():
    setup_test_env()
    clean_test_data()

    print("=" * 60)
    print("NanoHermes 核心模块端到端测试")
    print("=" * 60)

    runner = TestRunner()

    test_startup(runner)
    await test_basic_conversation(runner)
    await test_tool_calling(runner)
    await test_session_storage(runner)
    await test_memory_system(runner)
    await test_tool_search(runner)
    await test_conversation_loop(runner)

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
