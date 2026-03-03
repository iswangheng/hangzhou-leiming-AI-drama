"""
理解技能文件模块
读取技能文件，调用Gemini API生成技能理解框架
"""
import json
import os
import requests
from typing import Dict, Any
from pathlib import Path

# 尝试导入配置
try:
    from scripts.config import TrainingConfig
except ImportError:
    # 如果没有配置，使用默认值
    class TrainingConfig:
        GEMINI_API_KEY = "sk-iKGxKJOSZ4ZVAE9noaVSe3ahYkRVP7BbyfqFQtC7x88JatLW"
        GEMINI_MAX_TOKENS = 4096
        GEMINI_TEMPERATURE = 0.7


# Prompt模板
SKILL_UNDERSTAND_PROMPT = """你是一位短剧剪辑专家。请理解以下技能文件，生成一个用于分析视频的分析框架。

技能文件内容：
{SKILL_JSON}

请返回JSON格式：
{{
  "highlightTypes": [
    {{
      "name": "类型名",
      "keyFeatures": ["关键特征1", "关键特征2"],
      "visualCues": ["视觉线索1", "视觉线索2"],
      "audioCues": ["听觉线索1"]
    }}
  ],
  "hookTypes": [
    {{
      "name": "类型名", 
      "keyFeatures": ["关键特征"],
      "visualCues": ["视觉线索"],
      "audioCues": ["听觉线索"]
    }}
  ],
  "editingRules": {{
    "minDuration": 30,
    "maxDuration": 300
  }}
}}

只返回JSON，不要其他文字。"""


def load_skill_json(skill_file_path: str) -> Dict[str, Any]:
    """加载技能文件的JSON部分
    优先读取.json文件，如果不存在则尝试从.md文件提取

    Args:
        skill_file_path: 技能文件路径

    Returns:
        技能JSON数据
    """
    # 尝试1：直接读取JSON文件
    if skill_file_path.endswith('.md'):
        json_file_path = skill_file_path.replace('.md', '.json')
    else:
        json_file_path = skill_file_path

    if os.path.exists(json_file_path):
        print(f"读取JSON技能文件: {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # 尝试2：从MD文件中提取JSON
    if os.path.exists(skill_file_path):
        print(f"从Markdown文件提取JSON: {skill_file_path}")
        with open(skill_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 尝试提取 ```json 代码块
        json_start = content.find('```json\n')
        if json_start != -1:
            json_start += 9  # 跳过 ```json\n
            json_end = content.find('\n```', json_start)
            if json_end != -1:
                json_text = content[json_start:json_end].strip()
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    pass

        # 如果没有JSON代码块，返回空结构
        print("警告：未找到JSON数据，返回空结构")

    # 默认返回空结构
    return {
        "version": "v0.1",
        "highlight_types": [],
        "hook_types": [],
        "editing_rules": {
            "min_clip_duration": 30,
            "max_clip_duration": 300,
            "confidence_threshold": 8.0,
            "dedup_interval_seconds": 10,
            "max_same_type_per_episode": 1
        }
    }


def understand_skill(skill_file_path: str, force: bool = False) -> Dict[str, Any]:
    """理解技能文件，生成技能框架
    
    Args:
        skill_file_path: 技能文件路径
        force: 是否强制重新生成
        
    Returns:
        技能框架JSON
    """
    # 技能框架缓存路径
    skill_dir = Path(skill_file_path).parent
    framework_file = skill_dir / "framework.json"
    
    # 如果已存在且不强制重新生成，直接返回
    if framework_file.exists() and not force:
        with open(framework_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 加载技能JSON
    skill_json = load_skill_json(skill_file_path)
    
    # 构建prompt
    prompt = SKILL_UNDERSTAND_PROMPT.format(
        SKILL_JSON=json.dumps(skill_json, ensure_ascii=False, indent=2)
    )
    
    # 调用Gemini API
    url = f"https://yunwu.ai/v1beta/models/gemini-2.0-flash:generateContent?key={TrainingConfig.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": TrainingConfig.GEMINI_TEMPERATURE,
            "maxOutputTokens": TrainingConfig.GEMINI_MAX_TOKENS
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    
    data = response.json()
    response_text = data['candidates'][0]['content']['parts'][0]['text']
    
    # 解析JSON响应
    # 清理markdown格式
    clean_text = response_text.strip()
    if clean_text.startswith('```json'):
        clean_text = clean_text[7:]
    if clean_text.startswith('```'):
        clean_text = clean_text[3:]
    if clean_text.endswith('```'):
        clean_text = clean_text[:-3]
    
    # 尝试提取JSON
    import re
    json_match = re.search(r'\{[\s\S]*\}', clean_text)
    if json_match:
        try:
            framework = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"原始响应: {clean_text[:500]}")
            # 返回默认框架
            framework = {
                "highlightTypes": [],
                "hookTypes": [],
                "editingRules": {"minDuration": 30, "maxDuration": 300}
            }
    else:
        print("无法提取JSON")
        framework = {
            "highlightTypes": [],
            "hookTypes": [],
            "editingRules": {"minDuration": 30, "maxDuration": 300}
        }
    
    # 保存缓存
    framework_file.parent.mkdir(parents=True, exist_ok=True)
    with open(framework_file, 'w', encoding='utf-8') as f:
        json.dump(framework, f, ensure_ascii=False, indent=2)
    
    print(f"技能框架已生成: {framework_file}")
    return framework


if __name__ == "__main__":
    # 测试
    import sys
    skill_file = sys.argv[1] if len(sys.argv) > 1 else "data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.1.md"
    result = understand_skill(skill_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
