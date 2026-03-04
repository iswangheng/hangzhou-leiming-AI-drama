"""
视频理解主入口
整合所有模块，实现完整的视频理解流程
"""
import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# 导入子模块
from scripts.understand.understand_skill import understand_skill
from scripts.understand.extract_segments import extract_all_segments, VideoSegment
from scripts.understand.analyze_segment import analyze_all_segments, SegmentAnalysis
from scripts.understand.generate_clips import generate_clips, save_clips
from scripts.understand.quality_filter import apply_quality_pipeline

# 导入数据类和工具函数
from scripts.extract_keyframes import load_existing_keyframes, get_keyframe_output_path, extract_keyframes
from scripts.extract_asr import load_asr_from_file, get_asr_output_path, extract_audio, transcribe_audio, get_audio_output_path

# 导入文件名解析工具
from scripts.utils.filename_parser import parse_episode_number


def load_episode_data(project_path: str, auto_extract: bool = True) -> tuple:
    """
    加载项目数据（支持多种文件命名格式，支持自动提取）

    Args:
        project_path: 项目路径
        auto_extract: 是否自动提取缺失的关键帧和ASR（默认True）

    Returns:
        (episode_keyframes, episode_asr, episode_durations)
    """
    from scripts.config import TrainingConfig

    video_dir = Path(project_path)

    episode_keyframes = {}
    episode_asr = {}
    episode_durations = {}

    # 查找所有mp4文件
    mp4_files = sorted(video_dir.glob("*.mp4"))

    for mp4_file in mp4_files:
        # 使用增强的解析函数提取集数
        episode = parse_episode_number(mp4_file.name)

        if episode is None:
            print(f"⚠️  警告: 无法解析文件名 {mp4_file.name}，跳过")
            continue

        # ===== 自动检查并提取关键帧 =====
        keyframe_path = get_keyframe_output_path(video_dir.name, episode)

        if os.path.exists(keyframe_path):
            # 关键帧已存在，直接加载
            keyframes = load_existing_keyframes(keyframe_path)
            if keyframes:
                print(f"  第{episode}集: 关键帧已加载 ({len(keyframes)}帧)")
        else:
            # 关键帧不存在，自动提取
            if auto_extract:
                print(f"  ⚠️  第{episode}集关键帧不存在，开始自动提取...")
                print(f"     提取参数: fps=1.0 (每秒1帧)")
                try:
                    keyframes = extract_keyframes(
                        video_path=str(mp4_file),
                        output_dir=keyframe_path,
                        fps=1.0,  # 每秒1帧
                        quality=TrainingConfig.KEYFRAME_QUALITY
                    )
                    print(f"  ✅ 第{episode}集关键帧提取完成 ({len(keyframes)}帧)")
                except Exception as e:
                    print(f"  ❌ 第{episode}集关键帧提取失败: {e}")
                    keyframes = []
            else:
                keyframes = []

        episode_keyframes[episode] = keyframes

        # ===== 自动检查并提取ASR =====
        asr_path = get_asr_output_path(video_dir.name, episode)

        if os.path.exists(asr_path):
            # ASR已存在，直接加载
            asr_segments = load_asr_from_file(asr_path)
            if asr_segments:
                print(f"  第{episode}集: ASR已加载 ({len(asr_segments)}片段)")
        else:
            # ASR不存在，自动提取
            if auto_extract:
                print(f"  ⚠️  第{episode}集ASR不存在，开始自动转录...")

                try:
                    # 步骤1: 提取音频
                    audio_path = get_audio_output_path(video_dir.name, episode)
                    print(f"     步骤1/2: 提取音频...")
                    extract_audio(str(mp4_file), audio_path)

                    # 步骤2: 转录音频
                    print(f"     步骤2/2: Whisper转录...")
                    asr_segments = transcribe_audio(
                        audio_path=audio_path,
                        output_path=asr_path,
                        model=TrainingConfig.ASR_MODEL,
                        language=TrainingConfig.ASR_LANGUAGE
                    )
                    print(f"  ✅ 第{episode}集ASR转录完成 ({len(asr_segments)}片段)")
                except Exception as e:
                    print(f"  ❌ 第{episode}集ASR转录失败: {e}")
                    asr_segments = []
            else:
                asr_segments = []

        episode_asr[episode] = asr_segments

        # 获取视频时长（从关键帧估算或用ffprobe）
        if keyframes:
            max_ms = max(kf.timestamp_ms for kf in keyframes)
            episode_durations[episode] = (max_ms // 1000) + 10  # 加10秒缓冲
        else:
            episode_durations[episode] = 0

    return episode_keyframes, episode_asr, episode_durations


def video_understand(
    project_path: str,
    skill_file: str = None,
    force_skill: bool = False,
    output_dir: str = None
) -> Dict[str, Any]:
    """视频理解主函数
    
    Args:
        project_path: 项目路径（包含视频文件）
        skill_file: 技能文件路径
        force_skill: 是否强制重新生成技能框架
        output_dir: 输出目录
        
    Returns:
        理解结果dict
    """
    project_name = Path(project_path).name
    print(f"\n{'='*50}")
    print(f"开始视频理解: {project_name}")
    print(f"{'='*50}\n")

    # 1. 理解技能文件
    print("[1/5] 理解技能文件...")
    if skill_file is None:
        skill_file = "data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.1.md"
    skill_framework = understand_skill(skill_file, force=force_skill)
    print(f"技能框架加载完成\n")

    # 2. 加载项目数据（自动检查并提取缺失的关键帧和ASR）
    print("[2/5] 加载项目数据（自动检查并提取缺失数据）...")
    episode_keyframes, episode_asr, episode_durations = load_episode_data(project_path, auto_extract=True)

    # 过滤掉None值（提取失败的集）
    episode_keyframes = {k: v for k, v in episode_keyframes.items() if v is not None}
    episode_asr = {k: v for k, v in episode_asr.items() if v is not None}

    total_keyframes = sum(len(v) for v in episode_keyframes.values())
    total_asr = sum(len(v) for v in episode_asr.values())
    print(f"\n数据加载完成: {len(episode_keyframes)}集, {total_keyframes}关键帧, {total_asr}ASR片段\n")
    
    # 3. 提取分析片段
    print("[3/5] 提取分析片段...")
    segments = extract_all_segments(
        episode_keyframes,
        episode_asr,
        episode_durations
    )
    print(f"生成了 {len(segments)} 个分析片段\n")

    # 4. 逐段分析
    print("[4/5] 逐段分析（可能需要几分钟）...")
    analyses = analyze_all_segments(segments, skill_framework)

    # 去除完全重复的项（AI可能返回了相同的分析结果）
    unique_analyses = []
    seen = set()

    for analysis in analyses:
        # 创建唯一标识：集数 + 类型 + 时间戳
        if analysis.is_highlight:
            key = (analysis.episode, 'hl', analysis.highlight_timestamp, analysis.highlight_type)
        else:
            key = (analysis.episode, 'hook', analysis.hook_timestamp, analysis.hook_type)

        if key not in seen:
            seen.add(key)
            unique_analyses.append(analysis)

    duplicate_count = len(analyses) - len(unique_analyses)
    if duplicate_count > 0:
        print(f"去除完全重复的项: {len(analyses)} → {len(unique_analyses)} (移除{duplicate_count}个)")

    analyses = unique_analyses

    # 分离高光点和钩子点
    highlights = [a for a in analyses if a.is_highlight]
    hooks = [a for a in analyses if a.is_hook]
    print(f"识别到 {len(highlights)} 个高光点, {len(hooks)} 个钩子点")

    # 5. 质量筛选流程
    print("\n[5/5] 质量筛选...")
    analyses = apply_quality_pipeline(
        analyses,
        episode_durations,
        min_confidence=7.0,  # 测试7.0
        min_distance=10,  # 缩短到10秒
        max_same_type_per_episode=1  # 每集同类型最多1个
    )

    # 重新统计
    highlights = [a for a in analyses if a.is_highlight]
    hooks = [a for a in analyses if a.is_hook]
    print(f"\n筛选后: {len(highlights)} 个高光点, {len(hooks)} 个钩子点")

    # 5.5. 添加固定的开篇高光点(第1集0秒)
    print("\n[5.5/6] 添加固定的开篇高光点...")
    episode1_has_opening = any(
        h.episode == 1 and h.highlight_type == "开篇高光" and h.highlight_timestamp <= 5
        for h in highlights
    )

    if not episode1_has_opening:
        print("  第1集没有开篇高光,自动添加固定开篇高光点(第1集0秒)")
        # 创建一个固定的高光点对象
        from scripts.understand.analyze_segment import SegmentAnalysis
        opening_highlight = SegmentAnalysis(
            episode=1,
            start_time=0,
            end_time=30,  # 分析窗口30秒
            is_highlight=True,
            highlight_timestamp=0.0,  # V13: 浮点数精度
            highlight_type="开篇高光",
            highlight_desc="第1集固定开篇高光点",
            highlight_confidence=10.0,  # 最高置信度
            is_hook=False,
            hook_timestamp=0.0,  # V13: 浮点数精度
            hook_type="",
            hook_desc="",
            hook_confidence=0.0
        )
        analyses.insert(0, opening_highlight)  # 插入到列表开头
        highlights.insert(0, opening_highlight)
        print("  ✅ 已添加开篇高光点")
    else:
        print("  第1集已有开篇高光点,跳过")

    # 6. 生成剪辑组合（V13: 传入ASR数据进行时间戳优化）
    print("\n生成剪辑组合...")

    # 收集所有ASR片段（用于时间戳优化）
    all_asr_segments = []
    for asr_list in episode_asr.values():
        all_asr_segments.extend(asr_list)

    print(f"已收集 {len(all_asr_segments)} 个ASR片段，用于时间戳精度优化")

    clips = generate_clips(
        analyses,
        episode_durations,
        asr_segments=all_asr_segments,  # V13: 传入ASR数据
        enable_timestamp_optimization=True  # V13: 启用时间戳优化
    )

    # 7. 保存结果
    print("\n保存结果...")
    if output_dir is None:
        output_dir = f"data/hangzhou-leiming/analysis/{project_name}"

    os.makedirs(output_dir, exist_ok=True)
    result_path = os.path.join(output_dir, "result.json")

    # 构建结果数据结构（V13: 保留毫秒精度）
    def format_timestamp(ts):
        """格式化时间戳：整数值返回整数，浮点数保留3位小数"""
        if isinstance(ts, int):
            return ts
        if isinstance(ts, float) and ts.is_integer():
            return int(ts)
        return round(ts, 3)

    result = {
        "projectName": project_name,
        "episodeDurations": {ep: duration for ep, duration in episode_durations.items()},  # V13.1: 保存每集时长
        "highlights": [
            {
                "timestamp": format_timestamp(a.highlight_timestamp),  # V13: 保留精度
                "episode": a.episode,
                "type": a.highlight_type,
                "confidence": a.highlight_confidence,
                "description": a.highlight_desc
            }
            for a in highlights
        ],
        "hooks": [
            {
                "timestamp": format_timestamp(a.hook_timestamp),  # V13: 保留精度
                "episode": a.episode,
                "type": a.hook_type,
                "confidence": a.hook_confidence,
                "description": a.hook_desc
            }
            for a in hooks
        ],
        "clips": [c.to_dict() for c in clips],
        "statistics": {
            "totalHighlights": len(highlights),
            "totalHooks": len(hooks),
            "totalClips": len(clips),
            "averageConfidence": (
                sum(a.highlight_confidence for a in highlights) +
                sum(a.hook_confidence for a in hooks)
            ) / (len(highlights) + len(hooks)) if (len(highlights) + len(hooks)) > 0 else 0
        }
    }
    
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: {result_path}")
    print(f"高光点: {len(highlights)}")
    print(f"钩子点: {len(hooks)}")
    print(f"剪辑组合: {len(clips)}")
    
    return result


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python -m scripts.understand.video_understand <项目路径> [技能文件]")
        print("示例: python -m scripts.understand.video_understand ./漫剧素材/百里将就")
        sys.exit(1)
    
    project_path = sys.argv[1]
    skill_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    video_understand(project_path, skill_file)


if __name__ == "__main__":
    main()
