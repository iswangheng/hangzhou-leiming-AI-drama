"""
对比AI识别结果与人工标记
"""
import pandas as pd
import json
from pathlib import Path


def parse_excel_time(time_val, max_video_duration=600):
    """解析Excel时间格式

    Excel中可能是 datetime.time 对象或字符串
    max_video_duration: 视频最大时长（秒），用于判断格式
    """
    from datetime import time

    # 如果是 datetime.time 对象
    if isinstance(time_val, time):
        h, m, s = time_val.hour, time_val.minute, time_val.second
        total_seconds = h * 3600 + m * 60 + s

        # 如果总秒数超过视频时长，说明是 MM:SS 格式被误读为 HH:MM:SS
        if total_seconds > max_video_duration:
            return h * 60 + m  # 视为 MM:SS
        else:
            return total_seconds  # 正常的 HH:MM:SS

    # 如果是字符串
    time_str = str(time_val).strip()
    parts = time_str.split(':')

    if len(parts) == 2:
        # MM:SS 格式
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        # HH:MM:SS 格式
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        total_seconds = h * 3600 + m * 60 + s

        # 同样的判断逻辑
        if total_seconds > max_video_duration:
            return h * 60 + m
        else:
            return total_seconds
    return 0


def load_human_markings(excel_path: str):
    """加载人工标记数据"""
    df = pd.read_excel(excel_path)

    markings = {
        'highlights': [],
        'hooks': []
    }

    for idx, row in df.iterrows():
        episode_str = row['集数']
        episode_num = int(episode_str.replace('第', '').replace('集', ''))
        seconds = parse_excel_time(row['时间点'], max_video_duration=600)
        mark_type = row['标记类型']

        marking = {
            'episode': episode_num,
            'episode_str': episode_str,
            'timestamp': parse_excel_time(row['时间点'], max_video_duration=600),
            'type': mark_type
        }

        if mark_type == '高光点':
            markings['highlights'].append(marking)
        else:
            markings['hooks'].append(marking)

    return markings


def load_ai_results(result_path: str):
    """加载AI识别结果"""
    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return {
        'highlights': data.get('highlights', []),
        'hooks': data.get('hooks', []),
        'clips': data.get('clips', [])
    }


def format_time(seconds):
    """格式化时间为 MM:SS"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def find_matches(human_list, ai_list, tolerance=30):
    """查找匹配项

    Args:
        human_list: 人工标记列表
        ai_list: AI识别列表
        tolerance: 时间容差（秒）

    Returns:
        (匹配列表, 未匹配的人工标记, 未匹配的AI识别)
    """
    matches = []
    unmatched_human = []
    unmatched_ai = ai_list.copy()

    for human in human_list:
        human_time = human['timestamp']
        human_ep = human['episode']

        # 查找匹配的AI识别
        matched = None
        for ai in unmatched_ai:
            ai_time = ai['timestamp']
            ai_ep = ai.get('episode', 0)

            # 同一集且时间差在容差范围内
            if human_ep == ai_ep and abs(human_time - ai_time) <= tolerance:
                matched = ai
                break

        if matched:
            matches.append({
                'human': human,
                'ai': matched,
                'time_diff': human_time - matched['timestamp']
            })
            unmatched_ai.remove(matched)
        else:
            unmatched_human.append(human)

    return matches, unmatched_human, unmatched_ai


def print_comparison(human_markings, ai_results):
    """打印对比结果"""
    print("=" * 100)
    print("🎯 AI识别 vs 人工标记 - 对比报告")
    print("=" * 100)
    print()

    # 高光点对比
    print("【高光点对比】")
    print("-" * 100)

    human_highlights = human_markings['highlights']
    ai_highlights = ai_results['highlights']

    # 初始化匹配变量
    hl_matches, hl_unmatched_human, hl_unmatched_ai = [], [], []

    print(f"人工标记: {len(human_highlights)} 个")
    print(f"AI识别: {len(ai_highlights)} 个")
    print()

    if human_highlights:
        hl_matches, hl_unmatched_human, hl_unmatched_ai = find_matches(
            human_highlights, ai_highlights, tolerance=30
        )

        print(f"✅ 匹配: {len(hl_matches)} 个")
        for match in hl_matches:
            h = match['human']
            a = match['ai']
            diff = match['time_diff']
            print(f"   第{h['episode']}集 {format_time(h['timestamp'])} vs {format_time(a['timestamp'])} "
                  f"(差{diff}秒) | 人工:{h.get('type','')} | AI:{a.get('type','')}")

        print(f"\n❌ AI未识别: {len(hl_unmatched_human)} 个")
        for h in hl_unmatched_human:
            print(f"   第{h['episode']}集 {format_time(h['timestamp'])} | {h.get('type','')}")

        print(f"\n🆕 AI新增: {len(hl_unmatched_ai)} 个")
        for a in hl_unmatched_ai:
            print(f"   第{a.get('episode','?')}集 {format_time(a['timestamp'])} | {a.get('type','')}")
    else:
        print("人工没有高光点标记")
        print(f"\nAI识别了 {len(ai_highlights)} 个高光点:")
        for a in ai_highlights:
            print(f"   第{a.get('episode','?')}集 {format_time(a['timestamp'])} | {a.get('type','')}")

    print("\n" + "=" * 100)
    print()

    # 钩子点对比
    print("【钩子点对比】")
    print("-" * 100)

    human_hooks = human_markings['hooks']
    ai_hooks = ai_results['hooks']

    print(f"人工标记: {len(human_hooks)} 个")
    print(f"AI识别: {len(ai_hooks)} 个")
    print()

    if human_hooks:
        hook_matches, hook_unmatched_human, hook_unmatched_ai = find_matches(
            human_hooks, ai_hooks, tolerance=30
        )

        print(f"✅ 匹配: {len(hook_matches)} 个")
        for match in hook_matches:
            h = match['human']
            a = match['ai']
            diff = match['time_diff']
            print(f"   第{h['episode']}集 {format_time(h['timestamp'])} vs {format_time(a['timestamp'])} "
                  f"(差{diff}秒) | 人工:{h.get('type','')} | AI:{a.get('type','')}")

        print(f"\n❌ AI未识别: {len(hook_unmatched_human)} 个")
        for h in hook_unmatched_human:
            print(f"   第{h['episode']}集 {format_time(h['timestamp'])} | {h.get('type','')}")

        print(f"\n🆕 AI新增: {len(hook_unmatched_ai)} 个")
        for a in hook_unmatched_ai:
            print(f"   第{a.get('episode','?')}集 {format_time(a['timestamp'])} | {a.get('type','')}")
    else:
        print("人工没有钩子点标记")
        print(f"\nAI识别了 {len(ai_hooks)} 个钩子点:")
        for a in ai_hooks:
            print(f"   第{a.get('episode','?')}集 {format_time(a['timestamp'])} | {a.get('type','')}")

    print("\n" + "=" * 100)
    print()

    # 统计汇总
    total_human = len(human_markings['highlights']) + len(human_markings['hooks'])
    total_ai = len(ai_results['highlights']) + len(ai_results['hooks'])

    total_matches = len(hl_matches) + len(hook_matches)
    total_unmatched_human = len(hl_unmatched_human) + len(hook_unmatched_human)
    total_unmatched_ai = len(hl_unmatched_ai) + len(hook_unmatched_ai)

    print("【统计汇总】")
    print("-" * 100)
    print(f"人工标记总数: {total_human}")
    print(f"  ├─ 高光点: {len(human_markings['highlights'])} 个")
    print(f"  └─ 钩子点: {len(human_markings['hooks'])} 个")
    print()
    print(f"AI识别总数: {total_ai}")
    print(f"  ├─ 高光点: {len(ai_results['highlights'])} 个")
    print(f"  └─ 钩子点: {len(ai_hooks)} 个")
    print()
    print(f"✅ 匹配数: {total_matches}")
    print(f"❌ AI未识别: {total_unmatched_human}")
    print(f"🆕 AI新增: {total_unmatched_ai}")
    print()

    # 计算准确率
    if total_human > 0:
        recall = total_matches / total_human * 100
        print(f"召回率 (AI识别出人工标记的比例): {recall:.1f}%")

    if total_ai > 0:
        precision = total_matches / total_ai * 100
        print(f"精确率 (AI识别正确的比例): {precision:.1f}%")

    if total_human > 0 and total_ai > 0 and (recall + precision) > 0:
        f1 = 2 * (recall * precision) / (recall + precision)
        print(f"F1分数: {f1:.1f}%")

    print("=" * 100)


def main():
    """主函数"""
    import sys

    if len(sys.argv) < 3:
        print("用法: python compare_results.py <Excel文件> <AI结果JSON>")
        print("示例: python compare_results.py 漫剧素材/百里将就/百里将就.xlsx "
              "data/hangzhou-leiming/analysis/百里将就/result.json")
        sys.exit(1)

    excel_path = sys.argv[1]
    ai_result_path = sys.argv[2]

    # 加载数据
    print("加载人工标记...")
    human_markings = load_human_markings(excel_path)

    print("加载AI识别结果...")
    ai_results = load_ai_results(ai_result_path)

    # 对比并打印
    print_comparison(human_markings, ai_results)


if __name__ == "__main__":
    main()
