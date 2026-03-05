#!/usr/bin/env python3
"""
批量测试所有项目的片尾检测
"""
import sys
import json
from pathlib import Path

sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

from scripts.detect_ending_credits import detect_project_endings

# 所有8个项目
all_projects = [
    {
        "name": "多子多福，开局就送绝美老婆",
        "path": "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/多子多福，开局就送绝美老婆",
        "category": "晓红姐-3.4剧目",
        "status": "✅ 已测试"
    },
    {
        "name": "欺我年迈抢祖宅，和贫道仙法说吧",
        "path": "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/欺我年迈抢祖宅，和贫道仙法说吧",
        "category": "晓红姐-3.4剧目",
        "status": "待测试"
    },
    {
        "name": "老公成为首富那天我重生了",
        "path": "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/老公成为首富那天我重生了",
        "category": "晓红姐-3.4剧目",
        "status": "待测试"
    },
    {
        "name": "飒爽女友不好惹",
        "path": "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/飒爽女友不好惹",
        "category": "晓红姐-3.4剧目",
        "status": "待测试"
    },
    {
        "name": "雪烬梨香",
        "path": "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/新的漫剧素材/雪烬梨香",
        "category": "新的漫剧素材",
        "status": "待测试"
    },
    {
        "name": "休书落纸",
        "path": "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/新的漫剧素材/休书落纸",
        "category": "新的漫剧素材",
        "status": "待测试"
    },
    {
        "name": "不晚忘忧",
        "path": "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/新的漫剧素材/不晚忘忧",
        "category": "新的漫剧素材",
        "status": "✅ 已测试"
    },
    {
        "name": "恋爱综艺，匹配到心动男友",
        "path": "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/新的漫剧素材/恋爱综艺，匹配到心动男友",
        "category": "新的漫剧素材",
        "status": "待测试"
    },
]

output_dir = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/data/hangzhou-leiming/ending_credits"

print("=" * 100)
print("🎬 批量测试所有项目的片尾检测")
print("=" * 100)

# 筛选需要测试的项目
projects_to_test = [p for p in all_projects if p["status"] == "待测试"]

print(f"\n待测试项目: {len(projects_to_test)}个")
print(f"已测试项目: 2个（多子多福、不晚忘忧）")
print(f"总项目数: {len(all_projects)}个\n")

results = []

for i, project in enumerate(projects_to_test, 1):
    print("=" * 100)
    print(f"[{i}/{len(projects_to_test)}] 测试项目: {project['name']}")
    print(f"分类: {project['category']}")
    print("=" * 100)

    try:
        result = detect_project_endings(
            project_path=project['path'],
            output_dir=output_dir
        )

        if result:
            # 统计
            has_ending = sum(1 for ep in result.episodes if ep.ending_info.has_ending)
            no_ending = sum(1 for ep in result.episodes if not ep.ending_info.has_ending)

            if has_ending > 0:
                avg_duration = sum(ep.ending_info.duration for ep in result.episodes if ep.ending_info.has_ending) / has_ending
            else:
                avg_duration = 0

            project_result = {
                'name': project['name'],
                'category': project['category'],
                'total_episodes': len(result.episodes),
                'has_ending': has_ending,
                'no_ending': no_ending,
                'avg_duration': avg_duration,
                'status': '✅ 完成'
            }

            results.append(project_result)

            print(f"\n✅ {project['name']} 检测完成")
            print(f"   有片尾: {has_ending}集")
            print(f"   无片尾: {no_ending}集")
            if has_ending > 0:
                print(f"   平均片尾时长: {avg_duration:.2f}秒")

    except Exception as e:
        print(f"❌ {project['name']} 检测失败: {e}")
        results.append({
            'name': project['name'],
            'category': project['category'],
            'status': f'❌ 失败: {e}'
        })

# 读取已测试的项目数据
print("\n" + "=" * 100)
print("📊 汇总所有项目结果")
print("=" * 100)

# 添加已测试的项目结果
for project in all_projects:
    if project['status'] == '✅ 已测试':
        result_file = Path(output_dir) / f"{project['name']}_ending_credits.json"
        if result_file.exists():
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            has_ending = sum(1 for ep in data['episodes'] if ep['ending_info']['has_ending'])
            no_ending = sum(1 for ep in data['episodes'] if not ep['ending_info']['has_ending'])

            if has_ending > 0:
                avg_duration = sum(ep['ending_info']['duration'] for ep in data['episodes'] if ep['ending_info']['has_ending']) / has_ending
            else:
                avg_duration = 0

            results.append({
                'name': project['name'],
                'category': project['category'],
                'total_episodes': len(data['episodes']),
                'has_ending': has_ending,
                'no_ending': no_ending,
                'avg_duration': avg_duration,
                'status': '✅ 已测试'
            })

# 打印汇总表
print(f"\n{'项目名称':<40} {'分类':<20} {'集数':<6} {'有片尾':<8} {'无片尾':<8} {'平均片尾时长':<12}")
print("-" * 100)

for r in results:
    if 'avg_duration' in r:
        print(f"{r['name']:<40} {r['category']:<20} {r['total_episodes']:<6} {r['has_ending']:<8} {r['no_ending']:<8} {r['avg_duration']:.2f}秒")
    else:
        print(f"{r['name']:<40} {r['category']:<20} {'失败':<6} {'-':<8} {'-':<8} {'-'}")

print("\n" + "=" * 100)
print("✅ 批量测试完成")
print("=" * 100)
