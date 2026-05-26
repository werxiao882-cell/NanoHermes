"""快速测试脚本 - 验证 DashScope Qwen3.6-Plus API 连接。

使用方法:
    python test_api.py
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的配置
load_dotenv()

from openai import OpenAI

# 从环境变量读取配置
api_key = os.environ.get("DASHSCOPE_API_KEY")
base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
model = os.environ.get("MODEL_NAME", "qwen3.6-plus")

if not api_key:
    print("[ERROR] 未设置 DASHSCOPE_API_KEY 环境变量")
    exit(1)

print(f"[INFO] 连接: {base_url}")
print(f"[INFO] 模型: {model}")
print("[INFO] 发送测试请求...\n")

try:
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一个测试助手。"},
            {"role": "user", "content": "你好，请用一句话回复测试成功。"},
        ],
        max_tokens=50,
    )

    print("[OK] API 连接成功!")
    print(f"[RESPONSE] {response.choices[0].message.content}")
    print(f"[USAGE] 输入 {response.usage.prompt_tokens} tokens, 输出 {response.usage.completion_tokens} tokens")

except Exception as e:
    print(f"[ERROR] API 连接失败: {type(e).__name__}: {e}")
