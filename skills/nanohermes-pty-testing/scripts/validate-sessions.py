#!/usr/bin/env python3
"""NanoHermes 会话存储与记忆验证脚本。

测试后运行，验证 JSONL、SQLite、记忆文件的完整性。
输出：结构化验证报告。
"""

import json
import os
import sqlite3
import sys
from pathlib import Path


def check_jsonl_sessions(sessions_dir: Path) -> dict:
    """检查 JSONL 会话文件。"""
    result = {"files": [], "total_lines": 0, "total_size": 0}
    
    if not sessions_dir.exists():
        return {"error": f"目录不存在: {sessions_dir}"}
    
    jsonl_files = list(sessions_dir.glob("*.jsonl"))
    for f in jsonl_files:
        lines = f.read_text().strip().split("\n")
        valid_lines = 0
        invalid_lines = 0
        
        for line in lines:
            try:
                json.loads(line)
                valid_lines += 1
            except json.JSONDecodeError:
                invalid_lines += 1
        
        size_kb = f.stat().st_size / 1024
        result["files"].append({
            "name": f.name,
            "lines": len(lines),
            "valid": valid_lines,
            "invalid": invalid_lines,
            "size_kb": round(size_kb, 1),
        })
        result["total_lines"] += len(lines)
        result["total_size"] += size_kb
    
    return result


def check_sqlite_metadata(db_path: Path) -> dict:
    """检查 SQLite 会话元数据。"""
    result = {"sessions": [], "error": None}
    
    if not db_path.exists():
        return {"error": f"数据库不存在: {db_path}"}
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT id, model, title, message_count, tool_call_count, "
            "input_tokens, output_tokens, started_at "
            "FROM sessions ORDER BY started_at DESC"
        )
        for row in cursor.fetchall():
            result["sessions"].append({
                "id": row[0],
                "model": row[1],
                "title": row[2],
                "message_count": row[3],
                "tool_call_count": row[4],
                "input_tokens": row[5],
                "output_tokens": row[6],
                "started_at": row[7],
            })
        conn.close()
    except Exception as e:
        result["error"] = str(e)
    
    return result


def check_memory_files(memory_dir: Path) -> dict:
    """检查记忆文件。"""
    result = {}
    
    for filename in ["MEMORY.md", "USER.md"]:
        filepath = memory_dir / filename
        if filepath.exists():
            content = filepath.read_text().strip()
            result[filename] = {
                "exists": True,
                "size": filepath.stat().st_size,
                "lines": len(content.split("\n")),
                "preview": content[:200] if content else "(空)",
            }
        else:
            result[filename] = {"exists": False}
    
    return result


def main():
    nanohermes_home = Path.home() / ".nanohermes"
    sessions_dir = nanohermes_home / "sessions"
    db_path = nanohermes_home / "sessions.db"
    memory_dir = nanohermes_home / "memory"
    
    print("=" * 60)
    print("NanoHermes 会话存储与记忆验证")
    print("=" * 60)
    
    # JSONL
    print("\n📁 JSONL 会话文件:")
    jsonl_result = check_jsonl_sessions(sessions_dir)
    if "error" in jsonl_result:
        print(f"   ❌ {jsonl_result['error']}")
    else:
        print(f"   文件数: {len(jsonl_result['files'])}")
        print(f"   总行数: {jsonl_result['total_lines']}")
        print(f"   总大小: {jsonl_result['total_size']:.1f} KB")
        for f in jsonl_result["files"]:
            status = "✅" if f["invalid"] == 0 else "⚠️"
            print(f"   {status} {f['name']}: {f['lines']} 行, {f['size_kb']} KB")
    
    # SQLite
    print("\n🗄️ SQLite 元数据:")
    sqlite_result = check_sqlite_metadata(db_path)
    if sqlite_result["error"]:
        print(f"   ❌ {sqlite_result['error']}")
    else:
        print(f"   会话数: {len(sqlite_result['sessions'])}")
        for s in sqlite_result["sessions"]:
            print(f"   📝 {s['title'] or '(无标题)'}")
            print(f"      ID: {s['id'][:8]}... | 模型: {s['model']}")
            print(f"      消息: {s['message_count']} | 工具: {s['tool_call_count']}")
            print(f"      Token: 输入 {s['input_tokens']} | 输出 {s['output_tokens']}")
    
    # Memory
    print("\n🧠 记忆文件:")
    memory_result = check_memory_files(memory_dir)
    for filename, info in memory_result.items():
        if info["exists"]:
            print(f"   ✅ {filename}: {info['size']} bytes, {info['lines']} 行")
            print(f"      {info['preview']}")
        else:
            print(f"   ❌ {filename}: 不存在")
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
