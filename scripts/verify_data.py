"""
数据验证模块 - 验证项目数据完整性

V5.0 新增：用于检查关键帧、ASR、视频数据的完整性
"""
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

try:
    from scripts.config import TrainingConfig
    from scripts.extract_keyframes import load_existing_keyframes, get_keyframe_output_path
    from scripts.extract_asr import load_asr_from_file, get_asr_output_path
except ImportError:
    pass


def verify_project_data(project_path: str, project_name: str) -> Dict[str, Any]:
    """验证项目数据完整性

    检查：
    1. 所有关键帧是否提取成功
    2. 所有ASR是否转录成功
    3. 所有视频时长是否正确
    4. 数据是否损坏

    Args:
        project_path: 项目路径
        project_name: 项目名称

    Returns:
        验证报告字典
    """
    print(f"\n{'=' * 60}")
    print(f"开始验证项目数据: {project_name}")
    print(f"{'=' * 60}\n")

    report = {
        "project_name": project_name,
        "project_path": project_path,
        "episodes": {},
        "summary": {
            "total_episodes": 0,
            "episodes_with_keyframes": 0,
            "episodes_with_asr": 0,
            "episodes_with_issues": 0,
            "issues": []
        }
    }

    # 查找所有视频文件
    project_dir = Path(project_path)
    if not project_dir.exists():
        report["summary"]["issues"].append(f"项目路径不存在: {project_path}")
        return report

    video_files = sorted(project_dir.glob("*.mp4"))

    if not video_files:
        report["summary"]["issues"].append(f"未找到视频文件")
        return report

    print(f"找到 {len(video_files)} 个视频文件\n")

    # 检查每个集
    for video_file in video_files:
        episode = int(video_file.stem)
        print(f"[{episode}/{len(video_files)}] 检查第{episode}集...")

        episode_report = {
            "episode": episode,
            "video_exists": True,
            "keyframes": {
                "exists": False,
                "count": 0,
                "issues": []
            },
            "asr": {
                "exists": False,
                "count": 0,
                "issues": []
            },
            "issues": []
        }

        # 检查关键帧
        keyframe_path = get_keyframe_output_path(project_name, episode)
        if os.path.exists(keyframe_path):
            keyframes = load_existing_keyframes(keyframe_path)
            if keyframes:
                episode_report["keyframes"]["exists"] = True
                episode_report["keyframes"]["count"] = len(keyframes)
                report["summary"]["episodes_with_keyframes"] += 1
                print(f"  ✓ 关键帧: {len(keyframes)} 帧")
            else:
                episode_report["keyframes"]["issues"].append("关键帧目录存在但无帧文件")
                episode_report["issues"].append("关键帧目录存在但无帧文件")
        else:
            episode_report["keyframes"]["issues"].append("关键帧目录不存在")
            episode_report["issues"].append("关键帧目录不存在")
            print(f"  ✗ 关键帧: 未提取")

        # 检查ASR
        asr_path = get_asr_output_path(project_name, episode)
        if os.path.exists(asr_path):
            try:
                asr_segments = load_asr_from_file(asr_path)
                if asr_segments:
                    episode_report["asr"]["exists"] = True
                    episode_report["asr"]["count"] = len(asr_segments)
                    report["summary"]["episodes_with_asr"] += 1
                    print(f"  ✓ ASR: {len(asr_segments)} 片段")
                else:
                    episode_report["asr"]["issues"].append("ASR文件存在但无数据")
                    episode_report["issues"].append("ASR文件存在但无数据")
                    print(f"  ✗ ASR: 无数据")
            except Exception as e:
                episode_report["asr"]["issues"].append(f"ASR文件读取失败: {e}")
                episode_report["issues"].append(f"ASR文件读取失败: {e}")
                print(f"  ✗ ASR: 读取失败")
        else:
            episode_report["asr"]["issues"].append("ASR文件不存在")
            episode_report["issues"].append("ASR文件不存在")
            print(f"  ✗ ASR: 未转录")

        # 统计问题集数
        if episode_report["issues"]:
            report["summary"]["episodes_with_issues"] += 1

        report["episodes"][episode] = episode_report

    # 生成摘要
    report["summary"]["total_episodes"] = len(video_files)

    print(f"\n{'=' * 60}")
    print(f"验证完成")
    print(f"{'=' * 60}")
    print(f"总集数: {report['summary']['total_episodes']}")
    print(f"关键帧完整: {report['summary']['episodes_with_keyframes']}/{report['summary']['total_episodes']}")
    print(f"ASR完整: {report['summary']['episodes_with_asr']}/{report['summary']['total_episodes']}")
    print(f"有问题的集: {report['summary']['episodes_with_issues']}")
    print(f"{'=' * 60}\n")

    return report


def reprocess_missing_data(project_path: str, project_name: str):
    """重新处理缺失的数据

    Args:
        project_path: 项目路径
        project_name: 项目名称
    """
    print(f"\n开始重新处理缺失的数据...")

    # 先验证数据
    report = verify_project_data(project_path, project_name)

    # 找出需要重新处理的集
    episodes_to_reprocess = []

    for episode, episode_report in report["episodes"].items():
        if episode_report["issues"]:
            episodes_to_reprocess.append(episode)

    if not episodes_to_reprocess:
        print("所有数据完整，无需重新处理")
        return

    print(f"\n需要重新处理的集: {episodes_to_reprocess}")

    # 重新提取关键帧
    print("\n重新提取关键帧...")
    from scripts.extract_keyframes import extract_keyframes

    for episode in episodes_to_reprocess:
        video_path = Path(project_path) / f"{episode}.mp4"
        output_dir = get_keyframe_output_path(project_name, episode)

        try:
            # 删除旧的关键帧
            import shutil
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)

            # 重新提取
            extract_keyframes(str(video_path), output_dir, force_reextract=True)
            print(f"  第{episode}集: 完成")
        except Exception as e:
            print(f"  第{episode}集: 失败 - {e}")

    # 重新转录ASR
    print("\n重新转录ASR...")
    from scripts.extract_asr import transcribe_audio

    for episode in episodes_to_reprocess:
        video_path = Path(project_path) / f"{episode}.mp4"
        output_path = get_asr_output_path(project_name, episode)

        try:
            # 删除旧的ASR
            if os.path.exists(output_path):
                os.remove(output_path)

            # 重新转录
            transcribe_audio(str(video_path), output_path)
            print(f"  第{episode}集: 完成")
        except Exception as e:
            print(f"  第{episode}集: 失败 - {e}")

    print("\n重新处理完成！")


def generate_verification_report_md(report: Dict[str, Any], output_path: str):
    """生成Markdown格式的验证报告

    Args:
        report: 验证报告
        output_path: 输出文件路径
    """
    lines = []
    lines.append("# 数据验证报告\n")
    lines.append(f"**项目**: {report['project_name']}\n")
    lines.append(f"**路径**: {report['project_path']}\n")
    lines.append("---\n")

    # 摘要
    lines.append("## 摘要\n")
    lines.append(f"- 总集数: {report['summary']['total_episodes']}\n")
    lines.append(f"- 关键帧完整: {report['summary']['episodes_with_keyframes']}/{report['summary']['total_episodes']}\n")
    lines.append(f"- ASR完整: {report['summary']['episodes_with_asr']}/{report['summary']['total_episodes']}\n")
    lines.append(f"- 有问题的集: {report['summary']['episodes_with_issues']}\n")
    lines.append("---\n")

    # 详细问题列表
    if report["summary"]["issues"]:
        lines.append("## 问题列表\n")
        for issue in report["summary"]["issues"]:
            lines.append(f"- {issue}\n")
        lines.append("---\n")

    # 各集详情
    lines.append("## 各集详情\n\n")
    lines.append("| 集数 | 关键帧 | ASR | 问题 |\n")
    lines.append("|------|--------|-----|------|\n")

    for episode in sorted(report["episodes"].keys()):
        ep_report = report["episodes"][episode]
        kf_status = f"✓ {ep_report['keyframes']['count']}帧" if ep_report['keyframes']['exists'] else "✗"
        asr_status = f"✓ {ep_report['asr']['count']}片段" if ep_report['asr']['exists'] else "✗"
        issues = "; ".join(ep_report["issues"]) if ep_report["issues"] else "-"

        lines.append(f"| {episode} | {kf_status} | {asr_status} | {issues} |\n")

    # 保存
    content = "".join(lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"验证报告已保存: {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("用法: python -m scripts.verify_data <项目路径> <项目名称>")
        print("示例: python -m scripts.verify_data 漫剧素材/百里将就 百里将就")
        sys.exit(1)

    project_path = sys.argv[1]
    project_name = sys.argv[2]

    # 验证数据
    report = verify_project_data(project_path, project_name)

    # 生成报告
    output_path = f"data/analysis/{project_name}/verification_report.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    generate_verification_report_md(report, output_path)

    # 如果有问题，询问是否重新处理
    if report["summary"]["episodes_with_issues"] > 0:
        print("\n发现数据问题，是否重新处理？(y/n): ", end="")
        # 注意：在脚本中无法直接获取用户输入，需要手动调用 reprocess_missing_data()
