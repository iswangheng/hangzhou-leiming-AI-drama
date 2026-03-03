"""
提取所有项目的标记数据，用于生成HTML对比页面
"""
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict

def load_human_marks(excel_path: str) -> List[Dict]:
    """从Excel文件加载人工标记"""
    df = pd.read_excel(excel_path)
    marks = []
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

        marks.append({
            'episode': episode,
            'timestamp': timestamp,
            'type': mark_type
        })
    return marks

def format_timestamp(seconds: int) -> str:
    """将秒数转换为 MM:SS 格式"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"

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

all_data = []

for project in projects:
    try:
        # 加载人工标记
        human_marks = load_human_marks(base_path / project['excel'])

        # 加载AI标记
        with open(base_path / project['result'], 'r', encoding='utf-8') as f:
            ai_data = json.load(f)

        ai_highlights = ai_data.get('highlights', [])
        ai_hooks = ai_data.get('hooks', [])

        # 格式化人工标记
        human_formatted = []
        for m in human_marks:
            human_formatted.append({
                'episode': m['episode'],
                'timestamp': format_timestamp(m['timestamp']),
                'type': m['type'],
                'source': '人工'
            })

        # 格式化AI标记
        ai_formatted = []
        for m in ai_highlights:
            ai_formatted.append({
                'episode': m.get('episode'),
                'timestamp': format_timestamp(m.get('timestamp', 0)),
                'type': m.get('type', ''),
                'source': 'AI'
            })

        for m in ai_hooks:
            ai_formatted.append({
                'episode': m.get('episode'),
                'timestamp': format_timestamp(m.get('timestamp', 0)),
                'type': m.get('type', ''),
                'source': 'AI'
            })

        # 按集数和时间戳排序
        human_formatted.sort(key=lambda x: (x['episode'], x['timestamp']))
        ai_formatted.sort(key=lambda x: (x['episode'], x['timestamp']))

        all_data.append({
            'project': project['name'],
            'human_marks': human_formatted,
            'ai_marks': ai_formatted
        })

    except Exception as e:
        print(f"Error processing {project['name']}: {e}")
        import traceback
        traceback.print_exc()

# 输出JSON格式
print(json.dumps(all_data, ensure_ascii=False, indent=2))
