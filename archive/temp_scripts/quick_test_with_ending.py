#!/usr/bin/env python3
"""
快速测试晓红姐-3.4剧目项目（应该有片尾的项目）
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from scripts.detect_ending_credits import EndingCreditsDetector

# 测试晓红姐-3.4剧目项目（应该有片尾）
test_projects = [
    ('晓红姐-3.4剧目/多子多福，开局就送绝美老婆', True),  # True表示应该有片尾
    ('晓红姐-3.4剧目/老公成为首富那天我重生了', True),
]

detector = EndingCreditsDetector()

print('=' * 100)
print('快速测试：晓红姐-3.4剧目项目（应该有片尾）')
print('=' * 100)

for project_path, expected_has_ending in test_projects:
    full_path = Path(project_path)
    if not full_path.exists():
        print(f'⚠️  路径不存在: {project_path}')
        continue

    # 只测试第1集和第10集
    video_files = sorted(full_path.glob('*.mp4'), key=lambda x: int(x.stem))
    if not video_files:
        continue

    for video_file in [video_files[0], video_files[-1]]:  # 测试第1集和最后一集
        video_path = str(video_file)
        episode = int(video_file.stem)
        print(f'\n项目: {full_path.name}')
        print(f'视频: 第{episode}集')
        print(f'期望结果: {"有片尾" if expected_has_ending else "无片尾"}')

        # 执行检测
        result = detector.detect_video_ending(video_path, episode=episode)

        actual_has_ending = result.ending_info.has_ending
        status = '✅ 正确' if actual_has_ending == expected_has_ending else '❌ 错误'

        print(f'{status} - 实际结果: {"有片尾" if actual_has_ending else "无片尾"}')
        if actual_has_ending:
            print(f'  检测方法: {result.ending_info.method}')
            print(f'  片尾时长: {result.ending_info.duration:.2f}秒')
            print(f'  有效时长: {result.effective_duration:.2f}秒')
