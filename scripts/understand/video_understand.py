"""
视频理解主入口
整合所有模块，实现完整的视频理解流程

V15.9 更新（2026-03-11）：
- 【重要】ASR 并行提取优化：使用 ThreadPoolExecutor 并行提取多集 ASR
- 【重要】缓存复用优化：片尾检测阶段复用已缓存的 ASR，避免重复转录
- 预期效果：ASR 提取时间从 8分钟 → 2分钟（4个worker），片尾检测瞬间完成
"""
import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 导入子模块
from scripts.understand.understand_skill import understand_skill
from scripts.understand.extract_segments import extract_all_segments, VideoSegment
from scripts.understand.analyze_segment import analyze_all_segments, SegmentAnalysis
from scripts.understand.generate_clips import generate_clips, save_clips, sort_and_filter_clips
from scripts.understand.quality_filter import apply_quality_pipeline

# 导入数据类和工具函数
from scripts.extract_keyframes import load_existing_keyframes, get_keyframe_output_path, extract_keyframes
from scripts.extract_asr import load_asr_from_file, get_asr_output_path, extract_audio, transcribe_audio, get_audio_output_path

# 导入文件名解析工具
from scripts.utils.filename_parser import parse_episode_number
from scripts.utils.subprocess_utils import run_command
from scripts.config import TrainingConfig, TimeoutConfig
import shutil


def _extract_single_episode_asr(episode: int, mp4_file: Path, project_name: str) -> tuple:
    """
    提取单集的 ASR（用于并行处理）

    V15.9: 内部函数，用于 ThreadPoolExecutor 并行调用

    Args:
        episode: 集数
        mp4_file: 视频文件路径
        project_name: 项目名称

    Returns:
        (episode, asr_segments, error_message)
    """
    try:
        # 获取 ASR 缓存路径
        asr_path = get_asr_output_path(project_name, episode)

        # 检查缓存是否已存在
        if os.path.exists(asr_path):
            asr_segments = load_asr_from_file(asr_path, episode=episode)
            if asr_segments:
                return (episode, asr_segments, None)

        # 缓存不存在，开始提取
        # 步骤1: 提取音频
        audio_path = get_audio_output_path(project_name, episode)
        extract_audio(str(mp4_file), audio_path)

        # 步骤2: 转录音频
        asr_segments = transcribe_audio(
            audio_path=audio_path,
            output_path=asr_path,
            model=TrainingConfig.ASR_MODEL,
            language=TrainingConfig.ASR_LANGUAGE
        )

        return (episode, asr_segments, None)

    except Exception as e:
        return (episode, [], str(e))


def extract_asr_parallel(episode_files: Dict[int, Path], project_name: str,
                        max_workers: int = 4, progress_callback=None) -> Dict[int, list]:
    """
    并行提取多集的 ASR

    V15.9: 新增并行 ASR 提取功能
    - 使用 ThreadPoolExecutor 并行处理多集
    - 自动检测缓存，跳过已存在的 ASR
    - 提供进度回调支持

    Args:
        episode_files: {集数: mp4文件路径}
        project_name: 项目名称
        max_workers: 最大并行数（默认4，建议不超过4以避免内存不足）
        progress_callback: 进度回调函数 (episode, status, message)

    Returns:
        {集数: ASR片段列表}
    """
    episode_asr = {}
    total = len(episode_files)

    # 检查哪些集需要提取 ASR
    episodes_to_extract = []
    episodes_cached = []

    for episode, mp4_file in episode_files.items():
        asr_path = get_asr_output_path(project_name, episode)
        if os.path.exists(asr_path):
            episodes_cached.append(episode)
        else:
            episodes_to_extract.append(episode)

    if episodes_cached:
        print(f"  📦 已缓存 ASR: {len(episodes_cached)} 集")
        # 加载缓存的 ASR
        for episode in episodes_cached:
            asr_path = get_asr_output_path(project_name, episode)
            asr_segments = load_asr_from_file(asr_path, episode=episode)
            episode_asr[episode] = asr_segments

    if not episodes_to_extract:
        print(f"  ✅ 所有 ASR 均已缓存，无需提取")
        return episode_asr

    print(f"  🔄 需要提取 ASR: {len(episodes_to_extract)} 集")
    print(f"  ⚡ 并行 worker 数: {max_workers}")

    # 过滤出需要提取的文件
    files_to_extract = {ep: episode_files[ep] for ep in episodes_to_extract}

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_extract_single_episode_asr, ep, mp4, project_name): ep
            for ep, mp4 in files_to_extract.items()
        }

        completed = 0
        for future in as_completed(futures):
            ep = futures[future]
            try:
                episode, asr_segments, error = future.result()
                completed += 1

                if error:
                    print(f"  ❌ [{completed}/{len(episodes_to_extract)}] 第{episode}集 ASR 提取失败: {error}")
                    episode_asr[episode] = []
                else:
                    # V15.4修复: 确保每个 ASRSegment 都有正确的 episode 字段
                    for seg in asr_segments:
                        seg.episode = episode
                    episode_asr[episode] = asr_segments
                    print(f"  ✅ [{completed}/{len(episodes_to_extract)}] 第{episode}集 ASR 完成 ({len(asr_segments)}片段)")

                if progress_callback:
                    status = "error" if error else "success"
                    msg = error if error else f"完成 ({len(asr_segments)}片段)"
                    progress_callback(episode, status, msg)

            except Exception as e:
                completed += 1
                print(f"  ❌ [{completed}/{len(episodes_to_extract)}] 第{ep}集 ASR 提取异常: {e}")
                episode_asr[ep] = []

    elapsed = time.time() - start_time
    print(f"  ⏱️  ASR 并行提取完成，耗时: {elapsed:.1f}秒")

    return episode_asr


def load_episode_data(project_path: str, auto_extract: bool = True,
                     parallel_asr: bool = True, max_asr_workers: int = 4) -> tuple:
    """
    加载项目数据（支持多种文件命名格式，支持自动提取）

    V15.9 更新：
    - 新增 parallel_asr 参数，支持 ASR 并行提取
    - 新增 max_asr_workers 参数，控制并行度

    Args:
        project_path: 项目路径
        auto_extract: 是否自动提取缺失的关键帧和ASR（默认True）
        parallel_asr: 是否并行提取 ASR（默认True）
        max_asr_workers: ASR 并行提取的最大 worker 数（默认4）

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

    # V15.9: 收集所有需要处理的视频文件
    episode_video_files = {}

    for mp4_file in mp4_files:
        # 使用增强的解析函数提取集数
        episode = parse_episode_number(mp4_file.name)

        if episode is None:
            print(f"⚠️  警告: 无法解析文件名 {mp4_file.name}，跳过")
            continue

        episode_video_files[episode] = mp4_file

        # ===== 自动检查并提取关键帧 =====
        keyframe_path = get_keyframe_output_path(video_dir.name, episode)

        # 加载现有关键帧（如果存在且非空）
        keyframes = None
        if os.path.exists(keyframe_path):
            keyframes = load_existing_keyframes(keyframe_path)
            if keyframes:
                print(f"  第{episode}集: 关键帧已加载 ({len(keyframes)}帧)")

        # 如果没有关键帧（或目录为空），则提取
        if not keyframes:
            if auto_extract:
                print(f"  ⚠️  第{episode}集关键帧不存在或为空，开始自动提取...")

                # V14.2: 检测视频实际帧率
                try:
                    cmd = [
                        'ffprobe',
                        '-v', 'error',
                        '-select_streams', 'v:0',
                        '-show_entries', 'stream=r_frame_rate',
                        '-of', 'default=noprint_wrappers=1:nokey=1',
                        str(mp4_file)
                    ]
                    result = run_command(
                        cmd,
                        timeout=TimeoutConfig.FFPROBE_QUICK,
                        retries=2,
                        error_msg="ffprobe获取帧率超时"
                    )
                    fps_str = result.stdout.strip() if result else ""

                    # 解析帧率
                    if '/' in fps_str:
                        num, den = fps_str.split('/')
                        actual_fps = float(num) / float(den)
                    else:
                        actual_fps = float(fps_str)

                    print(f"     检测到视频帧率: {actual_fps:.2f} FPS")

                    # V14.2: 根据实际帧率调整提取参数
                    # 对于高帧率视频，需要更密集的采样
                    if actual_fps >= 50:
                        extract_fps = 2.0  # 50fps视频，每秒2帧
                        print(f"     提取参数: fps={extract_fps} (高帧率视频，增加采样密度)")
                    elif actual_fps <= 25:
                        extract_fps = 0.5  # 25fps视频，每秒0.5帧（减少采样）
                        print(f"     提取参数: fps={extract_fps} (低帧率视频，减少采样)")
                    else:
                        extract_fps = 1.0  # 30fps视频，每秒1帧（标准）
                        print(f"     提取参数: fps={extract_fps} (标准帧率视频)")

                except (ValueError, AttributeError) as e:
                    print(f"     ⚠️  无法检测帧率，使用默认值: 1.0 fps")
                    extract_fps = 1.0

                try:
                    keyframes = extract_keyframes(
                        video_path=str(mp4_file),
                        output_dir=keyframe_path,
                        fps=extract_fps,  # V14.2: 使用调整后的帧率
                        quality=TrainingConfig.KEYFRAME_QUALITY
                    )
                    print(f"  ✅ 第{episode}集关键帧提取完成 ({len(keyframes)}帧)")
                except Exception as e:
                    print(f"  ❌ 第{episode}集关键帧提取失败: {e}")
                    keyframes = []
            else:
                keyframes = []

        episode_keyframes[episode] = keyframes

        # ===== 获取视频时长 =====
        # V15.9: 将时长获取移到前面，因为 ASR 并行提取时也需要
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(mp4_file)
            ]
            result = run_command(
                cmd,
                timeout=TimeoutConfig.FFPROBE_METADATA,
                retries=2,
                error_msg="ffprobe获取视频时长超时"
            )
            if result is not None and result.returncode == 0:
                duration = float(result.stdout.strip())
                episode_durations[episode] = int(duration)  # 使用ffprobe获取的准确时长
            else:
                raise ValueError("ffprobe返回失败或超时")
        except (ValueError, AttributeError) as e:
            # ffprobe失败时，回退到关键帧估算
            if episode_keyframes.get(episode):
                max_ms = max(kf.timestamp_ms for kf in episode_keyframes[episode])
                episode_durations[episode] = (max_ms // 1000) + 10
            else:
                episode_durations[episode] = 0
            print(f"  ⚠️  第{episode}集: ffprobe失败，使用关键帧估算")

    # ===== V15.9: ASR 并行提取 =====
    if auto_extract:
        print(f"\n{'='*50}")
        print(f"ASR 提取阶段 ({'并行' if parallel_asr else '串行'})")
        print(f"{'='*50}")

        if parallel_asr:
            # 并行提取 ASR
            episode_asr = extract_asr_parallel(
                episode_video_files,
                video_dir.name,
                max_workers=max_asr_workers
            )
        else:
            # 串行提取 ASR（保持向后兼容）
            for episode, mp4_file in episode_video_files.items():
                asr_path = get_asr_output_path(video_dir.name, episode)

                if os.path.exists(asr_path):
                    # ASR已存在，直接加载
                    asr_segments = load_asr_from_file(asr_path, episode=episode)
                    if asr_segments:
                        print(f"  第{episode}集: ASR已加载 ({len(asr_segments)}片段)")
                else:
                    # ASR不存在，自动提取
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

                # V15.4修复: 确保每个ASRSegment都有正确的episode字段
                for seg in asr_segments:
                    seg.episode = episode

                episode_asr[episode] = asr_segments

    return episode_keyframes, episode_asr, episode_durations


def detect_project_endings_in_understand_phase(
    video_dir: str,
    episode_asr: dict,
    verbose: bool = True
) -> dict:
    """在video_understand阶段检测项目中所有视频的片尾

    使用复杂算法，检测结果保存到缓存供render阶段使用

    Args:
        video_dir: 视频目录路径
        episode_asr: 按集数分组的ASR数据 {集数: [ASR片段列表]}
        verbose: 是否打印详细信息

    Returns:
        片尾检测结果字典 {集数: {has_ending, duration, effective_duration}}
    """
    from pathlib import Path
    import json
    from scripts.detect_ending_credits import EndingCreditsDetector

    video_dir_path = Path(video_dir)
    project_name = video_dir_path.name

    # 输出目录 (与render_clips保持一致: data/ending_credits/)
    output_dir = Path("data/ending_credits")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{project_name}_ending_credits.json"

    # 检查缓存是否存在
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            cached = json.load(f)
            # 兼容新旧两种格式
            if 'episodes' in cached:
                # 新格式: {"project": "...", "episodes": [...]}
                results = {ep['episode']: ep for ep in cached['episodes']}
            else:
                # 旧格式: {episode: {...}}
                results = cached
            if verbose:
                print(f"  📦 使用已缓存的片尾检测结果: {len(results)}集")
            return results

    # 获取所有视频文件
    video_files = sorted(video_dir_path.glob("*.mp4"))
    if not video_files:
        return {}

    # 创建检测器
    detector = EndingCreditsDetector()

    # 检测每集片尾
    results = {}
    for video_path in video_files:
        # 提取集数
        filename = video_path.stem
        episode = None
        for part in filename.split('-'):
            if part.isdigit():
                episode = int(part)
                break
        if episode is None:
            continue

        if verbose:
            print(f"  检测第{episode}集片尾...")

        # 获取该集的ASR数据
        asr_segments = episode_asr.get(episode, [])

        # 调用复杂算法检测
        result = detector.detect_video_ending(
            video_path=str(video_path),
            episode=episode,
            asr_segments=asr_segments,
            use_complex_method=True
        )

        results[episode] = {
            'has_ending': result.ending_info.has_ending,
            'duration': result.ending_info.duration,
            'effective_duration': result.effective_duration,
            'confidence': result.ending_info.confidence,
            'method': result.ending_info.method
        }

    # 保存到缓存（使用与 render_clips.py 一致的格式）
    cache_data = {
        'project': project_name,
        'episodes': [
            {
                'episode': ep,
                **ep_info
            }
            for ep, ep_info in results.items()
        ]
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

    if verbose:
        print(f"  💾 片尾检测结果已保存到: {output_file}")

    return results


def cleanup_project_cache(project_name: str, min_age_hours: float = 3.0) -> dict:
    """清理项目的中间缓存文件（仅清理超过指定小时数的缓存）

    项目分析完成后，清理关键帧、音频、ASR等中间产物。
    为了方便后续测试，只清理超过 min_age_hours 小时的缓存文件。

    Args:
        project_name: 项目名称
        min_age_hours: 最小缓存保留时长（小时），默认3.0小时

    Returns:
        清理结果统计，包含跳过的文件数量
    """
    import time

    cache_dir = TrainingConfig.CACHE_DIR
    cutoff_time = time.time() - (min_age_hours * 3600)  # 计算截止时间戳

    result = {
        "keyframes_cleaned": 0,
        "audio_cleaned": 0,
        "asr_cleaned": 0,
        "skipped": 0,  # 新增：跳过的文件数
        "total_size_freed_mb": 0,
    }

    def clean_directory_with_age_check(dir_path: Path, cache_type: str) -> tuple:
        """清理目录中的文件，只删除超过指定时间的文件

        Args:
            dir_path: 目录路径
            cache_type: 缓存类型（用于日志）

        Returns:
            (清理的文件数, 跳过的文件数, 释放的空间MB)
        """
        if not dir_path.exists():
            return 0, 0, 0.0

        cleaned = 0
        skipped = 0
        size_freed = 0.0

        # 收集所有文件
        all_files = list(dir_path.rglob("*"))
        if not all_files:
            # 空目录，直接删除
            shutil.rmtree(dir_path)
            return 0, 0, 0.0

        for file_path in all_files:
            if not file_path.is_file():
                continue

            # 检查文件修改时间
            file_mtime = file_path.stat().st_mtime
            if file_mtime >= cutoff_time:
                # 文件还在保留期内，跳过
                skipped += 1
                continue

            # 文件超过保留期，删除
            size_freed += file_path.stat().st_size / (1024 * 1024)
            file_path.unlink()
            cleaned += 1

        # 如果所有文件都被删除或跳过，清理空目录
        if cleaned > 0:
            # 尝试删除空目录
            try:
                # 检查是否还有文件
                remaining = list(dir_path.rglob("*"))
                if not any(f.is_file() for f in remaining):
                    shutil.rmtree(dir_path)
            except Exception:
                pass

        return cleaned, skipped, size_freed

    # 清理关键帧缓存
    keyframes_dir = cache_dir / "keyframes" / project_name
    cleaned, skipped, size = clean_directory_with_age_check(keyframes_dir, "关键帧")
    result["keyframes_cleaned"] = 1 if cleaned > 0 else 0
    result["skipped"] += skipped
    result["total_size_freed_mb"] += size

    # 清理音频缓存
    audio_dir = cache_dir / "audio" / project_name
    cleaned, skipped, size = clean_directory_with_age_check(audio_dir, "音频")
    result["audio_cleaned"] = 1 if cleaned > 0 else 0
    result["skipped"] += skipped
    result["total_size_freed_mb"] += size

    # 清理ASR缓存
    asr_dir = cache_dir / "asr" / project_name
    cleaned, skipped, size = clean_directory_with_age_check(asr_dir, "ASR")
    result["asr_cleaned"] = 1 if cleaned > 0 else 0
    result["skipped"] += skipped
    result["total_size_freed_mb"] += size

    return result


def video_understand(
    project_path: str,
    skill_file: str = None,
    force_skill: bool = False,
    output_dir: str = None,
    no_cleanup: bool = False
) -> Dict[str, Any]:
    """视频理解主函数

    Args:
        project_path: 项目路径（包含视频文件）
        skill_file: 技能文件路径
        force_skill: 是否强制重新生成技能框架
        output_dir: 输出目录
        no_cleanup: 是否跳过清理中间缓存

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
        skill_file = "data/skills/ai-drama-clipping-thoughts-v0.1.md"
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

    # 2.5 片尾检测（使用复杂算法）
    print("[2.5/6] 片尾检测（复杂算法）...")
    ending_results = detect_project_endings_in_understand_phase(
        video_dir=project_path,
        episode_asr=episode_asr,
        verbose=True
    )
    print(f"片尾检测完成: {len(ending_results)}集\n")
    
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
    # V17.2: 修复第1集第0秒重复高光点问题
    print("\n[5.5/6] 添加固定的开篇高光点...")

    # 检查第1集第0秒附近是否已有开篇高光
    episode1_has_opening = any(
        h.episode == 1 and h.highlight_type == "开篇高光" and h.highlight_timestamp <= 5
        for h in highlights
    )

    if not episode1_has_opening:
        print("  第1集没有开篇高光,自动添加固定开篇高光点(第1集0秒)")

        # V17.2修复: 先移除第1集第0秒附近的AI检测高光点（避免重复）
        opening_conflict_highlights = [
            h for h in highlights
            if h.episode == 1 and h.highlight_timestamp <= 5
        ]
        if opening_conflict_highlights:
            print(f"  ⚠️  发现第1集开头有{len(opening_conflict_highlights)}个AI检测高光点，将被固定开篇高光替换")
            for h in opening_conflict_highlights:
                print(f"     - 移除: {h.highlight_type} @ {h.highlight_timestamp}s (置信度: {h.highlight_confidence})")
                highlights.remove(h)
                analyses.remove(h)

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
    # V15.2: 传入视频路径和帧率用于智能切割
    # V13时间戳修复: 传递按集分组的ASR数据，而不是平铺的列表
    print("\n生成剪辑组合...")

    # V13时间戳修复: 直接传递按集分组的episode_asr字典
    # 不再需要收集为平铺列表，保留集数信息用于精确匹配
    print(f"已准备 {len(episode_asr)} 集的ASR数据，用于时间戳精度优化")

    # V15.2: 获取第一个视频的路径和帧率（用于智能切割）
    video_dir = Path(project_path)
    mp4_files = sorted(video_dir.glob("*.mp4"))
    video_path = str(mp4_files[0]) if mp4_files else None

    # 获取视频帧率
    video_fps = 30.0
    if video_path:
        try:
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                   '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', video_path]
            result = run_command(
                cmd,
                timeout=TimeoutConfig.FFPROBE_QUICK,
                retries=1,
                error_msg="ffprobe获取视频帧率超时"
            )
            fps_str = result.stdout.strip() if result else ""
            if '/' in fps_str:
                num, denom = fps_str.split('/')
                video_fps = float(num) / float(denom)
            else:
                video_fps = float(fps_str)
            print(f"视频帧率: {video_fps:.2f}fps")
        except Exception as e:
            print(f"⚠️ 无法获取视频帧率，使用默认值: {video_fps}fps")

    clips = generate_clips(
        analyses,
        episode_durations,
        episode_asr=episode_asr,  # V13时间戳修复: 传入按集分组的ASR字典
        enable_timestamp_optimization=True,  # V13: 启用时间戳优化
        video_path=video_path,  # V15.2: 传入视频路径
        video_fps=video_fps  # V15.2: 传入视频帧率
    )

    # 6. V17: 剪辑组合排序与智能筛选（Top N 精选）
    print("\n[6/7] 剪辑组合排序与智能筛选...")
    clips = sort_and_filter_clips(
        highlights=highlights,
        hooks=hooks,
        episode_durations=episode_durations,
        max_output=20,
        min_output=10,
        top_highlights=10,
        top_hooks=10,
        max_same_type=2,
        max_same_episode=2
    )

    # 7. 保存结果
    print("\n保存结果...")
    if output_dir is None:
        output_dir = f"data/analysis/{project_name}"

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

    # 项目分析完成后清理中间缓存
    if not no_cleanup:
        print(f"\n清理项目 {project_name} 的中间缓存（仅清理超过3小时的缓存）...")
        cleanup_result = cleanup_project_cache(project_name)
        print(f"  已清理: 关键帧={cleanup_result['keyframes_cleaned']}, "
              f"音频={cleanup_result['audio_cleaned']}, "
              f"ASR={cleanup_result['asr_cleaned']}")
        if cleanup_result['skipped'] > 0:
            print(f"  ⏭️  跳过（未到3小时）: {cleanup_result['skipped']} 个文件")
        print(f"  释放空间: {cleanup_result['total_size_freed_mb']:.2f} MB")

    return result


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='视频理解 - 分析短剧并生成剪辑方案'
    )
    parser.add_argument('project_path', help='项目路径（包含视频文件）')
    parser.add_argument('skill_file', nargs='?', help='技能文件路径（可选）')
    parser.add_argument('--force-skill', action='store_true', help='强制重新生成技能框架')
    parser.add_argument('--output-dir', type=str, help='输出目录')
    parser.add_argument('--no-cleanup', action='store_true', help='跳过清理中间缓存（关键帧、音频、ASR）')

    args = parser.parse_args()

    video_understand(
        args.project_path,
        args.skill_file,
        args.force_skill,
        args.output_dir,
        args.no_cleanup
    )


if __name__ == "__main__":
    main()
