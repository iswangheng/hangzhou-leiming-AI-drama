"""
Gemini AI分析模块 - 调用Gemini API分析标记点
"""
import base64
import json
import re
import time
import os
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .data_models import MarkingContext, AnalysisResult
from .config import TrainingConfig


def encode_image(image_path: str) -> str:
    """将图片编码为 base64

    Args:
        image_path: 图片文件路径

    Returns:
        Base64编码的字符串
    """
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def build_gemini_request(context: MarkingContext, prompt_template: str) -> dict:
    """构建Gemini API请求

    Args:
        context: 标记上下文
        prompt_template: Prompt模板

    Returns:
        API请求数据
    """
    marking = context.marking

    # 构建时间范围描述
    if marking.type == "钩子点":
        time_range = f"{max(0, marking.seconds - 10):.1f}s - {marking.seconds:.1f}s"
    else:
        time_range = f"{marking.seconds:.1f}s - {marking.seconds + 10:.1f}s"

    # JSON输出模板（需要双花括号转义）
    json_template = '''{
  "highlight_types": [
    {
      "name": "类型名称",
      "description": "类型描述",
      "visual_features": {"expressions": [], "shots": [], "actions": [], "scenes": []},
      "audio_features": {"dialogue_type": [], "emotion": [], "content": ""},
      "emotion_features": {"type": [], "intensity": 5, "change": ""},
      "plot_features": {"function": "", "position": "", "revelation": false},
      "content_features": {"cool_points": [], "pain_points": []}
    }
  ],
  "hook_types": [],
  "reasoning": "分析理由"
}'''

    # 读取prompt模板并替换占位符
    prompt = prompt_template.replace('{episode}', marking.episode)
    prompt = prompt.replace('{timestamp}', marking.timestamp)
    prompt = prompt.replace('{type}', marking.type)
    prompt = prompt.replace('{time_range}', time_range)
    prompt = prompt.replace('{asr_text}', context.asr_text or "(无语音)")
    prompt = prompt.replace('PLACEHOLDER_JSON', json_template)

    # 准备关键帧图片（取前几张）
    keyframe_parts = []
    for kf in context.keyframes[:5]:  # 最多5张
        if os.path.exists(kf.frame_path):
            try:
                img_base64 = encode_image(kf.frame_path)
                keyframe_parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": img_base64
                    }
                })
            except Exception as e:
                print(f"警告: 无法编码图片 {kf.frame_path}: {e}")
                continue

    # 构建请求体
    parts = [{"text": prompt}]
    parts.extend(keyframe_parts)

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": TrainingConfig.GEMINI_TEMPERATURE,
            "maxOutputTokens": TrainingConfig.GEMINI_MAX_TOKENS
        }
    }

    return payload


def parse_gemini_response(response_text: str) -> dict:
    """解析Gemini API响应

    Args:
        response_text: 响应文本

    Returns:
        解析后的JSON数据
    """
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
        except json.JSONDecodeError as e:
            pass

    # 如果无法提取JSON，返回基本信息
    return {
        "highlight_types": [],
        "hook_types": [],
        "editing_rules": [],
        "reasoning": f"无法解析响应: {clean_text[:200]}"
    }


def analyze_marking_with_gemini(
    context: MarkingContext,
    prompt_template: str,
    max_retries: int = TrainingConfig.MAX_RETRIES
) -> AnalysisResult:
    """使用 Gemini 分析标记点

    Args:
        context: 标记上下文
        prompt_template: Prompt模板
        max_retries: 最大重试次数

    Returns:
        分析结果

    Raises:
        Exception: 分析失败
    """
    marking = context.marking

    for attempt in range(max_retries):
        try:
            print(f"分析标记 {marking.id}: {marking.episode} @ {marking.timestamp} ({marking.type})")

            # 构建请求
            payload = build_gemini_request(context, prompt_template)

            headers = {
                "Content-Type": "application/json"
            }

            # 发送请求
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
            result_data = parse_gemini_response(response_text)

            # 提取第一个高光或钩子类型
            highlight_types = result_data.get('highlight_types', [])
            hook_types = result_data.get('hook_types', [])

            if highlight_types:
                category_data = highlight_types[0]
                category = category_data.get('name', '未知高光类型')
                category_description = category_data.get('description', '')
            elif hook_types:
                category_data = hook_types[0]
                category = category_data.get('name', '未知钩子类型')
                category_description = category_data.get('description', '')
            else:
                category = '未分类'
                category_description = 'AI未能识别出具体类型'

            return AnalysisResult(
                type=marking.type,
                category=category,
                category_description=category_description,
                visual_features=category_data.get('visual_features', {}),
                audio_features=category_data.get('audio_features', {}),
                emotion_features=category_data.get('emotion_features', {}),
                plot_features=category_data.get('plot_features', {}),
                content_features=category_data.get('content_features', {}),
                reasoning=result_data.get('reasoning', '')
            )

        except requests.exceptions.RequestException as e:
            print(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                # 指数退避
                sleep_time = (2 ** attempt) * 5
                print(f"等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                raise Exception(f"Gemini API调用失败: {e}")

        except Exception as e:
            print(f"分析失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) * 5
                print(f"等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                raise


def analyze_markings_batch(
    contexts: List[MarkingContext],
    prompt_template: str,
    max_workers: int = TrainingConfig.MAX_CONCURRENT_ANALYSIS,
    show_progress: bool = True
) -> List[AnalysisResult]:
    """批量分析标记点

    Args:
        contexts: 标记上下文列表
        prompt_template: Prompt模板
        max_workers: 最大并发数
        show_progress: 是否显示进度

    Returns:
        分析结果列表
    """
    results = []
    failed_contexts = []

    if show_progress:
        print(f"开始批量分析 {len(contexts)} 个标记...")

    def analyze_with_error_handling(context: MarkingContext) -> Optional[AnalysisResult]:
        try:
            return analyze_marking_with_gemini(context, prompt_template)
        except Exception as e:
            print(f"错误: 标记 {context.marking.id} 分析失败: {e}")
            failed_contexts.append((context, str(e)))
            return None

    # 使用线程池并发分析
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(analyze_with_error_handling, ctx): ctx
            for ctx in contexts
        }

        for i, future in enumerate(as_completed(futures), 1):
            if show_progress:
                print(f"进度: {i}/{len(contexts)}")

            try:
                result = future.result(timeout=TrainingConfig.REQUEST_TIMEOUT + 60)
                if result:
                    results.append(result)
            except Exception as e:
                ctx = futures[future]
                print(f"错误: 标记 {ctx.marking.id} 处理超时或失败: {e}")
                failed_contexts.append((ctx, str(e)))

    if show_progress:
        print(f"分析完成: {len(results)} 成功, {len(failed_contexts)} 失败")
        if failed_contexts:
            print("失败的标记:")
            for ctx, error in failed_contexts[:5]:  # 只显示前5个
                print(f"  - {ctx.marking.episode} @ {ctx.marking.timestamp}: {error}")

    return results


def validate_api_key() -> bool:
    """验证API密钥是否有效

    Returns:
        是否有效
    """
    if TrainingConfig.GEMINI_API_KEY == "your-api-key":
        print("错误: 未设置GEMINI_API_KEY环境变量")
        return False
    return True


if __name__ == "__main__":
    # 测试代码
    from .config import PROJECTS, create_directories, get_prompt_template
    from .read_excel import load_project_markings, validate_markings, get_unique_episodes
    from .extract_context import prepare_episode_data, extract_contexts_for_markings, filter_valid_contexts

    create_directories()

    if not validate_api_key():
        print("请先设置 GEMINI_API_KEY 环境变量")
    else:
        if PROJECTS:
            project = PROJECTS[0]
            print(f"测试Gemini分析: {project.name}")

            try:
                # 读取标记数据
                markings = load_project_markings(project)
                valid_markings = validate_markings(markings, project)

                if valid_markings:
                    # 获取第一个有标记的集数
                    episode_numbers = sorted(get_unique_episodes(valid_markings))
                    episode_number = episode_numbers[0]

                    # 准备集数数据
                    video_path = project.get_video_path(episode_number)
                    keyframes, asr_segments = prepare_episode_data(
                        video_path, project.name, episode_number
                    )

                    # 获取该集的第一个标记
                    episode_markings = [m for m in valid_markings if m.episode_number == episode_number][:1]

                    # 提取上下文
                    episode_data = {episode_number: (keyframes, asr_segments)}
                    contexts = extract_contexts_for_markings(
                        episode_markings, project.name, episode_data
                    )

                    # 过滤有效上下文
                    valid_contexts = filter_valid_contexts(contexts)

                    if valid_contexts:
                        # 获取prompt模板
                        prompt_template = get_prompt_template()

                        # 分析单个标记
                        result = analyze_marking_with_gemini(valid_contexts[0], prompt_template)

                        print(f"分析结果:")
                        print(f"类型: {result.type}")
                        print(f"分类: {result.category}")
                        print(f"描述: {result.category_description}")
                        print(f"推理: {result.reasoning}")

            except Exception as e:
                print(f"错误: {e}")
                import traceback
                traceback.print_exc()