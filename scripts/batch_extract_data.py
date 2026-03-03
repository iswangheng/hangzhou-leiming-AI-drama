"""
批量数据提取脚本 - 提取所有项目的关键帧和ASR

V5.0 完整训练数据准备：14个项目，117集视频
"""
import os
import sys
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from scripts.config import PROJECTS, TrainingConfig
    from scripts.extract_keyframes import extract_keyframes, get_keyframe_output_path
    from scripts.extract_asr import transcribe_audio, get_asr_output_path
    from scripts.read_excel import load_project_markings, validate_markings, get_unique_episodes
except ImportError:
    print("错误: 无法导入必要的模块")
    sys.exit(1)


def get_video_episodes(project_path: str) -> List[int]:
    """获取项目的所有集数

    Args:
        project_path: 项目视频路径

    Returns:
        集数列表
    """
    project_dir = Path(project_path)
    video_files = sorted(project_dir.glob("*.mp4"))

    episodes = []
    for video_file in video_files:
        try:
            episode = int(video_file.stem)
            episodes.append(episode)
        except ValueError:
            # 文件名不是纯数字，尝试其他方式
            continue

    return sorted(episodes)


def check_data_status(project) -> Tuple[List[int], List[int]]:
    """检查项目数据状态

    Args:
        project: 项目配置

    Returns:
        (已提取集数列表, 未提取集数列表)
    """
    # 获取所有视频集数
    video_episodes = get_video_episodes(project.get_absolute_video_path())

    # 检查哪些集已提取
    extracted_keyframes = []
    extracted_asr = []
    not_extracted = []

    for episode in video_episodes:
        keyframe_path = get_keyframe_output_path(project.name, episode)
        asr_path = get_asr_output_path(project.name, episode)

        keyframe_exists = os.path.exists(keyframe_path) and os.path.isdir(keyframe_path)
        asr_exists = os.path.exists(asr_path) and os.path.isfile(asr_path)

        if keyframe_exists and asr_exists:
            extracted_keyframes.append(episode)
            extracted_asr.append(episode)
        else:
            not_extracted.append(episode)

    return extracted_keyframes, not_extracted


def extract_episode_data(project, episode: int) -> Tuple[bool, str]:
    """提取单集数据（关键帧+ASR）

    Args:
        project: 项目配置
        episode: 集数

    Returns:
        (是否成功, 错误信息)
    """
    try:
        # 获取视频路径
        video_path = project.get_video_path(episode)
        keyframe_output = get_keyframe_output_path(project.name, episode)
        asr_output = get_asr_output_path(project.name, episode)

        # 提取关键帧
        if not os.path.exists(keyframe_output) or not os.listdir(keyframe_output):
            extract_keyframes(video_path, keyframe_output, force_reextract=True)

        # 提取ASR
        if not os.path.exists(asr_output):
            transcribe_audio(video_path, asr_output)

        return True, ""

    except Exception as e:
        return False, str(e)


def batch_extract_all(max_workers: int = 1):
    """批量提取所有项目的数据

    Args:
        max_workers: 并发线程数（建议1，避免资源占用过高）
    """
    print("=" * 80)
    print("🚀 批量数据提取 - V5.0 完整训练数据准备")
    print("=" * 80)
    print()

    # 统计所有项目
    total_projects = len(PROJECTS)
    total_episodes = 0
    total_extracted = 0
    total_to_extract = 0

    project_status = []

    # 第一步：检查所有项目状态
    print("【步骤1/3】检查项目数据状态...")
    print()

    for i, project in enumerate(PROJECTS, 1):
        print(f"[{i}/{total_projects}] {project.name}")

        extracted, not_extracted = check_data_status(project)

        total_episodes += len(extracted) + len(not_extracted)
        total_extracted += len(extracted)
        total_to_extract += len(not_extracted)

        project_status.append({
            'project': project,
            'extracted': extracted,
            'not_extracted': not_extracted
        })

        print(f"  已提取: {len(extracted)}集")
        print(f"  待提取: {len(not_extracted)}集")
        print()

    print("=" * 80)
    print(f"总计: {total_projects}个项目, {total_episodes}集视频")
    print(f"  已提取: {total_extracted}集 ({total_extracted/total_episodes*100:.1f}%)")
    print(f"  待提取: {total_to_extract}集 ({total_to_extract/total_episodes*100:.1f}%)")
    print("=" * 80)
    print()

    if total_to_extract == 0:
        print("✅ 所有数据已提取完成，无需重复提取")
        return

    # 第二步：批量提取数据
    print(f"【步骤2/3】开始批量提取 {total_to_extract} 集数据...")
    print(f"配置: 并发线程数={max_workers}, FPS={TrainingConfig.KEYFRAME_FPS}")
    print()

    completed = 0
    failed_episodes = []

    for project_info in project_status:
        project = project_info['project']
        not_extracted = project_info['not_extracted']

        if not not_extracted:
            continue

        print(f"处理项目: {project.name} ({len(not_extracted)}集)")

        for episode in not_extracted:
            print(f"  [{completed+1}/{total_to_extract}] 第{episode}集...", end=" ")

            success, error = extract_episode_data(project, episode)

            if success:
                print("✓")
                completed += 1
            else:
                print(f"✗ 失败: {error}")
                failed_episodes.append((project.name, episode, error))

        print()

    # 第三步：生成报告
    print()
    print("=" * 80)
    print(f"【步骤3/3】提取完成")
    print("=" * 80)
    print(f"成功: {completed}/{total_to_extract}集")
    print(f"失败: {len(failed_episodes)}集")

    if failed_episodes:
        print()
        print("失败详情:")
        for project_name, episode, error in failed_episodes:
            print(f"  {project_name} 第{episode}集: {error}")

    print()
    print("=" * 80)
    print(f"📊 最终统计:")
    print(f"  总项目数: {total_projects}")
    print(f"  总集数: {total_episodes}")
    print(f"  已提取: {total_extracted + completed}集")
    print(f"  成功率: {(completed/total_to_extract*100):.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="批量提取所有项目数据")
    parser.add_argument("--workers", type=int, default=1,
                       help="并发线程数（默认1，建议不要太高）")
    parser.add_argument("--force", action="store_true",
                       help="强制重新提取所有数据（包括已提取的）")

    args = parser.parse_args()

    # 开始批量提取
    batch_extract_all(max_workers=args.workers)

    print("\n✅ 数据提取完成！现在可以运行训练了：")
    print("   python -m scripts.train")
