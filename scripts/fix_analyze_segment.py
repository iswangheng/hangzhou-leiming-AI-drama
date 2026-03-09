"""
修复 analyze_segment.py 使用通用 Gemini 客户端
"""
import re

# 读取文件
with open('scripts/understand/analyze_segment.py', 'r') as f:
    content = f.read()

# 1. 添加导入
old_import = "from scripts.config import TrainingConfig"
new_import = """from scripts.config import TrainingConfig
from scripts.lib.gemini_client import GeminiClient"""
content = content.replace(old_import, new_import)

# 2. 修改 prompt (添加 JSON schema)
old_prompt = "**只返回JSON，不要其他文字。**"
new_prompt = """{"highlight": {"exists": true/false, "preciseSecond": 数字, "type": "类型", "confidence": 数字, "reasoning": "原因"}, "hook": {"exists": true/false, "preciseSecond": 数字, "type": "类型", "confidence": 数字, "reasoning": "原因"}}
只返回上面这个JSON，不要其他任何文字。"""
content = content.replace(old_prompt, new_prompt)

# 3. 修改 API 调用 - 使用通用客户端
# 找到 analyze_segment 函数中定义 url 的位置并替换
old_url = '''url = f"https://yunwu.ai/v1beta/models/gemini-2.0-flash:generateContent?key={TrainingConfig.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        try:
            payload = build_analyze_prompt(segment, skill_framework)

            response = requests.post(
                url, headers=headers, json=payload, timeout=60
            )
            response.raise_for_status()

            data = response.json()
            response_text = data['candidates'][0]['content']['parts'][0]['text']'''

new_url = '''# 使用通用Gemini客户端
    client = GeminiClient(max_retries=max_retries)

    for attempt in range(max_retries):
        try:
            payload = build_analyze_prompt(segment, skill_framework)

            # 使用通用客户端调用API
            response_text = client.call_with_messages(
                payload["contents"],
                payload.get("generationConfig")
            )'''

content = content.replace(old_url, new_url)

# 写回文件
with open('scripts/understand/analyze_segment.py', 'w') as f:
    f.write(content)

print("修改完成!")
