"""
详细对比AI标记和人工标记
分析时间点匹配情况
"""
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple


def load_human_marks(excel_path: str) -> List[Dict]:
    """从Excel文件加载人工标记

    Args:
        excel_path: Excel文件路径

    Returns:
        人工标记列表，每个标记包含episode, timestamp, type
    """
    df = pd.read_excel(excel_path)

    marks = []
    for _, row in df.iterrows():
        # 解析集数
        episode_str = str(row.iloc[0]).strip()
        if episode_str.startswith('第'):
            episode = int(episode_str.replace('第', '').replace('集', ''))
        else:
            try:
                episode = int(episode_str)
            except:
                continue

        # 解析时间戳 MM:SS:ms 格式
        timestamp_str = str(row.iloc[1]).strip()
        try:
            parts = timestamp_str.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1])
            timestamp = minutes * 60 + seconds  # 转换为秒
        except:
            continue

        # 获取标记类型
        mark_type = str(row.iloc[2]).strip() if len(row) > 2 else "钩子"

        marks.append({
            'episode': episode,
            'timestamp': timestamp,
            'type': mark_type
        })

    return marks


def load_ai_marks(result_path: str) -> Dict:
    """加载AI标记结果

    Args:
        result_path: result.json文件路径

    Returns:
        AI标记字典，包含highlights和hooks
    """
    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data


def compare_marks(human_marks: List[Dict], ai_marks: List[Dict],
                  time_threshold: int = 15) -> Tuple[List, List, List]:
    """对比人工标记和AI标记

    Args:
        human_marks: 人工标记列表
        ai_marks: AI标记列表
        time_threshold: 时间匹配阈值（秒），默认15秒

    Returns:
        (匹配的标记, AI独有标记, 人工独有标记)
    """
    matched = []
    ai_only = []
    human_only = []

    # 标记已匹配的AI标记
    ai_matched_indices = set()

    for i, human_mark in enumerate(human_marks):
        found_match = False
        best_match_idx = None
        best_time_diff = float('inf')

        for j, ai_mark in enumerate(ai_marks):
            if j in ai_matched_indices:
                continue

            # 检查集数是否匹配
            if human_mark['episode'] != ai_mark.get('episode'):
                continue

            # 检查时间差距
            time_diff = abs(human_mark['timestamp'] - ai_mark.get('timestamp', 0))
            if time_diff <= time_threshold and time_diff < best_time_diff:
                best_match_idx = j
                best_time_diff = time_diff
                found_match = True

        if found_match and best_match_idx is not None:
            # 找到匹配
            ai_mark = ai_marks[best_match_idx]
            matched.append({
                'episode': human_mark['episode'],
                'human_timestamp': human_mark['timestamp'],
                'ai_timestamp': ai_mark.get('timestamp'),
                'time_diff': best_time_diff,
                'human_type': human_mark['type'],
                'ai_type': ai_mark.get('type'),
                'ai_description': ai_mark.get('description', '')
            })
            ai_matched_indices.add(best_match_idx)
        else:
            # 未找到匹配
            human_only.append(human_mark)

    # AI独有的标记
    for j, ai_mark in enumerate(ai_marks):
        if j not in ai_matched_indices:
            ai_only.append(ai_mark)

    return matched, ai_only, human_only


def format_timestamp(seconds: int) -> str:
    """格式化时间戳为 MM:SS 格式"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def analyze_project(project_name: str, excel_path: str, result_path: str):
    """分析单个项目的标记对比

    Args:
        project_name: 项目名称
        excel_path: 人工标记Excel路径
        result_path: AI结果JSON路径
    """
    print(f"\n{'='*60}")
    print(f"项目: {project_name}")
    print(f"{'='*60}")

    # 加载标记
    human_marks = load_human_marks(excel_path)
    ai_data = load_ai_marks(result_path)

    # 合并高光点和钩子点
    ai_highlights = ai_data.get('highlights', [])
    ai_hooks = ai_data.get('hooks', [])

    # 分别对比高光点和钩子点
    human_highlights = [m for m in human_marks if '高光' in m['type']]
    human_hooks = [m for m in human_marks if '高光' not in m['type']]

    print(f"\n人工标记: {len(human_marks)}个 (高光{len(human_highlights)} + 钩子{len(human_hooks)})")
    print(f"AI标记: {len(ai_highlights) + len(ai_hooks)}个 (高光{len(ai_highlights)} + 钩子{len(ai_hooks)})")

    # 对比高光点
    print(f"\n{'='*60}")
    print("高光点对比")
    print(f"{'='*60}")
    matched_hl, ai_only_hl, human_only_hl = compare_marks(
        human_highlights, ai_highlights, time_threshold=15
    )

    print(f"\n匹配的高光点: {len(matched_hl)}个")
    if matched_hl:
        for m in matched_hl:
            print(f"  第{m['episode']}集: 人工{format_timestamp(m['human_timestamp'])} "
                  f"vs AI{format_timestamp(m['ai_timestamp'])} "
                  f"(差距{m['time_diff']}秒, {m['ai_type']})")

    print(f"\nAI独有: {len(ai_only_hl)}个")
    if ai_only_hl and len(ai_only_hl) <= 10:
        for m in ai_only_hl[:10]:
            print(f"  第{m.get('episode')}集 {format_timestamp(m.get('timestamp'))}秒: {m.get('type')}")

    print(f"\n人工独有: {len(human_only_hl)}个")
    if human_only_hl:
        for m in human_only_hl:
            print(f"  第{m['episode']}集 {format_timestamp(m['timestamp'])}秒: {m['type']}")

    # 对比钩子点
    print(f"\n{'='*60}")
    print("钩子点对比")
    print(f"{'='*60}")
    matched_hooks, ai_only_hooks, human_only_hooks = compare_marks(
        human_hooks, ai_hooks, time_threshold=15
    )

    print(f"\n匹配的钩子点: {len(matched_hooks)}个")
    if matched_hooks:
        for m in matched_hooks:
            print(f"  第{m['episode']}集: 人工{format_timestamp(m['human_timestamp'])} "
                  f"vs AI{format_timestamp(m['ai_timestamp'])} "
                  f"(差距{m['time_diff']}秒, {m['ai_type']})")

    print(f"\nAI独有: {len(ai_only_hooks)}个")
    if ai_only_hooks and len(ai_only_hooks) <= 10:
        for m in ai_only_hooks[:10]:
            print(f"  第{m.get('episode')}集 {format_timestamp(m.get('timestamp'))}秒: {m.get('type')}")
    elif len(ai_only_hooks) > 10:
        print(f"  (显示前10个)")
        for m in ai_only_hooks[:10]:
            print(f"  第{m.get('episode')}集 {format_timestamp(m.get('timestamp'))}秒: {m.get('type')}")

    print(f"\n人工独有: {len(human_only_hooks)}个")
    if human_only_hooks:
        for m in human_only_hooks:
            print(f"  第{m['episode']}集 {format_timestamp(m['timestamp'])}秒: {m['type']}")

    # 计算指标
    total_human = len(human_marks)
    total_ai = len(ai_highlights) + len(ai_hooks)
    total_matched = len(matched_hl) + len(matched_hooks)

    recall = total_matched / total_human if total_human > 0 else 0
    precision = total_matched / total_ai if total_ai > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\n{'='*60}")
    print("性能指标")
    print(f"{'='*60}")
    print(f"人工标记总数: {total_human}")
    print(f"AI标记总数: {total_ai}")
    print(f"匹配数量: {total_matched}")
    print(f"召回率 (Recall): {recall:.1%} ({total_matched}/{total_human})")
    print(f"精确率 (Precision): {precision:.1%} ({total_matched}/{total_ai})")
    print(f"F1分数: {f1:.3f}")

    return {
        'project_name': project_name,
        'total_human': total_human,
        'total_ai': total_ai,
        'matched': total_matched,
        'recall': recall,
        'precision': precision,
        'f1': f1,
        'matched_details': matched_hl + matched_hooks
    }


def main():
    """主函数"""
    base_path = Path("/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama")

    # 5个项目配置 - 漫剧素材
    projects = [
        {
            'name': '再见，心机前夫',
            'excel': base_path / '漫剧素材/再见，心机前夫/再见，心机前夫.xlsx',
            'result': base_path / 'data/hangzhou-leiming/analysis/再见，心机前夫/result.json'
        },
        {
            'name': '弃女归来嚣张真千金不好惹',
            'excel': base_path / '漫剧素材/弃女归来嚣张真千金不好惹/弃女归来：嚣张真千金不好惹.xlsx',
            'result': base_path / 'data/hangzhou-leiming/analysis/弃女归来嚣张真千金不好惹/result.json'
        },
        {
            'name': '百里将就',
            'excel': base_path / '漫剧素材/百里将就/百里将就.xlsx',
            'result': base_path / 'data/hangzhou-leiming/analysis/百里将就/result.json'
        },
        {
            'name': '重生暖宠九爷的小娇妻不好惹',
            'excel': base_path / '漫剧素材/重生暖宠九爷的小娇妻不好惹/重生暖宠：九爷的小娇妻不好惹.xlsx',
            'result': base_path / 'data/hangzhou-leiming/analysis/重生暖宠九爷的小娇妻不好惹/result.json'
        },
        {
            'name': '小小飞梦',
            'excel': base_path / '漫剧素材/小小飞梦/小小飞梦.xlsx',
            'result': base_path / 'data/hangzhou-leiming/analysis/小小飞梦/result.json'
        }
    ]

    results = []

    for project in projects:
        try:
            result = analyze_project(
                project['name'],
                str(project['excel']),
                str(project['result'])
            )
            results.append(result)
        except Exception as e:
            print(f"\n❌ 分析项目 {project['name']} 失败: {e}")

    # 生成汇总报告
    print(f"\n\n{'='*80}")
    print("汇总报告 - 漫剧素材5个项目")
    print(f"{'='*80}\n")

    for r in results:
        print(f"{r['project_name']}: 召回率={r['recall']:.1%}, "
              f"精确率={r['precision']:.1%}, F1={r['f1']:.3f}")

    # 计算平均指标
    total_human = sum(r['total_human'] for r in results)
    total_ai = sum(r['total_ai'] for r in results)
    total_matched = sum(r['matched'] for r in results)

    avg_recall = total_matched / total_human if total_human > 0 else 0
    avg_precision = total_matched / total_ai if total_ai > 0 else 0
    avg_f1 = 2 * avg_precision * avg_recall / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0

    print(f"\n{'='*80}")
    print("总体平均")
    print(f"{'='*80}")
    print(f"人工标记总数: {total_human}")
    print(f"AI标记总数: {total_ai}")
    print(f"总匹配数: {total_matched}")
    print(f"平均召回率: {avg_recall:.1%}")
    print(f"平均精确率: {avg_precision:.1%}")
    print(f"平均F1分数: {avg_f1:.3f}")


if __name__ == '__main__':
    main()
