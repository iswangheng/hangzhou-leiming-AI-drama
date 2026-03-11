"""
AI训练主脚本 - 杭州雷鸣短剧剪辑技能训练
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Optional

from .config import (
    PROJECTS, TrainingConfig, create_directories, get_prompt_template
)
from .data_models import MarkingContext, AnalysisResult
from .read_excel import load_project_markings, validate_markings, get_unique_episodes
from .extract_context import (
    prepare_episode_data, extract_contexts_for_markings, filter_valid_contexts
)
from .analyze_gemini import analyze_markings_batch, validate_api_key
from .merge_skills import load_latest_skill, merge_skills, generate_skill_file
from .config import TrainingConfig
import shutil


def save_progress(progress: dict):
    """保存训练进度

    Args:
        progress: 进度数据
    """
    os.makedirs(TrainingConfig.CACHE_DIR, exist_ok=True)
    progress_file = TrainingConfig.PROGRESS_FILE
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_progress() -> Optional[dict]:
    """加载训练进度

    Returns:
        进度数据，如果不存在则返回None
    """
    progress_file = TrainingConfig.PROGRESS_FILE
    if not os.path.exists(progress_file):
        return None

    with open(progress_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def clear_progress():
    """清除训练进度"""
    progress_file = TrainingConfig.PROGRESS_FILE
    if os.path.exists(progress_file):
        os.remove(progress_file)
        print("已清除训练进度")


def cleanup_project_cache(project_name: str, min_age_hours: float = 3.0) -> dict:
    """清理项目的中间缓存文件（仅清理超过指定小时数的缓存）

    项目分析完成后，清理关键帧、音频、ASR等中间产物，
    只保留最终的技能文件。
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

    def clean_directory_with_age_check(dir_path, cache_type: str) -> tuple:
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


def process_project(
    project_config,
    force_reextract: bool = False,
    skip_analysis: bool = False
) -> tuple[List[MarkingContext], List[AnalysisResult]]:
    """处理单个项目

    Args:
        project_config: 项目配置
        force_reextract: 是否强制重新提取
        skip_analysis: 是否跳过AI分析

    Returns:
        (上下文列表, 分析结果列表)
    """
    print(f"\n{'='*60}")
    print(f"开始处理项目: {project_config.name}")
    print(f"{'='*60}")

    # 读取标记数据
    print("1. 读取Excel标记文件...")
    markings = load_project_markings(project_config)
    valid_markings = validate_markings(markings, project_config)

    if not valid_markings:
        print(f"警告: 项目 {project_config.name} 没有有效标记，跳过")
        return [], []

    print(f"   读取了 {len(valid_markings)} 个有效标记")

    # 获取唯一集数
    episode_numbers = sorted(get_unique_episodes(valid_markings))
    print(f"   涉及 {len(episode_numbers)} 集: {episode_numbers}")

    # 准备集数数据
    print("\n2. 准备集数数据（关键帧和ASR）...")
    episode_data = {}
    for episode_number in episode_numbers:
        print(f"   处理第 {episode_number} 集...")
        try:
            video_path = project_config.get_video_path(episode_number)
            keyframes, asr_segments = prepare_episode_data(
                video_path, project_config.name, episode_number, force_reextract
            )
            episode_data[episode_number] = (keyframes, asr_segments)
            print(f"     完成: {len(keyframes)} 帧, {len(asr_segments)} 个ASR片段")
        except Exception as e:
            print(f"     错误: {e}")
            continue

    if not episode_data:
        print(f"错误: 项目 {project_config.name} 没有成功的集数数据")
        return [], []

    # 提取上下文
    print("\n3. 提取标记上下文...")
    contexts = extract_contexts_for_markings(
        valid_markings, project_config.name, episode_data
    )
    print(f"   提取了 {len(contexts)} 个上下文")

    # 过滤有效上下文
    print("\n4. 验证上下文...")
    valid_contexts = filter_valid_contexts(contexts)
    print(f"   有效上下文: {len(valid_contexts)}")

    # AI分析
    results = []
    if not skip_analysis and valid_contexts:
        print("\n5. AI分析标记点...")
        if not validate_api_key():
            print("错误: 未设置GEMINI_API_KEY环境变量，跳过AI分析")
            print("提示: 请设置环境变量 export GEMINI_API_KEY=your-key")
        else:
            prompt_template = get_prompt_template()
            results = analyze_markings_batch(valid_contexts, prompt_template)
            print(f"   分析完成: {len(results)} 个结果")
    else:
        print("\n5. 跳过AI分析")

    return valid_contexts, results


def train(
    projects: Optional[List[str]] = None,
    force_reextract: bool = False,
    skip_analysis: bool = False,
    resume: bool = False,
    no_cleanup: bool = False
):
    """执行训练流程

    Args:
        projects: 要处理的项目列表，如果为None则处理所有项目
        force_reextract: 是否强制重新提取数据
        skip_analysis: 是否跳过AI分析
        resume: 是否从上次中断处继续
        no_cleanup: 项目完成后是否不清理中间缓存
    """
    start_time = time.time()
    print("="*60)
    print("AI训练流程开始")
    print("="*60)

    # 创建目录
    create_directories()

    # 检查API密钥
    if not skip_analysis and not validate_api_key():
        print("错误: 未设置GEMINI_API_KEY环境变量")
        print("请设置环境变量: export GEMINI_API_KEY=your-key")
        print("或者使用 --skip-analysis 跳过AI分析")
        return

    # 确定要处理的项目
    target_projects = []
    if projects:
        for project_name in projects:
            for project in PROJECTS:
                if project.name == project_name:
                    target_projects.append(project)
                    break
            else:
                print(f"警告: 未找到项目 '{project_name}'")
    else:
        target_projects = PROJECTS

    if not target_projects:
        print("错误: 没有要处理的项目")
        return

    print(f"将处理 {len(target_projects)} 个项目")
    for project in target_projects:
        print(f"  - {project.name}")

    # 加载进度
    progress = load_progress() if resume else None
    processed_projects = set(progress.get('processed_projects', [])) if progress else set()

    # 处理项目
    all_contexts = []
    all_results = []
    successfully_processed = []

    for i, project_config in enumerate(target_projects, 1):
        project_name = project_config.name

        if project_name in processed_projects:
            print(f"\n跳过已处理的项目: {project_name}")
            # 这里应该加载已保存的结果，简化起见跳过
            continue

        try:
            contexts, results = process_project(
                project_config, force_reextract, skip_analysis
            )
            all_contexts.extend(contexts)
            all_results.extend(results)
            successfully_processed.append(project_name)

            # 项目分析完成后清理中间缓存
            if not skip_analysis and results and not no_cleanup:
                print(f"\n清理项目 {project_name} 的中间缓存（仅清理超过3小时的缓存）...")
                cleanup_result = cleanup_project_cache(project_name)
                print(f"  已清理: 关键帧={cleanup_result['keyframes_cleaned']}, "
                      f"音频={cleanup_result['audio_cleaned']}, "
                      f"ASR={cleanup_result['asr_cleaned']}")
                if cleanup_result['skipped'] > 0:
                    print(f"  ⏭️  跳过（未到3小时）: {cleanup_result['skipped']} 个文件")
                print(f"  释放空间: {cleanup_result['total_size_freed_mb']:.2f} MB")

            # 保存进度
            progress = {
                'processed_projects': successfully_processed,
                'total_contexts': len(all_contexts),
                'total_results': len(all_results),
                'timestamp': datetime.now().isoformat()
            }
            save_progress(progress)

        except KeyboardInterrupt:
            print(f"\n用户中断，正在保存进度...")
            progress = {
                'processed_projects': successfully_processed,
                'total_contexts': len(all_contexts),
                'total_results': len(all_results),
                'timestamp': datetime.now().isoformat()
            }
            save_progress(progress)
            print("进度已保存，使用 --resume 可继续")
            return

        except Exception as e:
            print(f"错误: 处理项目 {project_name} 时出错: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 合并技能
    if all_results:
        print(f"\n{'='*60}")
        print("合并技能...")
        print(f"{'='*60}")

        old_skill = load_latest_skill()
        new_skill = merge_skills(
            old_skill,
            all_results,
            len(successfully_processed)
        )

        # 生成技能文件
        output_path = generate_skill_file(new_skill)
        print(f"技能文件已生成: {output_path}")

        # 显示统计信息
        print(f"\n统计信息:")
        print(f"  处理项目数: {len(successfully_processed)}")
        print(f"  总上下文数: {len(all_contexts)}")
        print(f"  总分析结果数: {len(all_results)}")
        print(f"  高光类型数: {new_skill.statistics.get('highlight_type_count', 0)}")
        print(f"  钩子类型数: {new_skill.statistics.get('hook_type_count', 0)}")
        print(f"  版本: {new_skill.version}")
    else:
        print("\n没有分析结果，跳过技能合并")

    # 清除进度
    if not resume:
        clear_progress()

    # 显示总耗时
    elapsed_time = time.time() - start_time
    print(f"\n训练完成! 总耗时: {elapsed_time:.1f} 秒")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI短剧剪辑技能训练")
    parser.add_argument(
        '--projects',
        type=str,
        help='要处理的项目列表，用逗号分隔 (如: "项目1,项目2")'
    )
    parser.add_argument(
        '--force-reextract',
        action='store_true',
        help='强制重新提取关键帧和ASR数据'
    )
    parser.add_argument(
        '--skip-analysis',
        action='store_true',
        help='跳过AI分析（仅提取数据）'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='从上次中断处继续'
    )
    parser.add_argument(
        '--clear-progress',
        action='store_true',
        help='清除训练进度'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='项目完成后不清理中间缓存（关键帧、音频、ASR）'
    )

    args = parser.parse_args()

    if args.clear_progress:
        clear_progress()
        print("训练进度已清除")
        return

    # 解析项目列表
    projects = None
    if args.projects:
        projects = [p.strip() for p in args.projects.split(',')]

    try:
        train(
            projects=projects,
            force_reextract=args.force_reextract,
            skip_analysis=args.skip_analysis,
            resume=args.resume,
            no_cleanup=args.no_cleanup
        )
    except KeyboardInterrupt:
        print("\n训练被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"训练失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()