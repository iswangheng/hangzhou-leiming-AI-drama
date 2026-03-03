"""
详细对比AI标记和人工标记 - 漫剧素材5个项目
"""
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple

# 项目配置
projects = [
    {
        'name': '再见，心机前夫',
        'excel': '漫剧素材/再见，心机前夫/再见，心机前夫.xlsx',
        'result': 'data/hangzhou-leiming/analysis/再见，心机前夫/result.json'
    },
    {
        'name': '弃女归来嚣张真千金不好惹',
        'excel': '漫剧素材/弃女归来嚣张真千金不好惹/弃女归来：嚣张真千金不好惹.xlsx',
        'result': 'data/hangzhou-leiming/analysis/弃女归来嚣张真千金不好惹/result.json'
    },
    {
        'name': '百里将就',
        'excel': '漫剧素材/百里将就/百里将就.xlsx',
        'result': 'data/hangzhou-leiming/analysis/百里将就/result.json'
    },
    {
        'name': '重生暖宠九爷的小娇妻不好惹',
        'excel': '漫剧素材/重生暖宠九爷的小娇妻不好惹/重生暖宠：九爷的小娇妻不好惹.xlsx',
        'result': 'data/hangzhou-leiming/analysis/重生暖宠九爷的小娇妻不好惹/result.json'
    },
    {
        'name': '小小飞梦',
        'excel': '漫剧素材/小小飞梦/小小飞梦.xlsx',
        'result': 'data/hangzhou-leiming/analysis/小小飞梦/result.json'
    }
]

base_path = Path("/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama")

for project in projects:
    print(f"\n{'='*80}")
    print(f"项目: {project['name']}")
    print(f"{'='*80}")

    try:
        # 加载数据
        df = pd.read_excel(base_path / project['excel'])
        with open(base_path / project['result'], 'r', encoding='utf-8') as f:
            ai_data = json.load(f)

        # 解析人工标记
        human_marks = []
        for _, row in df.iterrows():
            episode_str = str(row.iloc[0]).strip()
            if episode_str.startswith('第'):
                episode = int(episode_str.replace('第', '').replace('集', ''))
            else:
                try:
                    episode = int(episode_str)
                except:
                    continue

            timestamp_str = str(row.iloc[1]).strip()
            try:
                parts = timestamp_str.split(':')
                minutes = int(parts[0])
                seconds = int(parts[1])
                timestamp = minutes * 60 + seconds
            except:
                continue

            mark_type = str(row.iloc[2]).strip() if len(row) > 2 else "钩子"

            human_marks.append({
                'episode': episode,
                'timestamp': timestamp,
                'type': mark_type
            })

        # AI标记
        ai_highlights = ai_data.get('highlights', [])
        ai_hooks = ai_data.get('hooks', [])

        # 分类人工标记
        human_highlights = [m for m in human_marks if '高光' in m['type']]
        human_hooks = [m for m in human_marks if '高光' not in m['type']]

        print(f"\n人工标记: {len(human_marks)}个 (高光{len(human_highlights)} + 钩子{len(human_hooks)})")
        print(f"AI标记: {len(ai_highlights) + len(ai_hooks)}个 (高光{len(ai_highlights)} + 钩子{len(ai_hooks)})")

        # 显示AI标记详情
        print(f"\nAI标记详情:")
        print(f"高光点:")
        for h in ai_highlights[:5]:
            print(f"  第{h.get('episode')}集 {h.get('timestamp')}秒: {h.get('type')} - {h.get('description', '')[:60]}...")
        if len(ai_highlights) > 5:
            print(f"  ... 还有{len(ai_highlights)-5}个")

        print(f"\n钩子点:")
        for h in ai_hooks[:5]:
            print(f"  第{h.get('episode')}集 {h.get('timestamp')}秒: {h.get('type')} - {h.get('description', '')[:60]}...")
        if len(ai_hooks) > 5:
            print(f"  ... 还有{len(ai_hooks)-5}个")

    except Exception as e:
        print(f"\n❌ 加载数据失败: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("数据加载完成，准备进行时间点匹配分析")
print(f"{'='*80}")
