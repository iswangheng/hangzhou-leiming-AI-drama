"""
上下文提取模块 - 为标记点提取关键帧和ASR上下文
"""
from typing import List
import os

from .data_models import Marking, MarkingContext, KeyFrame, ASRSegment
from .config import TrainingConfig
from .extract_keyframes import extract_keyframes, get_keyframe_output_path
from .extract_asr import transcribe_audio, extract_audio, get_audio_output_path, get_asr_output_path


def extract_marking_context(
    marking: Marking,
    project_name: str,
    keyframes: List[KeyFrame],
    asr_segments: List[ASRSegment],
    context_seconds: float = TrainingConfig.CONTEXT_SECONDS
) -> MarkingContext:
    """提取标记点上下文

    高光点：从标记时间往后 context_seconds 秒
    钩子点：从标记时间往前 context_seconds 秒

    Args:
        marking: 标记数据
        project_name: 项目名称
        keyframes: 全集关键帧列表
        asr_segments: 全集ASR片段列表
        context_seconds: 上下文时间长度（秒）

    Returns:
        标记上下文对象
    """
    seconds = marking.seconds

    if marking.type == "高光点":
        # 高光点：往后找
        start_time = seconds
        end_time = seconds + context_seconds
    else:
        # 钩子点：往前找
        start_time = max(0, seconds - context_seconds)
        end_time = seconds

    # 筛选时间范围内的关键帧
    relevant_keyframes = [
        kf for kf in keyframes
        if start_time <= (kf.timestamp_ms / 1000) <= end_time
    ]

    # 筛选时间范围内的 ASR 片段
    relevant_asr = [
        seg for seg in asr_segments
        if seg.start < end_time and seg.end > start_time
    ]

    # 合并 ASR 文本
    asr_text = ' '.join(seg.text for seg in relevant_asr)

    return MarkingContext(
        project_name=project_name,
        marking=marking,
        keyframes=relevant_keyframes,
        asr_segments=relevant_asr,
        asr_text=asr_text
    )


def prepare_episode_data(
    video_path: str,
    project_name: str,
    episode_number: int,
    force_reextract: bool = False
) -> tuple[List[KeyFrame], List[ASRSegment]]:
    """准备集数的训练数据（关键帧和ASR）

    Args:
        video_path: 视频文件路径
        project_name: 项目名称
        episode_number: 集数编号
        force_reextract: 是否强制重新提取

    Returns:
        (关键帧列表, ASR片段列表)
    """
    # 提取关键帧
    keyframe_dir = get_keyframe_output_path(project_name, episode_number)
    keyframes = extract_keyframes(video_path, keyframe_dir, force_reextract=force_reextract)

    # 提取音频
    audio_path = get_audio_output_path(project_name, episode_number)
    if not os.path.exists(audio_path) or force_reextract:
        extract_audio(video_path, audio_path)

    # 转录音频
    asr_path = get_asr_output_path(project_name, episode_number)
    asr_segments = transcribe_audio(audio_path, asr_path, force_retranscribe=force_reextract)

    return keyframes, asr_segments


def extract_contexts_for_markings(
    markings: List[Marking],
    project_name: str,
    episode_data: dict[int, tuple[List[KeyFrame], List[ASRSegment]]],
    context_seconds: float = TrainingConfig.CONTEXT_SECONDS
) -> List[MarkingContext]:
    """为多个标记提取上下文

    Args:
        markings: 标记列表
        project_name: 项目名称
        episode_data: 集数数据映射 {episode_number: (keyframes, asr_segments)}
        context_seconds: 上下文时间长度

    Returns:
        标记上下文列表
    """
    contexts = []

    for marking in markings:
        episode_number = marking.episode_number

        # 获取该集的数据
        if episode_number not in episode_data:
            print(f"警告: 第{episode_number}集的数据不可用，跳过标记 {marking.id}")
            continue

        keyframes, asr_segments = episode_data[episode_number]

        # 提取上下文
        context = extract_marking_context(
            marking, project_name, keyframes, asr_segments, context_seconds
        )
        contexts.append(context)

    return contexts


def validate_context(context: MarkingContext) -> bool:
    """验证上下文数据是否有效

    Args:
        context: 标记上下文

    Returns:
        是否有效
    """
    # 检查是否有关键帧
    if not context.keyframes:
        print(f"警告: 标记 {context.marking.id} 没有关键帧")
        return False

    # 检查关键帧文件是否存在
    for keyframe in context.keyframes[:5]:  # 只检查前5个
        if not os.path.exists(keyframe.frame_path):
            print(f"警告: 关键帧文件不存在: {keyframe.frame_path}")
            return False

    return True


def filter_valid_contexts(contexts: List[MarkingContext]) -> List[MarkingContext]:
    """过滤出有效的上下文

    Args:
        contexts: 上下文列表

    Returns:
        有效的上下文列表
    """
    valid_contexts = [ctx for ctx in contexts if validate_context(ctx)]

    if len(valid_contexts) < len(contexts):
        print(f"过滤掉了 {len(contexts) - len(valid_contexts)} 个无效上下文")

    return valid_contexts


if __name__ == "__main__":
    # 测试代码
    from .config import PROJECTS, create_directories
    from .read_excel import load_project_markings, validate_markings, get_unique_episodes

    create_directories()

    if PROJECTS:
        project = PROJECTS[0]
        print(f"测试提取标记上下文: {project.name}")

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

                # 获取该集的标记
                episode_markings = [m for m in valid_markings if m.episode_number == episode_number]

                # 提取上下文
                episode_data = {episode_number: (keyframes, asr_segments)}
                contexts = extract_contexts_for_markings(
                    episode_markings, project.name, episode_data
                )

                # 过滤有效上下文
                valid_contexts = filter_valid_contexts(contexts)

                print(f"提取了 {len(valid_contexts)} 个有效上下文")

                # 显示第一个上下文的信息
                if valid_contexts:
                    ctx = valid_contexts[0]
                    print(f"标记: {ctx.marking.episode} @ {ctx.marking.timestamp}")
                    print(f"类型: {ctx.marking.type}")
                    print(f"关键帧数: {len(ctx.keyframes)}")
                    print(f"ASR片段数: {len(ctx.asr_segments)}")
                    print(f"ASR文本: {ctx.asr_text[:100]}..." if len(ctx.asr_text) > 100 else f"ASR文本: {ctx.asr_text}")

        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()