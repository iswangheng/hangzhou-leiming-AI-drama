"""
技能理解模块 - 理解技能文件，生成分析框架
"""
import json
import os
import base64
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .config import TrainingConfig


@dataclass
class SkillFramework:
    """技能框架"""
    skill_version: str
    generated_at: str
    framework: Dict[str, Any]


def encode_image(image_path: str) -> str:
    """将图片编码为 base64

    Args:
        image_path: 图片文件路径

    Returns:
        Base64编码的字符串
    """
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def build_skill_understanding_prompt(skill_json: str) -> str:
    """构建技能理解的prompt

    Args:
        skill_json: 技能文件的JSON部分

    Returns:
        Prompt字符串
    """
    prompt = f"""你是一位短剧剪辑专家。请理解以下技能文件，生成一个用于分析视频的分析框架。

技能文件内容：
{skill_json}

请返回：
1. 高光类型的核心特征
2. 钩子类型的核心特征
3. 判断高光/钩子的关键指标

返回JSON格式：
{{
  "highlight_types": [
    {{
      "name": "类型名称",
      "core_features": "核心特征描述",
      "visual_indicators": ["视觉指标1", "视觉指标2"],
      "audio_indicators": ["听觉指标1", "听觉指标2"],
      "emotion_indicators": ["情绪指标1"],
      "plot_indicators": ["剧情指标1"]
    }}
  ],
  "hook_types": [
    {{
      "name": "类型名称",
      "core_features": "核心特征描述",
      "visual_indicators": ["视觉指标1", "视觉指标2"],
      "audio_indicators": ["听觉指标1", "听觉指标2"],
      "emotion_indicators": ["情绪指标1"],
      "plot_indicators": ["剧情指标1"]
    }}
  ],
  "judgment_criteria": {{
    "highlight_confidence": "如何判断高光点的置信度",
    "hook_confidence": "如何判断钩子点的置信度"
  }}
}}"""

    return prompt


def parse_skill_framework_response(response_text: str) -> Dict[str, Any]:
    """解析技能框架响应

    Args:
        response_text: API响应文本

    Returns:
        解析后的框架数据
    """
    import re

    # 移除markdown代码块标记
    clean_text = response_text.strip()
    if clean_text.startswith('```json'):
        clean_text = clean_text[7:]
    if clean_text.startswith('```'):
        clean_text = clean_text[3:]
    if clean_text.endswith('```'):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    # 尝试提取JSON
    json_match = re.search(r'\{[\s\S]*\}', clean_text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # 返回默认框架
    return {
        "highlight_types": [],
        "hook_types": [],
        "judgment_criteria": {}
    }


def understand_skill(skill_file_path: str, max_retries: int = TrainingConfig.MAX_RETRIES) -> SkillFramework:
    """理解技能文件，生成技能框架

    Args:
        skill_file_path: 技能文件路径
        max_retries: 最大重试次数

    Returns:
        技能框架
    """
    if not os.path.exists(skill_file_path):
        raise FileNotFoundError(f"技能文件不存在: {skill_file_path}")

    # 读取技能文件
    with open(skill_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取JSON部分（查找第一个```json代码块）
    json_match = __import__('re').search(r'```json\s*\n([\s\S]*?)\n```', content)
    if json_match:
        skill_json = json_match.group(1)
    else:
        # 如果没有找到JSON代码块，尝试提取纯JSON
        json_match = __import__('re').search(r'\{[\s\S]*\}', content)
        if json_match:
            skill_json = json_match.group()
        else:
            raise ValueError("无法从技能文件中提取JSON部分")

    # 构建prompt
    prompt = build_skill_understanding_prompt(skill_json)

    # 调用Gemini API
    for attempt in range(max_retries):
        try:
            print(f"理解技能文件 (尝试 {attempt + 1}/{max_retries})...")

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 4096
                }
            }

            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(
                TrainingConfig.GEMINI_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=TrainingConfig.REQUEST_TIMEOUT
            )

            response.raise_for_status()

            # 解析响应
            data = response.json()
            response_text = data['candidates'][0]['content']['parts'][0]['text']
            framework_data = parse_skill_framework_response(response_text)

            # 提取版本号
            version_match = __import__('re').search(r'v[\d.]+', skill_file_path)
            version = version_match.group() if version_match else "unknown"

            from datetime import datetime
            framework = SkillFramework(
                skill_version=version,
                generated_at=datetime.now().isoformat(),
                framework=framework_data
            )

            print("技能框架生成完成")
            return framework

        except requests.exceptions.RequestException as e:
            print(f"API请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                sleep_time = (2 ** attempt) * 5
                print(f"等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                raise Exception(f"技能理解失败: {e}")

        except Exception as e:
            print(f"处理失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                sleep_time = (2 ** attempt) * 5
                print(f"等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                raise


def save_skill_framework(framework: SkillFramework, output_path: str):
    """保存技能框架到文件

    Args:
        framework: 技能框架
        output_path: 输出文件路径
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    output_data = {
        "skillVersion": framework.skill_version,
        "generatedAt": framework.generated_at,
        "framework": framework.framework
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"技能框架已保存到: {output_path}")


def load_skill_framework(framework_path: str) -> Optional[SkillFramework]:
    """加载技能框架

    Args:
        framework_path: 框架文件路径

    Returns:
        技能框架，如果文件不存在则返回None
    """
    if not os.path.exists(framework_path):
        return None

    with open(framework_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return SkillFramework(
        skill_version=data.get("skillVersion", "unknown"),
        generated_at=data.get("generatedAt", ""),
        framework=data.get("framework", {})
    )


if __name__ == "__main__":
    # 测试代码
    from .config import TrainingConfig
    from pathlib import Path

    # 查找最新的技能文件
    skills_dir = TrainingConfig.SKILLS_DIR
    skill_files = list(skills_dir.glob("ai-drama-clipping-thoughts-*.md"))

    if skill_files:
        latest_skill = sorted(skill_files)[-1]
        print(f"使用技能文件: {latest_skill}")

        try:
            framework = understand_skill(str(latest_skill))

            # 保存框架
            output_path = TrainingConfig.DATA_DIR / "frameworks" / f"{framework.skill_version}.json"
            save_skill_framework(framework, str(output_path))

            # 显示框架内容
            print("\n生成的框架:")
            print(json.dumps(framework.framework, ensure_ascii=False, indent=2))

        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("未找到技能文件")