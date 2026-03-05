#!/usr/bin/env python3
"""
快速测试新的漫剧素材项目（之前误判的项目）
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from scripts.detect_ending_credits import EndingCreditsDetector

# 测试新的漫剧素材项目（之前全部误判）
test_projects = [
    ('新的漫剧素材/雪烬梨香', False),  # False表示应该无片尾
    ('新的漫剧素材/休书落纸', False),
    ('新的漫剧素材/不晚忘忧', False),
]

detector = EndingCreditsDetector()

print('=' * 100)
print('快速测试：新的漫剧素材项目（验证ASR增强检测是否修正误判）')
print('=' * 100)

for project_path, expected_has_ending in test_projects:
    full_path = Path(project_path)
    if not full_path.exists():
        print(f'⚠️  路径不存在: {project_path}')
        continue

    # 只测试第1集
    video_files = sorted(full_path.glob('*.mp4'), key=lambda x: int(x.stem))
    if not video_files:
        continue

    video_path = str(video_files[0])
    print(f'\n项目: {full_path.name}')
    print(f'视频: {Path(video_path).name}')
    print(f'期望结果: {"无片尾" if not expected_has_ending else "有片尾"}')

    # 执行检测
    result = detector.detect_video_ending(video_path, episode=1)

    actual_has_ending = result.ending_info.has_ending
    status = '✅ 正确' if actual_has_ending == expected_has_ending else '❌ 错误'

    print(f'{status} - 实际结果: {"有片尾" if actual_has_ending else "无片尾"}')
    if actual_has_ending != expected_has_ending:
        print(f'  检测方法: {result.ending_info.method}')
        print(f'  片尾时长: {result.ending_info.duration:.2f}秒')
