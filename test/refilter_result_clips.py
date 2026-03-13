"""
对已有 result.json 重新应用排序筛选，只保留 top 20 精选剪辑组合

用途：当 result.json 中存有所有笛卡尔积组合（如77个）时，
      重新运行 sort_and_filter_clips 算法，只保留得分最高的 top 20。

用法：
    python test/refilter_result_clips.py data/analysis/烈日重生/result.json
    python test/refilter_result_clips.py data/analysis/烈日重生/result.json --max 10
"""
import json
import sys
import argparse
from pathlib import Path

# 确保能导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.understand.analyze_segment import SegmentAnalysis
from scripts.understand.generate_clips import sort_and_filter_clips


def load_result_json(path: str) -> dict:
    """加载 result.json"""
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def build_segment_analyses(data: dict) -> list:
    """从 result.json 重建 SegmentAnalysis 对象列表"""
    analyses = []

    # 高光点
    for h in data.get('highlights', []):
        sa = SegmentAnalysis(
            episode=h['episode'],
            start_time=0,
            end_time=0,
            is_highlight=True,
            highlight_timestamp=h['timestamp'],
            highlight_type=h.get('type'),
            highlight_desc=h.get('description', ''),
            highlight_confidence=h.get('confidence', 7.0),
            is_hook=False,
            hook_timestamp=0.0,
            hook_type=None,
            hook_desc='',
            hook_confidence=0.0
        )
        analyses.append(sa)

    # 钩子点
    for h in data.get('hooks', []):
        sa = SegmentAnalysis(
            episode=h['episode'],
            start_time=0,
            end_time=0,
            is_highlight=False,
            highlight_timestamp=0.0,
            highlight_type=None,
            highlight_desc='',
            highlight_confidence=0.0,
            is_hook=True,
            hook_timestamp=h['timestamp'],
            hook_type=h.get('type'),
            hook_desc=h.get('description', ''),
            hook_confidence=h.get('confidence', 7.0)
        )
        analyses.append(sa)

    return analyses


def format_timestamp(ts):
    """格式化时间戳"""
    if isinstance(ts, int):
        return ts
    if isinstance(ts, float) and ts.is_integer():
        return int(ts)
    return round(ts, 3)


def main():
    parser = argparse.ArgumentParser(description='对 result.json 重新应用 top-N 排序筛选')
    parser.add_argument('result_path', help='result.json 文件路径')
    parser.add_argument('--max', type=int, default=20, help='最大输出数量（默认20）')
    parser.add_argument('--min', type=int, default=10, help='最小输出数量（默认10）')
    parser.add_argument('--dry-run', action='store_true', help='只预览，不保存')
    args = parser.parse_args()

    result_path = Path(args.result_path)
    if not result_path.exists():
        print(f"❌ 文件不存在: {result_path}")
        sys.exit(1)

    # 加载数据
    data = load_result_json(result_path)
    project_name = data.get('projectName', '未知')
    print(f"项目: {project_name}")
    print(f"原始 clips 数量: {len(data.get('clips', []))}")
    print(f"highlights: {len(data.get('highlights', []))}, hooks: {len(data.get('hooks', []))}")

    # 重建 SegmentAnalysis 对象
    analyses = build_segment_analyses(data)
    highlights = [a for a in analyses if a.is_highlight]
    hooks = [a for a in analyses if a.is_hook]

    # 解析 episodeDurations（key 可能是字符串）
    episode_durations = {
        int(k): v for k, v in data.get('episodeDurations', {}).items()
    }

    print(f"\n运行 sort_and_filter_clips (max_output={args.max}, min_output={args.min})...")
    top_clips = sort_and_filter_clips(
        highlights=highlights,
        hooks=hooks,
        episode_durations=episode_durations,
        max_output=args.max,
        min_output=args.min,
        top_highlights=10,
        top_hooks=10,
        max_same_type=2,
        max_same_episode=2
    )

    print(f"\n✅ 筛选完成: {len(top_clips)} 个精选组合")
    print("\nTop 5 预览:")
    for i, c in enumerate(top_clips[:5]):
        print(f"  [{i+1}] 第{c.episode}集 {c.start:.1f}s → 第{c.hook_episode}集 {c.end:.1f}s "
              f"时长{c.duration:.0f}s [{c.highlight_type} × {c.hook_type}]")

    if args.dry_run:
        print("\n[Dry-run 模式] 未保存")
        return

    # 更新 result.json 中的 clips
    data['clips'] = [c.to_dict() for c in top_clips]
    data['statistics']['totalClips'] = len(top_clips)

    # 写回文件
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存: {result_path}")
    print(f"   clips: {len(data['clips'])} 个（原 {len(data.get('clips', []))} 个）")


if __name__ == '__main__':
    main()
