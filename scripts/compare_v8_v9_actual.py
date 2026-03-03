"""
V8 vs V9 实际测试对比脚本
对比人工标记、V8结果、V9结果
"""
import json
import openpyxl
from typing import List, Dict, Tuple
import os

def load_human_marks_from_excel(excel_path: str) -> List[dict]:
    """从Excel文件加载人工标记"""
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active

    marks = []
    for row in ws.iter_rows(min_row=2, values_only=True):  # 跳过标题行
        if row[0] is None:
            continue

        # 处理集数格式："第1集" -> 1
        episode_str = str(row[0]).strip()
        if episode_str.startswith('第'):
            episode = int(episode_str.replace('第', '').replace('集', ''))
        else:
            episode = int(episode_str)

        timestamp_str = str(row[1]).strip()

        # 解析时间戳 MM:SS:ms 格式 (如 "01:00:00" = 1分钟0秒 = 60秒)
        try:
            parts = timestamp_str.split(':')
            if len(parts) == 3:
                minutes = int(parts[0])
                seconds = int(parts[1])
                # 忽略毫秒 (parts[2])
                timestamp = minutes * 60 + seconds
            else:
                print(f"⚠️  跳过无效时间戳: {timestamp_str}")
                continue
        except:
            print(f"⚠️  跳过无效时间戳: {timestamp_str}")
            continue

        mark_type = str(row[2]).strip() if len(row) > 2 and row[2] else "未知"

        marks.append({
            "episode": episode,
            "timestamp": timestamp,
            "type": mark_type,
            "mark_type": mark_type  # 为了兼容
        })

    return marks

def load_ai_result(project_name: str, version: str) -> dict:
    """加载AI分析结果"""
    if version == "v8":
        path = f"data/hangzhou-leiming/analysis/{project_name}/result.json.v8_backup"
    else:  # v9
        path = f"data/hangzhou-leiming/analysis/{project_name}/result.json"

    if not os.path.exists(path):
        print(f"⚠️  文件不存在: {path}")
        return None

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_matches(human_marks: List[dict], ai_hooks: List[dict], time_window: int = 30) -> List[dict]:
    """查找人工标记和AI标记的匹配

    Args:
        human_marks: 人工标记列表
        ai_hooks: AI钩子标记列表
        time_window: 时间窗口（秒），默认30秒

    Returns:
        匹配列表
    """
    matches = []

    for human_mark in human_marks:
        if human_mark['mark_type'] != '钩子点':
            continue

        human_epi = human_mark['episode']
        human_time = human_mark['timestamp']

        for ai_hook in ai_hooks:
            ai_epi = ai_hook['episode']
            ai_time = ai_hook['timestamp']

            if human_epi != ai_epi:
                continue

            time_diff = abs(human_time - ai_time)
            if time_diff <= time_window:
                matches.append({
                    'episode': human_epi,
                    'human_time': human_time,
                    'ai_time': ai_time,
                    'time_diff': time_diff,
                    'human_type': human_mark['type'],
                    'ai_type': ai_hook['type']
                })
                break  # 每个人工标记只匹配一次

    return matches

def calculate_metrics(human_marks: List[dict], ai_result: dict) -> dict:
    """计算性能指标"""
    if ai_result is None:
        return {
            'human_hooks': 0,
            'ai_hooks': 0,
            'matches': 0,
            'recall': 0.0,
            'precision': 0.0,
            'f1_score': 0.0,
            'interrupt_count': 0,
            'interrupt_pct': 0.0
        }

    human_hooks = [m for m in human_marks if m['mark_type'] == '钩子点']
    ai_hooks = ai_result.get('hooks', [])

    matches = find_matches(human_marks, ai_hooks)

    human_count = len(human_hooks)
    ai_count = len(ai_hooks)
    match_count = len(matches)

    recall = match_count / human_count if human_count > 0 else 0.0
    precision = match_count / ai_count if ai_count > 0 else 0.0
    f1_score = 2 * recall * precision / (recall + precision) if (recall + precision) > 0 else 0.0

    # 统计"对话突然中断"
    interrupt_count = sum(1 for h in ai_hooks if '中断' in h.get('type', ''))
    interrupt_pct = interrupt_count / ai_count * 100 if ai_count > 0 else 0.0

    return {
        'human_hooks': human_count,
        'ai_hooks': ai_count,
        'matches': match_count,
        'recall': recall,
        'precision': precision,
        'f1_score': f1_score,
        'interrupt_count': interrupt_count,
        'interrupt_pct': interrupt_pct
    }

def print_comparison(project_name: str, v8_metrics: dict, v9_metrics: dict, v8_result: dict, v9_result: dict):
    """打印对比结果"""
    print(f"\n{'=' * 80}")
    print(f"项目: {project_name}")
    print('=' * 80)

    # 基本指标对比
    print(f"\n📊 核心指标对比:")
    print(f"{'指标':<20} {'V8':<15} {'V9':<15} {'改善':<15}")
    print('-' * 80)

    metrics_to_show = [
        ('人工钩子数', 'human_hooks', ''),
        ('AI钩子数', 'ai_hooks', 'ai_hooks'),
        ('匹配数', 'matches', 'matches'),
        ('召回率', 'recall', 'recall'),
        ('精确率', 'precision', 'precision'),
        ('F1分数', 'f1_score', 'f1_score'),
    ]

    for label, key, compare_key in metrics_to_show:
        v8_val = v8_metrics[key]
        v9_val = v9_metrics[key]

        if key in ['recall', 'precision', 'f1_score']:
            v8_str = f"{v8_val*100:.1f}%"
            v9_str = f"{v9_val*100:.1f}%"
            diff = (v9_val - v8_val) * 100
            diff_str = f"{'+' if diff >= 0 else ''}{diff:.1f}%" if compare_key else ""
        else:
            v8_str = str(v8_val)
            v9_str = str(v9_val)
            if compare_key:
                diff = v9_val - v8_val
                diff_str = f"{'+' if diff >= 0 else ''}{diff}" if compare_key else ""
            else:
                diff_str = ""

        print(f"{label:<20} {v8_str:<15} {v9_str:<15} {diff_str:<15}")

    # "对话突然中断"对比
    print(f"\n🎯 '对话突然中断'对比:")
    print(f"{'版本':<15} {'数量':<10} {'占比':<10}")
    print('-' * 80)
    print(f"{'V8':<15} {v8_metrics['interrupt_count']:<10} {v8_metrics['interrupt_pct']:.1f}%")
    print(f"{'V9':<15} {v9_metrics['interrupt_count']:<10} {v9_metrics['interrupt_pct']:.1f}%")

    diff_count = v9_metrics['interrupt_count'] - v8_metrics['interrupt_count']
    diff_pct = v9_metrics['interrupt_pct'] - v8_metrics['interrupt_pct']
    print(f"{'改善':<15} {diff_count:+d}个      {diff_pct:+.1f}%")

    # 详细匹配分析
    print(f"\n📋 V8详细匹配:")
    if v8_result:
        v8_hooks = v8_result.get('hooks', [])
        human_hooks = [m for m in load_human_marks_from_excel(f"新的漫剧素材/{project_name}/{project_name}.xlsx") if m['mark_type'] == '钩子点']
        v8_matches = find_matches(human_hooks, v8_hooks)

        if v8_matches:
            for i, m in enumerate(v8_matches, 1):
                print(f"  {i}. 第{m['episode']}集: 人工={m['human_time']}秒, AI={m['ai_time']}秒 (差距{m['time_diff']}秒)")
        else:
            print("  无匹配")

    print(f"\n📋 V9详细匹配:")
    if v9_result:
        v9_hooks = v9_result.get('hooks', [])
        human_hooks = [m for m in load_human_marks_from_excel(f"新的漫剧素材/{project_name}/{project_name}.xlsx") if m['mark_type'] == '钩子点']
        v9_matches = find_matches(human_hooks, v9_hooks)

        if v9_matches:
            for i, m in enumerate(v9_matches, 1):
                print(f"  {i}. 第{m['episode']}集: 人工={m['human_time']}秒, AI={m['ai_time']}秒 (差距{m['time_diff']}秒)")
        else:
            print("  无匹配")

def main():
    print("=" * 80)
    print("V8 vs V9 实际测试对比")
    print("=" * 80)

    projects = ["不晚忘忧", "休书落纸", "恋爱综艺，匹配到心动男友", "雪烬梨香"]

    all_v8_metrics = []
    all_v9_metrics = []

    for project in projects:
        # 加载数据
        excel_path = f"新的漫剧素材/{project}/{project}.xlsx"
        if not os.path.exists(excel_path):
            print(f"⚠️  Excel文件不存在: {excel_path}")
            continue

        human_marks = load_human_marks_from_excel(excel_path)
        v8_result = load_ai_result(project, "v8")
        v9_result = load_ai_result(project, "v9")

        # 计算指标
        v8_metrics = calculate_metrics(human_marks, v8_result)
        v9_metrics = calculate_metrics(human_marks, v9_result)

        all_v8_metrics.append(v8_metrics)
        all_v9_metrics.append(v9_metrics)

        # 打印对比
        print_comparison(project, v8_metrics, v9_metrics, v8_result, v9_result)

    # 汇总统计
    print(f"\n{'=' * 80}")
    print("📊 4个项目汇总对比")
    print('=' * 80)

    print(f"\n{'指标':<20} {'V8':<15} {'V9':<15} {'改善':<15}")
    print('-' * 80)

    # 计算汇总
    total_v8_human = sum(m['human_hooks'] for m in all_v8_metrics)
    total_v9_human = sum(m['human_hooks'] for m in all_v9_metrics)
    total_v8_ai = sum(m['ai_hooks'] for m in all_v8_metrics)
    total_v9_ai = sum(m['ai_hooks'] for m in all_v9_metrics)
    total_v8_matches = sum(m['matches'] for m in all_v8_metrics)
    total_v9_matches = sum(m['matches'] for m in all_v9_metrics)

    total_v8_interrupt = sum(m['interrupt_count'] for m in all_v8_metrics)
    total_v9_interrupt = sum(m['interrupt_count'] for m in all_v9_metrics)

    avg_v8_recall = sum(m['recall'] for m in all_v8_metrics) / len(all_v8_metrics)
    avg_v9_recall = sum(m['recall'] for m in all_v9_metrics) / len(all_v9_metrics)
    avg_v8_precision = sum(m['precision'] for m in all_v8_metrics) / len(all_v8_metrics)
    avg_v9_precision = sum(m['precision'] for m in all_v9_metrics) / len(all_v9_metrics)
    avg_v8_f1 = sum(m['f1_score'] for m in all_v8_metrics) / len(all_v8_metrics)
    avg_v9_f1 = sum(m['f1_score'] for m in all_v9_metrics) / len(all_v9_metrics)

    summary_metrics = [
        ('人工钩子总数', total_v8_human, total_v9_human, False),
        ('AI钩子总数', total_v8_ai, total_v9_ai, True),
        ('总匹配数', total_v8_matches, total_v9_matches, True),
        ('平均召回率', avg_v8_recall, avg_v9_recall, True, '%'),
        ('平均精确率', avg_v8_precision, avg_v9_precision, True, '%'),
        ('平均F1分数', avg_v8_f1, avg_v9_f1, True, ''),
        ('"对话突然中断"总数', total_v8_interrupt, total_v9_interrupt, True),
    ]

    for item in summary_metrics:
        label = item[0]
        v8_val = item[1]
        v9_val = item[2]
        should_compare = item[3]
        format_type = item[4] if len(item) > 4 else ''

        if format_type == '%':
            v8_str = f"{v8_val*100:.1f}%"
            v9_str = f"{v9_val*100:.1f}%"
            diff_str = f"{(v9_val-v8_val)*100:+.1f}%" if should_compare else ""
        elif format_type == '':
            v8_str = f"{v8_val:.3f}"
            v9_str = f"{v9_val:.3f}"
            diff_str = f"{v9_val-v8_val:+.3f}" if should_compare else ""
        else:
            v8_str = str(v8_val)
            v9_str = str(v9_val)
            diff_str = f"{v9_val-v8_val:+d}" if should_compare else ""

        print(f"{label:<20} {v8_str:<15} {v9_str:<15} {diff_str:<15}")

    print(f"\n" + "=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
