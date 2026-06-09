#!/usr/bin/env python3
"""NanoHermes 真实用户模拟测试。

像真实用户一样与 AI 对话，测试完整功能链。
"""

import os
import sys
import json
import tempfile
import time

# ─── 环境设置 ──────────────────────────────────────────────────
sys.path.insert(0, "/mnt/d/code/NanoHermes")

os.environ["OPENAI_API_KEY"] = "sk-testing"
os.environ["OPENAI_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ["MODEL_NAME"] = "qwen3.6-plus"

TEST_HOME = tempfile.mkdtemp(prefix="nanohermes_user_test_")
os.environ["NANOHERMES_HOME"] = TEST_HOME

print(f"🏠 测试 Home: {TEST_HOME}")
print("=" * 70)

# ─── 初始化所有模块（模拟 main.py 的组装过程） ─────────────────

print("\n📦 初始化模块...")

# 1. 配置加载
from src.config.loader import load_config
config = load_config()
print(f"  ✅ 配置加载: {type(config).__name__}")

# 2. 凭证解析
from src.provider.credentials import resolve_credentials
env_vars = {
    "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
    "OPENAI_BASE_URL": os.environ["OPENAI_BASE_URL"],
    "MODEL_NAME": os.environ["MODEL_NAME"],
}
creds = resolve_credentials(env_vars)
print(f"  ✅ 凭证解析: api_key={'已设置' if creds.api_key else '未设置'}, base_url={creds.base_url}")

# 3. Provider 客户端
from src.provider.client_factory import build_client
from src.provider.api_mode import ApiMode
client = build_client(ApiMode.CHAT_COMPLETIONS, creds)
print(f"  ✅ Provider 客户端: {type(client).__name__}")

# 4. 工具系统
from src.tools.registry import ToolRegistry
from src.tools.dispatcher import dispatch
ToolRegistry.init_all_tools()
tools = ToolRegistry.get_all_tools()
print(f"  ✅ 工具注册: {len(tools)} 个工具")

# 5. 会话存储
from src.session.session_db import SessionDB
from src.session.jsonl_store import JsonlSessionStore
from pathlib import Path

home = Path(TEST_HOME)
db_path = home / "sessions.db"
jsonl_dir = home / "sessions"
jsonl_dir.mkdir(parents=True, exist_ok=True)

session_db = SessionDB(db_path)
jsonl_store = JsonlSessionStore(jsonl_dir)
print(f"  ✅ 会话存储: SQLite + JSONL")

# 6. 记忆系统
from src.memory.file_provider import FileMemoryProvider
memory_dir = home / "memory"
memory_dir.mkdir(parents=True, exist_ok=True)
memory_provider = FileMemoryProvider(memory_dir)
print(f"  ✅ 记忆系统: FileMemoryProvider")

# 7. 提示组装
from src.prompt.assembler import PromptAssembler
prompt_assembler = PromptAssembler()
print(f"  ✅ 提示组装: PromptAssembler")

# 8. 上下文压缩
from src.compression.compressor import ContextCompressor
compressor = ContextCompressor(
    model=os.environ["MODEL_NAME"],
    main_credentials=creds,
)
print(f"  ✅ 上下文压缩: ContextCompressor")

# ─── 创建会话 ──────────────────────────────────────────────────
session_id = session_db.create_session(title="用户模拟测试")
print(f"\n💬 创建会话: {session_id[:12]}...")

# ─── 对话循环模拟 ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("🚀 开始模拟用户对话")
print("=" * 70)

def simulate_conversation(user_message: str, messages: list) -> dict:
    """模拟一轮对话。
    
    流程:
    1. 组装系统提示
    2. 调用 LLM
    3. 处理工具调用（如有）
    4. 返回最终回复
    """
    print(f"\n👤 用户: {user_message}")
    print(f"  📝 当前消息数: {len(messages)}")
    
    # 添加用户消息
    messages.append({"role": "user", "content": user_message})
    
    # 保存消息到存储
    session_db.insert_message(session_id, "user", user_message)
    jsonl_store.append_message(session_id, "user", user_message)
    
    # 组装系统提示
    try:
        system_prompt_result = prompt_assembler.build_system_prompt(
            model=os.environ["MODEL_NAME"],
            include_memory=True,
            include_user_profile=True,
        )
        system_prompt = system_prompt_result.text if hasattr(system_prompt_result, 'text') else str(system_prompt_result)
    except Exception as e:
        print(f"  ⚠️ 提示组装失败: {e}")
        system_prompt = "你是 NanoHermes 助手。"
    
    # 构建消息列表
    api_messages = [
        {"role": "system", "content": system_prompt},
        *messages
    ]
    
    # 获取工具 schema
    tool_schemas = ToolRegistry.get_tool_schemas()
    
    # 调用 LLM
    print(f"  🤖 调用 LLM (model={os.environ['MODEL_NAME']})...")
    try:
        response = client.chat.completions.create(
            model=os.environ["MODEL_NAME"],
            messages=api_messages,
            tools=tool_schemas if tool_schemas else None,
            max_tokens=2000,
        )
        
        choice = response.choices[0]
        message = choice.message
        
        # 检查是否有工具调用
        if message.tool_calls:
            print(f"  🔧 工具调用: {len(message.tool_calls)} 个")
            
            # 添加助手消息（含工具调用）
            assistant_msg = {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in message.tool_calls
                ]
            }
            messages.append(assistant_msg)
            
            # 执行工具
            tool_results = []
            for tc in message.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)
                
                print(f"    ⚙️  执行 {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:100]}...)")
                
                result = dispatch(tool_name, tool_args)
                result_data = json.loads(result)
                
                # 截断显示
                result_preview = str(result_data)[:200]
                print(f"    📤 结果: {result_preview}...")
                
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
                
                # 保存工具结果到存储
                session_db.insert_message(session_id, "tool", result[:500])
            
            messages.extend(tool_results)
            
            # 第二轮：让 AI 处理工具结果
            print(f"  🤖 二次调用 LLM（处理工具结果）...")
            api_messages_with_tools = [
                {"role": "system", "content": system_prompt},
                *messages
            ]
            
            response2 = client.chat.completions.create(
                model=os.environ["MODEL_NAME"],
                messages=api_messages_with_tools,
                max_tokens=2000,
            )
            
            final_message = response2.choices[0].message
            final_content = final_message.content or "(无内容)"
            
            print(f"\n  🤖 AI: {final_content[:300]}{'...' if len(final_content) > 300 else ''}")
            
            # 保存最终回复
            messages.append({"role": "assistant", "content": final_content})
            session_db.insert_message(session_id, "assistant", final_content)
            jsonl_store.append_message(session_id, "assistant", final_content)
            
            return {
                "status": "success",
                "tool_calls": len(message.tool_calls),
                "response_length": len(final_content),
            }
        
        else:
            # 无工具调用，直接回复
            content = message.content or "(无内容)"
            print(f"\n  🤖 AI: {content[:300]}{'...' if len(content) > 300 else ''}")
            
            messages.append({"role": "assistant", "content": content})
            session_db.insert_message(session_id, "assistant", content)
            jsonl_store.append_message(session_id, "assistant", content)
            
            return {
                "status": "success",
                "tool_calls": 0,
                "response_length": len(content),
            }
    
    except Exception as e:
        print(f"  ❌ LLM 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# ─── 执行测试场景 ──────────────────────────────────────────────
messages = []  # 对话历史

print("\n" + "=" * 70)
print("📋 测试场景 1: 首次对话")
print("=" * 70)
simulate_conversation("你好，介绍一下你自己", messages)

print("\n" + "=" * 70)
print("📋 测试场景 2: 文件读取")
print("=" * 70)
simulate_conversation("帮我读取 pyproject.toml 的内容", messages)

print("\n" + "=" * 70)
print("📋 测试场景 3: 终端命令")
print("=" * 70)
simulate_conversation("列出当前目录下的所有 .py 文件", messages)

print("\n" + "=" * 70)
print("📋 测试场景 4: 文件写入")
print("=" * 70)
simulate_conversation("在 /tmp/ 目录下创建一个 hello.txt，写入 Hello NanoHermes", messages)

print("\n" + "=" * 70)
print("📋 测试场景 5: 多轮上下文")
print("=" * 70)
simulate_conversation("刚才创建的文件内容是什么？", messages)

print("\n" + "=" * 70)
print("📋 测试场景 6: 错误处理")
print("=" * 70)
simulate_conversation("读取一个不存在的文件 /tmp/xxx_not_exist_12345.txt", messages)

# ─── 汇总 ─────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("📊 对话汇总")
print("=" * 70)
print(f"  总消息数: {len(messages)}")
print(f"  用户消息: {sum(1 for m in messages if m['role'] == 'user')}")
print(f"  AI 回复: {sum(1 for m in messages if m['role'] == 'assistant')}")
print(f"  工具调用: {sum(1 for m in messages if m['role'] == 'tool')}")

print(f"\n  会话 ID: {session_id}")
print(f"  消息存储: SQLite ✅, JSONL ✅")

# 验证存储
db_messages = session_db.get_messages(session_id)
print(f"  SQLite 消息数: {len(db_messages)}")

jsonl_messages = jsonl_store.load_messages(session_id)
print(f"  JSONL 消息数: {len(jsonl_messages)}")

# 清理
session_db.close()
import shutil
try:
    shutil.rmtree(TEST_HOME)
    print(f"\n🧹 已清理测试目录: {TEST_HOME}")
except:
    pass

print("\n" + "=" * 70)
print("✅ 用户模拟测试完成")
print("=" * 70)
